#!/usr/bin/env python3
"""Track upcoming stop trips and publish a small display-friendly board."""

import argparse
import csv
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from urllib import error, parse, request

REALTIME_URL = "https://api.at.govt.nz/realtime/legacy/tripupdates"
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


def parse_trip_time(value, service_date, now):
    """Turn an AT time, including times after midnight, into local datetime."""
    parts = [int(part) for part in value.split(":")]
    day_offset, hour = divmod(parts[0], 24)
    result = datetime.combine(service_date, datetime.min.time()).replace(
        hour=hour, minute=parts[1], second=parts[2]
    ) + timedelta(days=day_offset)
    if result < now - timedelta(hours=12):
        result += timedelta(days=1)
    return result


def connect_database(path):
    database = sqlite3.connect(path)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA busy_timeout = 5000")
    database.execute(
        """
        CREATE TABLE IF NOT EXISTS trips (
            trip_id TEXT PRIMARY KEY,
            scheduled_at TEXT NOT NULL,
            route_id TEXT NOT NULL,
            delay_seconds INTEGER NOT NULL DEFAULT 0,
            last_checked_at TEXT,
            completed INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    database.commit()
    return database


def read_trip_file(path, now):
    trips = []
    with Path(path).open(newline="", encoding="utf-8") as source:
        for line_number, row in enumerate(csv.reader(source), 1):
            if not row or not any(field.strip() for field in row):
                continue
            if len(row) < 3:
                raise ValueError(f"{path}:{line_number}: expected trip_id,start_time,arrival_time")
            trip_id, start_time, arrival_time = (field.strip() for field in row[:3])
            try:
                scheduled_at = parse_trip_time(arrival_time, now.date(), now)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{path}:{line_number}: invalid arrival time {arrival_time!r}") from exc
            trips.append((trip_id, scheduled_at, trip_id.split("-")[0]))
    return trips


def ingest_trips(database, trips):
    database.executemany(
        """
        INSERT INTO trips (trip_id, scheduled_at, route_id)
        VALUES (?, ?, ?)
        ON CONFLICT(trip_id) DO UPDATE SET
            scheduled_at = excluded.scheduled_at,
            route_id = excluded.route_id,
            completed = 0
        """,
        [(trip_id, scheduled_at.strftime(TIME_FORMAT), route_id) for trip_id, scheduled_at, route_id in trips],
    )


def fetch_realtime(api_key, trip_ids):
    if not trip_ids:
        return {}
    query = parse.urlencode({"tripid": ",".join(trip_ids)})
    request_object = request.Request(
        f"{REALTIME_URL}?{query}",
        headers={"Ocp-Apim-Subscription-Key": api_key, "Accept": "application/json"},
    )
    try:
        with request.urlopen(request_object, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (error.HTTPError, error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Realtime API request failed: {exc}") from exc

    updates = {}
    for entity in payload.get("entity", []):
        trip_update = entity.get("trip_update", {})
        trip = trip_update.get("trip", {})
        trip_id = trip.get("trip_id")
        if not trip_id:
            continue
        delay = trip_update.get("delay", 0)
        stop_updates = trip_update.get("stop_time_update", [])
        if isinstance(stop_updates, dict):
            stop_updates = [stop_updates]
        if stop_updates and stop_updates[0].get("arrival", {}).get("delay") is not None:
            delay = stop_updates[0]["arrival"]["delay"]
        updates[trip_id] = int(delay or 0)
    return updates


def select_trip_ids(database, now):
    lower = (now - timedelta(minutes=10)).strftime(TIME_FORMAT)
    upper = (now + timedelta(minutes=30)).strftime(TIME_FORMAT)
    rows = database.execute(
        "SELECT trip_id FROM trips WHERE completed = 0 AND scheduled_at BETWEEN ? AND ?",
        (lower, upper),
    ).fetchall()
    return [row["trip_id"] for row in rows]


def make_display_rows(database, now, delays):
    database.executemany(
        "UPDATE trips SET delay_seconds = ?, last_checked_at = ? WHERE trip_id = ?",
        [(delay, now.strftime(TIME_FORMAT), trip_id) for trip_id, delay in delays.items()],
    )
    cutoff = (now - timedelta(minutes=10)).strftime(TIME_FORMAT)
    database.execute("DELETE FROM trips WHERE scheduled_at < ? OR completed = 1", (cutoff,))
    rows = database.execute(
        """
        SELECT trip_id, route_id, scheduled_at, delay_seconds
        FROM trips
        WHERE completed = 0 AND scheduled_at BETWEEN ? AND ?
        ORDER BY julianday(scheduled_at) + delay_seconds / 86400.0
        LIMIT 12
        """,
        (cutoff, (now + timedelta(minutes=40)).strftime(TIME_FORMAT)),
    ).fetchall()
    result = []
    for row in rows:
        scheduled = datetime.strptime(row["scheduled_at"], TIME_FORMAT)
        estimated = scheduled + timedelta(seconds=row["delay_seconds"])
        result.append({"route_id": row["route_id"], "time": estimated.strftime("%H:%M"),
                       "minutes": max(0, round((estimated - now).total_seconds() / 60)),
                       "delay": row["delay_seconds"]})
    return result


def format_csv(rows):
    lines = ["route_id,time,minutes,delay"]
    lines.extend(f"{row['route_id']},{row['time']},{row['minutes']},{row['delay']}" for row in rows)
    return "\n".join(lines) + "\n"


def format_pretty(rows, now, stop_name=None):
    title = stop_name or "Bus departures"
    lines = [f"{title}  {now.strftime('%H:%M')}" ]
    lines.extend(f"{row['route_id']:<8} {row['time']}  ({row['minutes']} min)" for row in rows)
    return "\n".join(lines) + "\n"


def atomic_write(path, content):
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent, delete=False) as temporary:
        temporary.write(content)
        temporary_path = temporary.name
    os.replace(temporary_path, output)


def parse_args():
    parser = argparse.ArgumentParser(description="Track and display upcoming Auckland bus trips.")
    parser.add_argument("--input", default="trips.txt", help="Output file from get-stop-trips.py")
    parser.add_argument("--database", default="display-info.db")
    parser.add_argument("--output", default="display.csv")
    parser.add_argument("--pretty", action="store_true", help="Print a human-readable board")
    parser.add_argument("--once", action="store_true", help="Check every trip in the input once")
    parser.add_argument("--stop-name")
    return parser.parse_args()


def main():
    args = parse_args()
    now = datetime.now().replace(microsecond=0)
    try:
        trips = read_trip_file(args.input, now)
        with connect_database(args.database) as database:
            ingest_trips(database, trips)
            candidate_ids = [trip_id for trip_id, _, _ in trips] if args.once else select_trip_ids(database, now)
            delays = fetch_realtime(os.environ.get("AT_API_KEY", ""), candidate_ids) if os.environ.get("AT_API_KEY") else {}
            rows = make_display_rows(database, now, delays)
            database.commit()
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    output = format_pretty(rows, now, args.stop_name) if args.pretty else format_csv(rows)
    if args.pretty:
        print(output, end="")
    else:
        atomic_write(args.output, output)
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())