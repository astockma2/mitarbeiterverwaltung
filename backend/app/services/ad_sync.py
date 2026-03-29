"""Service fuer die Synchronisation von Mitarbeiterdaten aus Active Directory."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.ldap import determine_role_from_groups, sync_user_details
from app.models.employee import Employee, UserRole

logger = logging.getLogger(__name__)


async def sync_employee_from_ad(db: AsyncSession, employee: Employee) -> dict:
    """Synchronisiert einen einzelnen Mitarbeiter mit AD-Daten.

    Returns: Dict mit aktualisierten Feldern.
    """
    if not employee.ad_username:
        return {}

    ad_user = sync_user_details(employee.ad_username)
    if ad_user is None:
        logger.warning("AD-Benutzer '%s' nicht gefunden", employee.ad_username)
        return {}

    updates = {}

    if ad_user.email and ad_user.email != employee.email:
        updates["email"] = ad_user.email
        employee.email = ad_user.email

    if ad_user.first_name and ad_user.first_name != employee.first_name:
        updates["first_name"] = ad_user.first_name
        employee.first_name = ad_user.first_name

    if ad_user.last_name and ad_user.last_name != employee.last_name:
        updates["last_name"] = ad_user.last_name
        employee.last_name = ad_user.last_name

    # Rolle aus Gruppen ableiten
    ad_role = determine_role_from_groups(ad_user.groups)
    if ad_role != employee.role.value:
        updates["role"] = ad_role
        employee.role = UserRole(ad_role)

    if updates:
        logger.info(
            "AD-Sync fuer '%s': %s aktualisiert",
            employee.ad_username,
            list(updates.keys()),
        )

    return updates


async def sync_all_employees(db: AsyncSession) -> dict:
    """Synchronisiert alle aktiven Mitarbeiter mit AD.

    Returns: Zusammenfassung {synced: int, errors: int, updated_fields: int}
    """
    result = await db.execute(
        select(Employee).where(
            Employee.is_active == True,
            Employee.ad_username.isnot(None),
        )
    )
    employees = result.scalars().all()

    synced = 0
    errors = 0
    total_updates = 0

    for employee in employees:
        try:
            updates = await sync_employee_from_ad(db, employee)
            synced += 1
            total_updates += len(updates)
        except Exception:
            logger.exception("AD-Sync Fehler fuer '%s'", employee.ad_username)
            errors += 1

    return {"synced": synced, "errors": errors, "updated_fields": total_updates}
