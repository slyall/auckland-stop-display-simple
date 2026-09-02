#!/usr/bin/env python3
"""Resolve an Auckland Transport stop code into the GTFS stop_id."""

import argparse
import json
import os
import sys
from urllib import error, request

API_URL = "https://api.at.govt.nz/gtfs/v3/stops"


def fetch_stops(api_key: str, debug: bool = False):
    headers = {
        "Ocp-Apim-Subscription-Key": api_key,
        "Accept": "application/json",
    }

    if debug:
        print(f"Requesting stop list from: {API_URL}")

    req = request.Request(API_URL, headers=headers, method="GET")
    try:
        with request.urlopen(req, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"AT API request failed: {exc.code} {exc.reason}\n{body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach AT API: {exc}") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON returned from AT API: {exc}") from exc

    return data


def flatten_stop_records(obj):
    records = []

    if isinstance(obj, list):
        for item in obj:
            records.extend(flatten_stop_records(item))
        return records

    if isinstance(obj, dict):
        has_stop_like_fields = any(key in obj for key in ("stop_code", "stop_id", "id"))
        if has_stop_like_fields and any(key in obj for key in ("stop_code", "stop_id")):
            records.append(obj)

        for value in obj.values():
            records.extend(flatten_stop_records(value))
        return records

    return records


def find_stop_id(records, stop_code: str):
    code = str(stop_code).strip()
    exact_matches = []

    for item in records:
        if not isinstance(item, dict):
            continue

        stop_code_value = item.get("stop_code")
        if stop_code_value is None:
            stop_code_value = item.get("code")
        if stop_code_value is None:
            stop_code_value = item.get("short_name")

        if str(stop_code_value).strip() == code:
            exact_matches.append(item)

    if not exact_matches:
        return None

    # Prefer the most specific stop record when there are duplicates.
    matched = exact_matches[0]
    return matched.get("stop_id") or matched.get("id")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert an Auckland Transport stop code into the full stop_id."
    )
    parser.add_argument("stop_code", help="The public stop code, e.g. 8425")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print more API and matching details to the terminal.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    api_key = os.environ.get("AT_API_KEY")

    if not api_key:
        print("AT_API_KEY is not set. Export it before running this script.", file=sys.stderr)
        return 1

    try:
        response = fetch_stops(api_key, debug=args.debug)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    records = flatten_stop_records(response)
    if not records:
        print(f"No stop records found in AT response for {args.stop_code!r}", file=sys.stderr)
        return 1

    stop_id = find_stop_id(records, args.stop_code)
    if stop_id is None:
        print(f"No stop found for stop code: {args.stop_code}", file=sys.stderr)
        return 1

    if args.debug:
        print(f"Matched stop code {args.stop_code!r} to stop_id {stop_id!r}")
    else:
        print(stop_id)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
