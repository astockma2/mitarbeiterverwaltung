"""MVA-spezifische Anbindung an den zentralen LizenzServer.

Der License-Client (license.c3po42.de) wird hier mit MVA-Kontext initialisiert:
- product_code = "mva" (PRO_MA_MONAT, 4 EUR)
- get_usage_count = aktive Mitarbeiter (Employee.is_active=True)

Die aktive MA-Zahl wird einmal pro Tag an den LizenzServer gemeldet.
Dieser berechnet am Monatsende bei Ueberschreitung ein Supplementary-Invoice.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from sqlalchemy import func, select

from app.models.employee import Employee
from app.database import async_session
from app.services.license_client import LicenseClient

log = logging.getLogger(__name__)


_active_count_cache: dict = {"count": None, "last": 0.0}


async def _count_active_employees() -> Optional[int]:
    """Liest die aktuelle Anzahl aktiver Mitarbeiter."""
    try:
        async with async_session() as session:
            r = await session.execute(
                select(func.count()).select_from(Employee).where(Employee.is_active == True)
            )
            return int(r.scalar() or 0)
    except Exception as e:
        log.warning(f"Konnte aktive MA nicht zaehlen: {e}")
        return None


def _sync_active_count() -> Optional[int]:
    """Synchrone Bruecke fuer LicenseClient.get_usage_count (Callable)."""
    # Cache 30s, da usage_report_loop taeglich aufruft — sofort ok
    return _active_count_cache.get("count")


async def _refresh_count_loop():
    while True:
        _active_count_cache["count"] = await _count_active_employees()
        await asyncio.sleep(3600)  # stuendlich aktualisieren


LICENSE = LicenseClient(
    base_dir=Path(__file__).resolve().parent.parent.parent,  # /app
    product_code="mva",
    product_name="Mitarbeiterverwaltung",
    product_price="4",
    get_usage_count=_sync_active_count,
    exempt_paths=(
        "/api/v1/auth/",
        "/api/v1/app/version",
        "/api/health",
        "/api/docs",
        "/api/redoc",
        "/api/openapi.json",
        "/produkt",
        "/download/",
    ),
)


async def start_license_tasks():
    """In der lifespan-Funktion aufzurufen. Startet Hintergrundtasks."""
    # Erster Count sofort, damit der Cache nicht leer ist
    _active_count_cache["count"] = await _count_active_employees()
    tasks = [
        asyncio.create_task(_refresh_count_loop()),
        asyncio.create_task(LICENSE.check_loop()),
        asyncio.create_task(LICENSE.usage_report_loop()),
    ]
    return tasks
