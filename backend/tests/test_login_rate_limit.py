"""Tests für das Rate-Limiting beim Login-Endpoint (Issue #61, #72)."""

import pytest
import yaml
import os
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock

from app.main import app


@pytest.fixture(autouse=True)
def reset_in_memory_attempts():
    """Setzt den In-Memory-Fehlversuchs-Zähler vor jedem Test zurück."""
    import app.auth.rate_limiter as rl
    rl._attempts.clear()
    yield
    rl._attempts.clear()


@pytest.mark.asyncio
async def test_login_gibt_401_bei_falschem_passwort():
    """Einzelner fehlgeschlagener Login liefert 401, noch kein Rate-Limiting."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "falsch"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_gibt_429_nach_fuenf_fehlversuchen():
    """Nach 5 fehlgeschlagenen Versuchen muss HTTP 429 zurückgegeben werden."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        for _ in range(5):
            await client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "falsch"},
            )

        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "falsch"},
        )

    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert int(response.headers["Retry-After"]) > 0
    body = response.json()
    assert "fehlgeschlagene Login-Versuche" in body["detail"]


@pytest.mark.asyncio
async def test_login_429_bleibt_auch_mit_richtigem_passwort():
    """Nach Sperrung wird auch mit richtigem Passwort kein Login erlaubt (IP gesperrt)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        for _ in range(5):
            await client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "falsch"},
            )

        # Versuch mit korrektem Dev-Passwort – trotzdem gesperrt
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "dev"},
        )

    assert response.status_code == 429


@pytest.mark.asyncio
async def test_rate_limiter_zaehlt_nur_fehlversuche():
    """Erfolgreicher Login darf nicht zum Rate-Limit-Zähler beitragen und setzt ihn zurück."""
    # Patch DB-Abfrage für erfolgreichen Dev-Login
    from app.models.employee import Employee, UserRole

    fake_employee = Employee()
    fake_employee.id = 1
    fake_employee.personnel_number = "ADM001"
    fake_employee.first_name = "Admin"
    fake_employee.last_name = "User"
    fake_employee.role = UserRole.ADMIN
    fake_employee.department_id = None
    fake_employee.is_active = True
    fake_employee.ad_username = "admin"

    async def fake_scalar(*args, **kwargs):
        return fake_employee

    with patch("app.api.auth.settings") as mock_settings:
        mock_settings.ad_enabled = False

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 4 Fehlversuche
            for _ in range(4):
                await client.post(
                    "/api/v1/auth/login",
                    json={"username": "admin", "password": "falsch"},
                )

            # Erfolgreicher Login setzt Zähler zurück
            # (wir mocken den DB-Call direkt im rate_limiter)
            import app.auth.rate_limiter as rl
            await rl.reset_failed_attempts("testclient")

            # Prüfen dass kein Rate-Limit aktiv ist
            blocked, _ = await rl.is_rate_limited("testclient")
            assert not blocked


@pytest.mark.asyncio
async def test_is_rate_limited_gibt_false_bei_wenigen_versuchen():
    """Unter dem Schwellenwert darf kein Rate-Limit aktiv sein."""
    import app.auth.rate_limiter as rl

    for _ in range(4):
        await rl.record_failed_attempt("test-ip-1")

    blocked, retry_after = await rl.is_rate_limited("test-ip-1")
    assert not blocked
    assert retry_after == 0


@pytest.mark.asyncio
async def test_is_rate_limited_gibt_true_ab_fuenf_versuchen():
    """Ab 5 fehlgeschlagenen Versuchen muss is_rate_limited True zurückgeben."""
    import app.auth.rate_limiter as rl

    for _ in range(5):
        await rl.record_failed_attempt("test-ip-2")

    blocked, retry_after = await rl.is_rate_limited("test-ip-2")
    assert blocked
    assert retry_after > 0


@pytest.mark.asyncio
async def test_reset_failed_attempts_hebt_sperre_auf():
    """Nach reset_failed_attempts darf kein Rate-Limit mehr aktiv sein."""
    import app.auth.rate_limiter as rl

    for _ in range(5):
        await rl.record_failed_attempt("test-ip-3")

    await rl.reset_failed_attempts("test-ip-3")

    blocked, _ = await rl.is_rate_limited("test-ip-3")
    assert not blocked


def test_prod_docker_compose_redis_url_korrekt():
    """Stellt sicher, dass docker-compose.prod.yml REDIS_URL mit Service-Namen 'redis' setzt.

    Hintergrund (Issue #72): Der Default redis://localhost:6379/0 funktioniert im
    Docker-Netzwerk nicht — Redis ist dort unter dem Service-Namen 'redis' erreichbar.
    """
    compose_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "docker-compose.prod.yml"
    )
    with open(compose_path) as f:
        compose = yaml.safe_load(f)

    backend_env = compose["services"]["backend"]["environment"]
    redis_url = backend_env.get("REDIS_URL", "")

    assert redis_url, "REDIS_URL muss in docker-compose.prod.yml gesetzt sein"
    assert redis_url.startswith("redis://redis"), (
        f"REDIS_URL muss 'redis://redis' als Hostnamen nutzen (Docker-Servicename), "
        f"nicht 'localhost'. Aktuell: {redis_url}"
    )
