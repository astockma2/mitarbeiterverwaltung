"""Regelwerk fuer die Schichtplanung nach ArbZG und Haustarif."""

from datetime import date, time, timedelta, datetime
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shift import ShiftAssignment, ShiftTemplate, ShiftRequirement, ShiftStatus, ShiftPlan


# ArbZG Regeln
MAX_DAILY_HOURS = 10.0        # Max 10h/Tag (§3 ArbZG)
MAX_WEEKLY_HOURS = 48.0       # Max 48h/Woche (§3 ArbZG)
MIN_REST_HOURS = 11.0         # Min 11h Ruhezeit (§5 ArbZG)
MAX_CONSECUTIVE_DAYS = 6      # Max 6 Tage am Stueck (§9 ArbZG)


ACTIVE_SHIFT_STATUSES = (ShiftStatus.PLANNED, ShiftStatus.CONFIRMED, ShiftStatus.SWAPPED)


class ValidationResult:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, msg: str):
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def to_dict(self) -> dict:
        return {
            "valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


async def validate_assignment(
    db: AsyncSession,
    employee_id: int,
    shift_template: ShiftTemplate,
    assignment_date: date,
    exclude_assignment_id: Optional[int] = None,
) -> ValidationResult:
    """Prueft ob eine Schichtzuweisung alle Regeln einhalt."""
    result = ValidationResult()

    # Alle Zuweisungen des Mitarbeiters in der Woche laden
    week_start = assignment_date - timedelta(days=assignment_date.weekday())
    week_end = week_start + timedelta(days=6)

    query = select(ShiftAssignment).where(
        ShiftAssignment.employee_id == employee_id,
        ShiftAssignment.date >= week_start,
        ShiftAssignment.date <= week_end,
        ShiftAssignment.status.in_(ACTIVE_SHIFT_STATUSES),
    )
    if exclude_assignment_id:
        query = query.where(ShiftAssignment.id != exclude_assignment_id)

    existing_result = await db.execute(query)
    week_assignments = existing_result.scalars().all()

    # 1. Doppelbelegung am selben Tag pruefen
    same_day = [a for a in week_assignments if a.date == assignment_date]
    if same_day:
        result.add_error(
            f"Mitarbeiter hat bereits eine Schicht am {assignment_date.isoformat()}"
        )

    # 2. Maximale Tagesarbeitszeit
    if shift_template.net_hours > MAX_DAILY_HOURS:
        result.add_error(
            f"Schichtdauer {shift_template.net_hours}h ueberschreitet Maximum von {MAX_DAILY_HOURS}h"
        )

    # 3. Maximale Wochenarbeitszeit
    weekly_hours = sum(
        a.shift_template.net_hours for a in week_assignments
        if a.shift_template
    ) + shift_template.net_hours

    if weekly_hours > MAX_WEEKLY_HOURS:
        result.add_error(
            f"Wochenarbeitszeit {weekly_hours:.1f}h ueberschreitet Maximum von {MAX_WEEKLY_HOURS}h"
        )
    elif weekly_hours > 40:
        result.add_warning(
            f"Wochenarbeitszeit {weekly_hours:.1f}h liegt ueber 40h"
        )

    # 4. Mindestruhezeit (11h zwischen Schichten)
    await _check_rest_time(db, employee_id, shift_template, assignment_date, result, exclude_assignment_id)

    # 5. Maximale aufeinanderfolgende Arbeitstage
    await _check_consecutive_days(db, employee_id, assignment_date, result, exclude_assignment_id)

    return result


async def _check_rest_time(
    db: AsyncSession,
    employee_id: int,
    new_shift: ShiftTemplate,
    assignment_date: date,
    result: ValidationResult,
    exclude_id: Optional[int] = None,
):
    """Prueft die 11h Ruhezeit vor und nach der geplanten Schicht."""
    new_start, new_end = _shift_window(new_shift, assignment_date)

    # Vortag und Folgetag laden
    for delta, label in [(-1, "Vortag"), (1, "Folgetag")]:
        neighbor_date = assignment_date + timedelta(days=delta)
        query = select(ShiftAssignment).where(
            ShiftAssignment.employee_id == employee_id,
            ShiftAssignment.date == neighbor_date,
            ShiftAssignment.status.in_(ACTIVE_SHIFT_STATUSES),
        )
        if exclude_id:
            query = query.where(ShiftAssignment.id != exclude_id)

        neighbor_result = await db.execute(query)
        neighbor = neighbor_result.scalar_one_or_none()

        if neighbor and neighbor.shift_template:
            neighbor_start, neighbor_end = _shift_window(neighbor.shift_template, neighbor_date)
            if delta == -1:
                rest = (new_start - neighbor_end).total_seconds() / 3600
            else:
                rest = (neighbor_start - new_end).total_seconds() / 3600

            if rest < MIN_REST_HOURS:
                result.add_error(
                    f"Ruhezeit zum {label} ({neighbor_date}) nur {rest:.1f}h "
                    f"(Minimum: {MIN_REST_HOURS}h)"
                )


def _shift_window(shift: ShiftTemplate, shift_date: date) -> tuple[datetime, datetime]:
    """Gibt Start und Ende einer Schicht als echte Datumszeiten zurueck."""
    start = datetime.combine(shift_date, shift.start_time)
    end = datetime.combine(shift_date, shift.end_time)
    if shift.crosses_midnight:
        end += timedelta(days=1)
    return start, end


def _calculate_rest_hours(
    previous_shift: ShiftTemplate,
    previous_date: date,
    next_shift: ShiftTemplate,
    next_date: date,
) -> float:
    """Berechnet die Ruhezeit zwischen zwei konkreten Schichten."""
    _, previous_end = _shift_window(previous_shift, previous_date)
    next_start, _ = _shift_window(next_shift, next_date)
    return (next_start - previous_end).total_seconds() / 3600


async def _check_consecutive_days(
    db: AsyncSession,
    employee_id: int,
    assignment_date: date,
    result: ValidationResult,
    exclude_id: Optional[int] = None,
):
    """Prueft ob nicht mehr als 6 Tage am Stueck gearbeitet wird."""
    consecutive = 1  # Der neue Tag zaehlt mit

    # Vorwaerts zaehlen
    for i in range(1, MAX_CONSECUTIVE_DAYS + 1):
        check_date = assignment_date + timedelta(days=i)
        query = select(ShiftAssignment).where(
            ShiftAssignment.employee_id == employee_id,
            ShiftAssignment.date == check_date,
            ShiftAssignment.status.in_(ACTIVE_SHIFT_STATUSES),
        )
        if exclude_id:
            query = query.where(ShiftAssignment.id != exclude_id)
        r = await db.execute(query)
        if r.scalar_one_or_none():
            consecutive += 1
        else:
            break

    # Rueckwaerts zaehlen
    for i in range(1, MAX_CONSECUTIVE_DAYS + 1):
        check_date = assignment_date - timedelta(days=i)
        query = select(ShiftAssignment).where(
            ShiftAssignment.employee_id == employee_id,
            ShiftAssignment.date == check_date,
            ShiftAssignment.status.in_(ACTIVE_SHIFT_STATUSES),
        )
        if exclude_id:
            query = query.where(ShiftAssignment.id != exclude_id)
        r = await db.execute(query)
        if r.scalar_one_or_none():
            consecutive += 1
        else:
            break

    if consecutive > MAX_CONSECUTIVE_DAYS:
        result.add_error(
            f"{consecutive} aufeinanderfolgende Arbeitstage (Maximum: {MAX_CONSECUTIVE_DAYS})"
        )
    elif consecutive == MAX_CONSECUTIVE_DAYS:
        result.add_warning(
            f"{consecutive} aufeinanderfolgende Arbeitstage — Maximum erreicht"
        )


async def check_staffing(
    db: AsyncSession,
    department_id: int,
    check_date: date,
) -> list[dict]:
    """Prueft die Besetzung einer Abteilung gegen die Mindestanforderungen."""
    weekday = check_date.weekday()

    # Anforderungen laden
    req_result = await db.execute(
        select(ShiftRequirement).where(
            ShiftRequirement.department_id == department_id,
            ShiftRequirement.weekday == weekday,
            ShiftRequirement.is_active == True,
        )
    )
    requirements = req_result.scalars().all()

    # Zuweisungen laden
    assign_result = await db.execute(
        select(ShiftAssignment)
        .join(ShiftPlan, ShiftAssignment.plan_id == ShiftPlan.id)
        .where(
            ShiftPlan.department_id == department_id,
            ShiftAssignment.date == check_date,
            ShiftAssignment.status.in_(ACTIVE_SHIFT_STATUSES),
        )
    )
    assignments = assign_result.scalars().all()

    issues = []
    for req in requirements:
        # Zuweisungen fuer diese Schicht zaehlen
        matching = [
            a for a in assignments
            if a.shift_template_id == req.shift_template_id
        ]
        count = len(matching)

        if count < req.min_staff:
            shift_name = req.shift_template.name if req.shift_template else f"Schicht {req.shift_template_id}"
            issues.append({
                "date": check_date.isoformat(),
                "shift": shift_name,
                "required": req.min_staff,
                "assigned": count,
                "missing": req.min_staff - count,
            })

    return issues
