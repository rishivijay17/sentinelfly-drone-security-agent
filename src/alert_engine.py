"""Deterministic threat scoring and alert generation for SentinelFly."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from typing import Any


Event = dict[str, Any]
Alert = dict[str, Any]


def generate_alerts(events: list[Event]) -> list[Alert]:
    """Generate threat alerts for a batch of surveillance events."""
    repeat_counts = _build_repeat_counts(events)
    alerts: list[Alert] = []

    for event in events:
        alerts.extend(evaluate_alerts(event, repeat_counts))

    return alerts


def evaluate_alerts(
    event: Event, repeat_counts: dict[str, int] | None = None
) -> list[Alert]:
    """Evaluate one event and return alert dictionaries when action is useful."""
    score, explanation_parts = calculate_threat_score(event, repeat_counts or {})

    if not _should_generate_alert(event, score):
        return []

    severity = get_severity(score)
    return [
        {
            "alert_id": f"ALERT-{event['frame_id']}",
            "frame_id": event["frame_id"],
            "timestamp": event["timestamp"],
            "location": event["location"],
            "severity": severity,
            "threat_score": score,
            "alert_message": _alert_message(event, severity),
            "explanation": " ".join(explanation_parts),
            "recommended_action": _recommended_action(severity),
        }
    ]


def calculate_threat_score(
    event: Event, repeat_counts: dict[str, int] | None = None
) -> tuple[int, list[str]]:
    """Calculate a deterministic threat score between 0 and 100."""
    repeat_counts = repeat_counts or {}
    score = 10
    explanation: list[str] = ["Baseline event review started at 10 points."]

    object_type = event["object_type"].lower()
    activity = event["activity"].lower()
    location = event["location"].lower()
    risk_hint = event["risk_hint"].lower()
    timestamp = _parse_timestamp(event["timestamp"])

    if object_type == "person":
        score += 15
        explanation.append("Person detected.")
    elif object_type == "vehicle":
        score += 12
        explanation.append("Vehicle detected.")
    elif object_type == "none":
        score -= 10
        explanation.append("Empty patrol frame reduced risk.")

    activity_adjustments = [
        ("loiter", 30, "Loitering behavior increased risk."),
        ("restricted", 25, "Restricted-area activity increased risk."),
        ("running", 20, "Running behavior increased risk."),
        ("repeated suspicious", 25, "Repeated suspicious appearance increased risk."),
        ("perimeter approach", 30, "Perimeter approach increased risk."),
        ("stationary vehicle", 18, "Stationary vehicle activity increased risk."),
        ("delivery", -8, "Expected delivery activity reduced risk."),
        ("maintenance", -10, "Known maintenance activity reduced risk."),
        ("routine", -8, "Routine activity reduced risk."),
        ("empty patrol", -12, "Empty patrol activity reduced risk."),
    ]
    for keyword, adjustment, reason in activity_adjustments:
        if keyword in activity:
            score += adjustment
            explanation.append(reason)

    location_adjustments = [
        ("restricted", 20, "Sensitive restricted location increased risk."),
        ("main gate", 12, "Main gate access point increased risk."),
        ("fence", 18, "Fence-line location increased risk."),
        ("fuel storage", 18, "Fuel storage perimeter increased risk."),
        ("service road", 8, "Service road location increased risk."),
        ("parking", 3, "Parking area added minor risk."),
    ]
    for keyword, adjustment, reason in location_adjustments:
        if keyword in location:
            score += adjustment
            explanation.append(reason)

    if timestamp and _is_after_hours(timestamp):
        score += 15
        explanation.append("After-hours timestamp increased risk.")
    elif timestamp and _is_low_traffic_hour(timestamp):
        score += 8
        explanation.append("Low-traffic hour increased risk.")

    if "high" in risk_hint:
        score += 25
        explanation.append("High risk hint increased score.")
    elif "medium" in risk_hint:
        score += 12
        explanation.append("Medium risk hint increased score.")
    elif "low" in risk_hint:
        score -= 8
        explanation.append("Low risk hint reduced score.")

    entity = _entity_label(event)
    if entity:
        appearances = repeat_counts.get(entity, 0)
        if appearances >= 3:
            score += 18
            explanation.append(f"{entity} appeared {appearances} times today.")
        elif appearances == 2:
            score += 8
            explanation.append(f"{entity} appeared twice today.")

    normalized_score = max(0, min(100, score))
    explanation.append(f"Final threat score: {normalized_score}.")
    return normalized_score, explanation


def get_severity(threat_score: int) -> str:
    """Map a threat score to a severity level."""
    if threat_score <= 25:
        return "LOW"
    if threat_score <= 50:
        return "MEDIUM"
    if threat_score <= 75:
        return "HIGH"
    return "CRITICAL"


def _should_generate_alert(event: Event, threat_score: int) -> bool:
    """Decide whether an event deserves an analyst-facing alert."""
    if event["object_type"].lower() == "none":
        return False
    return threat_score >= 20 or "low" not in event["risk_hint"].lower()


def _recommended_action(severity: str) -> str:
    """Return a recommended analyst action for a severity level."""
    actions = {
        "LOW": "Continue passive monitoring",
        "MEDIUM": "Notify on-site security",
        "HIGH": "Dispatch security personnel",
        "CRITICAL": "Escalate to emergency contact",
    }
    return actions[severity]


def _alert_message(event: Event, severity: str) -> str:
    """Create a concise alert message."""
    return f"{severity}: {event['activity']} at {event['location']}"


def _build_repeat_counts(events: list[Event]) -> dict[str, int]:
    """Count repeated notable entities across a batch of events."""
    entities = [_entity_label(event) for event in events]
    return dict(Counter(entity for entity in entities if entity))


def _entity_label(event: Event) -> str | None:
    """Create a stable entity label for repeat detection."""
    if event["object_type"].lower() == "none":
        return None

    details = event["object_details"]
    lowered_details = details.lower()
    color = event["object_color"].title()

    if "ford f150" in lowered_details:
        return f"{color} Ford F150"
    if "maintenance worker" in lowered_details:
        return "Maintenance worker"
    if "delivery" in lowered_details and event["object_type"].lower() == "vehicle":
        return f"{color} delivery vehicle"
    if "white van" in lowered_details:
        return "White van"
    if event["object_type"].lower() == "vehicle":
        vehicle_match = re.search(r"\b(sedan|suv|truck|van|car|vehicle)\b", lowered_details)
        vehicle_type = vehicle_match.group(1).upper() if vehicle_match else "Vehicle"
        return f"{color} {vehicle_type}"
    if event["object_type"].lower() == "person":
        return f"Person in {event['object_color']}"

    return f"{color} {event['object_type']}".strip()


def _parse_timestamp(value: str) -> datetime | None:
    """Parse an ISO timestamp, returning None for malformed values."""
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _is_after_hours(timestamp: datetime) -> bool:
    """Return True for late-night and overnight security windows."""
    return timestamp.hour >= 22 or timestamp.hour < 5


def _is_low_traffic_hour(timestamp: datetime) -> bool:
    """Return True for periods with reduced normal site activity."""
    return timestamp.hour < 7 or timestamp.hour >= 20
