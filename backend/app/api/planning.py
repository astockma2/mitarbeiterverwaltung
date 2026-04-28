"""Gemeinsame Planungs-API fuer Jahres-/Monatsansicht, Marker und Dienstreisen."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.jwt import get_current_user
from app.auth.permissions import is_hr, is_manager
from app.database import get_db
from app.models.employee import Employee
from app.models.planning import PlanningMarker, TravelRequest, TravelStatus
from app.models.shift import ShiftAssignment, ShiftStatus
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


ACTIVE_TRAVEL_STATUSES = (
    TravelStatus.REQUESTED,
    TravelStatus.MANAGER_APPROVED,
    TravelStatus.APPROVED,
    TravelStatus.APPROVED_LEGACY,
)


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
                    type="travel",
                    code="DR",
                    label=travel.destination,
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


def _event_order(event_type: str) -> int:
    order = {
        "absence": 0,
        "travel": 1,
        "shift": 2,
        "duty": 3,
        "info": 4,
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
