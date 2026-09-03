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
LOOKBACK_MINUTES = 15
LOOKAHEAD_MINUTES = 45


def debug_log(enabled, message):
    if enabled:
        print(f"[debug] {message}", file=sys.stderr)


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
            next_stop_id TEXT,
            last_checked_at TEXT,
            completed INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    columns = {row[1] for row in database.execute("PRAGMA table_info(trips)")}
    if "next_stop_id" not in columns:
        database.execute("ALTER TABLE trips ADD COLUMN next_stop_id TEXT")
    database.commit()
    return database


def read_trip_file(path, now, return_stop_id=False):
    trips = []
    stop_id = None
    with Path(path).open(newline="", encoding="utf-8") as source:
        for line_number, row in enumerate(csv.reader(source), 1):
            if not row or not any(field.strip() for field in row):
                continue
            if row[0].strip().startswith("# stop_id="):
                stop_id = row[0].strip().split("=", 1)[1].strip() or None
                continue
            if len(row) < 3:
                raise ValueError(f"{path}:{line_number}: expected trip_id,route_id,arrival_time")
            trip_id, route_id, arrival_time = (field.strip() for field in row[:3])
            # Accept files from the original three-column producer format:
            # trip_id,trip_start_time,arrival_time.
            if len(row) == 3 and route_id.count(":") == 2:
                route_id = trip_id.split("-", 1)[0]
            try:
                scheduled_at = parse_trip_time(arrival_time, now.date(), now)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{path}:{line_number}: invalid arrival time {arrival_time!r}") from exc
            trips.append((trip_id, scheduled_at, route_id))
    return (trips, stop_id) if return_stop_id else trips


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


def fetch_realtime(api_key, trip_ids, debug=False):
    if not trip_ids:
        debug_log(debug, "realtime query skipped: no candidate trips")
        return {}
    query = parse.urlencode({"tripid": ",".join(trip_ids)})
    debug_log(debug, f"realtime query: {', '.join(trip_ids)}")
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
    response = payload.get("response", payload)
    for entity in response.get("entity", []):
        trip_update = entity.get("trip_update", {})
        trip = trip_update.get("trip", {})
        trip_id = trip.get("trip_id")
        if not trip_id:
            continue
        trip_delay = int(trip_update.get("delay", 0) or 0)
        stop_delay = None
        next_stop_id = None
        stop_updates = trip_update.get("stop_time_update", [])
        if isinstance(stop_updates, dict):
            stop_updates = [stop_updates]
        if stop_updates:
            next_stop_id = stop_updates[0].get("stop_id")
            stop_delay = stop_updates[0].get("arrival", {}).get("delay")
            if stop_delay is None:
                stop_delay = stop_updates[0].get("departure", {}).get("delay")
            if stop_delay is not None:
                stop_delay = int(stop_delay)
        updates[trip_id] = {
            "delay": trip_delay,
            "stop_delay": stop_delay,
            "next_stop_id": next_stop_id,
        }
        debug_log(
            debug,
            f"realtime response {trip_id}: trip delay={trip_delay}s, "
            f"stop delay={stop_delay if stop_delay is not None else 'none'}s, "
            f"next stop={next_stop_id or 'unknown'}",
        )
    missing_ids = [trip_id for trip_id in trip_ids if trip_id not in updates]
    for trip_id in missing_ids:
        debug_log(debug, f"realtime response {trip_id}: no update; existing database delay will be kept")
    return updates


def select_trip_ids(database, now, debug=False):
    lower = (now - timedelta(minutes=LOOKBACK_MINUTES)).strftime(TIME_FORMAT)
    upper = (now + timedelta(minutes=LOOKAHEAD_MINUTES)).strftime(TIME_FORMAT)
    debug_log(debug, f"candidate window: {lower} through {upper}")
    all_rows = database.execute(
        "SELECT trip_id, scheduled_at, completed FROM trips ORDER BY scheduled_at"
    ).fetchall()
    for row in all_rows:
        scheduled = datetime.strptime(row["scheduled_at"], TIME_FORMAT)
        if row["completed"]:
            status = "already departed (marked completed)"
        elif scheduled < now - timedelta(minutes=LOOKBACK_MINUTES):
            status = "too early / already departed"
        elif scheduled > now + timedelta(minutes=LOOKAHEAD_MINUTES):
            status = "too late for the lookahead window"
        else:
            status = "selected"
        debug_log(debug, f"candidate {row['trip_id']}: scheduled {row['scheduled_at']} -> {status}")
    rows = database.execute(
        "SELECT trip_id FROM trips WHERE completed = 0 AND scheduled_at BETWEEN ? AND ?",
        (lower, upper),
    ).fetchall()
    selected_ids = [row["trip_id"] for row in rows]
    debug_log(debug, f"candidate trips to check: {', '.join(selected_ids) or 'none'}")
    return selected_ids


def debug_input_trips(trips, now, debug):
    for trip_id, scheduled, _ in trips:
        if scheduled < now - timedelta(minutes=LOOKBACK_MINUTES):
            status = "too early / already departed"
        elif scheduled > now + timedelta(minutes=LOOKAHEAD_MINUTES):
            status = "too late for the lookahead window"
        else:
            status = "selected (--once)"
        debug_log(debug, f"candidate {trip_id}: scheduled {scheduled.strftime(TIME_FORMAT)} -> {status}")


def make_display_rows(database, now, updates, stop_id=None, debug=False):
    debug_log(debug, f"checking {len(updates)} realtime trip update(s)")
    database.executemany(
        "UPDATE trips SET delay_seconds = ?, next_stop_id = ?, last_checked_at = ? WHERE trip_id = ?",
        [(update["stop_delay"] if stop_id and update["next_stop_id"] == stop_id and update["stop_delay"] is not None
          else update["delay"], update["next_stop_id"], now.strftime(TIME_FORMAT), trip_id)
         for trip_id, update in updates.items()],
    )
    cutoff = (now - timedelta(minutes=LOOKBACK_MINUTES)).strftime(TIME_FORMAT)
    database.execute("DELETE FROM trips WHERE scheduled_at < ? OR completed = 1", (cutoff,))
    rows = database.execute(
        """
        SELECT trip_id, route_id, scheduled_at, delay_seconds, next_stop_id
        FROM trips
        WHERE completed = 0 AND scheduled_at BETWEEN ? AND ?
        ORDER BY julianday(scheduled_at) + delay_seconds / 86400.0
        """,
        (cutoff, (now + timedelta(minutes=LOOKAHEAD_MINUTES)).strftime(TIME_FORMAT)),
    ).fetchall()
    result = []
    for row in rows:
        scheduled = datetime.strptime(row["scheduled_at"], TIME_FORMAT)
        estimated = scheduled + timedelta(seconds=row["delay_seconds"])
        at_this_stop = stop_id is not None and row["next_stop_id"] == stop_id
        debug_log(
            debug,
            f"calculation {row['trip_id']}: scheduled {row['scheduled_at']} + "
            f"delay {row['delay_seconds']}s = arrival {estimated.strftime('%Y-%m-%d %H:%M:%S')} "
            f"(next stop={row['next_stop_id'] or 'unknown'})",
        )
        if estimated < now - timedelta(minutes=1) and not at_this_stop:
            debug_log(debug, f"display {row['trip_id']}: skip, already departed our stop")
            continue
        debug_log(debug, f"display {row['trip_id']}: show as {row['route_id']} at {estimated.strftime('%H:%M')}")
        result.append({"route_id": row["route_id"], "time": estimated.strftime("%H:%M"),
                       "minutes": max(0, round((estimated - now).total_seconds() / 60)),
                       "delay": row["delay_seconds"]})
        if len(result) == 12:
            break
    return result


def format_csv(rows):
    lines = ["route_id,time,minutes"]
    lines.extend(f"{row['route_id']},{row['time']},{row['minutes']}" for row in rows)
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
    parser.add_argument("--debug", action="store_true", help="Print candidate, realtime, and display decisions")
    parser.add_argument("--stop-id", help="AT stop ID used to identify buses currently at this stop")
    parser.add_argument("--stop-name")
    return parser.parse_args()


def main():
    args = parse_args()
    now = datetime.now().replace(microsecond=0)
    try:
        trips, file_stop_id = read_trip_file(args.input, now, return_stop_id=True)
        stop_id = args.stop_id or file_stop_id
        with connect_database(args.database) as database:
            ingest_trips(database, trips)
            candidate_ids = [trip_id for trip_id, _, _ in trips] if args.once else select_trip_ids(database, now, args.debug)
            if args.once:
                debug_input_trips(trips, now, args.debug)
                debug_log(args.debug, f"candidate trips to check (--once): {', '.join(candidate_ids) or 'none'}")
            updates = fetch_realtime(os.environ.get("AT_API_KEY", ""), candidate_ids, args.debug) if os.environ.get("AT_API_KEY") else {}
            if candidate_ids and not os.environ.get("AT_API_KEY"):
                debug_log(args.debug, "realtime query skipped: AT_API_KEY is not set; existing database delays will be used")
            rows = make_display_rows(database, now, updates, stop_id, args.debug)
            debug_log(args.debug, f"display result: {len(rows)} trip(s)")
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