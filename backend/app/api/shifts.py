"""API-Endpoints fuer Schichtplanung: Vorlagen, Dienstplaene, Zuweisung, Tausch."""

from calendar import monthrange
from datetime import date, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.jwt import get_current_user
from app.auth.permissions import is_hr, is_manager
from app.database import get_db
from app.models.employee import Employee
from app.models.shift import (
    CoverageRequest,
    CoverageStatus,
    PlanStatus,
    ShiftAssignment,
    ShiftPlan,
    ShiftRequirement,
    ShiftStatus,
    ShiftTemplate,
    SwapRequest,
    SwapStatus,
)
from app.services.audit import log_action
from app.services.shift_validator import check_staffing, validate_assignment

router = APIRouter(prefix="/shifts", tags=["Schichtplanung"])


# === Schemas ===


class ShiftTemplateCreate(BaseModel):
    name: str
    short_code: str
    start_time: str  # "06:00"
    end_time: str    # "14:00"
    break_minutes: int = 30
    crosses_midnight: bool = False
    color: str = "#3B82F6"
    department_id: Optional[int] = None


class ShiftTemplateResponse(BaseModel):
    id: int
    name: str
    short_code: str
    start_time: str
    end_time: str
    break_minutes: int
    crosses_midnight: bool
    color: str
    department_id: Optional[int]
    duration_hours: float
    net_hours: float
    is_active: bool


class PlanCreateRequest(BaseModel):
    department_id: int
    year: int
    month: int


class AssignmentCreate(BaseModel):
    employee_id: int
    shift_template_id: int
    date: date


class BulkAssignmentCreate(BaseModel):
    employee_id: int
    shift_template_id: int
    dates: list[date]


class AssignmentResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    shift_template_id: int
    shift_name: Optional[str] = None
    shift_code: Optional[str] = None
    shift_start: Optional[str] = None
    shift_end: Optional[str] = None
    date: date
    status: str
    notes: Optional[str] = None


class RequirementCreate(BaseModel):
    department_id: int
    shift_template_id: int
    weekday: int  # 0-6
    min_staff: int = 1
    required_qualifications: Optional[list[str]] = None


class CoverageRequestCreate(BaseModel):
    assignment_id: int
    reason: str


class SwapRequestCreate(BaseModel):
    my_assignment_id: int
    target_assignment_id: int
    reason: Optional[str] = None


# === Schichtvorlagen ===


@router.get("/templates", response_model=list[ShiftTemplateResponse])
async def list_templates(
    department_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Alle Schichtvorlagen auflisten."""
    query = select(ShiftTemplate).where(ShiftTemplate.is_active == True)
    if department_id:
        query = query.where(
            (ShiftTemplate.department_id == department_id)
            | (ShiftTemplate.department_id.is_(None))
        )
    query = query.order_by(ShiftTemplate.start_time)
    result = await db.execute(query)
    templates = result.scalars().all()
    return [_template_to_response(t) for t in templates]


@router.post("/templates", response_model=ShiftTemplateResponse, status_code=201)
async def create_template(
    request: ShiftTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Neue Schichtvorlage erstellen. Nur Manager/HR/Admin."""
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    h, m = map(int, request.start_time.split(":"))
    start = time(h, m)
    h, m = map(int, request.end_time.split(":"))
    end = time(h, m)

    template = ShiftTemplate(
        name=request.name,
        short_code=request.short_code,
        start_time=start,
        end_time=end,
        break_minutes=request.break_minutes,
        crosses_midnight=request.crosses_midnight,
        color=request.color,
        department_id=request.department_id,
    )
    db.add(template)
    await db.flush()
    await log_action(db, current_user.id, "CREATE", "shift_templates", template.id)
    return _template_to_response(template)


@router.put("/templates/{template_id}", response_model=ShiftTemplateResponse)
async def update_template(
    template_id: int,
    request: ShiftTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Schichtvorlage aktualisieren. Nur Manager/HR/Admin."""
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    result = await db.execute(
        select(ShiftTemplate).where(ShiftTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Schichtvorlage nicht gefunden")

    h, m = map(int, request.start_time.split(":"))
    template.start_time = time(h, m)
    h, m = map(int, request.end_time.split(":"))
    template.end_time = time(h, m)
    template.name = request.name
    template.short_code = request.short_code
    template.break_minutes = request.break_minutes
    template.crosses_midnight = request.crosses_midnight
    template.color = request.color
    template.department_id = request.department_id

    await log_action(db, current_user.id, "UPDATE", "shift_templates", template_id)
    return _template_to_response(template)


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Schichtvorlage deaktivieren (Soft-Delete). Nur Manager/HR/Admin."""
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    result = await db.execute(
        select(ShiftTemplate).where(ShiftTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Schichtvorlage nicht gefunden")

    template.is_active = False
    await log_action(db, current_user.id, "DELETE", "shift_templates", template_id)


# === Dienstplaene ===


@router.post("/plans", status_code=201)
async def create_plan(
    request: PlanCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Neuen Dienstplan (Entwurf) fuer eine Abteilung/Monat erstellen."""
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    # Pruefen ob bereits existiert
    existing = await db.execute(
        select(ShiftPlan).where(
            ShiftPlan.department_id == request.department_id,
            ShiftPlan.year == request.year,
            ShiftPlan.month == request.month,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Dienstplan existiert bereits")

    plan = ShiftPlan(
        department_id=request.department_id,
        year=request.year,
        month=request.month,
        created_by=current_user.id,
    )
    db.add(plan)
    await db.flush()

    return {
        "id": plan.id,
        "department_id": plan.department_id,
        "year": plan.year,
        "month": plan.month,
        "status": plan.status.value,
    }


@router.get("/plans")
async def list_plans(
    department_id: Optional[int] = None,
    year: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Dienstplaene auflisten."""
    query = select(ShiftPlan)
    if department_id:
        query = query.where(ShiftPlan.department_id == department_id)
    if year:
        query = query.where(ShiftPlan.year == year)
    query = query.order_by(ShiftPlan.year.desc(), ShiftPlan.month.desc())
    result = await db.execute(query)
    plans = result.scalars().all()

    return [
        {
            "id": p.id,
            "department_id": p.department_id,
            "department_name": p.department.name if p.department else None,
            "year": p.year,
            "month": p.month,
            "status": p.status.value,
            "published_at": p.published_at.isoformat() if p.published_at else None,
        }
        for p in plans
    ]


@router.post("/plans/{plan_id}/publish")
async def publish_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Dienstplan veroeffentlichen. Mitarbeiter werden benachrichtigt."""
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    result = await db.execute(select(ShiftPlan).where(ShiftPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Dienstplan nicht gefunden")

    if plan.status == PlanStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="Plan ist bereits veroeffentlicht")

    from datetime import datetime
    plan.status = PlanStatus.PUBLISHED
    plan.published_at = datetime.utcnow()

    # Alle Zuweisungen auf CONFIRMED setzen
    assign_result = await db.execute(
        select(ShiftAssignment).where(
            ShiftAssignment.plan_id == plan_id,
            ShiftAssignment.status == ShiftStatus.PLANNED,
        )
    )
    for assignment in assign_result.scalars().all():
        assignment.status = ShiftStatus.CONFIRMED

    await log_action(db, current_user.id, "PUBLISH", "shift_plans", plan_id)
    return {"message": "Dienstplan veroeffentlicht", "status": "PUBLISHED"}


# === Zuweisungen ===


@router.post("/plans/{plan_id}/assign", response_model=AssignmentResponse, status_code=201)
async def assign_shift(
    plan_id: int,
    request: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Mitarbeiter einer Schicht zuweisen (einzelner Tag)."""
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    # Plan pruefen
    plan_result = await db.execute(select(ShiftPlan).where(ShiftPlan.id == plan_id))
    plan = plan_result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Dienstplan nicht gefunden")
    if plan.status == PlanStatus.ARCHIVED:
        raise HTTPException(status_code=400, detail="Archivierter Plan kann nicht geaendert werden")

    # Schichtvorlage laden
    tmpl_result = await db.execute(
        select(ShiftTemplate).where(ShiftTemplate.id == request.shift_template_id)
    )
    template = tmpl_result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Schichtvorlage nicht gefunden")

    # Regelwerk pruefen
    validation = await validate_assignment(
        db, request.employee_id, template, request.date
    )
    if not validation.is_valid:
        raise HTTPException(status_code=400, detail=validation.to_dict())

    assignment = ShiftAssignment(
        plan_id=plan_id,
        employee_id=request.employee_id,
        shift_template_id=request.shift_template_id,
        date=request.date,
    )
    db.add(assignment)
    await db.flush()

    response = _assignment_to_response(assignment)
    if validation.warnings:
        return {**response.model_dump(), "warnings": validation.warnings}
    return response


@router.post("/plans/{plan_id}/assign-bulk")
async def assign_shift_bulk(
    plan_id: int,
    request: BulkAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Mitarbeiter fuer mehrere Tage einer Schicht zuweisen."""
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    plan_result = await db.execute(select(ShiftPlan).where(ShiftPlan.id == plan_id))
    plan = plan_result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Dienstplan nicht gefunden")

    tmpl_result = await db.execute(
        select(ShiftTemplate).where(ShiftTemplate.id == request.shift_template_id)
    )
    template = tmpl_result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=404, detail="Schichtvorlage nicht gefunden")

    results = []
    for d in request.dates:
        validation = await validate_assignment(db, request.employee_id, template, d)
        if not validation.is_valid:
            results.append({"date": d.isoformat(), "status": "error", "errors": validation.errors})
            continue

        assignment = ShiftAssignment(
            plan_id=plan_id,
            employee_id=request.employee_id,
            shift_template_id=request.shift_template_id,
            date=d,
        )
        db.add(assignment)
        await db.flush()
        results.append({
            "date": d.isoformat(),
            "status": "ok",
            "id": assignment.id,
            "warnings": validation.warnings,
        })

    return {"results": results}


@router.delete("/assignments/{assignment_id}", status_code=204)
async def remove_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Schichtzuweisung entfernen."""
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    result = await db.execute(
        select(ShiftAssignment).where(ShiftAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Zuweisung nicht gefunden")

    assignment.status = ShiftStatus.CANCELLED


# === Dienstplan anzeigen ===


@router.get("/plans/{plan_id}/view")
async def view_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Dienstplan als Kalenderansicht (Tage x Mitarbeiter)."""
    plan_result = await db.execute(select(ShiftPlan).where(ShiftPlan.id == plan_id))
    plan = plan_result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Dienstplan nicht gefunden")

    assign_result = await db.execute(
        select(ShiftAssignment)
        .options(selectinload(ShiftAssignment.employee), selectinload(ShiftAssignment.shift_template))
        .where(
            ShiftAssignment.plan_id == plan_id,
            ShiftAssignment.status.in_([ShiftStatus.PLANNED, ShiftStatus.CONFIRMED]),
        )
        .order_by(ShiftAssignment.date)
    )
    assignments = assign_result.scalars().all()

    # Gruppierung: Mitarbeiter -> Tage
    by_employee: dict[int, dict] = {}
    for a in assignments:
        emp_id = a.employee_id
        if emp_id not in by_employee:
            by_employee[emp_id] = {
                "employee_id": emp_id,
                "employee_name": a.employee.full_name if a.employee else None,
                "shifts": {},
            }
        by_employee[emp_id]["shifts"][a.date.isoformat()] = {
            "assignment_id": a.id,
            "shift_code": a.shift_template.short_code if a.shift_template else None,
            "shift_name": a.shift_template.name if a.shift_template else None,
            "color": a.shift_template.color if a.shift_template else None,
            "status": a.status.value,
        }

    _, last_day = monthrange(plan.year, plan.month)
    days = [date(plan.year, plan.month, d).isoformat() for d in range(1, last_day + 1)]

    return {
        "plan_id": plan.id,
        "department": plan.department.name if plan.department else None,
        "year": plan.year,
        "month": plan.month,
        "status": plan.status.value,
        "days": days,
        "employees": list(by_employee.values()),
    }


@router.get("/my-schedule")
async def my_schedule(
    start_date: date = Query(default=None),
    end_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Eigenen Dienstplan fuer einen Zeitraum anzeigen."""
    if start_date is None:
        start_date = date.today()
    if end_date is None:
        end_date = start_date + timedelta(days=30)

    result = await db.execute(
        select(ShiftAssignment)
        .options(selectinload(ShiftAssignment.shift_template))
        .where(
            ShiftAssignment.employee_id == current_user.id,
            ShiftAssignment.date >= start_date,
            ShiftAssignment.date <= end_date,
            ShiftAssignment.status.in_([ShiftStatus.PLANNED, ShiftStatus.CONFIRMED]),
        )
        .order_by(ShiftAssignment.date)
    )
    assignments = result.scalars().all()

    return [_assignment_to_response(a) for a in assignments]


# === Besetzungspruefung ===


@router.get("/staffing-check")
async def staffing_check(
    department_id: int,
    start_date: date,
    end_date: date,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Prueft Besetzung gegen Mindestanforderungen fuer einen Zeitraum."""
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    all_issues = []
    current = start_date
    while current <= end_date:
        issues = await check_staffing(db, department_id, current)
        all_issues.extend(issues)
        current += timedelta(days=1)

    return {
        "department_id": department_id,
        "period": f"{start_date.isoformat()} - {end_date.isoformat()}",
        "issues": all_issues,
        "total_gaps": sum(i["missing"] for i in all_issues),
    }


# === Mindestbesetzung ===


@router.post("/requirements", status_code=201)
async def create_requirement(
    request: RequirementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Mindestbesetzung definieren."""
    if not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    req = ShiftRequirement(
        department_id=request.department_id,
        shift_template_id=request.shift_template_id,
        weekday=request.weekday,
        min_staff=request.min_staff,
        required_qualifications=request.required_qualifications,
    )
    db.add(req)
    await db.flush()
    return {"id": req.id, "message": "Mindestbesetzung erstellt"}


@router.get("/requirements")
async def list_requirements(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Mindestbesetzung einer Abteilung anzeigen."""
    result = await db.execute(
        select(ShiftRequirement).where(
            ShiftRequirement.department_id == department_id,
            ShiftRequirement.is_active == True,
        )
    )
    requirements = result.scalars().all()

    weekdays = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
    return [
        {
            "id": r.id,
            "shift": r.shift_template.name if r.shift_template else None,
            "shift_code": r.shift_template.short_code if r.shift_template else None,
            "weekday": weekdays[r.weekday],
            "weekday_num": r.weekday,
            "min_staff": r.min_staff,
            "required_qualifications": r.required_qualifications,
        }
        for r in requirements
    ]


# === Vertretung ===


@router.post("/coverage", status_code=201)
async def create_coverage_request(
    request: CoverageRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Vertretungsanfrage erstellen (Schicht kann nicht wahrgenommen werden)."""
    assign_result = await db.execute(
        select(ShiftAssignment).where(ShiftAssignment.id == request.assignment_id)
    )
    assignment = assign_result.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Zuweisung nicht gefunden")

    if assignment.employee_id != current_user.id and not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    coverage = CoverageRequest(
        assignment_id=request.assignment_id,
        reason=request.reason,
        created_by=current_user.id,
    )
    db.add(coverage)
    await db.flush()

    return {
        "id": coverage.id,
        "status": "OPEN",
        "message": "Vertretungsanfrage erstellt",
    }


@router.get("/coverage/open")
async def list_open_coverage(
    department_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Offene Vertretungsanfragen anzeigen."""
    result = await db.execute(
        select(CoverageRequest)
        .where(CoverageRequest.status == CoverageStatus.OPEN)
        .order_by(CoverageRequest.created_at.desc())
    )
    requests = result.scalars().all()

    return [
        {
            "id": r.id,
            "assignment_id": r.assignment_id,
            "date": r.assignment.date.isoformat() if r.assignment else None,
            "shift": r.assignment.shift_template.name if r.assignment and r.assignment.shift_template else None,
            "employee": r.assignment.employee.full_name if r.assignment and r.assignment.employee else None,
            "reason": r.reason,
            "created_at": r.created_at.isoformat(),
        }
        for r in requests
    ]


@router.post("/coverage/{coverage_id}/volunteer")
async def volunteer_for_coverage(
    coverage_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Sich freiwillig fuer eine Vertretung melden."""
    result = await db.execute(
        select(CoverageRequest).where(CoverageRequest.id == coverage_id)
    )
    coverage = result.scalar_one_or_none()
    if coverage is None:
        raise HTTPException(status_code=404, detail="Anfrage nicht gefunden")
    if coverage.status != CoverageStatus.OPEN:
        raise HTTPException(status_code=400, detail="Anfrage nicht mehr offen")

    # Regelwerk pruefen
    assignment = coverage.assignment
    if assignment and assignment.shift_template:
        validation = await validate_assignment(
            db, current_user.id, assignment.shift_template, assignment.date
        )
        if not validation.is_valid:
            raise HTTPException(
                status_code=400,
                detail={"message": "Regelverstoesse", **validation.to_dict()},
            )

    coverage.status = CoverageStatus.FILLED
    coverage.filled_by = current_user.id

    # Alte Zuweisung stornieren, neue erstellen
    if assignment:
        assignment.status = ShiftStatus.CANCELLED
        new_assignment = ShiftAssignment(
            plan_id=assignment.plan_id,
            employee_id=current_user.id,
            shift_template_id=assignment.shift_template_id,
            date=assignment.date,
            notes=f"Vertretung fuer {assignment.employee.full_name if assignment.employee else 'N/A'}",
        )
        db.add(new_assignment)

    await log_action(db, current_user.id, "VOLUNTEER", "coverage_requests", coverage_id)
    return {"message": "Vertretung uebernommen"}


# === Diensttausch ===


@router.post("/swap", status_code=201)
async def request_swap(
    request: SwapRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Diensttausch mit einem anderen Mitarbeiter anfragen."""
    # Eigene Zuweisung pruefen
    my_result = await db.execute(
        select(ShiftAssignment).where(ShiftAssignment.id == request.my_assignment_id)
    )
    my_assign = my_result.scalar_one_or_none()
    if my_assign is None or my_assign.employee_id != current_user.id:
        raise HTTPException(status_code=400, detail="Ungueltige eigene Zuweisung")

    # Ziel-Zuweisung pruefen
    target_result = await db.execute(
        select(ShiftAssignment).where(ShiftAssignment.id == request.target_assignment_id)
    )
    target_assign = target_result.scalar_one_or_none()
    if target_assign is None:
        raise HTTPException(status_code=404, detail="Ziel-Zuweisung nicht gefunden")

    swap = SwapRequest(
        requester_assignment_id=request.my_assignment_id,
        target_assignment_id=request.target_assignment_id,
        requester_id=current_user.id,
        target_id=target_assign.employee_id,
        reason=request.reason,
    )
    db.add(swap)
    await db.flush()

    return {"id": swap.id, "status": "PENDING", "message": "Tausch-Anfrage gesendet"}


@router.post("/swap/{swap_id}/approve")
async def approve_swap(
    swap_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Diensttausch genehmigen (vom Tauschpartner oder Manager)."""
    result = await db.execute(
        select(SwapRequest).where(SwapRequest.id == swap_id)
    )
    swap = result.scalar_one_or_none()
    if swap is None:
        raise HTTPException(status_code=404, detail="Tausch-Anfrage nicht gefunden")
    if swap.status != SwapStatus.PENDING:
        raise HTTPException(status_code=400, detail="Anfrage bereits bearbeitet")

    # Nur Tauschpartner oder Manager duerfen genehmigen
    if current_user.id != swap.target_id and not is_manager(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    # Regelwerk pruefen fuer beide Richtungen
    req_assign = swap.requester_assignment
    target_assign = swap.target_assignment

    if req_assign and target_assign and req_assign.shift_template and target_assign.shift_template:
        # Kann Requester die Ziel-Schicht machen?
        v1 = await validate_assignment(
            db, swap.requester_id, target_assign.shift_template,
            target_assign.date, exclude_assignment_id=req_assign.id,
        )
        # Kann Target die Requester-Schicht machen?
        v2 = await validate_assignment(
            db, swap.target_id, req_assign.shift_template,
            req_assign.date, exclude_assignment_id=target_assign.id,
        )

        errors = v1.errors + v2.errors
        if errors:
            raise HTTPException(
                status_code=400,
                detail={"message": "Tausch verstoesst gegen Regeln", "errors": errors},
            )

    # Tausch durchfuehren
    swap.status = SwapStatus.APPROVED
    swap.reviewed_by = current_user.id

    if req_assign and target_assign:
        req_assign.employee_id, target_assign.employee_id = (
            target_assign.employee_id, req_assign.employee_id
        )
        req_assign.status = ShiftStatus.SWAPPED
        target_assign.status = ShiftStatus.SWAPPED

    await log_action(db, current_user.id, "SWAP_APPROVED", "swap_requests", swap_id)
    return {"message": "Diensttausch durchgefuehrt"}


# === Hilfsfunktionen ===


def _template_to_response(t: ShiftTemplate) -> ShiftTemplateResponse:
    return ShiftTemplateResponse(
        id=t.id,
        name=t.name,
        short_code=t.short_code,
        start_time=t.start_time.strftime("%H:%M"),
        end_time=t.end_time.strftime("%H:%M"),
        break_minutes=t.break_minutes,
        crosses_midnight=t.crosses_midnight,
        color=t.color,
        department_id=t.department_id,
        duration_hours=t.duration_hours,
        net_hours=t.net_hours,
        is_active=t.is_active,
    )


def _assignment_to_response(a: ShiftAssignment) -> AssignmentResponse:
    return AssignmentResponse(
        id=a.id,
        employee_id=a.employee_id,
        employee_name=a.employee.full_name if a.employee else None,
        shift_template_id=a.shift_template_id,
        shift_name=a.shift_template.name if a.shift_template else None,
        shift_code=a.shift_template.short_code if a.shift_template else None,
        shift_start=a.shift_template.start_time.strftime("%H:%M") if a.shift_template else None,
        shift_end=a.shift_template.end_time.strftime("%H:%M") if a.shift_template else None,
        date=a.date,
        status=a.status.value,
        notes=a.notes,
    )
