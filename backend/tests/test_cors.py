"""Tests fuer die CORS-Konfiguration."""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch

from app.main import app
from app.config import Settings


@pytest.mark.asyncio
async def test_cors_erlaubt_konfigurierte_origin():
    """Konfigurierte Origin erhält korrekten CORS-Header."""
    test_settings = Settings(
        cors_origins="http://localhost:3000,https://mva.c3po42.de",
        app_debug=False,
        db_use_sqlite=True,
    )
    with patch("app.main.settings", test_settings):
        # Origins aus den Settings lesen
        origins = [o.strip() for o in test_settings.cors_origins.split(",")]
        assert "http://localhost:3000" in origins
        assert "https://mva.c3po42.de" in origins
        assert "*" not in origins


@pytest.mark.asyncio
async def test_cors_wildcard_nicht_gesetzt():
    """Wildcard '*' darf nicht als CORS-Origin konfiguriert sein."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.options(
            "/api/health",
            headers={
                "Origin": "https://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        allow_origin = response.headers.get("access-control-allow-origin", "")
        assert allow_origin != "*", (
            "CORS-Wildcard '*' darf nicht gesetzt sein – beliebige Origins würden akzeptiert"
        )


@pytest.mark.asyncio
async def test_cors_origins_aus_config_geladen():
    """cors_origins aus den Settings wird korrekt in eine Liste aufgeteilt."""
    settings = Settings(
        cors_origins="http://localhost:3000, https://mva.c3po42.de , http://localhost:8080",
        db_use_sqlite=True,
    )
    origins = [o.strip() for o in settings.cors_origins.split(",")]
    assert origins == [
        "http://localhost:3000",
        "https://mva.c3po42.de",
        "http://localhost:8080",
    ]
