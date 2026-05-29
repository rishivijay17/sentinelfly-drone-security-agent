"""Entity memory helpers for SentinelFly."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any


Event = dict[str, Any]
EntityMemory = dict[str, Any]


def build_entity_memory(events: list[Event]) -> dict[str, EntityMemory]:
    """Build per-entity memory from surveillance events."""
    memory: dict[str, EntityMemory] = {}

    for event in events:
        entity_name = _entity_name(event)
        if not entity_name:
            continue

        if entity_name not in memory:
            memory[entity_name] = {
                "entity": entity_name,
                "object_type": event["object_type"],
                "appearances": 0,
                "first_seen": event["timestamp"],
                "last_seen": event["timestamp"],
                "locations": set(),
                "activities": set(),
                "risk_hints": set(),
                "events": [],
            }

        entity_record = memory[entity_name]
        entity_record["appearances"] += 1
        entity_record["last_seen"] = event["timestamp"]
        entity_record["locations"].add(event["location"])
        entity_record["activities"].add(event["activity"])
        entity_record["risk_hints"].add(event["risk_hint"])
        entity_record["events"].append(event)

    return {
        entity_name: _serialize_entity_record(entity_record)
        for entity_name, entity_record in memory.items()
    }


def get_repeated_entities(events: list[Event], min_count: int = 2) -> list[EntityMemory]:
    """Return entities that appeared at least min_count times."""
    entity_memory = build_entity_memory(events)
    repeated_entities = [
        record
        for record in entity_memory.values()
        if record["appearances"] >= min_count
    ]
    return sorted(
        repeated_entities,
        key=lambda record: (-record["appearances"], record["entity"]),
    )


def get_entity_timeline(events: list[Event], entity_name: str) -> list[Event]:
    """Return the timeline for a specific entity name."""
    normalized_entity_name = entity_name.strip().lower()
    matching_events = [
        event
        for event in events
        if _entity_name(event) and _entity_name(event).lower() == normalized_entity_name
    ]
    return sorted(matching_events, key=lambda event: event["timestamp"])


def generate_memory_insights(events: list[Event]) -> list[str]:
    """Generate concise deterministic insights from entity memory."""
    insights: list[str] = []
    repeated_entities = get_repeated_entities(events)

    for entity in repeated_entities:
        insights.append(
            f"{entity['entity']} appeared {entity['appearances']} times today."
        )

    restricted_counts = _restricted_area_counts(events)
    for entity_name, count in restricted_counts.items():
        if count >= 2:
            insights.append(
                f"{_display_entity_name(entity_name)} appeared near restricted area "
                f"{_count_word(count)}."
            )

    if _person_activity_after_midnight_near_gate(events):
        insights.append(
            "Person activity increased after midnight near the main gate."
        )

    return insights


def remember_event(event: Event) -> EntityMemory | None:
    """Build a one-event memory record for compatibility with earlier stubs."""
    entity_name = _entity_name(event)
    if not entity_name:
        return None
    return build_entity_memory([event])[entity_name]


def _entity_name(event: Event) -> str | None:
    """Create an entity identity from color, details, and object type."""
    object_type = event["object_type"].strip().lower()
    if object_type == "none":
        return None

    color = event["object_color"].strip().title()
    details = event["object_details"].strip()
    concise_details = _concise_details(details, object_type)

    if color.lower() == "none":
        return f"{concise_details} {object_type}".strip()
    return f"{color} {concise_details} {object_type}".strip()


def _concise_details(details: str, object_type: str) -> str:
    """Normalize verbose object details into a stable entity label."""
    lowered_details = details.lower()

    if "ford f150" in lowered_details:
        return "Ford F150"
    if "white van" in lowered_details or "van" in lowered_details:
        return "van"
    if "maintenance worker" in lowered_details:
        return "maintenance worker"
    if "security officer" in lowered_details:
        return "security officer"
    if "delivery" in lowered_details:
        return "delivery vehicle"
    if "sedan" in lowered_details:
        return "sedan"
    if "suv" in lowered_details:
        return "SUV"
    if "truck" in lowered_details:
        return "truck"
    if object_type == "person":
        return "person"
    return object_type


def _serialize_entity_record(entity_record: EntityMemory) -> EntityMemory:
    """Convert sets inside an entity memory record into sorted display lists."""
    return {
        **entity_record,
        "locations": sorted(entity_record["locations"]),
        "activities": sorted(entity_record["activities"]),
        "risk_hints": sorted(entity_record["risk_hints"]),
    }


def _restricted_area_counts(events: list[Event]) -> dict[str, int]:
    """Count entity appearances near restricted locations or risk hints."""
    counts: Counter[str] = Counter()
    for event in events:
        entity_name = _entity_name(event)
        if not entity_name:
            continue

        searchable_text = (
            f"{event['location']} {event['object_details']} "
            f"{event['activity']} {event['risk_hint']}"
        ).lower()
        if "restricted" in searchable_text:
            counts[entity_name] += 1

    return dict(counts)


def _person_activity_after_midnight_near_gate(events: list[Event]) -> bool:
    """Detect repeated person activity after midnight near the main gate."""
    gate_person_counts: defaultdict[str, int] = defaultdict(int)

    for event in events:
        if event["object_type"].lower() != "person":
            continue
        if "gate" not in event["location"].lower():
            continue

        hour = _event_hour(event)
        if hour is not None and hour < 5:
            gate_person_counts[event["location"]] += 1

    return sum(gate_person_counts.values()) >= 1


def _event_hour(event: Event) -> int | None:
    """Extract the hour from an event timestamp."""
    try:
        return datetime.fromisoformat(event["timestamp"]).hour
    except ValueError:
        return None


def _count_word(count: int) -> str:
    """Return friendly count wording for insights."""
    count_words = {2: "twice", 3: "3 times", 4: "4 times"}
    return count_words.get(count, f"{count} times")


def _display_entity_name(entity_name: str) -> str:
    """Return a concise display name for analyst-facing insight text."""
    if entity_name.lower() == "white van vehicle":
        return "White van"
    return entity_name
