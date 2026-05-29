"""Local Ollama-powered investigation assistant for SentinelFly."""

from __future__ import annotations

from datetime import datetime
from typing import Any

try:
    from ollama import chat
except ImportError:  # Ollama is optional at runtime; deterministic fallback remains available.
    chat = None

from src import database, indexer


Event = dict[str, Any]
AgentResult = dict[str, Any]

MODEL_NAME = "phi3"


def answer_question(question: str) -> str:
    """Answer an analyst question with the local AI assistant when available."""
    return ask_investigation_question(question)["response"]


def ask_investigation_question(question: str) -> AgentResult:
    """Retrieve relevant events and generate a grounded investigation response."""
    retrieved_events = retrieve_relevant_events(question)
    repeated_entities = indexer.get_repeat_entities()
    deterministic_response = _deterministic_response(
        question,
        retrieved_events,
        repeated_entities,
    )

    if chat is None:
        return {
            "response": deterministic_response,
            "events": retrieved_events,
            "repeated_entities": repeated_entities,
            "retrieval_mode": "Semantic Vector Memory + SQLite Evidence",
            "used_ai": False,
            "error": "Ollama Python client is not installed.",
        }

    prompt = _build_investigation_prompt(question, retrieved_events, repeated_entities)

    try:
        response = chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are SentinelFly, a drone security investigation copilot. "
                        "Use only the provided surveillance evidence. If the evidence "
                        "does not answer the question, say that clearly. Keep responses "
                        "concise and professional."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        return {
            "response": response["message"]["content"].strip(),
            "events": retrieved_events,
            "repeated_entities": repeated_entities,
            "retrieval_mode": "Semantic Vector Memory + SQLite Evidence",
            "used_ai": True,
            "error": None,
        }
    except Exception as error:
        return {
            "response": deterministic_response,
            "events": retrieved_events,
            "repeated_entities": repeated_entities,
            "retrieval_mode": "Semantic Vector Memory + SQLite Evidence",
            "used_ai": False,
            "error": f"Ollama unavailable: {error}",
        }


def generate_replay_insight(
    incident_reference: str,
    replay_context: dict[str, Any],
) -> AgentResult:
    """Generate a grounded AI insight for incident replay context."""
    replay_events = replay_context.get("replay_events", [])
    patterns = replay_context.get("patterns", [])
    deterministic_response = _deterministic_replay_insight(
        incident_reference,
        replay_events,
        patterns,
        replay_context.get("anomaly_score", 0),
    )

    if chat is None:
        return {
            "response": deterministic_response,
            "events": replay_events,
            "patterns": patterns,
            "used_ai": False,
            "error": "Ollama Python client is not installed.",
        }

    prompt = _build_replay_prompt(incident_reference, replay_context)

    try:
        response = chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are SentinelFly, a drone security incident replay analyst. "
                        "Use only the replay evidence and detected patterns provided. "
                        "Do not invent entities, timestamps, locations, or motives. "
                        "Provide one concise investigation insight and mention uncertainty "
                        "when the evidence is limited."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        return {
            "response": response["message"]["content"].strip(),
            "events": replay_events,
            "patterns": patterns,
            "used_ai": True,
            "error": None,
        }
    except Exception as error:
        return {
            "response": deterministic_response,
            "events": replay_events,
            "patterns": patterns,
            "used_ai": False,
            "error": f"Ollama unavailable: {error}",
        }


def retrieve_relevant_events(question: str) -> list[Event]:
    """Retrieve indexed surveillance events relevant to an investigation question."""
    normalized_question = question.strip().lower()
    if not normalized_question:
        return []

    semantic_events = indexer.semantic_search_events(question, top_k=8)
    sqlite_events = _retrieve_sqlite_evidence(normalized_question)
    return _deduplicate_events(semantic_events + sqlite_events)


def _retrieve_sqlite_evidence(normalized_question: str) -> list[Event]:
    """Retrieve deterministic SQLite evidence for known investigation intents."""
    if "suspicious" in normalized_question or "alert" in normalized_question:
        return database.fetch_suspicious_events()

    if "restricted" in normalized_question or "zone" in normalized_question:
        return _deduplicate_events(
            database.fetch_events_by_location("restricted")
            + indexer.search_by_keyword("restricted")
        )

    if "after midnight" in normalized_question or "midnight" in normalized_question:
        return [
            event
            for event in database.fetch_all_events()
            if _event_hour(event) is not None and _event_hour(event) < 5
        ]

    if "highest risk" in normalized_question or "high risk" in normalized_question:
        return database.fetch_suspicious_events()

    if "vehicle" in normalized_question:
        return database.fetch_events_by_object("vehicle")

    if "f150" in normalized_question or "ford" in normalized_question:
        return indexer.search_by_keyword("Ford F150")

    if "van" in normalized_question:
        return indexer.search_by_keyword("van")

    if "gate" in normalized_question:
        return database.fetch_events_by_location("gate")

    keyword = _keyword_from_question(normalized_question)
    return indexer.search_by_keyword(keyword)


def _build_investigation_prompt(
    question: str,
    events: list[Event],
    repeated_entities: list[dict[str, Any]],
) -> str:
    """Build a compact, evidence-grounded investigation prompt."""
    event_lines = [
        (
            f"- {event['frame_id']} | {event['timestamp']} | {event['location']} | "
            f"{event['object_type']} {event['object_color']} | {event['activity']} | "
            f"{event['object_details']} | risk: {event['risk_hint']}"
        )
        for event in events[:20]
    ]
    repeated_lines = [
        (
            f"- {entity['entity']} | appearances: {entity['appearances']} | "
            f"locations: {entity['locations']}"
        )
        for entity in repeated_entities[:10]
    ]

    return (
        f"Question: {question}\n\n"
        "Retrieved surveillance events:\n"
        f"{chr(10).join(event_lines) if event_lines else '- No matching events retrieved.'}\n\n"
        "Repeated entities:\n"
        f"{chr(10).join(repeated_lines) if repeated_lines else '- No repeated entities detected.'}\n\n"
        "Answer using only this evidence. Mention frame IDs when useful."
    )


def _build_replay_prompt(
    incident_reference: str,
    replay_context: dict[str, Any],
) -> str:
    """Build a grounded prompt for incident replay analysis."""
    replay_events = replay_context.get("replay_events", [])
    patterns = replay_context.get("patterns", [])
    event_lines = [
        (
            f"- {event['frame_id']} | {event['timestamp']} | {event['location']} | "
            f"{event['object_type']} {event['object_color']} | {event['activity']} | "
            f"{event['object_details']} | risk: {event['risk_hint']}"
        )
        for event in replay_events
    ]
    pattern_lines = [
        (
            f"- {pattern['pattern']} | severity: {pattern['severity']} | "
            f"score: {pattern['anomaly_score']} | frames: {pattern['frame_ids']} | "
            f"{pattern['explanation']}"
        )
        for pattern in patterns
    ]

    return (
        f"Incident reference: {incident_reference}\n"
        f"Replay anomaly score: {replay_context.get('anomaly_score', 0)}\n\n"
        "Replay events:\n"
        f"{chr(10).join(event_lines) if event_lines else '- No replay events found.'}\n\n"
        "Detected behavioral patterns:\n"
        f"{chr(10).join(pattern_lines) if pattern_lines else '- No patterns detected.'}\n\n"
        "Produce one concise investigation insight grounded only in this evidence."
    )


def _deterministic_response(
    question: str,
    events: list[Event],
    repeated_entities: list[dict[str, Any]],
) -> str:
    """Generate a concise deterministic fallback response."""
    normalized_question = question.strip().lower()

    if ("f150" in normalized_question or "ford" in normalized_question) and repeated_entities:
        ford_repeats = [
            entity
            for entity in repeated_entities
            if "ford f150" in entity["entity"].lower()
        ]
        if ford_repeats:
            primary = ford_repeats[0]
            return (
                f"Yes. {primary['summary']} Locations: "
                f"{primary['locations']}."
            )

    if "highest risk" in normalized_question and events:
        location_counts: dict[str, int] = {}
        for event in events:
            location_counts[event["location"]] = location_counts.get(event["location"], 0) + 1
        highest_location = max(location_counts, key=location_counts.get)
        return (
            f"{highest_location} had the highest retrieved risk activity, "
            f"with {location_counts[highest_location]} matching events."
        )

    if "vehicle" in normalized_question:
        return f"Found {len(events)} vehicle-related events in the indexed surveillance data."

    if "restricted" in normalized_question or "zone" in normalized_question:
        return f"Found {len(events)} events associated with restricted zones."

    if "midnight" in normalized_question:
        return f"Found {len(events)} events after midnight in the indexed surveillance data."

    if "suspicious" in normalized_question:
        return f"Found {len(events)} suspicious events requiring analyst review."

    return f"Found {len(events)} matching events in the indexed surveillance data."


def _deterministic_replay_insight(
    incident_reference: str,
    events: list[Event],
    patterns: list[dict[str, Any]],
    anomaly_score: int,
) -> str:
    """Generate a deterministic fallback replay insight."""
    if patterns:
        top_pattern = max(patterns, key=lambda pattern: pattern["anomaly_score"])
        return (
            f"{incident_reference} shows {top_pattern['pattern']} with an anomaly "
            f"score of {anomaly_score}. {top_pattern['explanation']}"
        )
    if events:
        incident_event = next(
            (
                event
                for event in events
                if event["frame_id"] in incident_reference
            ),
            events[len(events) // 2],
        )
        return (
            f"{incident_reference} has an anomaly score of {anomaly_score}. "
            f"The replay centers on {incident_event['activity']} at "
            f"{incident_event['location']}."
        )
    return f"No replay evidence was available for {incident_reference}."


def _keyword_from_question(question: str) -> str:
    """Pick a stable search keyword from a natural-language question."""
    keyword_map = {
        "f150": "Ford F150",
        "ford": "Ford F150",
        "van": "van",
        "gate": "gate",
        "loiter": "loiter",
        "running": "running",
        "fence": "fence",
        "delivery": "delivery",
        "maintenance": "maintenance",
        "parking": "parking",
        "vehicle": "vehicle",
        "person": "person",
        "restricted": "restricted",
    }
    for token, keyword in keyword_map.items():
        if token in question:
            return keyword
    return question.strip("?.!")


def _deduplicate_events(events: list[Event]) -> list[Event]:
    """Remove duplicate event rows while preserving order."""
    seen_frame_ids: set[str] = set()
    unique_events: list[Event] = []
    for event in events:
        if event["frame_id"] in seen_frame_ids:
            continue
        seen_frame_ids.add(event["frame_id"])
        unique_events.append(event)
    return unique_events


def _event_hour(event: Event) -> int | None:
    """Extract the hour from an event timestamp."""
    try:
        return datetime.fromisoformat(event["timestamp"]).hour
    except ValueError:
        return None
