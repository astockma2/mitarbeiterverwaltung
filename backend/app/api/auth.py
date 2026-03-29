import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import LoginRequest, RefreshRequest, TokenResponse
from app.auth.jwt import create_token_pair, decode_token, get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.employee import Employee

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentifizierung"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login. Im Dev-Modus ohne AD, in Produktion ueber Active Directory."""

    if settings.ad_enabled:
        # Produktion: AD-Authentifizierung
        from app.auth.ldap import authenticate_user, determine_role_from_groups
        from app.models.employee import UserRole

        ad_user = authenticate_user(request.username, request.password)
        if ad_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Benutzername oder Passwort falsch",
            )

        result = await db.execute(
            select(Employee).where(Employee.ad_username == ad_user.username)
        )
        employee = result.scalar_one_or_none()

        if employee is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Kein Mitarbeiter-Konto verknuepft. Bitte an die Personalabteilung wenden.",
            )

        if not employee.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Benutzerkonto deaktiviert",
            )

        ad_role = determine_role_from_groups(ad_user.groups)
        if ad_role != employee.role.value:
            employee.role = UserRole(ad_role)

    else:
        # Entwicklung: Login ueber AD-Username, Passwort = "dev"
        if request.password != "dev":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Im Dev-Modus ist das Passwort 'dev'",
            )

        result = await db.execute(
            select(Employee).where(Employee.ad_username == request.username)
        )
        employee = result.scalar_one_or_none()

        if employee is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Benutzer '{request.username}' nicht gefunden",
            )

    token_pair = create_token_pair(employee)
    logger.info("Login erfolgreich: %s (Rolle: %s)", request.username, employee.role.value)
    return token_pair


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Erneuert das Access-Token mit einem gueltigem Refresh-Token."""
    payload = decode_token(request.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kein gueltiger Refresh-Token",
        )

    employee_id = payload.get("sub")
    result = await db.execute(
        select(Employee).where(Employee.id == int(employee_id))
    )
    employee = result.scalar_one_or_none()

    if employee is None or not employee.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzer nicht gefunden oder deaktiviert",
        )

    return create_token_pair(employee)


@router.get("/me", response_model=dict)
async def get_me(current_user: Employee = Depends(get_current_user)):
    """Gibt die Daten des aktuell angemeldeten Benutzers zurueck."""
    return {
        "id": current_user.id,
        "personnel_number": current_user.personnel_number,
        "name": current_user.full_name,
        "role": current_user.role.value,
        "department_id": current_user.department_id,
    }
