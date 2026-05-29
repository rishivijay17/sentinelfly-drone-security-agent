from datetime import datetime
from typing import Any

import streamlit as st

from src import agent, alert_engine, database, indexer, memory, simulator, summarizer


st.set_page_config(
    page_title="SentinelFly",
    page_icon="SF",
    layout="wide",
)


st.markdown(
    """
    <style>
    :root {
        --sf-bg: #0a0a0a;
        --sf-panel: #141414;
        --sf-panel-soft: #1c1b1b;
        --sf-panel-high: #201f1f;
        --sf-border: #262626;
        --sf-border-strong: #353534;
        --sf-text: #e5e2e1;
        --sf-muted: #bbc9cd;
        --sf-dim: #859397;
        --sf-blue: #8aebff;
        --sf-cyan: #2fd9f4;
        --sf-orange: #d98b2b;
        --sf-red: #ffb4ab;
        --sf-red-deep: #93000a;
        --sf-green: #8aebff;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background: var(--sf-bg);
        color: var(--sf-text);
        font-family: Geist, Inter, "Segoe UI", Roboto, Arial, sans-serif;
    }

    [data-testid="stHeader"] {
        background: #141414;
        backdrop-filter: blur(12px);
        border-bottom: 1px solid var(--sf-border);
    }

    [data-testid="stSidebar"] {
        background: #141414;
        border-right: 1px solid var(--sf-border);
    }

    [data-testid="stSidebar"] .block-container {
        padding-top: 0.45rem;
    }

    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: var(--sf-text);
        letter-spacing: 0;
    }

    .block-container {
        width: 100%;
        max-width: none !important;
        padding: 0.75rem 1rem 1.5rem 1rem;
    }

    [data-testid="stMainBlockContainer"],
    [data-testid="stMain"] .block-container,
    .main .block-container {
        width: 100%;
        max-width: none !important;
    }

    .sf-topbar {
        border-bottom: 1px solid var(--sf-border);
        padding: 24px;
        margin-bottom: 28px;
    }

    .sf-topbar-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1.25rem;
        flex-wrap: wrap;
    }

    .sf-brand {
        display: flex;
        align-items: center;
        gap: 0.7rem;
    }

    .sf-logo {
        width: 34px;
        height: 34px;
        border: 1px solid var(--sf-border);
        border-radius: 4px;
        background: #262626;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        color: var(--sf-text);
        font-size: 0.82rem;
        font-weight: 680;
    }

    .sf-brand-text {
        display: flex;
        flex-direction: column;
        gap: 5px;
    }

    .sf-title {
        color: var(--sf-text);
        font-size: 1.28rem;
        font-weight: 600;
        line-height: 1;
        margin: 0;
        padding: 0;
        letter-spacing: 0;
    }

    .sf-subtitle {
        color: var(--sf-muted);
        margin: 0;
        padding: 0;
        font-size: 0.78rem;
        line-height: 1.15;
    }

    .sf-sidebar-controls {
        margin: 0 0 0.55rem 0;
    }

    .sf-sidebar-controls-title {
        color: var(--sf-muted);
        font-size: 0.72rem;
        font-weight: 620;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }

    .sf-chip-row {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.45rem;
        justify-content: flex-end;
    }

    .sf-chip {
        display: inline-flex;
        align-items: center;
        border: 1px solid var(--sf-border-strong);
        color: var(--sf-muted);
        background: #1c1b1b;
        padding: 0.28rem 0.56rem;
        border-radius: 3px;
        font-size: 0.76rem;
        font-weight: 500;
        white-space: nowrap;
    }

    .sf-session-chip {
        color: var(--sf-muted);
        border-color: var(--sf-border);
        background: #141414;
    }

    .sf-chip-active {
        color: var(--sf-blue);
        border-color: rgba(47, 217, 244, 0.42);
        background: rgba(0, 87, 99, 0.22);
    }

    .sf-chip-idle {
        color: var(--sf-muted);
        border-color: var(--sf-border);
        background: #141414;
    }

    .sf-chip-ai {
        color: var(--sf-blue);
        border-color: rgba(47, 217, 244, 0.38);
        background: rgba(0, 87, 99, 0.18);
    }

    h1, h2, h3, h4 {
        color: var(--sf-text);
        letter-spacing: 0;
    }

    h3 {
        margin-top: 1rem;
        padding-top: 0.2rem;
        font-size: 1rem;
        font-weight: 640;
    }

    p, li, span, label, div {
        letter-spacing: 0;
        line-height: 1.5;
    }

    [data-testid="stMetric"] {
        background: var(--sf-panel);
        border: 1px solid var(--sf-border);
        border-radius: 3px;
        padding: 0.65rem 0.78rem;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
    }

    [data-testid="stMetricLabel"] {
        color: var(--sf-muted);
        font-size: 0.78rem;
        font-weight: 560;
    }

    [data-testid="stMetricValue"] {
        color: var(--sf-text);
        font-weight: 680;
        font-size: 1.42rem;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: var(--sf-border) !important;
        background: var(--sf-panel);
        border-radius: 3px;
        padding: 0.42rem;
        box-shadow: 0 10px 24px rgba(0, 0, 0, 0.14);
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid var(--sf-border);
        border-radius: 3px;
        overflow: hidden;
        background: var(--sf-panel);
    }

    .stButton > button {
        border-radius: 7px;
        border: 1px solid var(--sf-border);
        background: #201f1f;
        color: var(--sf-text);
        font-weight: 600;
        box-shadow: none;
        min-height: 2.35rem;
    }

    .stButton > button:hover {
        border-color: var(--sf-border-strong);
        color: #ffffff;
        background: #2a2a2a;
    }

    .stButton > button[kind="primary"] {
        color: var(--sf-blue);
        background: rgba(0, 87, 99, 0.22);
        border-color: rgba(47, 217, 244, 0.48);
        box-shadow: inset 0 1px 0 rgba(47, 217, 244, 0.12);
    }

    .stButton > button[kind="primary"]:hover {
        color: #ffffff;
        background: rgba(0, 87, 99, 0.32);
        border-color: rgba(47, 217, 244, 0.62);
    }

    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        min-height: 2.25rem;
        padding: 0.45rem 0.7rem;
        border-radius: 5px;
    }

    [data-testid="stTextInput"] input,
    [data-testid="stSelectbox"] div,
    [data-testid="stRadio"] label {
        color: var(--sf-text);
    }

    [data-testid="stTextInput"] input {
        background: #141414;
        border: 1px solid var(--sf-border);
        border-radius: 3px;
    }

    .stAlert {
        border-radius: 8px;
    }

    hr {
        border-color: var(--sf-border);
        margin: 0.9rem 0;
    }

    [data-testid="stProgress"] > div > div > div {
        background: linear-gradient(90deg, var(--sf-orange), var(--sf-red));
    }

    .sf-nav-wrap {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.75rem;
        margin: 0.2rem 0 0.55rem;
    }

    .sf-nav-card {
        border: 1px solid var(--sf-border);
        background: var(--sf-panel);
        border-radius: 3px;
        padding: 0.9rem 1rem;
        min-height: 74px;
    }

    .sf-nav-card-active {
        border-color: rgba(47, 217, 244, 0.45);
        background: #201f1f;
    }

    .sf-nav-title {
        color: var(--sf-text);
        font-size: 0.92rem;
        font-weight: 620;
        margin-bottom: 0.22rem;
    }

    .sf-nav-desc {
        color: var(--sf-muted);
        font-size: 0.75rem;
        line-height: 1.4;
    }

    .sf-section-note {
        color: var(--sf-muted);
        font-size: 0.86rem;
        line-height: 1.55;
    }

    .sf-nav-actions {
        margin-bottom: 0.8rem;
    }

    .sf-panel-title {
        color: var(--sf-text);
        font-size: 0.95rem;
        font-weight: 500;
        margin: 0 0 0.35rem 0;
    }

    .sf-panel-copy {
        color: var(--sf-muted);
        font-size: 0.8rem;
        margin-bottom: 0.55rem;
    }

    [data-testid="stHorizontalBlock"] {
        gap: 0.9rem;
    }

    .sf-panel-header {
        border: 1px solid var(--sf-border);
        background: var(--sf-panel-high);
        border-radius: 3px;
        padding: 0.55rem 0.7rem;
        margin: 0.4rem 0 0.65rem 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.75rem;
    }

    .sf-panel-heading {
        color: var(--sf-text);
        font-size: 0.92rem;
        font-weight: 500;
    }

    .sf-panel-kicker {
        color: var(--sf-muted);
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }

    ::-webkit-scrollbar {
        width: 5px;
        height: 5px;
    }

    ::-webkit-scrollbar-track {
        background: #0a0a0a;
    }

    ::-webkit-scrollbar-thumb {
        background: #353534;
        border-radius: 8px;
    }

    @media (max-width: 760px) {
        .sf-title {
            font-size: 1.15rem;
        }
        .sf-chip-row {
            justify-content: flex-start;
        }
        .sf-nav-wrap {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


if "simulation_started" not in st.session_state:
    st.session_state["simulation_started"] = False
if "events" not in st.session_state:
    st.session_state["events"] = []
if "alerts" not in st.session_state:
    st.session_state["alerts"] = []
if "suspicious_events" not in st.session_state:
    st.session_state["suspicious_events"] = []
if "repeated_entities" not in st.session_state:
    st.session_state["repeated_entities"] = []
if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"
if "selected_page" in st.session_state:
    st.session_state.current_page = st.session_state.pop("selected_page")

database_error = st.session_state.get("database_error")
active_events = st.session_state["events"] if st.session_state["simulation_started"] else []
alerts = st.session_state["alerts"] if st.session_state["simulation_started"] else []
suspicious_events = (
    st.session_state["suspicious_events"] if st.session_state["simulation_started"] else []
)
entity_memory = memory.build_entity_memory(active_events) if active_events else {}
memory_repeated_entities = (
    st.session_state["repeated_entities"] if st.session_state["simulation_started"] else []
)
memory_insights = memory.generate_memory_insights(active_events) if active_events else []
daily_briefing = (
    summarizer.generate_daily_summary(active_events, alerts) if active_events else None
)

status_label = "Simulation Active" if st.session_state["simulation_started"] else "Idle"
status_class = "sf-chip-active" if st.session_state["simulation_started"] else "sf-chip-idle"
st.markdown(
    f"""
    <header class="sf-topbar">
        <div class="sf-topbar-row">
            <div class="sf-brand">
                <div class="sf-logo">SF</div>
                <div class="sf-brand-text">
                    <h1 class="sf-title">SentinelFly</h1>
                    <div class="sf-subtitle">Drone Security Analyst Agent</div>
                </div>
            </div>
            <div class="sf-chip-row">
                <span class="sf-chip {status_class}">{status_label}</span>
                <span class="sf-chip">SQLite Indexed Memory</span>
                <span class="sf-chip sf-chip-ai">Local AI: phi3</span>
            </div>
        </div>
    </header>
    """,
    unsafe_allow_html=True,
)


def event_table(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Format stored events for compact Streamlit tables."""
    return [
        {
            "Frame": event["frame_id"],
            "Timestamp": event["timestamp"],
            "Location": event["location"],
            "Object": event["object_type"],
            "Color": event["object_color"],
            "Activity": event["activity"],
            "Risk Hint": event["risk_hint"],
        }
        for event in events
    ]


def memory_table(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Format entity memory records for Streamlit display."""
    return [
        {
            "Entity": entity["entity"],
            "Appearances": entity["appearances"],
            "First Seen": entity["first_seen"],
            "Last Seen": entity["last_seen"],
            "Locations": ", ".join(entity["locations"]),
            "Activities": ", ".join(entity["activities"]),
        }
        for entity in entities
    ]


def high_risk_area_table(areas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Format high-risk area summaries for Streamlit display."""
    return [
        {
            "Location": area["location"],
            "Risk Weight": area["risk_weight"],
            "Event Count": area["event_count"],
        }
        for area in areas
    ]


def pattern_table(patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Format behavioral patterns for Streamlit display."""
    return [
        {
            "Pattern": pattern["pattern"],
            "Severity": pattern["severity"],
            "Anomaly Score": pattern["anomaly_score"],
            "Frames": ", ".join(pattern["frame_ids"]),
            "Explanation": pattern["explanation"],
        }
        for pattern in patterns
    ]


def alert_badge(severity: str) -> str:
    """Return a small HTML severity badge for alert cards."""
    colors = {
        "LOW": "#1f7a4d",
        "MEDIUM": "#b45309",
        "HIGH": "#dc2626",
        "CRITICAL": "#991b1b",
    }
    color = colors.get(severity, "#455a64")
    return (
        f"<span style='background:{color};color:white;padding:0.2rem 0.55rem;"
        f"border-radius:0.35rem;font-size:0.78rem;font-weight:700;'>{severity}</span>"
    )


def severity_rank(severity: str) -> int:
    """Return a numeric rank for sorting alert severity."""
    return {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(severity, 0)


def sorted_alerts(alert_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort alerts by threat score descending."""
    return sorted(
        alert_items,
        key=lambda alert: (alert["threat_score"], alert["timestamp"]),
        reverse=True,
    )


def alert_card(alert: dict[str, Any]) -> None:
    """Render one compact alert card."""
    with st.container(border=True):
        st.markdown(
            f"{alert_badge(alert['severity'])} "
            f"**{alert['alert_id']} - Score {alert['threat_score']}**",
            unsafe_allow_html=True,
        )
        st.write(alert["alert_message"])
        st.caption(f"{alert['timestamp']} | {alert['location']} | {alert['frame_id']}")
        st.write(f"**Explanation:** {alert['explanation']}")
        st.write(f"**Recommended action:** {alert['recommended_action']}")


def replay_card(event: dict[str, Any], phase: str, is_incident: bool = False) -> None:
    """Render one compact event card in an incident replay timeline."""
    threat_score, explanation_parts = alert_engine.calculate_threat_score(event)
    severity = alert_engine.get_severity(threat_score)
    border_label = "Incident" if is_incident else phase

    with st.container(border=True):
        st.markdown(
            f"{alert_badge(severity)} **{border_label}: {event['frame_id']} - "
            f"Score {threat_score}**",
            unsafe_allow_html=True,
        )
        st.write(f"**{event['timestamp']} | {event['location']}**")
        st.write(event["object_details"])
        st.caption(f"{event['activity']} | {event['risk_hint']}")
        if is_incident:
            st.progress(threat_score / 100)
            st.write(f"**Sequence note:** {' '.join(explanation_parts[-3:])}")


def frame_id_from_alert_id(alert_id: str) -> str:
    """Convert ALERT-SF-0001 style identifiers to frame IDs."""
    return alert_id.removeprefix("ALERT-")


def investigate_query(question: str) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    """Return a deterministic assistant response with matching events."""
    normalized_question = question.strip().lower()
    if not normalized_question:
        return (
            "Enter an investigation question to search the indexed surveillance data.",
            [],
            [],
        )

    repeat_entities = indexer.get_repeat_entities()

    if _asks_about_repeats(normalized_question):
        relevant_repeats = _filter_repeat_entities(normalized_question, repeat_entities)
        if relevant_repeats:
            primary_repeat = relevant_repeats[0]
            matching_events = _events_for_repeat_entity(primary_repeat["entity"])
            return (
                f"Yes. {primary_repeat['summary']} Locations: "
                f"{primary_repeat['locations']}.",
                matching_events,
                relevant_repeats,
            )
        return "No repeated entity pattern matched that question.", [], []

    if "suspicious" in normalized_question or "alert" in normalized_question:
        matching_events = database.fetch_suspicious_events()
        return (
            f"Found {len(matching_events)} suspicious events requiring analyst review.",
            matching_events,
            repeat_entities,
        )

    if "restricted" in normalized_question:
        matching_events = _deduplicate_events(
            database.fetch_events_by_location("restricted")
            + indexer.search_by_keyword("restricted")
        )
        return (
            f"Found {len(matching_events)} events near restricted areas.",
            matching_events,
            repeat_entities,
        )

    if "gate" in normalized_question and (
        "midnight" in normalized_question or "after hours" in normalized_question
    ):
        gate_events = database.fetch_events_by_location("gate")
        matching_events = [
            event
            for event in gate_events
            if _event_hour(event) is not None and _event_hour(event) < 5
        ]
        return (
            f"Found {len(matching_events)} gate events after midnight.",
            matching_events,
            repeat_entities,
        )

    if "vehicle" in normalized_question and (
        "entered" in normalized_question
        or "enter" in normalized_question
        or "today" in normalized_question
    ):
        vehicle_events = database.fetch_events_by_object("vehicle")
        matching_events = [
            event
            for event in vehicle_events
            if any(
                term in f"{event['activity']} {event['object_details']}".lower()
                for term in ("enter", "arrival", "appeared", "passes", "parked")
            )
        ]
        vehicle_labels = sorted(
            {
                f"{event['object_color'].title()} {event['object_details']}"
                for event in matching_events
            }
        )
        response = (
            f"Found {len(matching_events)} vehicle events today, including "
            f"{len(vehicle_labels)} distinct vehicle observations."
        )
        return response, matching_events, repeat_entities

    keyword = _keyword_from_question(normalized_question)
    matching_events = indexer.search_by_keyword(keyword)
    return (
        f"Found {len(matching_events)} matching events for '{keyword}'.",
        matching_events,
        repeat_entities if matching_events else [],
    )


def _asks_about_repeats(question: str) -> bool:
    """Detect questions about repeated appearances."""
    return any(term in question for term in ("multiple", "repeat", "repeated", "again"))


def _filter_repeat_entities(
    question: str, repeat_entities: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Filter repeated entities to the specific subject in the question."""
    if "f150" in question or "ford" in question:
        return [
            entity
            for entity in repeat_entities
            if "ford f150" in entity["entity"].lower()
        ]
    if "van" in question:
        return [entity for entity in repeat_entities if "van" in entity["entity"].lower()]
    if "vehicle" in question:
        return [
            entity
            for entity in repeat_entities
            if any(
                term in entity["entity"].lower()
                for term in ("truck", "van", "suv", "car", "vehicle", "f150")
            )
        ]
    return repeat_entities


def _events_for_repeat_entity(entity: str) -> list[dict[str, Any]]:
    """Find events that match a repeated entity label."""
    lowered_entity = entity.lower()
    if "ford f150" in lowered_entity:
        return indexer.search_by_keyword("Ford F150")
    if "white van" in lowered_entity:
        return indexer.search_by_keyword("white van")
    if "maintenance worker" in lowered_entity:
        return indexer.search_by_keyword("maintenance worker")
    return indexer.search_by_keyword(entity)


def _deduplicate_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate event rows while preserving order."""
    seen_frame_ids: set[str] = set()
    unique_events: list[dict[str, Any]] = []
    for event in events:
        if event["frame_id"] in seen_frame_ids:
            continue
        seen_frame_ids.add(event["frame_id"])
        unique_events.append(event)
    return unique_events


def _event_hour(event: dict[str, Any]) -> int | None:
    """Extract the hour from an event timestamp."""
    try:
        return datetime.fromisoformat(event["timestamp"]).hour
    except ValueError:
        return None


def _keyword_from_question(question: str) -> str:
    """Pick a stable search keyword from a natural investigation question."""
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
    }
    for token, keyword in keyword_map.items():
        if token in question:
            return keyword
    return question.strip("?.!")


def clear_dashboard_state() -> None:
    """Return the UI to its empty pre-simulation state."""
    st.session_state["simulation_started"] = False
    st.session_state["events"] = []
    st.session_state["alerts"] = []
    st.session_state["suspicious_events"] = []
    st.session_state["repeated_entities"] = []
    st.session_state["database_error"] = None
    for key in (
        "show_daily_briefing",
        "ai_security_briefing",
        "ai_replay_insight",
        "ai_replay_reference",
    ):
        st.session_state.pop(key, None)


def start_simulation_session() -> None:
    """Generate a fresh simulation, store it, and hydrate session state."""
    try:
        generated_events = simulator.get_all_frames()
        database.reset_database()
        indexer.reset_vector_index()
        database.insert_events(generated_events)
        stored_simulation_events = database.fetch_all_events()
        indexer.index_events_semantically(stored_simulation_events)
        generated_alerts = alert_engine.generate_alerts(stored_simulation_events)

        st.session_state["simulation_started"] = True
        st.session_state["events"] = stored_simulation_events
        st.session_state["alerts"] = generated_alerts
        st.session_state["suspicious_events"] = database.fetch_suspicious_events()
        st.session_state["repeated_entities"] = memory.get_repeated_entities(
            stored_simulation_events
        )
        st.session_state["database_error"] = None
        for key in (
            "show_daily_briefing",
            "ai_security_briefing",
            "ai_replay_insight",
            "ai_replay_reference",
        ):
            st.session_state.pop(key, None)
    except (RuntimeError, ValueError) as error:
        clear_dashboard_state()
        st.session_state["database_error"] = str(error)


def render_top_nav() -> None:
    """Render top-level page navigation as horizontal button cards."""
    pages = [
        ("Dashboard", "Operations overview, feed, telemetry, and alerts"),
        ("Investigation", "Search, assistant, and entity memory"),
        ("Incident Replay", "Timeline context and anomaly progression"),
        ("Security Briefing", "Daily summary and local AI briefing"),
    ]

    st.markdown('<div class="sf-nav-actions">', unsafe_allow_html=True)
    nav_columns = st.columns(4)
    for column, (page_name, _) in zip(nav_columns, pages):
        with column:
            is_current_page = st.session_state.current_page == page_name
            if st.button(
                page_name,
                use_container_width=True,
                key=f"nav_{page_name}",
                type="primary" if is_current_page else "secondary",
            ):
                st.session_state.current_page = page_name
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_metrics() -> None:
    """Render the top operations metrics."""
    metric_columns = st.columns(4)
    metric_columns[0].metric("Total Events", len(active_events))
    metric_columns[1].metric("Alerts Generated", len(alerts))
    metric_columns[2].metric(
        "Critical Alerts",
        len([alert for alert in alerts if alert["severity"] == "CRITICAL"]),
    )
    metric_columns[3].metric("Suspicious Events", len(suspicious_events))


def render_live_feed() -> None:
    """Render the latest simulated drone feed."""
    st.markdown(
        """
        <div class="sf-panel-header">
            <div>
                <div class="sf-panel-heading">Live Drone Feed</div>
                <div class="sf-panel-kicker">Primary sector feed</div>
            </div>
            <div class="sf-chip">Video</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if active_events:
        for frame in active_events[-3:]:
            with st.container(border=True):
                st.markdown(f"**{frame['frame_id']} - {frame['location']}**")
                st.write(frame["object_details"])
                st.caption(
                    f"{frame['timestamp']} | {frame['activity']} | {frame['risk_hint']}"
                )
    else:
        st.info("No live drone feed is active. Click Start Simulation to begin.")


def render_telemetry() -> None:
    """Render telemetry rows."""
    st.markdown(
        """
        <div class="sf-panel-header">
            <div>
                <div class="sf-panel-heading">Telemetry</div>
                <div class="sf-panel-kicker">Position / altitude / speed</div>
            </div>
            <div class="sf-chip">Snapshot</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    telemetry_rows = [
        {
            "Frame": event["frame_id"],
            "Timestamp": event["timestamp"],
            "Location": event["location"],
            "Latitude": event.get("latitude", event.get("telemetry", {}).get("latitude")),
            "Longitude": event.get(
                "longitude", event.get("telemetry", {}).get("longitude")
            ),
            "Altitude": event.get("altitude", event.get("telemetry", {}).get("altitude")),
            "Drone Speed": event.get(
                "drone_speed", event.get("telemetry", {}).get("drone_speed")
            ),
        }
        for event in active_events[-10:]
    ]
    if telemetry_rows:
        st.dataframe(telemetry_rows, use_container_width=True, hide_index=True)
    else:
        st.info("Telemetry will appear after the simulation starts.")


def render_event_timeline() -> None:
    """Render the full simulated event timeline in a compact area."""
    with st.expander("Event Timeline", expanded=False):
        st.write("Full-day simulated event timeline generated by the surveillance engine.")
        if active_events:
            st.dataframe(event_table(active_events), use_container_width=True, hide_index=True)
        else:
            st.info("No event timeline is available yet.")


def render_dashboard_snapshot() -> None:
    """Render compact entity and recent-event monitoring snapshots."""
    st.markdown(
        """
        <div class="sf-panel-header">
            <div>
                <div class="sf-panel-heading">Entity Snapshot / Recent Events</div>
                <div class="sf-panel-kicker">Memory and latest observations</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not active_events:
        st.info("Entity snapshots will appear after the simulation starts.")
        return

    if memory_repeated_entities:
        st.markdown("**Repeated Entities**")
        st.dataframe(
            memory_table(memory_repeated_entities[:5]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No repeated entities detected in the current event set.")

    st.markdown("**Recent Events**")
    st.dataframe(
        event_table(active_events[-6:]),
        use_container_width=True,
        hide_index=True,
    )


def render_alerts_summary() -> None:
    """Render a compact alert summary."""
    st.markdown(
        """
        <div class="sf-panel-header">
            <div>
                <div class="sf-panel-heading">Alerts / Threat Summary</div>
                <div class="sf-panel-kicker">Active priority queue</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if alerts:
        ranked_alerts = sorted_alerts(alerts)
        with st.container(height=390, border=True):
            for alert in ranked_alerts:
                alert_card(alert)
    else:
        st.info("No alerts generated for the current surveillance events.")


def render_dashboard_page() -> None:
    """Render the main operations dashboard page."""
    render_metrics()
    st.divider()

    render_alerts_summary()

    st.divider()
    feed_column, telemetry_column = st.columns([1.25, 1])
    with feed_column:
        render_live_feed()
    with telemetry_column:
        render_telemetry()

    st.divider()
    render_dashboard_snapshot()


def render_investigation_search() -> None:
    """Render indexed search controls and results."""
    st.markdown(
        """
        <div class="sf-panel-header">
            <div>
                <div class="sf-panel-heading">Investigation Search</div>
                <div class="sf-panel-kicker">Indexed evidence retrieval</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    search_column, filter_column, toggle_column = st.columns([2, 1, 1])

    with search_column:
        keyword = st.text_input(
            "Keyword",
            placeholder="Search gate, Ford F150, van, loitering",
            disabled=not active_events,
        )

    with filter_column:
        object_filter = st.selectbox(
            "Object Filter",
            ["All", "vehicle", "person", "none"],
            disabled=not active_events,
        )

    with toggle_column:
        suspicious_only = st.checkbox("Suspicious only", disabled=not active_events)

    if active_events:
        try:
            if keyword:
                search_results = indexer.search_by_keyword(keyword)
            else:
                search_results = active_events

            if object_filter != "All":
                search_results = [
                    event
                    for event in search_results
                    if event["object_type"].lower() == object_filter.lower()
                ]

            if suspicious_only:
                suspicious_ids = {
                    event["frame_id"] for event in database.fetch_suspicious_events()
                }
                search_results = [
                    event
                    for event in search_results
                    if event["frame_id"] in suspicious_ids
                ]

            st.dataframe(
                event_table(search_results),
                use_container_width=True,
                hide_index=True,
            )

            repeat_entities = indexer.get_repeat_entities()
            if repeat_entities:
                st.markdown("**Repeated Entities**")
                st.dataframe(repeat_entities, use_container_width=True, hide_index=True)
        except RuntimeError as error:
            st.error(str(error))
    else:
        st.info("Investigation search will be available after the simulation starts.")


def render_investigation_assistant() -> None:
    """Render the local AI investigation assistant."""
    st.markdown(
        """
        <div class="sf-panel-header">
            <div>
                <div class="sf-panel-heading">Investigation Assistant</div>
                <div class="sf-panel-kicker">Grounded local AI analysis</div>
            </div>
            <div class="sf-chip sf-chip-ai">phi3</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    assistant_question = st.text_input(
        "Investigation question",
        placeholder="Did the Blue Ford F150 appear multiple times?",
        disabled=not active_events,
    )

    if active_events:
        st.caption("Retrieval Mode: Semantic Vector Memory + SQLite Evidence")

    if not active_events:
        st.info("Investigation Assistant will be available after the simulation starts.")
    elif assistant_question:
        try:
            with st.spinner("Generating local AI investigation response with phi3..."):
                ai_investigation = agent.ask_investigation_question(assistant_question)

            assistant_response = ai_investigation["response"]
            assistant_events = ai_investigation["events"]
            assistant_repeats = ai_investigation["repeated_entities"]

            st.caption(f"Retrieved evidence count: {len(assistant_events)}")

            with st.container(border=True):
                st.markdown("**AI-Generated Investigation Response**")
                if not ai_investigation["used_ai"]:
                    st.warning(
                        "Using deterministic investigation fallback. "
                        f"{ai_investigation['error']}"
                    )
                st.write(assistant_response)

            if assistant_events:
                st.markdown("**Matching Events**")
                st.dataframe(
                    event_table(assistant_events),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No matching events found for this investigation question.")

            if assistant_repeats:
                st.markdown("**Repeated Entities**")
                st.dataframe(
                    assistant_repeats,
                    use_container_width=True,
                    hide_index=True,
                )
        except RuntimeError as error:
            st.error(str(error))


def render_entity_memory() -> None:
    """Render entity memory and timelines."""
    st.markdown(
        """
        <div class="sf-panel-header">
            <div>
                <div class="sf-panel-heading">Entity Memory</div>
                <div class="sf-panel-kicker">Repeated appearances and timelines</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if memory_repeated_entities:
        st.markdown("**Repeated Entities**")
        st.dataframe(
            memory_table(memory_repeated_entities),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No repeated entities detected in the current event set.")

    entity_options = sorted(entity_memory.keys())
    if entity_options:
        selected_entity = st.selectbox("Entity Timeline", entity_options)
        selected_timeline = memory.get_entity_timeline(active_events, selected_entity)
        st.dataframe(
            event_table(selected_timeline),
            use_container_width=True,
            hide_index=True,
        )

    if memory_insights:
        st.markdown("**Memory Insights**")
        for insight in memory_insights:
            with st.container(border=True):
                st.write(insight)


def render_investigation_page() -> None:
    """Render investigation tools."""
    render_investigation_search()
    st.divider()
    render_entity_memory()
    st.divider()
    render_investigation_assistant()


def render_incident_replay_page() -> None:
    """Render incident replay and timeline intelligence."""
    st.markdown(
        """
        <div class="sf-panel-header">
            <div>
                <div class="sf-panel-heading">Incident Replay & Timeline Intelligence</div>
                <div class="sf-panel-kicker">Replay context and anomaly progression</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not active_events:
        st.info("Incident replay will be available after the simulation starts.")
        return

    replay_source = st.radio(
        "Replay Source",
        ["Alert", "Frame"],
        horizontal=True,
    )

    selected_frame_id = active_events[0]["frame_id"]
    selected_reference = selected_frame_id

    if replay_source == "Alert" and alerts:
        alert_options = {
            (
                f"{alert['alert_id']} | {alert['severity']} | "
                f"{alert['location']} | score {alert['threat_score']}"
            ): alert
            for alert in alerts
        }
        selected_alert_label = st.selectbox("Select Alert", list(alert_options.keys()))
        selected_alert = alert_options[selected_alert_label]
        selected_frame_id = selected_alert["frame_id"]
        selected_reference = selected_alert["alert_id"]
    elif replay_source == "Alert" and not alerts:
        st.info("No alerts are available. Select a frame for replay.")
        replay_source = "Frame"

    if replay_source == "Frame":
        frame_options = {
            f"{event['frame_id']} | {event['timestamp']} | {event['location']}": event[
                "frame_id"
            ]
            for event in active_events
        }
        selected_frame_label = st.selectbox("Select Frame", list(frame_options.keys()))
        selected_frame_id = frame_options[selected_frame_label]
        selected_reference = selected_frame_id

    replay_context = indexer.get_incident_context(selected_frame_id)
    incident_event = replay_context["incident"]

    if not incident_event:
        st.warning("No replay context found for the selected incident.")
        return

    replay_metrics = st.columns(4)
    replay_metrics[0].metric("Replay Events", len(replay_context["replay_events"]))
    replay_metrics[1].metric("Related Events", len(replay_context["related_events"]))
    replay_metrics[2].metric("Patterns", len(replay_context["patterns"]))
    replay_metrics[3].metric("Anomaly Score", replay_context["anomaly_score"])

    if replay_context["patterns"]:
        st.markdown("**Suspicious Sequence Progression**")
        st.dataframe(
            pattern_table(replay_context["patterns"]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No behavioral escalation pattern detected in this replay window.")

    st.markdown("**Full Timeline Replay**")
    with st.container(height=450, border=True):
        for event in replay_context["before"]:
            replay_card(event, "Before")
        replay_card(incident_event, "Incident", is_incident=True)
        for event in replay_context["after"]:
            replay_card(event, "After")

    if st.button("Generate AI Replay Insight", use_container_width=True):
        with st.spinner("Generating local AI replay insight with phi3..."):
            st.session_state["ai_replay_insight"] = agent.generate_replay_insight(
                selected_reference,
                replay_context,
            )
            st.session_state["ai_replay_reference"] = selected_reference

    ai_replay_insight = st.session_state.get("ai_replay_insight")
    if (
        ai_replay_insight
        and st.session_state.get("ai_replay_reference") == selected_reference
    ):
        st.markdown("**AI-Generated Investigation Insight**")
        if not ai_replay_insight["used_ai"]:
            st.warning(
                f"Using deterministic replay fallback. {ai_replay_insight['error']}"
            )
        with st.container(border=True):
            st.write(ai_replay_insight["response"])


def render_security_briefing_page() -> None:
    """Render deterministic and AI-generated security briefings."""
    st.markdown(
        """
        <div class="sf-panel-header">
            <div>
                <div class="sf-panel-heading">Daily Security Briefing</div>
                <div class="sf-panel-kicker">System evidence and executive synthesis</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not daily_briefing:
        st.info("Start the simulation to review the daily security briefing.")
        return

    st.markdown("**Executive Summary**")
    for item in daily_briefing["executive_summary"]:
        with st.container(border=True):
            st.write(item)

    st.markdown("**Key Incidents**")
    if daily_briefing["key_incidents"]:
        for incident in daily_briefing["key_incidents"]:
            st.write(f"- {incident}")
    else:
        st.write("No key incidents required escalation in this briefing.")

    st.markdown("**High-Risk Areas**")
    if daily_briefing["high_risk_areas"]:
        st.dataframe(
            high_risk_area_table(daily_briefing["high_risk_areas"]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.write("No high-risk areas were identified.")

    if daily_briefing["location_insights"]:
        for insight in daily_briefing["location_insights"]:
            st.write(f"- {insight}")

    st.markdown("**Repeated Entity Insights**")
    if daily_briefing["repeated_entity_insights"]:
        for insight in daily_briefing["repeated_entity_insights"]:
            st.write(f"- {insight}")
    else:
        st.write("No repeated entity patterns were detected.")

    st.markdown("**Behavioral Patterns**")
    for pattern in daily_briefing["behavioral_patterns"]:
        st.write(f"- {pattern}")

    st.markdown("**Recommended Operational Actions**")
    for action in daily_briefing["recommended_actions"]:
        st.write(f"- {action}")

    st.divider()

    if st.button("Generate AI Security Briefing", use_container_width=True):
        if active_events:
            st.session_state["show_daily_briefing"] = True
            with st.spinner("Generating local AI security briefing with phi3..."):
                st.session_state["ai_security_briefing"] = (
                    summarizer.generate_ai_security_briefing(
                        active_events,
                        alerts,
                    )
                )
        else:
            st.warning("Start the simulation before generating a security briefing.")

    ai_security_briefing = st.session_state.get("ai_security_briefing")
    if ai_security_briefing:
        st.markdown("**AI-Generated Security Briefing**")
        if not ai_security_briefing["used_ai"]:
            st.warning(
                f"Using deterministic briefing fallback. {ai_security_briefing['error']}"
            )
        with st.container(border=True):
            st.markdown(ai_security_briefing["briefing"])


def render_sidebar() -> None:
    """Render global simulation controls."""
    with st.sidebar:
        st.markdown(
            """
            <div class="sf-sidebar-controls">
                <div class="sf-sidebar-controls-title">Controls</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Start Simulation", use_container_width=True):
            start_simulation_session()
            st.rerun()

        if st.button("Reset Database", use_container_width=True):
            reset_error = None
            try:
                database.reset_database()
                indexer.reset_vector_index()
            except (RuntimeError, ValueError) as error:
                reset_error = str(error)
            clear_dashboard_state()
            st.session_state["database_error"] = reset_error
            st.rerun()


def render_current_page() -> None:
    """Render only the selected top-level page."""
    if st.session_state.current_page == "Dashboard":
        render_dashboard_page()
    elif st.session_state.current_page == "Investigation":
        render_investigation_page()
    elif st.session_state.current_page == "Incident Replay":
        render_incident_replay_page()
    else:
        render_security_briefing_page()


render_sidebar()

if database_error:
    st.error(database_error)

render_top_nav()
render_current_page()
