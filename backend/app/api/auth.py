import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import LoginRequest, RefreshRequest, TokenResponse
from app.auth.jwt import create_token_pair, decode_token, get_current_user
from app.auth.rate_limiter import is_rate_limited, record_failed_attempt, reset_failed_attempts
from app.config import get_settings
from app.database import get_db
from app.models.employee import Employee

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentifizierung"])


def _get_client_ip(request: Request) -> str:
    """Ermittelt die Client-IP, berücksichtigt X-Forwarded-For (Nginx-Proxy)."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, http_request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    """Login. Im Dev-Modus ohne AD, in Produktion ueber Active Directory."""

    client_ip = _get_client_ip(http_request)
    blocked, retry_after = await is_rate_limited(client_ip)
    if blocked:
        response.headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Zu viele fehlgeschlagene Login-Versuche. Bitte in {retry_after} Sekunden erneut versuchen.",
            headers={"Retry-After": str(retry_after)},
        )

    try:
        if settings.ad_enabled:
            # Produktion: AD-Authentifizierung
            from app.auth.ldap import authenticate_user, determine_role_from_groups
            from app.models.employee import UserRole

            ad_user = authenticate_user(request.username, request.password)
            if ad_user is None:
                await record_failed_attempt(client_ip)
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
                await record_failed_attempt(client_ip)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Im Dev-Modus ist das Passwort 'dev'",
                )

            result = await db.execute(
                select(Employee).where(Employee.ad_username == request.username)
            )
            employee = result.scalar_one_or_none()

            if employee is None:
                await record_failed_attempt(client_ip)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Benutzer '{request.username}' nicht gefunden",
                )

    except HTTPException:
        raise

    await reset_failed_attempts(client_ip)
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
