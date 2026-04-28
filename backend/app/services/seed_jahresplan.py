"""Idempotenter Seed fuer den Jahres-Dienstplan 2026 (IT-Team).

Legt 9 IT-Mitarbeiter an (falls fehlend) und uebertraegt die Codes aus dem
Plan-Screenshot vom 26.04.2026 als DutyPlanEntry-Eintraege.
Codes: U=Urlaub, Ug=Urlaub geplant, A=Arbeitszeitausgleich, S=Schule Azubi,
B=Bereitschaft, I=Ilmenau, H=Hotlinedienst, M=MVZ, Dr=Dienstreise, K=Kur,
su=security update day, T=Teammeeting, Ez=Elternzeit, TSC=Zeitreduzierung TSC.
Leere Felder = Normaldienst.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import select

from app.database import async_session
from app.models.department import Department
from app.models.employee import Employee, EmploymentType, UserRole
from app.models.shift import DutyPlanEntry

logger = logging.getLogger(__name__)


# (Personalnummer, AD-Username, Vorname, Nachname, Resturlaub-2026)
IT_TEAM: list[tuple[str, str, str, str, int]] = [
    ("IT001", "s.raida",       "Stefan", "Raida",       28),
    ("IT002", "h.enig",        "Holger", "Enig",        27),
    ("IT003", "t.scheike",     "Tom",    "Scheike",     29),
    ("IT004", "a.stoecklein",  "Andre",  "Stoecklein",  25),
    ("IT005", "p.czaikowski",  "Peter",  "Czaikowski",  26),
    ("IT006", "m.nitsch",      "Marc",   "Nitsch",      24),
    ("IT007", "r.weise",       "Ronny",  "Weise",       30),
    ("IT008", "a.stockmann",   "Andre",  "Stockmann",   30),
    ("IT009", "b.nettkau",     "Ben",    "Nettkau",     11),
]


def _r(start: str, end: str, code: str) -> tuple[date, date, str]:
    """Helper: Datumsbereich (inklusiv) mit Code."""
    return date.fromisoformat(start), date.fromisoformat(end), code


# Eintraege pro Personalnummer als Liste (start, end, code).
# Fokus auf gut erkennbare Wochenbloecke aus dem Screenshot 26.04.2026.
# Legende-Zeile + Ferienbalken werden vom Frontend selbst gerendert.
PLAN_2026: dict[str, list[tuple[date, date, str]]] = {
    # Stefan Raida
    "IT001": [
        _r("2026-01-19", "2026-01-23", "I"),
        _r("2026-02-09", "2026-02-13", "U"),
        _r("2026-03-16", "2026-03-20", "T"),
        _r("2026-04-13", "2026-04-17", "U"),
        _r("2026-04-20", "2026-04-21", "Dr"),
        _r("2026-05-11", "2026-05-15", "U"),
        _r("2026-05-18", "2026-05-19", "Dr"),
        _r("2026-06-08", "2026-06-08", "T"),
        _r("2026-09-07", "2026-09-11", "T"),
        _r("2026-09-14", "2026-09-18", "U"),
    ],
    # Holger Enig
    "IT002": [
        _r("2026-01-05", "2026-01-09", "B"),
        _r("2026-01-12", "2026-01-12", "B"),
        _r("2026-01-26", "2026-01-30", "B"),
        _r("2026-02-02", "2026-02-06", "U"),
        _r("2026-02-16", "2026-02-20", "U"),
        _r("2026-03-09", "2026-03-13", "B"),
        _r("2026-03-16", "2026-03-20", "T"),
        _r("2026-04-06", "2026-04-10", "U"),
        _r("2026-04-13", "2026-04-17", "B"),
        _r("2026-04-20", "2026-04-24", "A"),
        _r("2026-05-04", "2026-05-08", "A"),
        _r("2026-05-11", "2026-05-15", "B"),
        _r("2026-06-01", "2026-06-05", "B"),
        _r("2026-06-08", "2026-06-08", "T"),
    ],
    # Tom Scheike
    "IT003": [
        _r("2026-01-02", "2026-01-02", "U"),
        _r("2026-01-05", "2026-01-09", "U"),
        _r("2026-02-09", "2026-02-13", "H"),
        _r("2026-03-02", "2026-03-06", "H"),
        _r("2026-03-09", "2026-03-13", "TSC"),
        _r("2026-03-16", "2026-03-20", "T"),
        _r("2026-03-23", "2026-03-27", "TSC"),
        _r("2026-04-06", "2026-04-10", "U"),
        _r("2026-04-13", "2026-04-17", "B"),
        _r("2026-06-22", "2026-06-26", "TSC"),
        _r("2026-07-06", "2026-07-10", "TSC"),
        _r("2026-08-17", "2026-08-21", "TSC"),
        _r("2026-09-07", "2026-09-11", "T"),
        _r("2026-10-12", "2026-10-16", "TSC"),
        _r("2026-11-23", "2026-11-27", "TSC"),
    ],
    # Andre Stoecklein
    "IT004": [
        _r("2026-01-02", "2026-01-02", "U"),
        _r("2026-01-05", "2026-01-09", "U"),
        _r("2026-01-12", "2026-01-16", "B"),
        _r("2026-02-02", "2026-02-06", "I"),
        _r("2026-02-09", "2026-02-13", "U"),
        _r("2026-03-02", "2026-03-06", "H"),
        _r("2026-04-06", "2026-04-10", "U"),
        _r("2026-04-13", "2026-04-17", "B"),
        _r("2026-05-04", "2026-05-08", "U"),
        _r("2026-05-11", "2026-05-15", "U"),
        _r("2026-06-08", "2026-06-08", "T"),
    ],
    # Peter Czaikowski
    "IT005": [
        _r("2026-01-02", "2026-01-02", "U"),
        _r("2026-01-05", "2026-01-09", "B"),
        _r("2026-01-12", "2026-01-16", "H"),
        _r("2026-01-26", "2026-01-30", "I"),
        _r("2026-02-02", "2026-02-06", "U"),
        _r("2026-03-09", "2026-03-13", "B"),
        _r("2026-03-16", "2026-03-20", "T"),
        _r("2026-03-23", "2026-03-27", "K"),
        _r("2026-03-30", "2026-04-03", "K"),
        _r("2026-04-06", "2026-04-10", "U"),
        _r("2026-04-13", "2026-04-17", "U"),
        _r("2026-05-04", "2026-05-08", "su"),
        _r("2026-05-25", "2026-05-29", "B"),
        _r("2026-06-22", "2026-06-22", "su"),
        _r("2026-07-06", "2026-07-10", "Ug"),
        _r("2026-07-13", "2026-07-17", "Ug"),
        _r("2026-07-20", "2026-07-24", "Ug"),
        _r("2026-07-27", "2026-07-31", "Ug"),
        _r("2026-08-03", "2026-08-07", "Ug"),
        _r("2026-08-10", "2026-08-14", "Ug"),
        _r("2026-08-31", "2026-08-31", "su"),
        _r("2026-10-26", "2026-10-30", "su"),
        _r("2026-11-23", "2026-11-27", "su"),
    ],
    # Marc Nitsch
    "IT006": [
        _r("2026-01-19", "2026-01-23", "I"),
        _r("2026-02-23", "2026-02-27", "A"),
        _r("2026-03-02", "2026-03-06", "A"),
        _r("2026-03-16", "2026-03-20", "T"),
        _r("2026-04-13", "2026-04-17", "B"),
        _r("2026-04-20", "2026-04-24", "A"),
        _r("2026-05-04", "2026-05-04", "A"),
        _r("2026-05-11", "2026-05-15", "B"),
        _r("2026-06-15", "2026-06-19", "B"),
        _r("2026-07-13", "2026-07-17", "B"),
        _r("2026-09-07", "2026-09-11", "T"),
        _r("2026-10-26", "2026-10-30", "A"),
    ],
    # Ronny Weise
    "IT007": [
        _r("2026-01-02", "2026-01-02", "H"),
        _r("2026-02-09", "2026-02-13", "H"),
        _r("2026-03-09", "2026-03-13", "B"),
        _r("2026-03-16", "2026-03-20", "T"),
        _r("2026-03-23", "2026-03-27", "U"),
        _r("2026-03-30", "2026-04-03", "U"),
        _r("2026-04-13", "2026-04-17", "B"),
        _r("2026-04-20", "2026-04-24", "B"),
        _r("2026-05-18", "2026-05-22", "Dr"),
        _r("2026-07-13", "2026-07-17", "U"),
        _r("2026-07-20", "2026-07-24", "U"),
        _r("2026-07-27", "2026-07-31", "U"),
        _r("2026-09-07", "2026-09-11", "T"),
    ],
    # Andre Stockmann
    "IT008": [
        _r("2026-01-02", "2026-01-02", "U"),
        _r("2026-01-05", "2026-01-05", "U"),
        _r("2026-02-09", "2026-02-13", "I"),
        _r("2026-02-23", "2026-02-27", "H"),
        _r("2026-03-16", "2026-03-20", "T"),
        _r("2026-04-06", "2026-04-10", "U"),
        _r("2026-05-04", "2026-05-08", "H"),
        _r("2026-06-15", "2026-06-19", "T"),
        _r("2026-09-07", "2026-09-11", "T"),
        _r("2026-12-21", "2026-12-31", "B"),
    ],
    # Ben Nettkau
    "IT009": [
        _r("2026-02-23", "2026-02-27", "S"),
        _r("2026-03-02", "2026-03-06", "S"),
        _r("2026-04-27", "2026-04-30", "S"),
        _r("2026-05-04", "2026-05-08", "S"),
        _r("2026-05-11", "2026-05-15", "S"),
        _r("2026-10-19", "2026-10-23", "S"),
        _r("2026-10-26", "2026-10-30", "S"),
    ],
}


async def seed_jahresplan_2026() -> None:
    """Legt 9 IT-Mitarbeiter und die Plan-Eintraege fuer 2026 an, falls noch nicht vorhanden."""
    async with async_session() as db:
        # IT-Abteilung finden (oder anlegen)
        result = await db.execute(select(Department).where(Department.short_name == "IT"))
        it_dept = result.scalar_one_or_none()
        if it_dept is None:
            it_dept = Department(name="IT-Abteilung", short_name="IT", cost_center="1200")
            db.add(it_dept)
            await db.flush()

        # Mitarbeiter anlegen falls fehlend - Match ueber personnel_number ODER ad_username
        # damit pre-existierende Mitarbeiter mit gleichem ad_user (z.B. a.stockmann)
        # wiederverwendet werden statt UniqueViolationError zu werfen.
        emp_by_pn: dict[str, Employee] = {}
        for personnel_number, ad_user, vorname, nachname, _rest in IT_TEAM:
            existing = await db.execute(
                select(Employee).where(
                    (Employee.personnel_number == personnel_number)
                    | (Employee.ad_username == ad_user)
                )
            )
            emp = existing.scalars().first()
            if emp is None:
                emp = Employee(
                    personnel_number=personnel_number,
                    ad_username=ad_user,
                    first_name=vorname,
                    last_name=nachname,
                    email=f"{ad_user}@klinik.local",
                    department_id=it_dept.id,
                    role=UserRole.EMPLOYEE,
                    job_title="IT-Systemadministrator",
                    employment_type=EmploymentType.FULLTIME,
                    weekly_hours=38.5,
                    hire_date=date(2018, 1, 1),
                    vacation_days_per_year=30,
                )
                db.add(emp)
                await db.flush()
                logger.info("Jahresplan-Seed: Mitarbeiter angelegt %s %s", vorname, nachname)
            else:
                emp.personnel_number = personnel_number
                emp.ad_username = ad_user
                emp.first_name = vorname
                emp.last_name = nachname
                emp.email = emp.email or f"{ad_user}@klinik.local"
                emp.department_id = it_dept.id
                emp.role = emp.role or UserRole.EMPLOYEE
                emp.job_title = emp.job_title or "IT-Systemadministrator"
                emp.employment_type = emp.employment_type or EmploymentType.FULLTIME
                emp.weekly_hours = emp.weekly_hours or 38.5
                emp.hire_date = emp.hire_date or date(2018, 1, 1)
                emp.vacation_days_per_year = 30
                emp.is_active = True
            emp_by_pn[personnel_number] = emp

        # Pruefen ob bereits Eintraege fuer 2026 existieren - dann ueberspringen
        existing_count = await db.execute(
            select(DutyPlanEntry).where(
                DutyPlanEntry.date.between(date(2026, 1, 1), date(2026, 12, 31)),
                DutyPlanEntry.employee_id.in_([e.id for e in emp_by_pn.values()]),
            ).limit(1)
        )
        if existing_count.scalar_one_or_none() is not None:
            logger.info("Jahresplan-Seed: 2026-Eintraege vorhanden, ueberspringe.")
            return

        # Plan-Eintraege schreiben
        total = 0
        for personnel_number, ranges in PLAN_2026.items():
            emp = emp_by_pn.get(personnel_number)
            if emp is None:
                continue
            for start, end, code in ranges:
                cursor = start
                while cursor <= end:
                    # Wochenende auslassen, ausser Bereitschaft (B) - im Screenshot
                    # ziehen sich B-Bloecke teils ueber Wochenenden, andere Codes nicht.
                    if cursor.weekday() >= 5 and code != "B":
                        cursor += timedelta(days=1)
                        continue
                    db.add(DutyPlanEntry(
                        employee_id=emp.id,
                        date=cursor,
                        code=code,
                    ))
                    total += 1
                    cursor += timedelta(days=1)

        await db.commit()
        logger.info("Jahresplan-Seed: %d Eintraege fuer 2026 geschrieben.", total)
