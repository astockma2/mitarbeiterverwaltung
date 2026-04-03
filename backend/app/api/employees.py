import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdate,
    PaginatedResponse,
    QualificationCreate,
    QualificationResponse,
)
from app.auth.jwt import get_current_user
from app.auth.permissions import can_view_employee, is_hr
from app.database import get_db
from app.models.employee import Employee, UserRole
from app.models.qualification import Qualification
from app.services.audit import log_action

router = APIRouter(prefix="/employees", tags=["Mitarbeiter"])


@router.get("", response_model=PaginatedResponse)
async def list_employees(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=500),
    search: Optional[str] = None,
    department_id: Optional[int] = None,
    is_active: Optional[bool] = True,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Liste aller Mitarbeiter mit Suche, Filter und Paginierung."""
    query = select(Employee)

    # Filter
    if is_active is not None:
        query = query.where(Employee.is_active == is_active)
    if department_id is not None:
        query = query.where(Employee.department_id == department_id)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (Employee.first_name.ilike(search_term))
            | (Employee.last_name.ilike(search_term))
            | (Employee.personnel_number.ilike(search_term))
            | (Employee.email.ilike(search_term))
        )

    # Gesamtanzahl
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Paginierung
    query = query.order_by(Employee.last_name, Employee.first_name)
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    employees = result.scalars().all()

    return PaginatedResponse(
        items=[EmployeeListResponse.model_validate(e) for e in employees],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Einzelnen Mitarbeiter mit allen Details abrufen."""
    if not await can_view_employee(db, current_user, employee_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keine Berechtigung")

    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()
    if employee is None:
        raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden")

    return EmployeeResponse.model_validate(employee)


@router.post("", response_model=EmployeeResponse, status_code=201)
async def create_employee(
    data: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Neuen Mitarbeiter anlegen. Nur HR und Admin."""
    if not is_hr(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keine Berechtigung")

    # Personalnummer eindeutig pruefen
    existing = await db.execute(
        select(Employee).where(Employee.personnel_number == data.personnel_number)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Personalnummer bereits vergeben")

    employee = Employee(**data.model_dump())
    db.add(employee)
    await db.flush()

    await log_action(db, current_user.id, "CREATE", "employees", employee.id)

    return EmployeeResponse.model_validate(employee)


@router.patch("/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Mitarbeiter aktualisieren. HR/Admin oder eigenes Profil (eingeschraenkt)."""
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()
    if employee is None:
        raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden")

    # Berechtigungspruefung
    is_self = current_user.id == employee_id
    if not is_hr(current_user) and not is_self:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keine Berechtigung")

    # Mitarbeiter duerfen nur bestimmte Felder selbst aendern
    self_editable = {"phone", "mobile", "email", "street", "zip_code", "city", "emergency_contact_name", "emergency_contact_phone"}
    update_data = data.model_dump(exclude_unset=True)

    if is_self and not is_hr(current_user):
        forbidden_fields = set(update_data.keys()) - self_editable
        if forbidden_fields:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Keine Berechtigung fuer: {', '.join(forbidden_fields)}",
            )

    changes = {}
    for field, value in update_data.items():
        old_value = getattr(employee, field)
        if old_value != value:
            changes[field] = {"old": str(old_value), "new": str(value)}
            setattr(employee, field, value)

    if changes:
        await log_action(
            db, current_user.id, "UPDATE", "employees", employee_id, changes
        )

    return EmployeeResponse.model_validate(employee)


@router.delete("/{employee_id}", status_code=204)
async def deactivate_employee(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Mitarbeiter deaktivieren (Soft-Delete). Nur HR und Admin."""
    if not is_hr(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keine Berechtigung")

    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    employee = result.scalar_one_or_none()
    if employee is None:
        raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden")

    employee.is_active = False
    await log_action(db, current_user.id, "DEACTIVATE", "employees", employee_id)


# === Qualifikationen ===

@router.get("/{employee_id}/qualifications", response_model=list[QualificationResponse])
async def list_qualifications(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Qualifikationen eines Mitarbeiters auflisten."""
    if not await can_view_employee(db, current_user, employee_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keine Berechtigung")

    result = await db.execute(
        select(Qualification).where(Qualification.employee_id == employee_id)
    )
    return [QualificationResponse.model_validate(q) for q in result.scalars().all()]


@router.post(
    "/{employee_id}/qualifications",
    response_model=QualificationResponse,
    status_code=201,
)
async def add_qualification(
    employee_id: int,
    data: QualificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Qualifikation hinzufuegen. Nur HR und Admin."""
    if not is_hr(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keine Berechtigung")

    # Mitarbeiter existiert?
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden")

    qualification = Qualification(employee_id=employee_id, **data.model_dump())
    db.add(qualification)
    await db.flush()

    await log_action(db, current_user.id, "CREATE", "qualifications", qualification.id)
    return QualificationResponse.model_validate(qualification)
