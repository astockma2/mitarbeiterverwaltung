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
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.planning import PlanningMarker, PlanningMarkerKind, TravelRequest, TravelStatus
from app.models.shift import DutyPlanEntry
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
        "Schulung",
        color="#2563EB",
        absence_type=AbsenceType.TRAINING,
        absence_status=AbsenceStatus.APPROVED,
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

    employee_result = await db.execute(select(Employee).where(Employee.is_active == True))
    employees = employee_result.scalars().all()
    employees_by_name = {normalize_name(employee.full_name): employee for employee in employees}

    daily_tokens: dict[tuple[int, date, str], ImportedToken] = {}
    raw_entries: list[tuple[Employee, date, str]] = []
    skipped: dict[str, int] = defaultdict(int)

    for entry in entries:
        employee_name = str(entry.get("employee_name") or "").strip()
        raw_code = str(entry.get("code") or "").strip()
        if not employee_name or not raw_code:
            skipped["invalid_entry"] += 1
            continue

        employee = employees_by_name.get(normalize_name(employee_name))
        if employee is None:
            skipped["unknown_employee"] += 1
            continue

        entry_date = _parse_date(entry["date"])
        raw_entries.append((employee, entry_date, raw_code))
        for token in split_code(raw_code):
            daily_tokens[(employee.id, entry_date, token.code)] = token

    counts = defaultdict(int)

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
    await _import_travel(db, daily_tokens, source, actor_id, counts)
    await _import_markers(db, daily_tokens, source, counts)

    return {
        "source": source,
        "entries_seen": len(entries),
        "tokens_seen": len(daily_tokens),
        "created_or_updated": dict(counts),
        "skipped": dict(skipped),
    }


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
