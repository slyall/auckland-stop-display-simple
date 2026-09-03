#!/usr/bin/env python3
"""Fetch Auckland Transport stop trip data for a stop ID."""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib import error, request

API_URL = "https://api.at.govt.nz/gtfs/v3/stops"


def calculate_query_window(now=None):
    """Return the AT query start hour and hour range for the current local time.

    If the clock is within the first few minutes past the top of the hour, include the previous
    hour in the search window so late buses that were due just before the hour are still visible.
    """
    current = now or datetime.now()
    current_hour = current.hour
    minute = current.minute

    if minute <= 10:
        start_hour = (current_hour - 1) % 24
        hour_range = 2
    else:
        start_hour = current_hour
        # Keep a two-hour window when we are still within the hour window we care about,
        # e.g. 19:55 should include trips from 19:00 through 20:59.
        hour_range = 2

    return start_hour, hour_range


def calculate_query_date(now=None):
    """Return the date associated with the query window start."""
    current = now or datetime.now()
    start_hour, _ = calculate_query_window(current)
    if start_hour > current.hour and current.hour == 0:
        return current.date() - timedelta(days=1)
    if start_hour > current.hour:
        return current.date() - timedelta(days=1)
    return current.date()


def read_stop_id(stop_id_arg=None, file_path=None):
    if stop_id_arg:
        return stop_id_arg.strip()

    if file_path:
        text = Path(file_path).read_text(encoding="utf-8").strip()
        if not text:
            raise ValueError(f"Stop ID file is empty: {file_path}")
        return text.splitlines()[0].strip()

    raise ValueError("Stop ID is required. Supply a stop_id as a positional argument or via --file.")


def fetch_stop_trips(api_key: str, stop_id: str, date_value: str, start_hour: int, hour_range: int, debug: bool = False):
    url = f"{API_URL}/{stop_id}/stoptrips"
    params = {
        "filter[date]": date_value,
        "filter[start_hour]": str(start_hour),
        "filter[hour_range]": str(hour_range),
    }

    query = "&".join(f"{key}={value}" for key, value in params.items())
    full_url = f"{url}?{query}"

    headers = {
        "Ocp-Apim-Subscription-Key": api_key,
        "Accept": "application/json",
    }

    if debug:
        print(f"Requesting: {full_url}")

    req = request.Request(full_url, headers=headers, method="GET")
    try:
        with request.urlopen(req, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"AT API request failed: {exc.code} {exc.reason}\n{body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach AT API: {exc}") from exc

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON returned from AT API: {exc}") from exc


def format_stop_trips(payload, json_output=False, stop_id=None):
    """Format stop-trip data for console output.

    Default output is a compact CSV-like format with trip id, route id, and arrival time.
    When json_output is true, return the full payload as JSON.
    """
    if json_output:
        return json.dumps(payload, indent=2)

    lines = [f"# stop_id={stop_id}"] if stop_id else []
    for item in payload.get("data", []):
        attributes = item.get("attributes", {})
        trip_id = attributes.get("trip_id", "")
        route_id = attributes.get("route_id", "").split("-", 1)[0]
        arrival_time = attributes.get("arrival_time", "")
        lines.append(f"{trip_id},{route_id},{arrival_time}")
    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Get upcoming Auckland Transport stop trips for a stop id."
    )
    parser.add_argument("stop_id", nargs="?", help="AT stop_id such as 8313-ec0c55f5")
    parser.add_argument("--file", dest="file_path", help="Read the stop_id from a file instead of the command line")
    parser.add_argument("--date", help="Override the date in YYYY-MM-DD format. Defaults to the current local date.")
    parser.add_argument("--debug", action="store_true", help="Print the API request and extra details")
    parser.add_argument("--output", help="Write the output to a file. Use --json to write the full API JSON payload.")
    parser.add_argument("--json", action="store_true", help="Output the full JSON payload instead of the compact trip summary")
    return parser.parse_args()


def main():
    args = parse_args()
    api_key = os.environ.get("AT_API_KEY")
    if not api_key:
        print("AT_API_KEY is not set. Export it before running this script.", file=sys.stderr)
        return 1

    try:
        stop_id = read_stop_id(args.stop_id, args.file_path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    now = datetime.now()
    if args.date:
        try:
            query_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print("The --date value must be in YYYY-MM-DD format.", file=sys.stderr)
            return 1
        start_hour, hour_range = calculate_query_window(now)
        if start_hour > now.hour:
            query_date = query_date - timedelta(days=1)
    else:
        start_hour, hour_range = calculate_query_window(now)
        query_date = calculate_query_date(now)

    if args.debug:
        print(f"Using date={query_date.isoformat()} start_hour={start_hour} hour_range={hour_range}")

    try:
        payload = fetch_stop_trips(api_key, stop_id, query_date.isoformat(), start_hour, hour_range, debug=args.debug)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    data = payload.get("data", [])
    formatted_output = format_stop_trips(payload, json_output=args.json, stop_id=stop_id)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(formatted_output, encoding="utf-8")
        if args.debug:
            print(f"Saved output to {output_path}")

    print(formatted_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
