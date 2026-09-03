import importlib.util
from datetime import datetime, timedelta


MODULE_PATH = __import__("pathlib").Path(__file__).resolve().parents[1] / "display-info.py"


def load_module():
    spec = importlib.util.spec_from_file_location("display_info", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_make_display_rows_applies_delay_and_removes_old_trips(tmp_path):
    module = load_module()
    now = datetime(2026, 9, 3, 12, 0)
    database = module.connect_database(tmp_path / "display.db")
    module.ingest_trips(database, [
        ("late-trip", now + timedelta(minutes=10), "24"),
        ("old-trip", now - timedelta(minutes=16), "25"),
    ])
    database.execute("UPDATE trips SET delay_seconds = 120 WHERE trip_id = 'late-trip'")

    rows = module.make_display_rows(database, now, {})

    assert rows == [{"route_id": "24", "time": "12:12", "minutes": 12, "delay": 120}]
    assert database.execute("SELECT COUNT(*) FROM trips").fetchone()[0] == 1
    database.close()


def test_read_trip_file_keeps_api_route_id(tmp_path):
    module = load_module()
    input_path = tmp_path / "trips.txt"
    input_path.write_text("27-02707-41700-2-fe6656cf,27H,12:08:56\n", encoding="utf-8")

    trips = module.read_trip_file(input_path, datetime(2026, 9, 3, 12, 0))

    assert trips[0][2] == "27H"


def test_make_display_rows_hides_arrivals_more_than_one_minute_old(tmp_path):
    module = load_module()
    now = datetime(2026, 9, 3, 12, 0)
    database = module.connect_database(tmp_path / "display.db")
    module.ingest_trips(database, [("past-trip", now - timedelta(minutes=2), "24")])

    assert module.make_display_rows(database, now, {}) == []
    database.close()


def test_make_display_rows_fills_display_after_skipping_old_arrivals(tmp_path):
    module = load_module()
    now = datetime(2026, 9, 3, 12, 0)
    database = module.connect_database(tmp_path / "display.db")
    module.ingest_trips(database, [
        (f"old-trip-{number}", now - timedelta(minutes=2), "old")
        for number in range(12)
    ] + [
        ("next-trip", now + timedelta(minutes=10), "75"),
    ])

    rows = module.make_display_rows(database, now, {})

    assert rows == [{"route_id": "75", "time": "12:10", "minutes": 10, "delay": 0}]
    database.close()


def test_make_display_rows_applies_negative_delay(tmp_path):
    module = load_module()
    now = datetime(2026, 9, 3, 12, 0)
    database = module.connect_database(tmp_path / "display.db")
    module.ingest_trips(database, [("early-trip", now + timedelta(minutes=10), "24")])

    rows = module.make_display_rows(database, now, {"early-trip": {
        "delay": -590, "stop_delay": None, "next_stop_id": None,
    }})

    assert rows == [{"route_id": "24", "time": "12:00", "minutes": 0, "delay": -590}]
    database.close()


def test_make_display_rows_uses_stop_delay_only_at_that_stop(tmp_path):
    module = load_module()
    now = datetime(2026, 9, 3, 12, 0)
    database = module.connect_database(tmp_path / "display.db")
    module.ingest_trips(database, [("trip", now + timedelta(minutes=10), "24")])
    update = {"delay": 120, "stop_delay": -590, "next_stop_id": "other-stop"}

    rows = module.make_display_rows(database, now, {"trip": update}, stop_id="my-stop")

    assert rows[0]["time"] == "12:12"
    database.close()


def test_format_csv_has_stable_display_contract():
    module = load_module()

    assert module.format_csv([{"route_id": "24", "time": "12:12", "minutes": 12, "delay": 120}]) == (
        "route_id,time,minutes\n24,12:12,12\n"
    )