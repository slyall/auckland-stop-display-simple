import importlib.util
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
