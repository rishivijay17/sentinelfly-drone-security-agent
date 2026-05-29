"""Deterministic daily security briefing generation for SentinelFly."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

try:
    from ollama import chat
except ImportError:  # Ollama is optional at runtime; deterministic fallback remains available.
    chat = None

from src import memory


Event = dict[str, Any]
Alert = dict[str, Any]
Briefing = dict[str, Any]
MODEL_NAME = "phi3"


def generate_daily_summary(events: list[Event], alerts: list[Alert]) -> Briefing:
    """Generate a structured daily security briefing."""
    risk_overview = generate_risk_overview(alerts)
    location_insights = generate_location_insights(events)
    behavioral_patterns = generate_behavioral_patterns(events)
    repeated_entities = memory.get_repeated_entities(events)
    suspicious_events = _suspicious_events(events)

    executive_summary = [
        f"A total of {len(events)} surveillance events were recorded today.",
        (
            f"{len(suspicious_events)} suspicious events and "
            f"{risk_overview['critical_alerts']} critical alerts were identified."
        ),
    ]

    if risk_overview["after_midnight_high_risk"]:
        executive_summary.append(
            f"{risk_overview['after_midnight_high_risk']} high-risk incidents "
            "occurred after midnight."
        )

    key_incidents = [
        (
            f"{alert['severity']} alert at {alert['location']} "
            f"({alert['timestamp']}): {alert['alert_message']}"
        )
        for alert in sorted(
            alerts,
            key=lambda alert: (-alert["threat_score"], alert["timestamp"]),
        )[:5]
    ]

    repeated_entity_insights = [
        f"{entity['entity']} appeared {entity['appearances']} times today."
        for entity in repeated_entities
    ]

    recommended_actions = _recommended_actions(
        alerts,
        location_insights["high_risk_locations"],
        repeated_entities,
    )

    return {
        "executive_summary": executive_summary,
        "risk_overview": risk_overview,
        "key_incidents": key_incidents,
        "high_risk_areas": location_insights["high_risk_locations"],
        "location_insights": location_insights["insights"],
        "behavioral_patterns": behavioral_patterns,
        "repeated_entity_insights": repeated_entity_insights,
        "recommended_actions": recommended_actions,
    }


def generate_ai_security_briefing(events: list[Event], alerts: list[Alert]) -> dict[str, Any]:
    """Generate an Ollama-powered briefing grounded in deterministic evidence."""
    deterministic_briefing = generate_daily_summary(events, alerts)
    fallback_text = _format_deterministic_briefing(deterministic_briefing)

    if chat is None:
        return {
            "briefing": fallback_text,
            "deterministic_briefing": deterministic_briefing,
            "used_ai": False,
            "error": "Ollama Python client is not installed.",
        }

    prompt = _build_briefing_prompt(deterministic_briefing)

    try:
        response = chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are SentinelFly, a local drone security briefing copilot. "
                        "Write a professional daily security briefing using only the "
                        "provided deterministic evidence. Do not invent incidents, "
                        "counts, locations, entities, or recommendations."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        return {
            "briefing": response["message"]["content"].strip(),
            "deterministic_briefing": deterministic_briefing,
            "used_ai": True,
            "error": None,
        }
    except Exception as error:
        return {
            "briefing": fallback_text,
            "deterministic_briefing": deterministic_briefing,
            "used_ai": False,
            "error": f"Ollama unavailable: {error}",
        }


def generate_risk_overview(alerts: list[Alert]) -> dict[str, Any]:
    """Summarize alert severity and timing."""
    severity_counts = Counter(alert["severity"] for alert in alerts)
    after_midnight_high_risk = [
        alert
        for alert in alerts
        if alert["severity"] in {"HIGH", "CRITICAL"}
        and _event_hour(alert) is not None
        and _event_hour(alert) < 5
    ]

    return {
        "total_alerts": len(alerts),
        "low_alerts": severity_counts["LOW"],
        "medium_alerts": severity_counts["MEDIUM"],
        "high_alerts": severity_counts["HIGH"],
        "critical_alerts": severity_counts["CRITICAL"],
        "after_midnight_high_risk": len(after_midnight_high_risk),
    }


def generate_location_insights(events: list[Event]) -> dict[str, Any]:
    """Identify high-risk locations and notable location patterns."""
    risk_by_location: Counter[str] = Counter()
    event_count_by_location: Counter[str] = Counter(event["location"] for event in events)
    insights: list[str] = []

    for event in events:
        risk_hint = event["risk_hint"].lower()
        if "high" in risk_hint:
            risk_by_location[event["location"]] += 2
        elif "medium" in risk_hint:
            risk_by_location[event["location"]] += 1
        if "restricted" in f"{event['location']} {event['risk_hint']}".lower():
            risk_by_location[event["location"]] += 1

    high_risk_locations = [
        {
            "location": location,
            "risk_weight": risk_weight,
            "event_count": event_count_by_location[location],
        }
        for location, risk_weight in risk_by_location.most_common()
        if risk_weight >= 2
    ]

    for location in ("Main gate", "Restricted area perimeter", "North fence line"):
        if event_count_by_location[location]:
            insights.append(
                f"{location} recorded {event_count_by_location[location]} events today."
            )

    return {
        "high_risk_locations": high_risk_locations,
        "insights": insights,
    }


def generate_behavioral_patterns(events: list[Event]) -> list[str]:
    """Generate deterministic behavior and timing observations."""
    patterns: list[str] = []
    events_by_location_hour: defaultdict[tuple[str, int], int] = defaultdict(int)

    for event in events:
        hour = _event_hour(event)
        if hour is None:
            continue
        events_by_location_hour[(event["location"], hour)] += 1

    main_gate_after_midnight = sum(
        count
        for (location, hour), count in events_by_location_hour.items()
        if location == "Main gate" and 0 <= hour <= 2
    )
    if main_gate_after_midnight:
        patterns.append(
            "The main gate showed increased person activity between 00:00 and 02:00."
        )

    for entity in memory.get_repeated_entities(events):
        if "Ford F150" in entity["entity"] and "Visitor parking" in entity["locations"]:
            patterns.append("Blue Ford F150 appeared repeatedly near visitor parking.")

    restricted_events = [
        event
        for event in events
        if "restricted" in f"{event['location']} {event['risk_hint']}".lower()
    ]
    if restricted_events:
        patterns.append(
            f"{len(restricted_events)} events were associated with restricted areas."
        )

    after_hours_events = [
        event
        for event in events
        if _event_hour(event) is not None
        and (_event_hour(event) >= 22 or _event_hour(event) < 5)
    ]
    if after_hours_events:
        patterns.append(
            f"{len(after_hours_events)} events occurred during after-hours patrol windows."
        )

    return patterns


def _suspicious_events(events: list[Event]) -> list[Event]:
    """Return events with medium or high risk indicators."""
    suspicious_markers = ("medium", "high", "suspicious", "restricted", "after-hours")
    return [
        event
        for event in events
        if any(marker in event["risk_hint"].lower() for marker in suspicious_markers)
    ]


def _recommended_actions(
    alerts: list[Alert],
    high_risk_locations: list[dict[str, Any]],
    repeated_entities: list[dict[str, Any]],
) -> list[str]:
    """Generate operational actions from briefing signals."""
    actions = ["Continue routine drone patrol coverage across low-risk areas."]

    if any(alert["severity"] == "CRITICAL" for alert in alerts):
        actions.append("Escalate critical incidents to the security duty lead.")
    if high_risk_locations:
        actions.append("Increase patrol frequency around high-risk access points.")
    if repeated_entities:
        actions.append("Review repeated entity timelines before shift handoff.")
    if any("fence" in area["location"].lower() for area in high_risk_locations):
        actions.append("Inspect fence-line camera coverage and response readiness.")

    return actions


def _event_hour(item: dict[str, Any]) -> int | None:
    """Extract the hour from an event or alert timestamp."""
    try:
        return datetime.fromisoformat(item["timestamp"]).hour
    except ValueError:
        return None


def _build_briefing_prompt(briefing: Briefing) -> str:
    """Build a grounded prompt for the local daily briefing model."""
    return (
        "Create a concise daily security briefing with these sections:\n"
        "1. Executive Summary\n"
        "2. Suspicious Events\n"
        "3. Repeated Entities\n"
        "4. Critical Alerts\n"
        "5. Operational Recommendations\n\n"
        "Use only the evidence below.\n\n"
        f"Executive summary evidence:\n{_bullet_lines(briefing['executive_summary'])}\n\n"
        f"Key incidents:\n{_bullet_lines(briefing['key_incidents'])}\n\n"
        f"High-risk areas:\n{_area_lines(briefing['high_risk_areas'])}\n\n"
        f"Location insights:\n{_bullet_lines(briefing['location_insights'])}\n\n"
        f"Behavioral patterns:\n{_bullet_lines(briefing['behavioral_patterns'])}\n\n"
        f"Repeated entity insights:\n{_bullet_lines(briefing['repeated_entity_insights'])}\n\n"
        f"Recommended actions:\n{_bullet_lines(briefing['recommended_actions'])}"
    )


def _format_deterministic_briefing(briefing: Briefing) -> str:
    """Format the deterministic briefing as readable fallback text."""
    sections = [
        ("Executive Summary", briefing["executive_summary"]),
        ("Suspicious Events", briefing["key_incidents"]),
        ("Repeated Entities", briefing["repeated_entity_insights"]),
        (
            "Critical Alerts",
            [
                f"{briefing['risk_overview']['critical_alerts']} critical alerts were identified."
            ],
        ),
        ("Operational Recommendations", briefing["recommended_actions"]),
    ]

    formatted_sections: list[str] = []
    for title, items in sections:
        formatted_sections.append(f"{title}\n{_bullet_lines(items)}")
    return "\n\n".join(formatted_sections)


def _bullet_lines(items: list[Any]) -> str:
    """Render a list as bullet lines for prompts and fallback text."""
    if not items:
        return "- None identified."
    return "\n".join(f"- {item}" for item in items)


def _area_lines(areas: list[dict[str, Any]]) -> str:
    """Render high-risk areas as compact evidence lines."""
    if not areas:
        return "- None identified."
    return "\n".join(
        (
            f"- {area['location']} | risk weight: {area['risk_weight']} | "
            f"event count: {area['event_count']}"
        )
        for area in areas
    )
