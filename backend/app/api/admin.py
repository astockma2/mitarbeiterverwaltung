from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user
from app.auth.permissions import is_admin, is_hr
from app.database import get_db
from app.models.employee import Employee, UserRole
from app.services.ad_sync import sync_all_employees

router = APIRouter(prefix="/admin", tags=["Administration"])


@router.get("/dashboard")
async def dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Dashboard mit Kennzahlen. Nur HR und Admin."""
    if not is_hr(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keine Berechtigung")

    total = (
        await db.execute(select(func.count(Employee.id)))
    ).scalar()
    active = (
        await db.execute(
            select(func.count(Employee.id)).where(Employee.is_active == True)
        )
    ).scalar()

    return {
        "employees_total": total,
        "employees_active": active,
        "employees_inactive": total - active,
    }


@router.post("/ad-sync")
async def trigger_ad_sync(
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """AD-Synchronisation manuell ausloesen. Nur Admin."""
    if not is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Keine Berechtigung")

    result = await sync_all_employees(db)
    return {
        "message": "AD-Synchronisation abgeschlossen",
        "synced": result["synced"],
        "errors": result["errors"],
        "updated_fields": result["updated_fields"],
    }
