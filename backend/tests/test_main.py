"""Tests fuer den globalen Exception-Handler in main.py."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_global_exception_handler_gibt_keine_internen_details_zurueck():
    """HTTP-500-Antworten dürfen keine internen Fehlermeldungen enthalten."""

    # Hilfroute, die absichtlich eine Exception wirft
    test_app = FastAPI()

    @test_app.get("/trigger-error")
    async def trigger_error():
        raise RuntimeError("Geheimer Datenbankfehler: SELECT * FROM users WHERE password='secret'")

    # Den globalen Exception-Handler aus main.py registrieren
    from app.main import global_exception_handler
    test_app.add_exception_handler(Exception, global_exception_handler)

    async with AsyncClient(
        transport=ASGITransport(app=test_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/trigger-error")

    assert response.status_code == 500
    body = response.json()
    # Generische Meldung muss vorhanden sein
    assert body["detail"] == "Interner Serverfehler. Bitte Administrator kontaktieren."
    # Interne Fehlerdetails dürfen nicht zurückgegeben werden
    assert "Geheimer" not in body["detail"]
    assert "SELECT" not in body["detail"]
    assert "secret" not in body["detail"]
