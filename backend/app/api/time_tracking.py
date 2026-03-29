"""API-Endpoints fuer Zeiterfassung: Stempeln, Zeiten einsehen, Korrekturen."""

import math
from datetime import datetime, date, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.jwt import get_current_user
from app.auth.permissions import is_hr, is_manager
from app.database import get_db
from app.models.employee import Employee
from app.models.time_entry import (
    CorrectionRequest,
    CorrectionStatus,
    EntryStatus,
    EntryType,
    Surcharge,
    TimeEntry,
)
from app.services.audit import log_action
from app.services.time_calculator import (
    calculate_net_hours,
    calculate_surcharges,
    enforce_break_rules,
)

router = APIRouter(prefix="/time", tags=["Zeiterfassung"])


def _utcnow() -> datetime:
    """Gibt die aktuelle UTC-Zeit als naive datetime zurueck (SQLite-kompatibel)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _ensure_naive(dt: datetime) -> datetime:
    """Entfernt Timezone-Info falls vorhanden (fuer SQLite)."""
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


# === Schemas ===


class ClockInRequest(BaseModel):
    notes: Optional[str] = None


class ClockOutRequest(BaseModel):
    break_minutes: Optional[int] = None
    notes: Optional[str] = None


class ManualEntryRequest(BaseModel):
    employee_id: Optional[int] = None  # Nur fuer HR/Admin
    date: date
    clock_in: datetime
    clock_out: datetime
    break_minutes: int = 0
    notes: Optional[str] = None


class CorrectionRequestCreate(BaseModel):
    time_entry_id: int
    field: str  # clock_in, clock_out, break_minutes
    new_value: str
    reason: str


class CorrectionReviewRequest(BaseModel):
    approved: bool


class TimeEntryResponse(BaseModel):
    id: int
    employee_id: int
    date: date
    clock_in: datetime
    clock_out: Optional[datetime]
    break_minutes: int
    net_hours: Optional[float]
    entry_type: str
    status: str
    notes: Optional[str]
    surcharges: list[dict] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class DailySummary(BaseModel):
    date: date
    entries: list[TimeEntryResponse]
    total_hours: float
    total_break_minutes: int


class MonthlySummary(BaseModel):
    year: int
    month: int
    total_hours: float
    target_hours: float
    overtime_hours: float
    work_days: int
    surcharges: dict  # {type: hours}


# === Stempeln ===


@router.post("/clock-in", response_model=TimeEntryResponse)
async def clock_in(
    request: ClockInRequest = ClockInRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Kommen stempeln. Erstellt einen neuen Zeiteintrag."""
    now = _utcnow()
    today = now.date()

    # Pruefen ob bereits eingestempelt (offener Eintrag ohne clock_out)
    result = await db.execute(
        select(TimeEntry).where(
            TimeEntry.employee_id == current_user.id,
            TimeEntry.clock_out.is_(None),
        )
    )
    open_entry = result.scalar_one_or_none()
    if open_entry:
        raise HTTPException(
            status_code=400,
            detail="Bereits eingestempelt. Bitte zuerst ausstempeln.",
        )

    entry = TimeEntry(
        employee_id=current_user.id,
        date=today,
        clock_in=now,
        entry_type=EntryType.REGULAR,
        notes=request.notes,
    )
    db.add(entry)
    await db.flush()

    return _entry_to_response(entry, surcharges_list=[])


@router.post("/clock-out", response_model=TimeEntryResponse)
async def clock_out(
    request: ClockOutRequest = ClockOutRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Gehen stempeln. Schliesst den offenen Zeiteintrag ab."""
    # Offenen Eintrag finden
    result = await db.execute(
        select(TimeEntry).where(
            TimeEntry.employee_id == current_user.id,
            TimeEntry.clock_out.is_(None),
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(
            status_code=400,
            detail="Kein offener Zeiteintrag. Bitte zuerst einstempeln.",
        )

    now = _utcnow()
    entry.clock_out = now

    # Pause: entweder manuell oder nach ArbZG
    break_minutes = request.break_minutes if request.break_minutes is not None else 0
    entry.break_minutes = enforce_break_rules(entry.clock_in, now, break_minutes)

    if request.notes:
        entry.notes = (entry.notes or "") + " " + request.notes

    # Zuschlaege berechnen
    net_hours = calculate_net_hours(entry.clock_in, now, entry.break_minutes)
    surcharge_data = calculate_surcharges(entry.clock_in, now, entry.date, net_hours)

    created_surcharges = []
    for s in surcharge_data:
        surcharge = Surcharge(
            time_entry_id=entry.id,
            type=s["type"],
            hours=s["hours"],
            rate_percent=s["rate_percent"],
        )
        db.add(surcharge)
        created_surcharges.append(surcharge)

    await db.flush()
    return _entry_to_response(entry, surcharges_list=created_surcharges)


@router.get("/status")
async def get_clock_status(
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Gibt den aktuellen Stempel-Status zurueck (eingestempelt oder nicht)."""
    result = await db.execute(
        select(TimeEntry).where(
            TimeEntry.employee_id == current_user.id,
            TimeEntry.clock_out.is_(None),
        )
    )
    open_entry = result.scalar_one_or_none()

    if open_entry:
        elapsed = (_utcnow() - open_entry.clock_in).total_seconds()
        return {
            "clocked_in": True,
            "since": open_entry.clock_in.isoformat(),
            "elapsed_hours": round(elapsed / 3600, 2),
            "entry_id": open_entry.id,
        }
    return {"clocked_in": False}


# === Manuelle Eintraege ===


@router.post("/manual", response_model=TimeEntryResponse, status_code=201)
async def create_manual_entry(
    request: ManualEntryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Manuellen Zeiteintrag erstellen. Mitarbeiter fuer sich selbst, HR fuer alle."""
    target_employee_id = current_user.id
    if request.employee_id and request.employee_id != current_user.id:
        if not is_hr(current_user):
            raise HTTPException(status_code=403, detail="Keine Berechtigung")
        target_employee_id = request.employee_id

    clock_in = _ensure_naive(request.clock_in)
    clock_out = _ensure_naive(request.clock_out)

    if clock_out <= clock_in:
        raise HTTPException(status_code=400, detail="Ende muss nach Beginn liegen")

    break_minutes = enforce_break_rules(clock_in, clock_out, request.break_minutes)
    net_hours = calculate_net_hours(clock_in, clock_out, break_minutes)

    entry = TimeEntry(
        employee_id=target_employee_id,
        date=request.date,
        clock_in=clock_in,
        clock_out=clock_out,
        break_minutes=break_minutes,
        entry_type=EntryType.MANUAL,
        notes=request.notes,
    )
    db.add(entry)
    await db.flush()

    # Zuschlaege
    surcharge_data = calculate_surcharges(clock_in, clock_out, request.date, net_hours)
    created_surcharges = []
    for s in surcharge_data:
        surcharge = Surcharge(
            time_entry_id=entry.id,
            type=s["type"],
            hours=s["hours"],
            rate_percent=s["rate_percent"],
        )
        db.add(surcharge)
        created_surcharges.append(surcharge)

    await db.flush()
    await log_action(db, current_user.id, "CREATE", "time_entries", entry.id)
    return _entry_to_response(entry, surcharges_list=created_surcharges)


# === Zeiten einsehen ===


@router.get("/entries", response_model=list[TimeEntryResponse])
async def list_time_entries(
    employee_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Zeiteintraege auflisten. Eigene oder (als Manager/HR) fuer andere."""
    target_id = employee_id or current_user.id

    if target_id != current_user.id and not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    query = (
        select(TimeEntry)
        .options(selectinload(TimeEntry.surcharges))
        .where(TimeEntry.employee_id == target_id)
    )

    if start_date:
        query = query.where(TimeEntry.date >= start_date)
    if end_date:
        query = query.where(TimeEntry.date <= end_date)

    query = query.order_by(TimeEntry.date.desc(), TimeEntry.clock_in.desc())
    result = await db.execute(query)
    entries = result.scalars().all()

    return [_entry_to_response(e, surcharges_list=e.surcharges) for e in entries]


@router.get("/daily", response_model=DailySummary)
async def get_daily_summary(
    day: date = Query(default=None),
    employee_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Tageszusammenfassung der Arbeitszeit."""
    target_id = employee_id or current_user.id
    if target_id != current_user.id and not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    if day is None:
        day = date.today()

    result = await db.execute(
        select(TimeEntry)
        .options(selectinload(TimeEntry.surcharges))
        .where(TimeEntry.employee_id == target_id, TimeEntry.date == day)
        .order_by(TimeEntry.clock_in)
    )
    entries = result.scalars().all()

    total_hours = sum(e.net_hours or 0 for e in entries)
    total_break = sum(e.break_minutes for e in entries)

    return DailySummary(
        date=day,
        entries=[_entry_to_response(e, surcharges_list=e.surcharges) for e in entries],
        total_hours=round(total_hours, 2),
        total_break_minutes=total_break,
    )


@router.get("/monthly", response_model=MonthlySummary)
async def get_monthly_summary(
    year: int = Query(default=None),
    month: int = Query(default=None, ge=1, le=12),
    employee_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Monatszusammenfassung der Arbeitszeit."""
    target_id = employee_id or current_user.id
    if target_id != current_user.id and not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    now = date.today()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    from app.services.time_calculator import calculate_monthly_target_hours

    # Mitarbeiter laden fuer Soll-Stunden
    emp_result = await db.execute(
        select(Employee).where(Employee.id == target_id)
    )
    employee = emp_result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden")

    # Eintraege des Monats
    from calendar import monthrange
    _, last_day = monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, last_day)

    result = await db.execute(
        select(TimeEntry)
        .options(selectinload(TimeEntry.surcharges))
        .where(
            TimeEntry.employee_id == target_id,
            TimeEntry.date >= start,
            TimeEntry.date <= end,
        )
    )
    entries = result.scalars().all()

    total_hours = sum(e.net_hours or 0 for e in entries)
    target_hours = calculate_monthly_target_hours(employee.weekly_hours, year, month)
    work_days = len(set(e.date for e in entries if e.clock_out is not None))

    # Zuschlaege aggregieren
    surcharge_totals = {}
    for entry in entries:
        for s in entry.surcharges:
            surcharge_totals[s.type.value] = surcharge_totals.get(s.type.value, 0) + s.hours

    return MonthlySummary(
        year=year,
        month=month,
        total_hours=round(total_hours, 2),
        target_hours=target_hours,
        overtime_hours=round(total_hours - target_hours, 2),
        work_days=work_days,
        surcharges=surcharge_totals,
    )


# === Korrekturen ===


@router.post("/corrections", status_code=201)
async def request_correction(
    request: CorrectionRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Korrekturantrag fuer einen Zeiteintrag stellen."""
    if request.field not in ("clock_in", "clock_out", "break_minutes"):
        raise HTTPException(status_code=400, detail="Ungueltiges Feld")

    # Zeiteintrag laden
    result = await db.execute(
        select(TimeEntry).where(TimeEntry.id == request.time_entry_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Zeiteintrag nicht gefunden")

    if entry.employee_id != current_user.id and not is_hr(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    if entry.status == EntryStatus.LOCKED:
        raise HTTPException(status_code=400, detail="Eintrag ist gesperrt (Monatsabschluss)")

    old_value = str(getattr(entry, request.field))

    correction = CorrectionRequest(
        time_entry_id=entry.id,
        employee_id=current_user.id,
        field=request.field,
        old_value=old_value,
        new_value=request.new_value,
        reason=request.reason,
    )
    db.add(correction)
    await db.flush()

    return {"id": correction.id, "status": "PENDING", "message": "Korrekturantrag erstellt"}


@router.get("/corrections/pending", response_model=list[dict])
async def list_pending_corrections(
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Offene Korrekturantraege auflisten (fuer Vorgesetzte/HR)."""
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    result = await db.execute(
        select(CorrectionRequest)
        .where(CorrectionRequest.status == CorrectionStatus.PENDING)
        .order_by(CorrectionRequest.created_at.desc())
    )
    corrections = result.scalars().all()

    return [
        {
            "id": c.id,
            "time_entry_id": c.time_entry_id,
            "employee_id": c.employee_id,
            "employee_name": c.employee.full_name if c.employee else None,
            "field": c.field,
            "old_value": c.old_value,
            "new_value": c.new_value,
            "reason": c.reason,
            "created_at": c.created_at.isoformat(),
        }
        for c in corrections
    ]


@router.post("/corrections/{correction_id}/review")
async def review_correction(
    correction_id: int,
    request: CorrectionReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Korrekturantrag genehmigen oder ablehnen."""
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    result = await db.execute(
        select(CorrectionRequest).where(CorrectionRequest.id == correction_id)
    )
    correction = result.scalar_one_or_none()
    if correction is None:
        raise HTTPException(status_code=404, detail="Korrekturantrag nicht gefunden")

    if correction.status != CorrectionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Antrag bereits bearbeitet")

    if request.approved:
        correction.status = CorrectionStatus.APPROVED
        correction.reviewed_by = current_user.id

        # Aenderung am Zeiteintrag durchfuehren
        entry_result = await db.execute(
            select(TimeEntry).where(TimeEntry.id == correction.time_entry_id)
        )
        entry = entry_result.scalar_one()

        if correction.field == "break_minutes":
            setattr(entry, correction.field, int(correction.new_value))
        else:
            setattr(entry, correction.field, datetime.fromisoformat(correction.new_value))

        entry.entry_type = EntryType.CORRECTION

        await log_action(
            db, current_user.id, "CORRECTION_APPROVED", "time_entries", entry.id,
            {correction.field: {"old": correction.old_value, "new": correction.new_value}},
        )
    else:
        correction.status = CorrectionStatus.REJECTED
        correction.reviewed_by = current_user.id

    return {
        "id": correction.id,
        "status": correction.status.value,
        "message": "Genehmigt" if request.approved else "Abgelehnt",
    }


# === Hilfsfunktionen ===


def _entry_to_response(entry: TimeEntry, surcharges_list=None) -> TimeEntryResponse:
    surcharges = []
    if surcharges_list is not None:
        surcharges = [
            {
                "type": s.type.value if hasattr(s.type, 'value') else s.type,
                "hours": s.hours,
                "rate_percent": s.rate_percent,
            }
            for s in surcharges_list
        ]

    return TimeEntryResponse(
        id=entry.id,
        employee_id=entry.employee_id,
        date=entry.date,
        clock_in=entry.clock_in,
        clock_out=entry.clock_out,
        break_minutes=entry.break_minutes,
        net_hours=entry.net_hours,
        entry_type=entry.entry_type.value,
        status=entry.status.value,
        notes=entry.notes,
        surcharges=surcharges,
        created_at=entry.created_at,
    )
