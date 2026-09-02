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
        ("old-trip", now - timedelta(minutes=11), "25"),
    ])
    database.execute("UPDATE trips SET delay_seconds = 120 WHERE trip_id = 'late-trip'")

    rows = module.make_display_rows(database, now, {})

    assert rows == [{"route_id": "24", "time": "12:12", "minutes": 12, "delay": 120}]
    assert database.execute("SELECT COUNT(*) FROM trips").fetchone()[0] == 1
    database.close()


def test_format_csv_has_stable_display_contract():
    module = load_module()

    assert module.format_csv([{"route_id": "24", "time": "12:12", "minutes": 12, "delay": 120}]) == (
        "route_id,time,minutes,delay\n24,12:12,12,120\n"
    )