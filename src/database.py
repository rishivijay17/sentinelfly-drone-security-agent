"""SQLite database helpers for SentinelFly surveillance events."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


DatabaseRow = dict[str, Any]

DB_PATH = Path(__file__).resolve().parent.parent / "sentinelfly.db"


def _get_connection() -> sqlite3.Connection:
    """Create a SQLite connection configured to return rows as dictionaries."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    """Create the surveillance_events table when it does not already exist."""
    try:
        with _get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS surveillance_events (
                    frame_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    location TEXT NOT NULL,
                    object_type TEXT NOT NULL,
                    object_color TEXT NOT NULL,
                    object_details TEXT NOT NULL,
                    activity TEXT NOT NULL,
                    risk_hint TEXT NOT NULL,
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    altitude REAL NOT NULL,
                    drone_speed REAL NOT NULL
                )
                """
            )
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to initialize SentinelFly database: {error}") from error


def reset_database() -> None:
    """Remove stored surveillance events while keeping the table available."""
    initialize_database()
    try:
        with _get_connection() as connection:
            connection.execute("DELETE FROM surveillance_events")
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to reset SentinelFly database: {error}") from error


def insert_event(event: dict[str, Any]) -> None:
    """Insert or update one surveillance event."""
    telemetry = event.get("telemetry", {})

    values = {
        "frame_id": event["frame_id"],
        "timestamp": event["timestamp"],
        "location": event["location"],
        "object_type": event["object_type"],
        "object_color": event["object_color"],
        "object_details": event["object_details"],
        "activity": event["activity"],
        "risk_hint": event["risk_hint"],
        "latitude": event.get("latitude", telemetry.get("latitude")),
        "longitude": event.get("longitude", telemetry.get("longitude")),
        "altitude": event.get("altitude", telemetry.get("altitude")),
        "drone_speed": event.get("drone_speed", telemetry.get("drone_speed")),
    }

    missing_fields = [key for key, value in values.items() if value is None]
    if missing_fields:
        raise ValueError(f"Event is missing required fields: {', '.join(missing_fields)}")

    try:
        with _get_connection() as connection:
            connection.execute(
                """
                INSERT INTO surveillance_events (
                    frame_id,
                    timestamp,
                    location,
                    object_type,
                    object_color,
                    object_details,
                    activity,
                    risk_hint,
                    latitude,
                    longitude,
                    altitude,
                    drone_speed
                )
                VALUES (
                    :frame_id,
                    :timestamp,
                    :location,
                    :object_type,
                    :object_color,
                    :object_details,
                    :activity,
                    :risk_hint,
                    :latitude,
                    :longitude,
                    :altitude,
                    :drone_speed
                )
                ON CONFLICT(frame_id) DO UPDATE SET
                    timestamp = excluded.timestamp,
                    location = excluded.location,
                    object_type = excluded.object_type,
                    object_color = excluded.object_color,
                    object_details = excluded.object_details,
                    activity = excluded.activity,
                    risk_hint = excluded.risk_hint,
                    latitude = excluded.latitude,
                    longitude = excluded.longitude,
                    altitude = excluded.altitude,
                    drone_speed = excluded.drone_speed
                """,
                values,
            )
    except KeyError as error:
        raise ValueError(f"Event is missing required field: {error}") from error
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to insert surveillance event: {error}") from error


def insert_events(events: list[dict[str, Any]]) -> None:
    """Insert or update multiple surveillance events."""
    initialize_database()
    for event in events:
        insert_event(event)


def fetch_all_events() -> list[DatabaseRow]:
    """Return every stored surveillance event ordered by timestamp."""
    return _fetch_many("SELECT * FROM surveillance_events ORDER BY timestamp")


def fetch_events_by_object(object_type: str) -> list[DatabaseRow]:
    """Return stored events for one object type."""
    return _fetch_many(
        """
        SELECT *
        FROM surveillance_events
        WHERE lower(object_type) = lower(?)
        ORDER BY timestamp
        """,
        (object_type,),
    )


def fetch_events_by_location(location: str) -> list[DatabaseRow]:
    """Return stored events matching a location search term."""
    return _fetch_many(
        """
        SELECT *
        FROM surveillance_events
        WHERE lower(location) LIKE lower(?)
        ORDER BY timestamp
        """,
        (f"%{location}%",),
    )


def fetch_suspicious_events() -> list[DatabaseRow]:
    """Return events with medium or high risk indicators."""
    return _fetch_many(
        """
        SELECT *
        FROM surveillance_events
        WHERE lower(risk_hint) LIKE '%medium%'
           OR lower(risk_hint) LIKE '%high%'
           OR lower(risk_hint) LIKE '%suspicious%'
           OR lower(risk_hint) LIKE '%restricted%'
           OR lower(risk_hint) LIKE '%after-hours%'
        ORDER BY timestamp
        """
    )


def _fetch_many(query: str, parameters: tuple[Any, ...] = ()) -> list[DatabaseRow]:
    """Run a SELECT query and return rows as dictionaries."""
    initialize_database()
    try:
        with _get_connection() as connection:
            cursor = connection.execute(query, parameters)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as error:
        raise RuntimeError(f"Failed to fetch surveillance events: {error}") from error
