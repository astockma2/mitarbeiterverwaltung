"""Bereinigt Dienstplan-Konflikte nach Importen oder manuellen Aenderungen."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.planning import TravelRequest, TravelStatus
from app.models.shift import ShiftAssignment, ShiftStatus, ShiftTemplate
from app.models.time_entry import Absence, AbsenceStatus


ACTIVE_TRAVEL_STATUSES = (
    TravelStatus.REQUESTED,
    TravelStatus.MANAGER_APPROVED,
    TravelStatus.APPROVED,
    TravelStatus.APPROVED_LEGACY,
)


async def reconcile_blocked_normal_shifts(db: AsyncSession) -> dict[str, int]:
    """Setzt Normaldienst D auf CANCELLED, wenn eine Abwesenheit den Tag blockiert."""
    result = await db.execute(
        select(ShiftAssignment)
        .join(ShiftTemplate, ShiftAssignment.shift_template_id == ShiftTemplate.id)
        .where(
            ShiftAssignment.status.in_(
                [ShiftStatus.PLANNED, ShiftStatus.CONFIRMED, ShiftStatus.SWAPPED]
            ),
            ShiftTemplate.short_code == "D",
        )
    )
    assignments = result.scalars().all()
    if not assignments:
        return {"checked": 0, "cancelled": 0}

    employee_ids = {assignment.employee_id for assignment in assignments}
    start = min(assignment.date for assignment in assignments)
    end = max(assignment.date for assignment in assignments)
    blocked_dates: dict[int, set[date]] = defaultdict(set)

    absence_result = await db.execute(
        select(Absence).where(
            Absence.employee_id.in_(employee_ids),
            Absence.status.in_([AbsenceStatus.REQUESTED, AbsenceStatus.APPROVED]),
            Absence.start_date <= end,
            Absence.end_date >= start,
        )
    )
    for absence in absence_result.scalars().all():
        for day in _date_range(max(absence.start_date, start), min(absence.end_date, end)):
            blocked_dates[absence.employee_id].add(day)

    travel_result = await db.execute(
        select(TravelRequest).where(
            TravelRequest.employee_id.in_(employee_ids),
            TravelRequest.status.in_(ACTIVE_TRAVEL_STATUSES),
            TravelRequest.start_date <= end,
            TravelRequest.end_date >= start,
        )
    )
    for travel in travel_result.scalars().all():
        for day in _date_range(max(travel.start_date, start), min(travel.end_date, end)):
            blocked_dates[travel.employee_id].add(day)

    cancelled = 0
    for assignment in assignments:
        if assignment.date not in blocked_dates.get(assignment.employee_id, set()):
            continue
        assignment.status = ShiftStatus.CANCELLED
        assignment.notes = (
            f"{assignment.notes or ''}\n"
            "Automatisch bereinigt: Abwesenheit/Dienstreise schliesst Dienst aus"
        ).strip()
        cancelled += 1

    return {"checked": len(assignments), "cancelled": cancelled}


def _date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


async def main() -> None:
    async with async_session() as db:
        result = await reconcile_blocked_normal_shifts(db)
        await db.commit()
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
