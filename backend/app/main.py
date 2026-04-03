import logging
from contextlib import asynccontextmanager

import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.employees import router as employees_router
from app.api.departments import router as departments_router
from app.api.admin import router as admin_router
from app.api.time_tracking import router as time_router
from app.api.absences import router as absences_router
from app.api.monthly_closing import router as monthly_router
from app.api.shifts import router as shifts_router
from app.api.chat import router as chat_router
from app.api.reports import router as reports_router
from app.api.tickets import router as tickets_router
from app.config import get_settings
from app.database import create_tables
from app.services.seed import seed_demo_data
from app.services.seed_prod import seed_bot_user

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.app_debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Tabellen erstellen und Demo-Daten laden
    await create_tables()
    await seed_demo_data()
    await seed_bot_user()
    logging.getLogger(__name__).info("Anwendung gestartet")
    yield
    logging.getLogger(__name__).info("Anwendung beendet")


app = FastAPI(
    title=settings.app_name,
    description="Mitarbeiterverwaltung mit Zeiterfassung und Kommunikation",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS
origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router einbinden
API_PREFIX = "/api/v1"
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(employees_router, prefix=API_PREFIX)
app.include_router(departments_router, prefix=API_PREFIX)
app.include_router(admin_router, prefix=API_PREFIX)
app.include_router(time_router, prefix=API_PREFIX)
app.include_router(absences_router, prefix=API_PREFIX)
app.include_router(monthly_router, prefix=API_PREFIX)
app.include_router(shifts_router, prefix=API_PREFIX)
app.include_router(chat_router, prefix=API_PREFIX)
app.include_router(reports_router, prefix=API_PREFIX)
app.include_router(tickets_router, prefix=API_PREFIX)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    logging.getLogger(__name__).error("Unhandled error: %s\n%s", exc, "".join(tb))
    return JSONResponse(
        status_code=500,
        content={"detail": "Interner Serverfehler. Bitte Administrator kontaktieren."},
    )


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "1.2.0"}


@app.get("/api/v1/app/version")
async def app_version():
    """Aktuelle App-Version fuer Auto-Update-Check."""
    return {
        "version": "1.2.0",
        "download_url": "https://mva.c3po42.de/download/app-release.apk",
        "force_update": False,
    }
