"""API-Endpoints fuer Abwesenheiten: Urlaub, Krankheit, Fortbildung."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user
from app.auth.permissions import is_hr, is_manager
from app.database import get_db
from app.models.employee import Employee
from app.models.time_entry import Absence, AbsenceStatus, AbsenceType
from app.services.audit import log_action

router = APIRouter(prefix="/absences", tags=["Abwesenheiten"])


# === Schemas ===


class AbsenceCreateRequest(BaseModel):
    type: AbsenceType
    start_date: date
    end_date: date
    days: Optional[float] = None  # Wird berechnet falls nicht angegeben
    notes: Optional[str] = None


class AbsenceResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    type: str
    start_date: date
    end_date: date
    days: float
    status: str
    notes: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}


class AbsenceReviewRequest(BaseModel):
    approved: bool
    notes: Optional[str] = None


# === Endpoints ===


@router.post("", response_model=AbsenceResponse, status_code=201)
async def create_absence(
    request: AbsenceCreateRequest,
    employee_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Abwesenheit / Urlaubsantrag erstellen."""
    target_id = employee_id or current_user.id

    if target_id != current_user.id and not is_hr(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    if request.end_date < request.start_date:
        raise HTTPException(status_code=400, detail="Enddatum muss nach Startdatum liegen")

    # Arbeitstage berechnen
    days = request.days
    if days is None:
        days = _count_workdays(request.start_date, request.end_date)

    # Ueberschneidung pruefen
    result = await db.execute(
        select(Absence).where(
            Absence.employee_id == target_id,
            Absence.status.in_([AbsenceStatus.REQUESTED, AbsenceStatus.APPROVED]),
            Absence.start_date <= request.end_date,
            Absence.end_date >= request.start_date,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Ueberschneidung mit bestehender Abwesenheit",
        )

    # Krankmeldung wird sofort genehmigt
    initial_status = AbsenceStatus.REQUESTED
    if request.type == AbsenceType.SICK:
        initial_status = AbsenceStatus.APPROVED

    absence = Absence(
        employee_id=target_id,
        type=request.type,
        start_date=request.start_date,
        end_date=request.end_date,
        days=days,
        status=initial_status,
        notes=request.notes,
    )
    db.add(absence)
    await db.flush()

    await log_action(db, current_user.id, "CREATE", "absences", absence.id)

    return _absence_to_response(absence)


@router.get("", response_model=list[AbsenceResponse])
async def list_absences(
    employee_id: Optional[int] = None,
    status: Optional[AbsenceStatus] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Abwesenheiten auflisten."""
    target_id = employee_id or current_user.id

    if target_id != current_user.id and not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    query = select(Absence).where(Absence.employee_id == target_id)

    if status:
        query = query.where(Absence.status == status)
    if year:
        query = query.where(
            Absence.start_date >= date(year, 1, 1),
            Absence.start_date <= date(year, 12, 31),
        )

    query = query.order_by(Absence.start_date.desc())
    result = await db.execute(query)
    absences = result.scalars().all()

    return [_absence_to_response(a) for a in absences]


@router.get("/pending", response_model=list[AbsenceResponse])
async def list_pending_absences(
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Offene Abwesenheitsantraege (fuer Vorgesetzte/HR)."""
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    result = await db.execute(
        select(Absence)
        .where(Absence.status == AbsenceStatus.REQUESTED)
        .order_by(Absence.created_at.desc())
    )
    absences = result.scalars().all()
    return [_absence_to_response(a) for a in absences]


@router.post("/{absence_id}/review")
async def review_absence(
    absence_id: int,
    request: AbsenceReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Abwesenheitsantrag genehmigen oder ablehnen."""
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    result = await db.execute(
        select(Absence).where(Absence.id == absence_id)
    )
    absence = result.scalar_one_or_none()
    if absence is None:
        raise HTTPException(status_code=404, detail="Antrag nicht gefunden")

    if absence.status != AbsenceStatus.REQUESTED:
        raise HTTPException(status_code=400, detail="Antrag bereits bearbeitet")

    if request.approved:
        absence.status = AbsenceStatus.APPROVED
        absence.approved_by = current_user.id
    else:
        absence.status = AbsenceStatus.REJECTED

    if request.notes:
        absence.notes = (absence.notes or "") + f" | {request.notes}"

    await log_action(
        db, current_user.id,
        "APPROVED" if request.approved else "REJECTED",
        "absences", absence_id,
    )

    return {
        "id": absence.id,
        "status": absence.status.value,
        "message": "Genehmigt" if request.approved else "Abgelehnt",
    }


@router.delete("/{absence_id}")
async def cancel_absence(
    absence_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Abwesenheitsantrag stornieren (nur eigene, nur wenn noch nicht abgeschlossen)."""
    result = await db.execute(
        select(Absence).where(Absence.id == absence_id)
    )
    absence = result.scalar_one_or_none()
    if absence is None:
        raise HTTPException(status_code=404, detail="Antrag nicht gefunden")

    if absence.employee_id != current_user.id and not is_hr(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    if absence.status not in (AbsenceStatus.REQUESTED, AbsenceStatus.APPROVED):
        raise HTTPException(status_code=400, detail="Kann nicht mehr storniert werden")

    absence.status = AbsenceStatus.CANCELLED
    await log_action(db, current_user.id, "CANCELLED", "absences", absence_id)

    return {"message": "Antrag storniert"}


@router.get("/vacation-balance")
async def get_vacation_balance(
    employee_id: Optional[int] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Urlaubskonto: Anspruch, genommen, offen."""
    target_id = employee_id or current_user.id
    if target_id != current_user.id and not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    if year is None:
        year = date.today().year

    # Standard-Urlaubsanspruch (konfigurierbar, hier 30 Tage)
    annual_entitlement = 30.0

    # Genommene / genehmigte Urlaubstage
    result = await db.execute(
        select(Absence).where(
            Absence.employee_id == target_id,
            Absence.type == AbsenceType.VACATION,
            Absence.status.in_([AbsenceStatus.APPROVED, AbsenceStatus.REQUESTED]),
            Absence.start_date >= date(year, 1, 1),
            Absence.start_date <= date(year, 12, 31),
        )
    )
    absences = result.scalars().all()

    taken = sum(a.days for a in absences if a.status == AbsenceStatus.APPROVED)
    pending = sum(a.days for a in absences if a.status == AbsenceStatus.REQUESTED)
    remaining = annual_entitlement - taken - pending

    return {
        "year": year,
        "entitlement": annual_entitlement,
        "taken": taken,
        "pending": pending,
        "remaining": remaining,
    }


# === Hilfsfunktionen ===


def _count_workdays(start: date, end: date) -> float:
    """Zaehlt Arbeitstage (Mo-Fr) im Zeitraum."""
    from app.services.time_calculator import get_holidays

    holidays = get_holidays(start.year)
    if start.year != end.year:
        holidays |= get_holidays(end.year)

    count = 0
    current = start
    from datetime import timedelta
    while current <= end:
        if current.weekday() < 5 and current not in holidays:
            count += 1
        current += timedelta(days=1)
    return float(count)


def _absence_to_response(absence: Absence) -> AbsenceResponse:
    employee_name = None
    if absence.employee:
        employee_name = absence.employee.full_name

    return AbsenceResponse(
        id=absence.id,
        employee_id=absence.employee_id,
        employee_name=employee_name,
        type=absence.type.value,
        start_date=absence.start_date,
        end_date=absence.end_date,
        days=absence.days,
        status=absence.status.value,
        notes=absence.notes,
        created_at=absence.created_at.isoformat(),
    )
