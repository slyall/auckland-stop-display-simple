import importlib.util
import json
from datetime import datetime
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "get-stop-trips.py"


def load_module():
    spec = importlib.util.spec_from_file_location("get_stop_trips", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_calculate_query_window_just_after_hour_uses_previous_hour():
    module = load_module()

    start_hour, hour_range = module.calculate_query_window(datetime(2026, 9, 2, 20, 2))

    assert (start_hour, hour_range) == (19, 2)


def test_calculate_query_window_later_in_hour_uses_current_hour():
    module = load_module()

    start_hour, hour_range = module.calculate_query_window(datetime(2026, 9, 2, 20, 20))

    assert (start_hour, hour_range) == (20, 2)


def test_calculate_query_window_late_in_hour_keeps_two_hour_window():
    module = load_module()

    start_hour, hour_range = module.calculate_query_window(datetime(2026, 9, 2, 19, 55))

    assert (start_hour, hour_range) == (19, 2)


def test_calculate_query_window_at_ten_minutes_past_hour_still_uses_previous_hour():
    module = load_module()

    start_hour, hour_range = module.calculate_query_window(datetime(2026, 9, 2, 20, 10))

    assert (start_hour, hour_range) == (19, 2)


def test_format_stop_trips_defaults_to_compact_trip_fields():
    module = load_module()
    payload = {
        "data": [
            {
                "attributes": {
                    "trip_id": "24-02403-74400-2-fb29cf95",
                    "trip_start_time": "20:40:00",
                    "arrival_time": "21:01:03",
                    "route_id": "24B-202",
                }
            },
            {
                "attributes": {
                    "trip_id": "1279-02401-75480-2-cc67cdfd",
                    "trip_start_time": "20:58:00",
                    "arrival_time": "21:16:00",
                    "route_id": "1279",
                }
            },
        ]
    }

    assert module.format_stop_trips(payload) == (
        "24-02403-74400-2-fb29cf95,24B,21:01:03\n"
        "1279-02401-75480-2-cc67cdfd,1279,21:16:00"
    )


def test_format_stop_trips_includes_stop_id_metadata():
    module = load_module()
    payload = {"data": []}

    assert module.format_stop_trips(payload, stop_id="8313-ec0c55f5") == (
        "# stop_id=8313-ec0c55f5"
    )


def test_format_stop_trips_includes_stop_name_metadata():
    module = load_module()

    assert module.format_stop_trips(
        {"data": []}, stop_id="7149-6d6d1e99", stop_name="Symonds Street/Karangahape Road"
    ) == (
        "# stop_id=7149-6d6d1e99\n"
        "# stop_name=Symonds Street/Karangahape Road"
    )


def test_fetch_stop_info_returns_stop_name(monkeypatch):
    module = load_module()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self):
            return b'{"data": {"attributes": {"stop_name": "Symonds Street/Karangahape Road"}}}'

    monkeypatch.setattr(module.request, "urlopen", lambda req, timeout: Response())

    assert module.fetch_stop_info("key", "7149-6d6d1e99") == "Symonds Street/Karangahape Road"


def test_format_stop_trips_includes_stop_sequence():
    module = load_module()
    payload = {"data": [{"attributes": {
        "trip_id": "trip",
        "route_id": "24B-202",
        "arrival_time": "12:01:17",
        "stop_sequence": 26,
    }}]}

    assert module.format_stop_trips(payload) == "trip,24B,12:01:17,26"


def test_format_stop_trips_json_output_keeps_full_api_payload():
    module = load_module()
    payload = {
        "data": [
            {
                "type": "stoptrip",
                "id": "stop:8313-ec0c55f5_trip:24-02403-74400-2-fb29cf95",
                "attributes": {
                    "arrival_time": "21:01:03",
                    "departure_time": "21:01:03",
                    "trip_id": "24-02403-74400-2-fb29cf95",
                    "trip_start_time": "20:40:00",
                },
            }
        ]
    }

    assert json.loads(module.format_stop_trips(payload, json_output=True)) == payload
