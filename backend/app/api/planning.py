"""Gemeinsame Planungs-API fuer Jahres-/Monatsansicht, Marker und Dienstreisen."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.jwt import get_current_user
from app.auth.permissions import is_hr, is_manager
from app.database import get_db
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
from app.services.audit import log_action
from app.services.planning_import import import_planning_payload

router = APIRouter(prefix="/planning", tags=["Planung"])


class PlanningEventResponse(BaseModel):
    id: int
    type: str
    code: str
    label: str
    status: str
    color: str
    source: Optional[str] = None


class PlanningDayResponse(BaseModel):
    date: date
    events: list[PlanningEventResponse]


class PlanningEmployeeResponse(BaseModel):
    id: int
    name: str
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    vacation_days_per_year: int
    days: list[PlanningDayResponse]


class PlanningCalendarResponse(BaseModel):
    start_date: date
    end_date: date
    days: list[date]
    employees: list[PlanningEmployeeResponse]


class TravelCreateRequest(BaseModel):
    start_date: date
    end_date: date
    destination: str
    purpose: str
    employee_id: Optional[int] = None
    cost_center: Optional[str] = None
    transport_type: Optional[str] = None
    estimated_costs: Optional[float] = None


class PlanningCellUpsert(BaseModel):
    employee_id: int
    date: date
    code: Optional[str] = None


class PlanningCellBulkUpsert(BaseModel):
    entries: list[PlanningCellUpsert]


class PlanningCellResponse(BaseModel):
    employee_id: int
    date: date
    code: Optional[str] = None
    status: str


class TravelResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    start_date: date
    end_date: date
    destination: str
    purpose: str
    cost_center: Optional[str] = None
    transport_type: Optional[str] = None
    estimated_costs: Optional[float] = None
    status: str
    review_notes: Optional[str] = None
    source: Optional[str] = None
    created_at: str


class TravelReviewRequest(BaseModel):
    approved: bool
    final_approval: bool = False
    notes: Optional[str] = None


class PlanningImportRequest(BaseModel):
    source: str
    entries: list[dict[str, Any]]
    employees: list[dict[str, Any] | str] = Field(default_factory=list)
    years: list[int] = Field(default_factory=list)


ACTIVE_TRAVEL_STATUSES = (
    TravelStatus.REQUESTED,
    TravelStatus.MANAGER_APPROVED,
    TravelStatus.APPROVED,
    TravelStatus.APPROVED_LEGACY,
)

MANUAL_SOURCE = "planung-manual"

ABSENCE_CELL_CODES: dict[str, tuple[str, AbsenceType, AbsenceStatus, str]] = {
    "U": ("Urlaub", AbsenceType.VACATION, AbsenceStatus.APPROVED, "#FACC15"),
    "Ug": ("Urlaub geplant", AbsenceType.VACATION, AbsenceStatus.REQUESTED, "#0EA5E9"),
    "A": ("Arbeitszeitausgleich", AbsenceType.COMP_TIME, AbsenceStatus.APPROVED, "#FB7185"),
}

MARKER_CELL_CODES: dict[str, tuple[str, PlanningMarkerKind, str]] = {
    "B": ("Bereitschaft", PlanningMarkerKind.DUTY, "#C2410C"),
    "H": ("Hotlinedienst", PlanningMarkerKind.DUTY, "#16A34A"),
    "T": ("Teammeeting", PlanningMarkerKind.INFO, "#1D4ED8"),
    "S": ("Schule Azubi", PlanningMarkerKind.INFO, "#2563EB"),
    "I": ("Ilmenau", PlanningMarkerKind.DUTY, "#F97316"),
    "M": ("MVZ", PlanningMarkerKind.DUTY, "#EAB308"),
}

DUTY_CELL_CODES = {"D", "B", "H", "I", "M"}

DUTY_ENTRY_EVENTS: dict[str, tuple[str, str, str]] = {
    "D": ("Normaldienst", "shift", "#2563EB"),
    "U": ("Urlaub", "absence", "#FACC15"),
    "Ug": ("Urlaub geplant", "absence", "#0EA5E9"),
    "A": ("Arbeitszeitausgleich", "absence", "#FB7185"),
    "DR": ("Dienstreise", "absence", "#65A30D"),
    "B": ("Bereitschaft", "duty", "#C2410C"),
    "H": ("Hotlinedienst", "duty", "#16A34A"),
    "T": ("Teammeeting", "info", "#1D4ED8"),
    "S": ("Schule Azubi", "info", "#2563EB"),
    "I": ("Ilmenau", "duty", "#F97316"),
    "M": ("MVZ", "duty", "#EAB308"),
    "K": ("Kur", "absence", "#FB923C"),
    "su": ("Security Update Day", "info", "#F43F5E"),
    "Ez": ("Elternzeit", "absence", "#D97706"),
    "TSC": ("Zeitreduzierung TSC", "info", "#315D1E"),
}


@router.get("/calendar", response_model=PlanningCalendarResponse)
async def get_planning_calendar(
    start_date: date = Query(...),
    end_date: date = Query(...),
    department_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Aggregierte Kalenderansicht aus Diensten, Abwesenheiten, Reisen und Markern."""
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="Enddatum muss nach Startdatum liegen")
    if (end_date - start_date).days > 370:
        raise HTTPException(status_code=400, detail="Zeitraum darf maximal ein Jahr umfassen")

    employees = await _visible_employees(db, current_user, department_id)
    employee_ids = [employee.id for employee in employees]
    days = list(_daterange(start_date, end_date))
    by_employee_day: dict[int, dict[date, list[PlanningEventResponse]]] = {
        employee.id: {day: [] for day in days} for employee in employees
    }

    if employee_ids:
        await _add_shift_events(db, employee_ids, start_date, end_date, by_employee_day)
        await _add_absence_events(db, employee_ids, start_date, end_date, by_employee_day)
        await _add_travel_events(db, employee_ids, start_date, end_date, by_employee_day)
        await _add_marker_events(db, employee_ids, start_date, end_date, by_employee_day)
        await _add_duty_plan_entry_events(db, employee_ids, start_date, end_date, by_employee_day)
        _hide_shift_events_on_absence_days(by_employee_day)

    return PlanningCalendarResponse(
        start_date=start_date,
        end_date=end_date,
        days=days,
        employees=[
            PlanningEmployeeResponse(
                id=employee.id,
                name=employee.full_name,
                department_id=employee.department_id,
                department_name=employee.department.name if employee.department else None,
                vacation_days_per_year=employee.vacation_days_per_year,
                days=[
                    PlanningDayResponse(
                        date=day,
                        events=sorted(
                            by_employee_day[employee.id][day],
                            key=lambda event: _event_order(event.type),
                        ),
                    )
                    for day in days
                ],
            )
            for employee in employees
        ],
    )


@router.put("/cells", response_model=list[PlanningCellResponse])
async def upsert_planning_cells(
    request: PlanningCellBulkUpsert,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Planungszellen aus der Monatsansicht setzen oder leeren."""
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")
    if not request.entries:
        return []

    employee_ids = {entry.employee_id for entry in request.entries}
    result = await db.execute(
        select(Employee)
        .options(selectinload(Employee.department))
        .where(Employee.id.in_(employee_ids), Employee.is_active == True)
    )
    employees_by_id = {employee.id: employee for employee in result.scalars().all()}
    missing = employee_ids - set(employees_by_id)
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Mitarbeiter nicht gefunden: {', '.join(map(str, sorted(missing)))}",
        )

    if not is_hr(current_user):
        forbidden = [
            employee.full_name
            for employee in employees_by_id.values()
            if employee.department_id != current_user.department_id
        ]
        if forbidden:
            raise HTTPException(
                status_code=403,
                detail=f"Keine Berechtigung fuer: {', '.join(forbidden)}",
            )

    responses: list[PlanningCellResponse] = []
    for cell in request.entries:
        employee = employees_by_id[cell.employee_id]
        code = _normalize_cell_code(cell.code)

        if code is None:
            await _clear_manual_cell(db, employee.id, cell.date, current_user.id)
            responses.append(
                PlanningCellResponse(
                    employee_id=employee.id,
                    date=cell.date,
                    code=None,
                    status="CLEARED",
                )
            )
            continue

        await _clear_manual_cell(
            db,
            employee.id,
            cell.date,
            current_user.id,
            cancel_normal_shift=code == "D" or code in ABSENCE_CELL_CODES or code == "DR",
        )
        if code in DUTY_CELL_CODES and await _has_blocking_absence(db, employee.id, cell.date):
            raise HTTPException(
                status_code=409,
                detail=f"{employee.full_name}: Abwesenheit blockiert Dienst am {cell.date.isoformat()}",
            )

        await _sync_duty_plan_entry(db, employee.id, cell.date, code, current_user.id)
        if code == "D":
            await _upsert_normal_shift(db, employee, cell.date, current_user.id)
            status = "SHIFT_SAVED"
        elif code in ABSENCE_CELL_CODES:
            await _upsert_single_day_absence(db, employee.id, cell.date, code)
            await _cancel_normal_shift(db, employee.id, cell.date, current_user.id)
            status = "ABSENCE_SAVED"
        elif code == "DR":
            await _upsert_single_day_travel(db, employee.id, cell.date, current_user.id)
            await _cancel_normal_shift(db, employee.id, cell.date, current_user.id)
            status = "TRAVEL_SAVED"
        elif code in MARKER_CELL_CODES:
            await _upsert_marker(db, employee.id, cell.date, code)
            status = "MARKER_SAVED"
        else:
            raise HTTPException(status_code=400, detail=f"Ungueltiger Planungscode: {code}")

        responses.append(
            PlanningCellResponse(
                employee_id=employee.id,
                date=cell.date,
                code=code,
                status=status,
            )
        )

    await log_action(
        db,
        current_user.id,
        "UPSERT",
        "planning_cells",
        0,
        {"entries": len(responses)},
    )
    return responses


@router.post("/travel-requests", response_model=TravelResponse, status_code=201)
async def create_travel_request(
    request: TravelCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Dienstreise beantragen."""
    if request.end_date < request.start_date:
        raise HTTPException(status_code=400, detail="Enddatum muss nach Startdatum liegen")

    target_id = request.employee_id or current_user.id
    target = await _get_employee(db, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden")
    if target_id != current_user.id and not _can_manage_employee(current_user, target):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    travel = TravelRequest(
        employee_id=target_id,
        start_date=request.start_date,
        end_date=request.end_date,
        destination=request.destination.strip(),
        purpose=request.purpose.strip(),
        cost_center=request.cost_center,
        transport_type=request.transport_type,
        estimated_costs=request.estimated_costs,
        requested_by=current_user.id,
        status=TravelStatus.REQUESTED,
    )
    db.add(travel)
    travel.employee = target
    await db.flush()
    await log_action(db, current_user.id, "CREATE", "travel_requests", travel.id)
    return _travel_to_response(travel)


@router.get("/travel-requests", response_model=list[TravelResponse])
async def list_travel_requests(
    status: Optional[TravelStatus] = None,
    employee_id: Optional[int] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    query = select(TravelRequest).options(selectinload(TravelRequest.employee))

    if employee_id:
        employee = await _get_employee(db, employee_id)
        if employee is None:
            raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden")
        if employee_id != current_user.id and not _can_manage_employee(current_user, employee):
            raise HTTPException(status_code=403, detail="Keine Berechtigung")
        query = query.where(TravelRequest.employee_id == employee_id)
    elif not is_manager(current_user):
        query = query.where(TravelRequest.employee_id == current_user.id)
    elif not is_hr(current_user):
        query = query.join(Employee, TravelRequest.employee_id == Employee.id).where(
            Employee.department_id == current_user.department_id
        )

    if status:
        query = query.where(TravelRequest.status == status)
    if year:
        query = query.where(
            TravelRequest.start_date >= date(year, 1, 1),
            TravelRequest.start_date <= date(year, 12, 31),
        )

    result = await db.execute(query.order_by(TravelRequest.start_date.desc()))
    return [_travel_to_response(travel) for travel in result.scalars().all()]


@router.get("/travel-requests/pending", response_model=list[TravelResponse])
async def list_pending_travel_requests(
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    query = select(TravelRequest).options(selectinload(TravelRequest.employee))
    if is_hr(current_user):
        query = query.where(
            TravelRequest.status.in_([TravelStatus.REQUESTED, TravelStatus.MANAGER_APPROVED])
        )
    else:
        query = query.join(Employee, TravelRequest.employee_id == Employee.id).where(
            Employee.department_id == current_user.department_id,
            TravelRequest.status == TravelStatus.REQUESTED,
        )

    result = await db.execute(query.order_by(TravelRequest.created_at.desc()))
    return [_travel_to_response(travel) for travel in result.scalars().all()]


@router.post("/travel-requests/{travel_id}/review")
async def review_travel_request(
    travel_id: int,
    request: TravelReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    result = await db.execute(
        select(TravelRequest)
        .options(selectinload(TravelRequest.employee))
        .where(TravelRequest.id == travel_id)
    )
    travel = result.scalar_one_or_none()
    if travel is None:
        raise HTTPException(status_code=404, detail="Dienstreise nicht gefunden")
    if travel.status not in (TravelStatus.REQUESTED, TravelStatus.MANAGER_APPROVED):
        raise HTTPException(status_code=400, detail="Antrag bereits bearbeitet")
    if travel.employee_id == current_user.id and not is_hr(current_user):
        raise HTTPException(status_code=403, detail="Eigene Dienstreise kann nicht genehmigt werden")
    if not _can_manage_employee(current_user, travel.employee):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    if request.approved:
        if request.final_approval:
            if not is_hr(current_user):
                raise HTTPException(status_code=403, detail="Finale Freigabe nur durch HR")
            travel.status = TravelStatus.APPROVED
            travel.hr_approved_by = current_user.id
        elif is_hr(current_user) and travel.status == TravelStatus.MANAGER_APPROVED:
            travel.status = TravelStatus.APPROVED
            travel.hr_approved_by = current_user.id
        else:
            travel.status = TravelStatus.MANAGER_APPROVED
            travel.manager_approved_by = current_user.id
    else:
        travel.status = TravelStatus.REJECTED

    if request.notes:
        travel.review_notes = request.notes

    await log_action(
        db,
        current_user.id,
        "APPROVED" if request.approved else "REJECTED",
        "travel_requests",
        travel.id,
    )
    return {"id": travel.id, "status": travel.status.value}


@router.post("/import")
async def import_planning_data(
    request: PlanningImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Importiert bereinigte Excel-Plandaten. Nur HR/Admin."""
    if not is_hr(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    result = await import_planning_payload(
        db,
        request.model_dump(),
        actor_id=current_user.id,
    )
    await log_action(db, current_user.id, "IMPORT", "planning", 0, result)
    return result


async def _visible_employees(
    db: AsyncSession,
    current_user: Employee,
    department_id: Optional[int],
) -> list[Employee]:
    query = (
        select(Employee)
        .options(selectinload(Employee.department))
        .where(Employee.is_active == True)
    )
    if not is_manager(current_user):
        query = query.where(Employee.id == current_user.id)
    elif is_hr(current_user):
        if department_id:
            query = query.where(Employee.department_id == department_id)
    else:
        query = query.where(Employee.department_id == current_user.department_id)

    result = await db.execute(query.order_by(Employee.last_name, Employee.first_name))
    return result.scalars().all()


async def _get_employee(db: AsyncSession, employee_id: int) -> Employee | None:
    result = await db.execute(
        select(Employee).options(selectinload(Employee.department)).where(Employee.id == employee_id)
    )
    return result.scalar_one_or_none()


def _can_manage_employee(current_user: Employee, employee: Employee | None) -> bool:
    if employee is None:
        return False
    if is_hr(current_user):
        return True
    return is_manager(current_user) and employee.department_id == current_user.department_id


def _normalize_cell_code(raw_code: Optional[str]) -> str | None:
    if raw_code is None:
        return None
    code = raw_code.strip()
    if not code:
        return None
    lookup = {
        "d": "D",
        "u": "U",
        "ug": "Ug",
        "a": "A",
        "dr": "DR",
        "b": "B",
        "h": "H",
        "t": "T",
        "s": "S",
        "i": "I",
        "m": "M",
    }
    return lookup.get(code.lower(), code)


async def _sync_duty_plan_entry(
    db: AsyncSession,
    employee_id: int,
    entry_date: date,
    code: str,
    actor_id: int,
) -> None:
    result = await db.execute(
        select(DutyPlanEntry).where(
            DutyPlanEntry.employee_id == employee_id,
            DutyPlanEntry.date == entry_date,
        )
    )
    existing = result.scalar_one_or_none()
    note = f"Manuelle Planung {MANUAL_SOURCE}"
    if existing:
        existing.code = code[:8]
        existing.note = note
        existing.updated_by = actor_id
        return
    db.add(
        DutyPlanEntry(
            employee_id=employee_id,
            date=entry_date,
            code=code[:8],
            note=note,
            created_by=actor_id,
            updated_by=actor_id,
        )
    )


async def _clear_manual_cell(
    db: AsyncSession,
    employee_id: int,
    entry_date: date,
    actor_id: int,
    cancel_normal_shift: bool = True,
) -> None:
    duty_result = await db.execute(
        select(DutyPlanEntry).where(
            DutyPlanEntry.employee_id == employee_id,
            DutyPlanEntry.date == entry_date,
        )
    )
    if duty_entry := duty_result.scalar_one_or_none():
        await db.delete(duty_entry)

    marker_result = await db.execute(
        select(PlanningMarker).where(
            PlanningMarker.employee_id == employee_id,
            PlanningMarker.date == entry_date,
        )
    )
    for marker in marker_result.scalars().all():
        await db.delete(marker)

    absence_result = await db.execute(
        select(Absence).where(
            Absence.employee_id == employee_id,
            Absence.start_date == entry_date,
            Absence.end_date == entry_date,
            Absence.status.in_([AbsenceStatus.REQUESTED, AbsenceStatus.APPROVED]),
            Absence.notes == f"Manuelle Planung {MANUAL_SOURCE}",
        )
    )
    for absence in absence_result.scalars().all():
        absence.status = AbsenceStatus.CANCELLED

    travel_result = await db.execute(
        select(TravelRequest).where(
            TravelRequest.employee_id == employee_id,
            TravelRequest.start_date == entry_date,
            TravelRequest.end_date == entry_date,
            TravelRequest.status.in_(ACTIVE_TRAVEL_STATUSES),
            TravelRequest.source == MANUAL_SOURCE,
        )
    )
    for travel in travel_result.scalars().all():
        travel.status = TravelStatus.CANCELLED

    if cancel_normal_shift:
        await _cancel_normal_shift(db, employee_id, entry_date, actor_id)


async def _has_blocking_absence(db: AsyncSession, employee_id: int, entry_date: date) -> bool:
    absence_result = await db.execute(
        select(Absence.id)
        .where(
            Absence.employee_id == employee_id,
            Absence.status.in_([AbsenceStatus.REQUESTED, AbsenceStatus.APPROVED]),
            Absence.start_date <= entry_date,
            Absence.end_date >= entry_date,
        )
        .limit(1)
    )
    if absence_result.scalar_one_or_none() is not None:
        return True

    travel_result = await db.execute(
        select(TravelRequest.id)
        .where(
            TravelRequest.employee_id == employee_id,
            TravelRequest.status.in_(ACTIVE_TRAVEL_STATUSES),
            TravelRequest.start_date <= entry_date,
            TravelRequest.end_date >= entry_date,
        )
        .limit(1)
    )
    return travel_result.scalar_one_or_none() is not None


async def _upsert_normal_shift(
    db: AsyncSession,
    employee: Employee,
    entry_date: date,
    actor_id: int,
) -> None:
    if entry_date.weekday() >= 5:
        raise HTTPException(status_code=400, detail="Normaldienst ist nur Montag bis Freitag vorgesehen")
    if employee.department_id is None:
        raise HTTPException(status_code=400, detail=f"{employee.full_name} hat keine Abteilung")

    template = await _ensure_normal_shift_template(db)
    plan = await _ensure_shift_plan(
        db,
        department_id=employee.department_id,
        year=entry_date.year,
        month=entry_date.month,
        creator_id=actor_id,
    )

    existing_result = await db.execute(
        select(ShiftAssignment).where(
            ShiftAssignment.employee_id == employee.id,
            ShiftAssignment.shift_template_id == template.id,
            ShiftAssignment.date == entry_date,
        )
    )
    existing = existing_result.scalars().first()
    if existing:
        existing.plan_id = plan.id
        existing.status = ShiftStatus.CONFIRMED
        existing.notes = f"Manuelle Planung {MANUAL_SOURCE}: Normaldienst 07:00-15:30, 30 Min Pause"
        return

    db.add(
        ShiftAssignment(
            plan_id=plan.id,
            employee_id=employee.id,
            shift_template_id=template.id,
            date=entry_date,
            status=ShiftStatus.CONFIRMED,
            notes=f"Manuelle Planung {MANUAL_SOURCE}: Normaldienst 07:00-15:30, 30 Min Pause",
        )
    )


async def _cancel_normal_shift(
    db: AsyncSession,
    employee_id: int,
    entry_date: date,
    actor_id: int,
) -> None:
    result = await db.execute(
        select(ShiftAssignment)
        .join(ShiftTemplate, ShiftAssignment.shift_template_id == ShiftTemplate.id)
        .where(
            ShiftAssignment.employee_id == employee_id,
            ShiftAssignment.date == entry_date,
            ShiftAssignment.status.in_(
                [ShiftStatus.PLANNED, ShiftStatus.CONFIRMED, ShiftStatus.SWAPPED]
            ),
            ShiftTemplate.short_code == "D",
        )
    )
    for assignment in result.scalars().all():
        assignment.status = ShiftStatus.CANCELLED
        assignment.notes = f"{assignment.notes or ''}\nBlockiert durch Abwesenheit ({MANUAL_SOURCE}, {actor_id})".strip()


async def _upsert_single_day_absence(
    db: AsyncSession,
    employee_id: int,
    entry_date: date,
    code: str,
) -> None:
    label, absence_type, status, _ = ABSENCE_CELL_CODES[code]
    existing_result = await db.execute(
        select(Absence).where(
            Absence.employee_id == employee_id,
            Absence.status.in_([AbsenceStatus.REQUESTED, AbsenceStatus.APPROVED]),
            Absence.start_date <= entry_date,
            Absence.end_date >= entry_date,
        )
    )
    existing_absence = existing_result.scalars().first()
    if existing_absence:
        if existing_absence.start_date == entry_date and existing_absence.end_date == entry_date:
            existing_absence.type = absence_type
            existing_absence.status = status
            existing_absence.notes = f"Manuelle Planung {MANUAL_SOURCE}"
        return

    db.add(
        Absence(
            employee_id=employee_id,
            type=absence_type,
            start_date=entry_date,
            end_date=entry_date,
            days=1.0 if entry_date.weekday() < 5 else 0.0,
            status=status,
            notes=f"Manuelle Planung {MANUAL_SOURCE}",
        )
    )


async def _upsert_single_day_travel(
    db: AsyncSession,
    employee_id: int,
    entry_date: date,
    actor_id: int,
) -> None:
    existing_result = await db.execute(
        select(TravelRequest).where(
            TravelRequest.employee_id == employee_id,
            TravelRequest.status.in_(ACTIVE_TRAVEL_STATUSES),
            TravelRequest.start_date <= entry_date,
            TravelRequest.end_date >= entry_date,
        )
    )
    if existing_result.scalars().first():
        return

    db.add(
        TravelRequest(
            employee_id=employee_id,
            start_date=entry_date,
            end_date=entry_date,
            destination="Dienstreise",
            purpose="Manuelle Planung im Dienstplan",
            status=TravelStatus.APPROVED_LEGACY,
            requested_by=actor_id,
            hr_approved_by=actor_id if actor_id else None,
            source=MANUAL_SOURCE,
        )
    )


async def _upsert_marker(
    db: AsyncSession,
    employee_id: int,
    entry_date: date,
    code: str,
) -> None:
    label, kind, color = MARKER_CELL_CODES[code]
    existing_result = await db.execute(
        select(PlanningMarker).where(
            PlanningMarker.employee_id == employee_id,
            PlanningMarker.date == entry_date,
            PlanningMarker.code == code,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        existing.label = label
        existing.kind = kind
        existing.color = color
        existing.source = MANUAL_SOURCE
        return

    db.add(
        PlanningMarker(
            employee_id=employee_id,
            date=entry_date,
            code=code,
            label=label,
            kind=kind,
            color=color,
            source=MANUAL_SOURCE,
        )
    )


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


async def _add_shift_events(
    db: AsyncSession,
    employee_ids: list[int],
    start_date: date,
    end_date: date,
    by_employee_day: dict[int, dict[date, list[PlanningEventResponse]]],
) -> None:
    result = await db.execute(
        select(ShiftAssignment)
        .options(selectinload(ShiftAssignment.shift_template))
        .where(
            ShiftAssignment.employee_id.in_(employee_ids),
            ShiftAssignment.date >= start_date,
            ShiftAssignment.date <= end_date,
            ShiftAssignment.status.in_(
                [ShiftStatus.PLANNED, ShiftStatus.CONFIRMED, ShiftStatus.SWAPPED]
            ),
        )
    )
    for assignment in result.scalars().all():
        template = assignment.shift_template
        by_employee_day[assignment.employee_id][assignment.date].append(
            PlanningEventResponse(
                id=assignment.id,
                type="shift",
                code=template.short_code if template else "D",
                label=template.name if template else "Dienst",
                status=assignment.status.value,
                color=template.color if template else "#3B82F6",
            )
        )


async def _add_absence_events(
    db: AsyncSession,
    employee_ids: list[int],
    start_date: date,
    end_date: date,
    by_employee_day: dict[int, dict[date, list[PlanningEventResponse]]],
) -> None:
    result = await db.execute(
        select(Absence).where(
            Absence.employee_id.in_(employee_ids),
            Absence.status.in_([AbsenceStatus.REQUESTED, AbsenceStatus.APPROVED]),
            Absence.start_date <= end_date,
            Absence.end_date >= start_date,
        )
    )
    for absence in result.scalars().all():
        for day in _daterange(max(absence.start_date, start_date), min(absence.end_date, end_date)):
            by_employee_day[absence.employee_id][day].append(
                PlanningEventResponse(
                    id=absence.id,
                    type="absence",
                    code=_absence_code(absence),
                    label=_absence_label(absence),
                    status=absence.status.value,
                    color=_absence_color(absence),
                    source=absence.notes,
                )
            )


async def _add_travel_events(
    db: AsyncSession,
    employee_ids: list[int],
    start_date: date,
    end_date: date,
    by_employee_day: dict[int, dict[date, list[PlanningEventResponse]]],
) -> None:
    result = await db.execute(
        select(TravelRequest).where(
            TravelRequest.employee_id.in_(employee_ids),
            TravelRequest.status.in_(ACTIVE_TRAVEL_STATUSES),
            TravelRequest.start_date <= end_date,
            TravelRequest.end_date >= start_date,
        )
    )
    for travel in result.scalars().all():
        for day in _daterange(max(travel.start_date, start_date), min(travel.end_date, end_date)):
            by_employee_day[travel.employee_id][day].append(
                PlanningEventResponse(
                    id=travel.id,
                    type="absence",
                    code="DR",
                    label=f"Dienstreise: {travel.destination}",
                    status=travel.status.value,
                    color="#65A30D",
                    source=travel.source,
                )
            )


async def _add_marker_events(
    db: AsyncSession,
    employee_ids: list[int],
    start_date: date,
    end_date: date,
    by_employee_day: dict[int, dict[date, list[PlanningEventResponse]]],
) -> None:
    result = await db.execute(
        select(PlanningMarker).where(
            PlanningMarker.employee_id.in_(employee_ids),
            PlanningMarker.date >= start_date,
            PlanningMarker.date <= end_date,
        )
    )
    for marker in result.scalars().all():
        by_employee_day[marker.employee_id][marker.date].append(
            PlanningEventResponse(
                id=marker.id,
                type=marker.kind.value.lower(),
                code=marker.code,
                label=marker.label,
                status="IMPORTED",
                color=marker.color,
                source=marker.source,
            )
        )


async def _add_duty_plan_entry_events(
    db: AsyncSession,
    employee_ids: list[int],
    start_date: date,
    end_date: date,
    by_employee_day: dict[int, dict[date, list[PlanningEventResponse]]],
) -> None:
    result = await db.execute(
        select(DutyPlanEntry).where(
            DutyPlanEntry.employee_id.in_(employee_ids),
            DutyPlanEntry.date >= start_date,
            DutyPlanEntry.date <= end_date,
        )
    )
    for entry in result.scalars().all():
        events = by_employee_day[entry.employee_id][entry.date]
        code = _normalize_duty_entry_code(entry.code)
        if any(_normalize_duty_entry_code(event.code) == code for event in events):
            continue
        label, event_type, color = DUTY_ENTRY_EVENTS.get(
            code,
            (f"Planungscode {entry.code}", "info", "#64748B"),
        )
        events.append(
            PlanningEventResponse(
                id=entry.id,
                type=event_type,
                code=code,
                label=label,
                status="IMPORTED" if not entry.note else "PLANNED",
                color=color,
                source=entry.note or "duty-plan",
            )
        )


def _hide_shift_events_on_absence_days(
    by_employee_day: dict[int, dict[date, list[PlanningEventResponse]]],
) -> None:
    for days in by_employee_day.values():
        for day, events in days.items():
            if not any(event.type == "absence" for event in events):
                continue
            days[day] = [event for event in events if event.type != "shift"]


def _daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _absence_code(absence: Absence) -> str:
    if absence.type == AbsenceType.VACATION:
        return "Ug" if absence.status == AbsenceStatus.REQUESTED else "U"
    if absence.type == AbsenceType.COMP_TIME:
        return "A"
    if absence.type == AbsenceType.TRAINING:
        return "S"
    if absence.type == AbsenceType.SICK:
        return "K"
    return absence.type.value[:2]


def _absence_label(absence: Absence) -> str:
    labels = {
        AbsenceType.VACATION: "Urlaub",
        AbsenceType.SICK: "Krankheit",
        AbsenceType.TRAINING: "Schulung",
        AbsenceType.SPECIAL: "Sonderurlaub",
        AbsenceType.COMP_TIME: "Arbeitszeitausgleich",
    }
    label = labels.get(absence.type, absence.type.value)
    if absence.status == AbsenceStatus.REQUESTED:
        return f"{label} beantragt"
    return label


def _absence_color(absence: Absence) -> str:
    if absence.status == AbsenceStatus.REQUESTED:
        return "#0EA5E9"
    colors = {
        AbsenceType.VACATION: "#FACC15",
        AbsenceType.SICK: "#EF4444",
        AbsenceType.TRAINING: "#2563EB",
        AbsenceType.SPECIAL: "#A855F7",
        AbsenceType.COMP_TIME: "#FB7185",
    }
    return colors.get(absence.type, "#64748B")


def _normalize_duty_entry_code(raw_code: str | None) -> str:
    code = _normalize_cell_code(raw_code)
    if code is None:
        return ""
    lookup = {
        "dr": "DR",
        "ug": "Ug",
        "ez": "Ez",
        "su": "su",
        "tsc": "TSC",
    }
    return lookup.get(code.lower(), code)


def _event_order(event_type: str) -> int:
    order = {
        "absence": 0,
        "travel": 1,
        "duty": 2,
        "info": 3,
        "shift": 4,
    }
    return order.get(event_type, 9)


def _travel_to_response(travel: TravelRequest) -> TravelResponse:
    return TravelResponse(
        id=travel.id,
        employee_id=travel.employee_id,
        employee_name=travel.employee.full_name if travel.employee else None,
        start_date=travel.start_date,
        end_date=travel.end_date,
        destination=travel.destination,
        purpose=travel.purpose,
        cost_center=travel.cost_center,
        transport_type=travel.transport_type,
        estimated_costs=travel.estimated_costs,
        status=travel.status.value,
        review_notes=travel.review_notes,
        source=travel.source,
        created_at=travel.created_at.isoformat(),
    )
