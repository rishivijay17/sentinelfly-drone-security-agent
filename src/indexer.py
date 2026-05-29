"""Investigation search helpers for SentinelFly."""

from __future__ import annotations

import re
import sqlite3
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src import database

try:
    import chromadb
except ImportError:  # Semantic memory is optional; SQLite search remains available.
    chromadb = None

try:
    from chromadb.utils import embedding_functions
except ImportError:  # Chroma can still attempt its default embedding function.
    embedding_functions = None


SearchResult = dict[str, Any]
VECTOR_COLLECTION_NAME = "sentinelfly_event_memory"
VECTOR_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "chroma"
_vector_index_error: str | None = None


def search_by_keyword(keyword: str) -> list[SearchResult]:
    """Search surveillance events across analyst-facing text fields."""
    clean_keyword = keyword.strip()
    if not clean_keyword:
        return []

    query = """
        SELECT *
        FROM surveillance_events
        WHERE lower(frame_id) LIKE lower(?)
           OR lower(location) LIKE lower(?)
           OR lower(object_type) LIKE lower(?)
           OR lower(object_color) LIKE lower(?)
           OR lower(object_details) LIKE lower(?)
           OR lower(activity) LIKE lower(?)
           OR lower(risk_hint) LIKE lower(?)
        ORDER BY timestamp
    """
    like_value = f"%{clean_keyword}%"
    return _fetch_many(query, (like_value,) * 7)


def search_by_time_range(start_timestamp: str, end_timestamp: str) -> list[SearchResult]:
    """Return events with timestamps inside an inclusive ISO timestamp range."""
    if not start_timestamp or not end_timestamp:
        return []

    return _fetch_many(
        """
        SELECT *
        FROM surveillance_events
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp
        """,
        (start_timestamp, end_timestamp),
    )


def initialize_vector_index() -> Any:
    """Create or return the ChromaDB event memory collection."""
    global _vector_index_error

    if chromadb is None:
        _vector_index_error = "ChromaDB is not installed."
        return None

    try:
        VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))
        embedding_function = _get_embedding_function()
        if embedding_function is None:
            collection = client.get_or_create_collection(name=VECTOR_COLLECTION_NAME)
        else:
            collection = client.get_or_create_collection(
                name=VECTOR_COLLECTION_NAME,
                embedding_function=embedding_function,
            )
        _vector_index_error = None
        return collection
    except Exception as error:
        _vector_index_error = f"Vector memory unavailable: {error}"
        return None


def index_events_semantically(events: list[SearchResult]) -> None:
    """Store surveillance events as semantic documents in ChromaDB."""
    collection = initialize_vector_index()
    if collection is None or not events:
        return

    documents = [_event_document(event) for event in events]
    metadatas = [_event_metadata(event) for event in events]
    ids = [event["frame_id"] for event in events]

    try:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    except Exception as error:
        global _vector_index_error
        _vector_index_error = f"Failed to index semantic event memory: {error}"


def semantic_search_events(query: str, top_k: int = 5) -> list[SearchResult]:
    """Search surveillance events using semantic vector memory with SQLite fallback."""
    clean_query = query.strip()
    if not clean_query:
        return []

    collection = initialize_vector_index()
    if collection is None:
        return search_by_keyword(clean_query)

    try:
        results = collection.query(query_texts=[clean_query], n_results=max(1, top_k))
        frame_ids = results.get("ids", [[]])[0]
        if not frame_ids:
            return search_by_keyword(clean_query)

        events_by_frame = {event["frame_id"]: event for event in database.fetch_all_events()}
        semantic_events = [
            events_by_frame[frame_id]
            for frame_id in frame_ids
            if frame_id in events_by_frame
        ]
        return semantic_events or search_by_keyword(clean_query)
    except Exception as error:
        global _vector_index_error
        _vector_index_error = f"Semantic search unavailable: {error}"
        return search_by_keyword(clean_query)


def reset_vector_index() -> None:
    """Clear the ChromaDB event memory collection without affecting SQLite."""
    global _vector_index_error

    if chromadb is None:
        _vector_index_error = "ChromaDB is not installed."
        return

    try:
        VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))
        try:
            client.delete_collection(VECTOR_COLLECTION_NAME)
        except Exception:
            pass
        _vector_index_error = None
        initialize_vector_index()
    except Exception as error:
        _vector_index_error = f"Failed to reset semantic event memory: {error}"


def get_repeat_entities(min_appearances: int = 2) -> list[dict[str, Any]]:
    """Detect repeated vehicles, people, or notable objects in stored events."""
    events = database.fetch_all_events()
    entity_counter: Counter[str] = Counter()
    examples: dict[str, list[SearchResult]] = {}

    for event in events:
        entity = _entity_label(event)
        if not entity:
            continue
        entity_counter[entity] += 1
        examples.setdefault(entity, []).append(event)

    repeated_entities: list[dict[str, Any]] = []
    for entity, count in entity_counter.most_common():
        if count < min_appearances:
            continue
        repeated_entities.append(
            {
                "entity": entity,
                "appearances": count,
                "summary": f"{entity} appeared {count} times today.",
                "first_seen": examples[entity][0]["timestamp"],
                "last_seen": examples[entity][-1]["timestamp"],
                "locations": ", ".join(
                    sorted({event["location"] for event in examples[entity]})
                ),
            }
        )

    return repeated_entities


def get_incident_context(frame_id: str, window: int = 3) -> dict[str, Any]:
    """Return replay context around a surveillance incident frame."""
    events = database.fetch_all_events()
    normalized_frame_id = frame_id.strip().removeprefix("ALERT-")
    incident_index = next(
        (
            index
            for index, event in enumerate(events)
            if event["frame_id"] == normalized_frame_id
        ),
        None,
    )

    if incident_index is None:
        return {
            "frame_id": normalized_frame_id,
            "incident": None,
            "before": [],
            "after": [],
            "replay_events": [],
            "related_events": [],
            "patterns": [],
            "anomaly_score": 0,
        }

    start_index = max(0, incident_index - window)
    end_index = min(len(events), incident_index + window + 1)
    incident = events[incident_index]
    before = events[start_index:incident_index]
    after = events[incident_index + 1 : end_index]
    replay_events = before + [incident] + after
    related_events = get_related_events(incident["location"], _timeframe_for_event(incident))
    pattern_events = _deduplicate_events(replay_events + related_events)
    patterns = detect_behavioral_patterns(pattern_events)

    return {
        "frame_id": normalized_frame_id,
        "incident": incident,
        "before": before,
        "after": after,
        "replay_events": replay_events,
        "related_events": related_events,
        "patterns": patterns,
        "anomaly_score": _sequence_anomaly_score(replay_events, patterns),
    }


def get_related_events(location: str, timeframe: Any) -> list[SearchResult]:
    """Return events near a location within a timeframe."""
    start_timestamp, end_timestamp = _normalize_timeframe(timeframe)
    if not start_timestamp or not end_timestamp:
        return []

    return _fetch_many(
        """
        SELECT *
        FROM surveillance_events
        WHERE lower(location) LIKE lower(?)
          AND timestamp BETWEEN ? AND ?
        ORDER BY timestamp
        """,
        (f"%{location.strip()}%", start_timestamp, end_timestamp),
    )


def detect_behavioral_patterns(events: list[SearchResult]) -> list[dict[str, Any]]:
    """Detect timeline intelligence patterns across event sequences."""
    ordered_events = sorted(events, key=lambda event: event["timestamp"])
    patterns: list[dict[str, Any]] = []
    entity_events: dict[str, list[SearchResult]] = {}
    restricted_events: list[SearchResult] = []
    late_night_events: list[SearchResult] = []
    suspicious_events: list[SearchResult] = []

    for event in ordered_events:
        entity = _entity_label(event)
        if entity:
            entity_events.setdefault(entity, []).append(event)

        searchable_text = (
            f"{event['location']} {event['activity']} "
            f"{event['object_details']} {event['risk_hint']}"
        ).lower()
        if "restricted" in searchable_text:
            restricted_events.append(event)
        if _is_after_hours(event):
            late_night_events.append(event)
        if _is_suspicious(event):
            suspicious_events.append(event)

    for entity, entity_sequence in entity_events.items():
        locations = {event["location"] for event in entity_sequence}
        is_vehicle_sequence = any(
            event["object_type"].lower() == "vehicle" for event in entity_sequence
        )
        if is_vehicle_sequence and len(entity_sequence) >= 3 and len(locations) >= 2:
            patterns.append(
                _pattern(
                    "repeated vehicle circling",
                    "HIGH",
                    (
                        f"{entity} appeared {len(entity_sequence)} times across "
                        f"{len(locations)} locations."
                    ),
                    entity_sequence,
                    82,
                )
            )

    if len(late_night_events) >= 3:
        patterns.append(
            _pattern(
                "increasing late-night activity",
                "MEDIUM",
                f"{len(late_night_events)} events occurred during after-hours windows.",
                late_night_events,
                68,
            )
        )

    restricted_entities = Counter(
        entity
        for event in restricted_events
        if (entity := _entity_label(event)) is not None
    )
    for entity, count in restricted_entities.items():
        if count >= 2:
            entity_restricted_events = [
                event for event in restricted_events if _entity_label(event) == entity
            ]
            patterns.append(
                _pattern(
                    "repeated restricted-zone approaches",
                    "HIGH",
                    f"{entity} approached restricted zones {count} times.",
                    entity_restricted_events,
                    86,
                )
            )

    if _has_coordinated_suspicious_movement(suspicious_events):
        patterns.append(
            _pattern(
                "coordinated suspicious movement",
                "HIGH",
                "Multiple suspicious events clustered across nearby patrol windows.",
                suspicious_events,
                78,
            )
        )

    if len(late_night_events) >= 2 and len(late_night_events) >= len(ordered_events) / 2:
        patterns.append(
            _pattern(
                "unusual after-hours activity spike",
                "MEDIUM",
                "After-hours activity dominates this replay window.",
                late_night_events,
                72,
            )
        )

    return patterns


def index_event(event: dict[str, Any]) -> None:
    """Store a single event in the investigation database."""
    database.insert_event(event)
    index_events_semantically([event])


def _fetch_many(query: str, parameters: tuple[Any, ...] = ()) -> list[SearchResult]:
    """Run an investigation query and return rows as dictionaries."""
    database.initialize_database()
    try:
        with sqlite3.connect(database.DB_PATH) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(query, parameters)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to search surveillance events: {error}") from error


def _get_embedding_function() -> Any:
    """Return a sentence-transformers embedding function when available."""
    if embedding_functions is None:
        return None

    try:
        return embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
    except Exception:
        return None


def _event_document(event: SearchResult) -> str:
    """Create the searchable semantic document for one event."""
    return (
        f"timestamp: {event['timestamp']} | "
        f"location: {event['location']} | "
        f"object: {event['object_color']} {event['object_details']} "
        f"{event['object_type']} | "
        f"activity: {event['activity']} | "
        f"risk: {event['risk_hint']}"
    )


def _event_metadata(event: SearchResult) -> dict[str, str]:
    """Create Chroma-compatible metadata for one surveillance event."""
    return {
        "frame_id": str(event["frame_id"]),
        "timestamp": str(event["timestamp"]),
        "location": str(event["location"]),
        "object_type": str(event["object_type"]),
        "object_color": str(event["object_color"]),
        "object_details": str(event["object_details"]),
        "activity": str(event["activity"]),
        "risk_hint": str(event["risk_hint"]),
    }


def _entity_label(event: SearchResult) -> str | None:
    """Create a repeat-detection label from event details."""
    if event["object_type"] == "none":
        return None

    details = event["object_details"]
    lowered_details = details.lower()
    color = event["object_color"].title()

    if "ford f150" in lowered_details:
        return f"{color} Ford F150"
    if "maintenance worker" in lowered_details:
        return "Maintenance worker"
    if "delivery" in lowered_details and event["object_type"] == "vehicle":
        return f"{color} delivery vehicle"
    if "white van" in lowered_details:
        return "White van"
    if event["object_type"] == "vehicle":
        vehicle_match = re.search(r"\b(sedan|suv|truck|van|car|vehicle)\b", lowered_details)
        vehicle_type = vehicle_match.group(1).upper() if vehicle_match else "Vehicle"
        return f"{color} {vehicle_type}"
    if event["object_type"] == "person":
        return f"Person in {event['object_color']}"

    return f"{color} {event['object_type']}".strip()


def _timeframe_for_event(event: SearchResult, minutes: int = 120) -> tuple[str, str]:
    """Return a timestamp window centered on an event."""
    timestamp = _parse_timestamp(event["timestamp"])
    if timestamp is None:
        return ("", "")
    start_timestamp = timestamp - timedelta(minutes=minutes)
    end_timestamp = timestamp + timedelta(minutes=minutes)
    return (
        start_timestamp.isoformat(timespec="minutes"),
        end_timestamp.isoformat(timespec="minutes"),
    )


def _normalize_timeframe(timeframe: Any) -> tuple[str, str]:
    """Normalize supported timeframe values into start and end timestamps."""
    if isinstance(timeframe, tuple) and len(timeframe) == 2:
        return str(timeframe[0]), str(timeframe[1])
    if isinstance(timeframe, list) and len(timeframe) == 2:
        return str(timeframe[0]), str(timeframe[1])
    if isinstance(timeframe, dict):
        return str(timeframe.get("start", "")), str(timeframe.get("end", ""))
    return ("", "")


def _deduplicate_events(events: list[SearchResult]) -> list[SearchResult]:
    """Remove duplicate events while preserving replay order."""
    seen_frame_ids: set[str] = set()
    unique_events: list[SearchResult] = []
    for event in events:
        if event["frame_id"] in seen_frame_ids:
            continue
        seen_frame_ids.add(event["frame_id"])
        unique_events.append(event)
    return unique_events


def _pattern(
    pattern_type: str,
    severity: str,
    explanation: str,
    events: list[SearchResult],
    anomaly_score: int,
) -> dict[str, Any]:
    """Build a behavior pattern record."""
    return {
        "pattern": pattern_type,
        "severity": severity,
        "explanation": explanation,
        "frame_ids": [event["frame_id"] for event in events],
        "anomaly_score": anomaly_score,
    }


def _sequence_anomaly_score(
    replay_events: list[SearchResult],
    patterns: list[dict[str, Any]],
) -> int:
    """Score replay anomaly intensity from events and detected patterns."""
    score = 10
    for event in replay_events:
        risk_hint = event["risk_hint"].lower()
        activity = event["activity"].lower()
        location = event["location"].lower()
        if "high" in risk_hint:
            score += 12
        elif "medium" in risk_hint:
            score += 6
        if "restricted" in location or "restricted" in activity:
            score += 8
        if "loiter" in activity or "running" in activity:
            score += 7
        if _is_after_hours(event):
            score += 5

    if patterns:
        score += max(pattern["anomaly_score"] for pattern in patterns) // 4

    return max(0, min(100, score))


def _has_coordinated_suspicious_movement(events: list[SearchResult]) -> bool:
    """Detect clustered suspicious activity across distinct object types."""
    if len(events) < 2:
        return False

    object_types = {event["object_type"] for event in events}
    timestamps = [_parse_timestamp(event["timestamp"]) for event in events]
    valid_timestamps = [timestamp for timestamp in timestamps if timestamp is not None]
    if len(object_types) < 2 or len(valid_timestamps) < 2:
        return False

    return (
        max(valid_timestamps) - min(valid_timestamps)
    ) <= timedelta(hours=3)


def _is_suspicious(event: SearchResult) -> bool:
    """Return True when an event carries suspicious risk language."""
    risk_hint = event["risk_hint"].lower()
    activity = event["activity"].lower()
    return any(
        marker in f"{risk_hint} {activity}"
        for marker in ("medium", "high", "suspicious", "restricted", "after-hours")
    )


def _is_after_hours(event: SearchResult) -> bool:
    """Return True for events in overnight security windows."""
    timestamp = _parse_timestamp(event["timestamp"])
    if timestamp is None:
        return False
    return timestamp.hour >= 22 or timestamp.hour < 5


def _parse_timestamp(value: str) -> datetime | None:
    """Parse an ISO timestamp, returning None for malformed values."""
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
