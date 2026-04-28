"""Importiert bereinigte Planungsdaten aus Excel-Ausleitungen.

Die Original-Excel-Dateien enthalten neben der Planung auch Kontakthinweise.
Dieser Import erwartet deshalb bereits bereinigte JSON-Eintraege mit Name, Datum
und Zellcode und erzeugt daraus strukturierte Planungsobjekte.
"""

from __future__ import annotations

import json
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.planning import PlanningMarker, PlanningMarkerKind, TravelRequest, TravelStatus
from app.models.shift import (
    DutyPlanEntry,
    PlanStatus,
    ShiftAssignment,
    ShiftPlan,
    ShiftStatus,
    ShiftTemplate,
)
from app.models.time_entry import Absence, AbsenceStatus, AbsenceType


@dataclass(frozen=True)
class ImportedToken:
    code: str
    label: str
    kind: PlanningMarkerKind | None = None
    color: str = "#64748B"
    absence_type: AbsenceType | None = None
    absence_status: AbsenceStatus | None = None
    is_travel: bool = False


TOKEN_MAP: dict[str, ImportedToken] = {
    "U": ImportedToken(
        "U",
        "Urlaub",
        color="#FACC15",
        absence_type=AbsenceType.VACATION,
        absence_status=AbsenceStatus.APPROVED,
    ),
    "UG": ImportedToken(
        "Ug",
        "Urlaub geplant",
        color="#0EA5E9",
        absence_type=AbsenceType.VACATION,
        absence_status=AbsenceStatus.REQUESTED,
    ),
    "A": ImportedToken(
        "A",
        "Arbeitszeitausgleich",
        color="#FB7185",
        absence_type=AbsenceType.COMP_TIME,
        absence_status=AbsenceStatus.APPROVED,
    ),
    "S": ImportedToken(
        "S",
        "Schule Azubi",
        color="#2563EB",
        kind=PlanningMarkerKind.INFO,
    ),
    "B": ImportedToken(
        "B",
        "Bereitschaft",
        kind=PlanningMarkerKind.DUTY,
        color="#C2410C",
    ),
    "I": ImportedToken(
        "I",
        "Ilmenau",
        kind=PlanningMarkerKind.DUTY,
        color="#F97316",
    ),
    "H": ImportedToken(
        "H",
        "Hotlinedienst",
        kind=PlanningMarkerKind.DUTY,
        color="#16A34A",
    ),
    "M": ImportedToken(
        "M",
        "MVZ",
        kind=PlanningMarkerKind.DUTY,
        color="#EAB308",
    ),
    "DR": ImportedToken("DR", "Dienstreise", color="#65A30D", is_travel=True),
    "K": ImportedToken(
        "K",
        "Kur",
        kind=PlanningMarkerKind.ABSENCE,
        color="#FB923C",
    ),
    "SU": ImportedToken(
        "su",
        "Security Update Day",
        kind=PlanningMarkerKind.INFO,
        color="#F43F5E",
    ),
    "T": ImportedToken(
        "T",
        "Teammeeting",
        kind=PlanningMarkerKind.INFO,
        color="#1D4ED8",
    ),
    "EZ": ImportedToken(
        "Ez",
        "Elternzeit",
        kind=PlanningMarkerKind.ABSENCE,
        color="#D97706",
    ),
    "TSC": ImportedToken(
        "TSC",
        "Zeitreduzierung TSC",
        kind=PlanningMarkerKind.INFO,
        color="#315D1E",
    ),
}

COMPOSITE_CODES: dict[str, list[str]] = {
    "BH": ["B", "H"],
    "BI": ["B", "I"],
    "IB": ["I", "B"],
    "IH": ["I", "H"],
    "HB": ["H", "B"],
    "BT": ["B", "T"],
    "HT": ["H", "T"],
    "BHT": ["B", "H", "T"],
}


def normalize_name(value: str) -> str:
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "ß": "ss",
    }
    for old, new in replacements.items():
        value = value.replace(old, new)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(value.lower().split())


def split_code(raw_code: str) -> list[ImportedToken]:
    code = raw_code.strip()
    if not code:
        return []
    normalized = code.upper()
    if normalized == "DR":
        return [TOKEN_MAP["DR"]]
    if normalized in COMPOSITE_CODES:
        return [TOKEN_MAP[token] for token in COMPOSITE_CODES[normalized]]
    if normalized in TOKEN_MAP:
        return [TOKEN_MAP[normalized]]
    return [
        ImportedToken(
            code=code,
            label=f"Importcode {code}",
            kind=PlanningMarkerKind.INFO,
            color="#64748B",
        )
    ]


def _daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _parse_date(value: str | date) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value[:10])


async def import_planning_payload(
    db: AsyncSession,
    payload: dict[str, Any],
    actor_id: int | None = None,
) -> dict[str, Any]:
    source = str(payload.get("source") or "excel-import")
    entries = payload.get("entries") or []
    roster_names, roster_years = _extract_roster(payload)

    employee_result = await db.execute(select(Employee).where(Employee.is_active == True))
    employees = employee_result.scalars().all()
    employees_by_name = {normalize_name(employee.full_name): employee for employee in employees}

    daily_tokens: dict[tuple[int, date, str], ImportedToken] = {}
    raw_entries: list[tuple[Employee, date, str]] = []
    baseline_employees: dict[int, Employee] = {}
    baseline_years: set[int] = set(roster_years)
    skipped: dict[str, int] = defaultdict(int)

    for entry in entries:
        employee_name = str(entry.get("employee_name") or "").strip()
        raw_code = str(entry.get("code") or "").strip()
        if not employee_name or not raw_code:
            skipped["invalid_entry"] += 1
            continue

        entry_date = _parse_date(entry["date"])
        baseline_years.add(entry_date.year)

        employee = employees_by_name.get(normalize_name(employee_name))
        if employee is None:
            skipped["unknown_employee"] += 1
            continue

        baseline_employees[employee.id] = employee
        raw_entries.append((employee, entry_date, raw_code))
        for token in split_code(raw_code):
            daily_tokens[(employee.id, entry_date, token.code)] = token

    for employee_name in roster_names:
        employee = employees_by_name.get(normalize_name(employee_name))
        if employee is None:
            skipped["unknown_roster_employee"] += 1
            continue
        baseline_employees[employee.id] = employee

    counts = defaultdict(int)
    blocking_dates = _blocking_dates_by_employee(daily_tokens)

    for employee, entry_date, raw_code in raw_entries:
        existing_result = await db.execute(
            select(DutyPlanEntry).where(
                DutyPlanEntry.employee_id == employee.id,
                DutyPlanEntry.date == entry_date,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            existing.code = raw_code[:8]
            existing.note = f"Import {source}"
            existing.updated_by = actor_id
        else:
            db.add(
                DutyPlanEntry(
                    employee_id=employee.id,
                    date=entry_date,
                    code=raw_code[:8],
                    note=f"Import {source}",
                    created_by=actor_id,
                    updated_by=actor_id,
                )
            )
        counts["duty_plan_entries"] += 1

    await _import_absences(db, daily_tokens, source, counts, skipped)
    await _cancel_imported_school_absences(db, daily_tokens, source, counts)
    await _import_travel(db, daily_tokens, source, actor_id, counts)
    await _import_markers(db, daily_tokens, source, counts)
    await _cancel_blocked_normal_assignments(db, blocking_dates, source, counts)
    await _ensure_normal_weekday_assignments(
        db,
        list(baseline_employees.values()),
        baseline_years,
        blocking_dates,
        source,
        actor_id,
        counts,
        skipped,
    )

    return {
        "source": source,
        "entries_seen": len(entries),
        "tokens_seen": len(daily_tokens),
        "created_or_updated": dict(counts),
        "skipped": dict(skipped),
    }


def _extract_roster(payload: dict[str, Any]) -> tuple[set[str], set[int]]:
    names: set[str] = set()
    years: set[int] = set()

    for raw_year in payload.get("years") or []:
        try:
            years.add(int(raw_year))
        except (TypeError, ValueError):
            continue

    for item in payload.get("employees") or []:
        if isinstance(item, str):
            name = item.strip()
            if name:
                names.add(name)
            continue
        if not isinstance(item, dict):
            continue
        name = str(item.get("employee_name") or item.get("name") or "").strip()
        if name:
            names.add(name)
        try:
            if item.get("year"):
                years.add(int(item["year"]))
        except (TypeError, ValueError):
            continue

    return names, years


def _blocking_dates_by_employee(
    daily_tokens: dict[tuple[int, date, str], ImportedToken],
) -> dict[int, set[date]]:
    dates: dict[int, set[date]] = defaultdict(set)
    for (employee_id, entry_date, _), token in daily_tokens.items():
        if token.absence_type or token.is_travel or token.kind == PlanningMarkerKind.ABSENCE:
            dates[employee_id].add(entry_date)
    return dates


async def _import_absences(
    db: AsyncSession,
    daily_tokens: dict[tuple[int, date, str], ImportedToken],
    source: str,
    counts: defaultdict[str, int],
    skipped: defaultdict[str, int],
) -> None:
    by_employee_type_status: dict[tuple[int, AbsenceType, AbsenceStatus], list[date]] = defaultdict(list)
    for (employee_id, entry_date, _), token in daily_tokens.items():
        if token.absence_type and token.absence_status:
            by_employee_type_status[(employee_id, token.absence_type, token.absence_status)].append(
                entry_date
            )

    for (employee_id, absence_type, status), dates in by_employee_type_status.items():
        for start, end in _group_contiguous(sorted(set(dates))):
            overlap_result = await db.execute(
                select(Absence).where(
                    Absence.employee_id == employee_id,
                    Absence.status.in_([AbsenceStatus.REQUESTED, AbsenceStatus.APPROVED]),
                    Absence.start_date <= end,
                    Absence.end_date >= start,
                )
            )
            overlaps = overlap_result.scalars().all()
            exact = [
                item
                for item in overlaps
                if item.type == absence_type
                and item.status == status
                and item.start_date == start
                and item.end_date == end
            ]
            if exact:
                skipped["existing_absence"] += 1
                continue
            if overlaps:
                skipped["absence_overlap"] += 1
                continue

            db.add(
                Absence(
                    employee_id=employee_id,
                    type=absence_type,
                    start_date=start,
                    end_date=end,
                    days=float(sum(1 for day in _daterange(start, end) if day.weekday() < 5)),
                    status=status,
                    notes=f"Import {source}",
                )
            )
            counts["absences"] += 1


async def _cancel_imported_school_absences(
    db: AsyncSession,
    daily_tokens: dict[tuple[int, date, str], ImportedToken],
    source: str,
    counts: defaultdict[str, int],
) -> None:
    school_dates: dict[int, set[date]] = defaultdict(set)
    for (employee_id, entry_date, _), token in daily_tokens.items():
        if token.code == "S":
            school_dates[employee_id].add(entry_date)

    for employee_id, dates in school_dates.items():
        if not dates:
            continue
        start = min(dates)
        end = max(dates)
        result = await db.execute(
            select(Absence).where(
                Absence.employee_id == employee_id,
                Absence.type == AbsenceType.TRAINING,
                Absence.status.in_([AbsenceStatus.REQUESTED, AbsenceStatus.APPROVED]),
                Absence.notes == f"Import {source}",
                Absence.start_date <= end,
                Absence.end_date >= start,
            )
        )
        for absence in result.scalars().all():
            if any(absence.start_date <= day <= absence.end_date for day in dates):
                absence.status = AbsenceStatus.CANCELLED
                counts["cancelled_school_absences"] += 1


async def _import_travel(
    db: AsyncSession,
    daily_tokens: dict[tuple[int, date, str], ImportedToken],
    source: str,
    actor_id: int | None,
    counts: defaultdict[str, int],
) -> None:
    by_employee: dict[int, list[date]] = defaultdict(list)
    for (employee_id, entry_date, _), token in daily_tokens.items():
        if token.is_travel:
            by_employee[employee_id].append(entry_date)

    for employee_id, dates in by_employee.items():
        for start, end in _group_contiguous(sorted(set(dates))):
            existing_result = await db.execute(
                select(TravelRequest).where(
                    TravelRequest.employee_id == employee_id,
                    TravelRequest.start_date == start,
                    TravelRequest.end_date == end,
                    TravelRequest.source == source,
                )
            )
            if existing_result.scalar_one_or_none():
                continue

            db.add(
                TravelRequest(
                    employee_id=employee_id,
                    start_date=start,
                    end_date=end,
                    destination="Dienstreise",
                    purpose="Importierte Dienstreise aus Urlaubsplanung",
                    status=TravelStatus.APPROVED_LEGACY,
                    requested_by=actor_id or employee_id,
                    hr_approved_by=actor_id,
                    source=source,
                )
            )
            counts["travel_requests"] += 1


async def _import_markers(
    db: AsyncSession,
    daily_tokens: dict[tuple[int, date, str], ImportedToken],
    source: str,
    counts: defaultdict[str, int],
) -> None:
    for (employee_id, entry_date, _), token in daily_tokens.items():
        if not token.kind:
            continue
        existing_result = await db.execute(
            select(PlanningMarker).where(
                PlanningMarker.employee_id == employee_id,
                PlanningMarker.date == entry_date,
                PlanningMarker.code == token.code,
                PlanningMarker.source == source,
            )
        )
        if existing_result.scalar_one_or_none():
            continue
        db.add(
            PlanningMarker(
                employee_id=employee_id,
                date=entry_date,
                code=token.code,
                label=token.label,
                kind=token.kind,
                color=token.color,
                source=source,
            )
        )
        counts["planning_markers"] += 1


async def _cancel_blocked_normal_assignments(
    db: AsyncSession,
    blocking_dates: dict[int, set[date]],
    source: str,
    counts: defaultdict[str, int],
) -> None:
    employee_ids = [employee_id for employee_id, dates in blocking_dates.items() if dates]
    if not employee_ids:
        return

    all_dates = [day for dates in blocking_dates.values() for day in dates]
    start = min(all_dates)
    end = max(all_dates)
    result = await db.execute(
        select(ShiftAssignment)
        .join(ShiftTemplate, ShiftAssignment.shift_template_id == ShiftTemplate.id)
        .where(
            ShiftAssignment.employee_id.in_(employee_ids),
            ShiftAssignment.date >= start,
            ShiftAssignment.date <= end,
            ShiftAssignment.status.in_(
                [ShiftStatus.PLANNED, ShiftStatus.CONFIRMED, ShiftStatus.SWAPPED]
            ),
            ShiftTemplate.short_code == "D",
        )
    )
    for assignment in result.scalars().all():
        if assignment.date not in blocking_dates.get(assignment.employee_id, set()):
            continue
        assignment.status = ShiftStatus.CANCELLED
        assignment.notes = f"{assignment.notes or ''}\nBlockiert durch Import-Abwesenheit {source}".strip()
        counts["cancelled_blocked_normal_shifts"] += 1


async def _ensure_normal_weekday_assignments(
    db: AsyncSession,
    employees: list[Employee],
    years: set[int],
    blocking_dates: dict[int, set[date]],
    source: str,
    actor_id: int | None,
    counts: defaultdict[str, int],
    skipped: defaultdict[str, int],
) -> None:
    if not employees or not years:
        return

    normal_template = await _ensure_normal_shift_template(db)
    creator_id = actor_id or employees[0].id
    employee_ids = [employee.id for employee in employees]

    for year in sorted(years):
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        existing_result = await db.execute(
            select(ShiftAssignment.employee_id, ShiftAssignment.date).where(
                ShiftAssignment.employee_id.in_(employee_ids),
                ShiftAssignment.date >= year_start,
                ShiftAssignment.date <= year_end,
                ShiftAssignment.status.in_(
                    [ShiftStatus.PLANNED, ShiftStatus.CONFIRMED, ShiftStatus.SWAPPED]
                ),
            )
        )
        existing_assignments = {(employee_id, assignment_date) for employee_id, assignment_date in existing_result.all()}
        plan_cache: dict[tuple[int, int], ShiftPlan] = {}

        for employee in employees:
            if employee.department_id is None:
                skipped["normal_shift_no_department"] += 1
                continue

            for current in _daterange(year_start, year_end):
                if current.weekday() >= 5:
                    continue
                if current in blocking_dates.get(employee.id, set()):
                    skipped["normal_shift_blocked_by_absence"] += 1
                    continue
                if (employee.id, current) in existing_assignments:
                    skipped["existing_normal_shift"] += 1
                    continue

                cache_key = (employee.department_id, current.month)
                plan = plan_cache.get(cache_key)
                if plan is None:
                    plan = await _ensure_shift_plan(
                        db,
                        department_id=employee.department_id,
                        year=current.year,
                        month=current.month,
                        creator_id=creator_id,
                    )
                    plan_cache[cache_key] = plan

                db.add(
                    ShiftAssignment(
                        plan_id=plan.id,
                        employee_id=employee.id,
                        shift_template_id=normal_template.id,
                        date=current,
                        status=ShiftStatus.CONFIRMED,
                        notes=f"Import {source}: Normaldienst 07:00-15:30, 30 Min Pause",
                    )
                )
                existing_assignments.add((employee.id, current))
                counts["normal_shift_assignments"] += 1


async def _ensure_normal_shift_template(db: AsyncSession) -> ShiftTemplate:
    result = await db.execute(
        select(ShiftTemplate)
        .where(ShiftTemplate.short_code == "D")
        .order_by(ShiftTemplate.id)
        .limit(1)
    )
    template = result.scalars().first()
    if template is None:
        template = ShiftTemplate(
            name="Normaldienst",
            short_code="D",
            start_time=time(7, 0),
            end_time=time(15, 30),
            break_minutes=30,
            crosses_midnight=False,
            color="#2563EB",
            department_id=None,
            is_active=True,
        )
        db.add(template)
        await db.flush()
        return template

    template.name = "Normaldienst"
    template.start_time = time(7, 0)
    template.end_time = time(15, 30)
    template.break_minutes = 30
    template.crosses_midnight = False
    template.color = "#2563EB"
    template.is_active = True
    return template


async def _ensure_shift_plan(
    db: AsyncSession,
    department_id: int,
    year: int,
    month: int,
    creator_id: int,
) -> ShiftPlan:
    result = await db.execute(
        select(ShiftPlan)
        .where(
            ShiftPlan.department_id == department_id,
            ShiftPlan.year == year,
            ShiftPlan.month == month,
        )
        .order_by(ShiftPlan.id)
        .limit(1)
    )
    plan = result.scalars().first()
    if plan is not None:
        return plan

    plan = ShiftPlan(
        department_id=department_id,
        year=year,
        month=month,
        status=PlanStatus.PUBLISHED,
        created_by=creator_id,
        published_at=datetime.utcnow(),
    )
    db.add(plan)
    await db.flush()
    return plan


def _group_contiguous(dates: list[date]) -> list[tuple[date, date]]:
    if not dates:
        return []

    groups: list[tuple[date, date]] = []
    start = dates[0]
    previous = dates[0]

    for current in dates[1:]:
        if current == previous + timedelta(days=1):
            previous = current
            continue
        groups.append((start, previous))
        start = current
        previous = current

    groups.append((start, previous))
    return groups


async def import_planning_payload_file(
    db: AsyncSession,
    path: str | Path,
    actor_id: int | None = None,
) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return await import_planning_payload(db, payload, actor_id=actor_id)
