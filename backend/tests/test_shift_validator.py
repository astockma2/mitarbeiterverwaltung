from datetime import date, time

from app.models.shift import ShiftStatus, ShiftTemplate
from app.services.shift_validator import ACTIVE_SHIFT_STATUSES, _calculate_rest_hours


def make_shift(
    start: time,
    end: time,
    crosses_midnight: bool = False,
) -> ShiftTemplate:
    return ShiftTemplate(
        name="Test",
        short_code="T",
        start_time=start,
        end_time=end,
        break_minutes=0,
        crosses_midnight=crosses_midnight,
    )


def test_rest_time_after_night_shift_uses_real_end_date():
    night = make_shift(time(22, 0), time(6, 0), crosses_midnight=True)
    late = make_shift(time(14, 0), time(22, 0))

    rest = _calculate_rest_hours(night, date(2026, 5, 1), late, date(2026, 5, 2))

    assert rest == 8.0


def test_swapped_shifts_are_active_for_validation():
    assert ShiftStatus.SWAPPED in ACTIVE_SHIFT_STATUSES
