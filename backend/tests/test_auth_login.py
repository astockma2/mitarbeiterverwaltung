"""Tests für den Produktions-Login via ad_username ODER Personalnummer (Issue #78)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.employee import Employee, UserRole


def _make_employee(ad_username: str, personnel_number: str) -> Employee:
    """Erzeugt einen minimalen Employee-Stub für Login-Tests."""
    import bcrypt

    emp = Employee()
    emp.id = 1
    emp.ad_username = ad_username
    emp.personnel_number = personnel_number
    emp.first_name = "Test"
    emp.last_name = "User"
    emp.role = UserRole.ADMIN
    emp.department_id = None
    emp.is_active = True
    emp.password_hash = bcrypt.hashpw(b"geheim123", bcrypt.gensalt()).decode("utf-8")
    return emp


def _make_db_mock(employee: Employee | None):
    """Gibt einen AsyncSession-Mock zurück, der `employee` als Ergebnis liefert."""
    scalar_result = MagicMock()
    scalar_result.scalar_one_or_none.return_value = employee

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=scalar_result)
    return db_mock


@pytest.mark.asyncio
async def test_prod_login_mit_ad_username():
    """Produktions-Login funktioniert mit dem Benutzernamen (ad_username)."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.database import get_db
    import app.auth.rate_limiter as rl

    rl._attempts.clear()
    employee = _make_employee(ad_username="admin", personnel_number="ADMIN001")

    async def override_get_db():
        yield _make_db_mock(employee)

    with patch("app.api.auth.settings") as mock_settings:
        mock_settings.ad_enabled = False
        mock_settings.app_env = "production"

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "geheim123"},
            )

        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_prod_login_mit_personalnummer():
    """Produktions-Login funktioniert mit der Personalnummer (personnel_number)."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.database import get_db
    import app.auth.rate_limiter as rl

    rl._attempts.clear()
    employee = _make_employee(ad_username="admin", personnel_number="ADMIN001")

    async def override_get_db():
        yield _make_db_mock(employee)

    with patch("app.api.auth.settings") as mock_settings:
        mock_settings.ad_enabled = False
        mock_settings.app_env = "production"

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "ADMIN001", "password": "geheim123"},
            )

        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_prod_login_falsches_passwort_gibt_401():
    """Falsches Passwort im Produktions-Modus liefert HTTP 401."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.database import get_db
    import app.auth.rate_limiter as rl

    rl._attempts.clear()
    employee = _make_employee(ad_username="admin", personnel_number="ADMIN001")

    async def override_get_db():
        yield _make_db_mock(employee)

    with patch("app.api.auth.settings") as mock_settings:
        mock_settings.ad_enabled = False
        mock_settings.app_env = "production"

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "falsch"},
            )

        app.dependency_overrides.clear()

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_prod_login_unbekannter_benutzer_gibt_401():
    """Unbekannter Benutzername im Produktions-Modus liefert HTTP 401."""
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.database import get_db
    import app.auth.rate_limiter as rl

    rl._attempts.clear()

    async def override_get_db():
        yield _make_db_mock(None)

    with patch("app.api.auth.settings") as mock_settings:
        mock_settings.ad_enabled = False
        mock_settings.app_env = "production"

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"username": "nichtvorhanden", "password": "irgendwas"},
            )

        app.dependency_overrides.clear()

    assert response.status_code == 401
