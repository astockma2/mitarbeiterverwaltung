from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.auth.jwt import get_current_user
from app.auth.permissions import is_hr
from app.database import get_db
from app.models.department import Department
from app.models.employee import Employee
from app.services.audit import log_action

router = APIRouter(prefix="/departments", tags=["Abteilungen"])


@router.get("", response_model=list[DepartmentResponse])
async def list_departments(
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Alle Abteilungen auflisten."""
    result = await db.execute(
        select(Department).where(Department.is_active == True).order_by(Department.name)
    )
    return [DepartmentResponse.model_validate(d) for d in result.scalars().all()]


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Einzelne Abteilung abrufen."""
    result = await db.execute(
        select(Department).where(Department.id == department_id)
    )
    department = result.scalar_one_or_none()
    if department is None:
        raise HTTPException(status_code=404, detail="Abteilung nicht gefunden")
    return DepartmentResponse.model_validate(department)


@router.post("", response_model=DepartmentResponse, status_code=201)
async def create_department(
    data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Neue Abteilung anlegen. Nur Admin."""
    if not is_hr(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keine Berechtigung")

    department = Department(**data.model_dump())
    db.add(department)
    await db.flush()

    await log_action(db, current_user.id, "CREATE", "departments", department.id)
    return DepartmentResponse.model_validate(department)


@router.patch("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: int,
    data: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Abteilung aktualisieren. Nur Admin."""
    if not is_hr(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keine Berechtigung")

    result = await db.execute(
        select(Department).where(Department.id == department_id)
    )
    department = result.scalar_one_or_none()
    if department is None:
        raise HTTPException(status_code=404, detail="Abteilung nicht gefunden")

    update_data = data.model_dump(exclude_unset=True)
    changes = {}
    for field, value in update_data.items():
        old_value = getattr(department, field)
        if old_value != value:
            changes[field] = {"old": str(old_value), "new": str(value)}
            setattr(department, field, value)

    if changes:
        await log_action(
            db, current_user.id, "UPDATE", "departments", department_id, changes
        )

    return DepartmentResponse.model_validate(department)


@router.get("/{department_id}/employees", response_model=list[dict])
async def list_department_employees(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Alle Mitarbeiter einer Abteilung auflisten."""
    result = await db.execute(
        select(Employee)
        .where(Employee.department_id == department_id, Employee.is_active == True)
        .order_by(Employee.last_name, Employee.first_name)
    )
    employees = result.scalars().all()
    return [
        {
            "id": e.id,
            "personnel_number": e.personnel_number,
            "first_name": e.first_name,
            "last_name": e.last_name,
            "role": e.role.value,
            "job_title": e.job_title,
        }
        for e in employees
    ]
