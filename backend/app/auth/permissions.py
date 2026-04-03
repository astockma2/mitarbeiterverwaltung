from functools import wraps

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee, UserRole


def require_roles(*roles: UserRole):
    """Decorator/Dependency: Prueft ob der Benutzer eine der angegebenen Rollen hat."""

    def dependency(current_user: Employee) -> Employee:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Keine Berechtigung fuer diese Aktion",
            )
        return current_user

    return dependency


def is_admin(user: Employee) -> bool:
    return user.role == UserRole.ADMIN


def is_hr(user: Employee) -> bool:
    return user.role in (UserRole.ADMIN, UserRole.HR)


def is_manager(user: Employee) -> bool:
    return user.role in (
        UserRole.ADMIN,
        UserRole.HR,
        UserRole.DEPARTMENT_MANAGER,
        UserRole.TEAM_LEADER,
    )


async def can_view_employee(db: AsyncSession, viewer: Employee, target_employee_id: int) -> bool:
    """Prüft ob ein Benutzer die Daten eines anderen Mitarbeiters sehen darf.

    ADMIN und HR sehen alle Mitarbeiter.
    DEPARTMENT_MANAGER und TEAM_LEADER sehen nur Mitarbeiter ihrer eigenen Abteilung.
    Alle Benutzer können ihre eigenen Daten einsehen.
    """
    if viewer.role in (UserRole.ADMIN, UserRole.HR):
        return True
    if viewer.id == target_employee_id:
        return True
    if viewer.role in (UserRole.DEPARTMENT_MANAGER, UserRole.TEAM_LEADER):
        result = await db.execute(select(Employee).where(Employee.id == target_employee_id))
        target = result.scalar_one_or_none()
        return target is not None and target.department_id == viewer.department_id
    return False
