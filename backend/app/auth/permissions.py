from functools import wraps

from fastapi import HTTPException, status

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


def can_view_employee(viewer: Employee, target_employee_id: int) -> bool:
    """Prueft ob ein Benutzer die Daten eines anderen Mitarbeiters sehen darf."""
    if viewer.role in (UserRole.ADMIN, UserRole.HR):
        return True
    if viewer.id == target_employee_id:
        return True
    # Abteilungsleiter sehen ihre Abteilung
    if viewer.role in (UserRole.DEPARTMENT_MANAGER, UserRole.TEAM_LEADER):
        return True  # Wird spaeter verfeinert mit Abteilungspruefung
    return False
