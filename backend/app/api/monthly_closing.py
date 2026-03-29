"""API-Endpoints fuer Monatsabschluss und Loga-Export."""

from datetime import date, datetime
from calendar import monthrange
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user
from app.auth.permissions import is_hr
from app.database import get_db
from app.models.employee import Employee
from app.models.time_entry import (
    Absence,
    AbsenceStatus,
    AbsenceType,
    EntryStatus,
    MonthlyClosing,
    TimeEntry,
)
from app.services.audit import log_action
from app.services.time_calculator import calculate_monthly_target_hours

router = APIRouter(prefix="/monthly", tags=["Monatsabschluss"])


class MonthlyClosingResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: Optional[str] = None
    year: int
    month: int
    total_hours: float
    target_hours: float
    overtime_hours: float
    sick_days: float
    vacation_days: float
    status: str


class MonthlyOverview(BaseModel):
    year: int
    month: int
    total_employees: int
    closed: int
    open: int
    exported: int
    closings: list[MonthlyClosingResponse]


@router.post("/close")
async def close_month(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    employee_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Monatsabschluss fuer einen oder alle Mitarbeiter durchfuehren. Nur HR/Admin."""
    if not is_hr(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    _, last_day = monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, last_day)

    # Welche Mitarbeiter?
    if employee_id:
        emp_result = await db.execute(
            select(Employee).where(Employee.id == employee_id)
        )
        employees = [emp_result.scalar_one_or_none()]
        if employees[0] is None:
            raise HTTPException(status_code=404, detail="Mitarbeiter nicht gefunden")
    else:
        emp_result = await db.execute(
            select(Employee).where(Employee.is_active == True)
        )
        employees = emp_result.scalars().all()

    results = []
    for emp in employees:
        # Pruefen ob bereits abgeschlossen
        existing = await db.execute(
            select(MonthlyClosing).where(
                MonthlyClosing.employee_id == emp.id,
                MonthlyClosing.year == year,
                MonthlyClosing.month == month,
            )
        )
        if existing.scalar_one_or_none():
            results.append({"employee": emp.full_name, "status": "bereits abgeschlossen"})
            continue

        # Zeiteintraege laden
        entries_result = await db.execute(
            select(TimeEntry).where(
                TimeEntry.employee_id == emp.id,
                TimeEntry.date >= start,
                TimeEntry.date <= end,
            )
        )
        entries = entries_result.scalars().all()

        # Abwesenheiten laden
        abs_result = await db.execute(
            select(Absence).where(
                Absence.employee_id == emp.id,
                Absence.status == AbsenceStatus.APPROVED,
                Absence.start_date <= end,
                Absence.end_date >= start,
            )
        )
        absences = abs_result.scalars().all()

        total_hours = sum(e.net_hours or 0 for e in entries)
        target_hours = calculate_monthly_target_hours(emp.weekly_hours, year, month)
        sick_days = sum(a.days for a in absences if a.type == AbsenceType.SICK)
        vacation_days = sum(a.days for a in absences if a.type == AbsenceType.VACATION)

        # Eintraege sperren
        for entry in entries:
            entry.status = EntryStatus.LOCKED

        # Abschluss erstellen
        closing = MonthlyClosing(
            employee_id=emp.id,
            year=year,
            month=month,
            total_hours=round(total_hours, 2),
            target_hours=target_hours,
            overtime_hours=round(total_hours - target_hours, 2),
            sick_days=sick_days,
            vacation_days=vacation_days,
            status="CLOSED",
            closed_by=current_user.id,
            closed_at=datetime.utcnow(),
        )
        db.add(closing)

        results.append({
            "employee": emp.full_name,
            "status": "abgeschlossen",
            "total_hours": round(total_hours, 2),
            "overtime": round(total_hours - target_hours, 2),
        })

    await log_action(
        db, current_user.id, "MONTHLY_CLOSE", "monthly_closings", 0,
        {"year": year, "month": month, "count": len(results)},
    )

    return {"year": year, "month": month, "results": results}


@router.get("/overview", response_model=MonthlyOverview)
async def get_monthly_overview(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Uebersicht ueber den Monatsabschluss. Nur HR/Admin."""
    if not is_hr(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    # Alle aktiven Mitarbeiter zaehlen
    emp_count = await db.execute(
        select(Employee).where(Employee.is_active == True)
    )
    total_employees = len(emp_count.scalars().all())

    # Abschluesse laden
    result = await db.execute(
        select(MonthlyClosing).where(
            MonthlyClosing.year == year,
            MonthlyClosing.month == month,
        )
    )
    closings = result.scalars().all()

    closed = sum(1 for c in closings if c.status == "CLOSED")
    exported = sum(1 for c in closings if c.status == "EXPORTED")

    closing_responses = []
    for c in closings:
        emp_name = c.employee.full_name if c.employee else None
        closing_responses.append(MonthlyClosingResponse(
            id=c.id,
            employee_id=c.employee_id,
            employee_name=emp_name,
            year=c.year,
            month=c.month,
            total_hours=c.total_hours,
            target_hours=c.target_hours,
            overtime_hours=c.overtime_hours,
            sick_days=c.sick_days,
            vacation_days=c.vacation_days,
            status=c.status,
        ))

    return MonthlyOverview(
        year=year,
        month=month,
        total_employees=total_employees,
        closed=closed,
        open=total_employees - closed - exported,
        exported=exported,
        closings=closing_responses,
    )


@router.post("/export")
async def export_for_loga(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Exportiert die Monatsdaten im Loga-kompatiblen CSV-Format. Nur HR/Admin."""
    if not is_hr(current_user):
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    result = await db.execute(
        select(MonthlyClosing).where(
            MonthlyClosing.year == year,
            MonthlyClosing.month == month,
            MonthlyClosing.status == "CLOSED",
        )
    )
    closings = result.scalars().all()

    if not closings:
        raise HTTPException(
            status_code=400,
            detail="Keine abgeschlossenen Daten fuer diesen Monat",
        )

    # CSV generieren
    import csv
    import io

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    # Header
    writer.writerow([
        "Personalnummer",
        "Nachname",
        "Vorname",
        "Jahr",
        "Monat",
        "Ist-Stunden",
        "Soll-Stunden",
        "Ueberstunden",
        "Krankheitstage",
        "Urlaubstage",
    ])

    for closing in closings:
        emp = closing.employee
        writer.writerow([
            emp.personnel_number if emp else "",
            emp.last_name if emp else "",
            emp.first_name if emp else "",
            closing.year,
            closing.month,
            f"{closing.total_hours:.2f}".replace(".", ","),
            f"{closing.target_hours:.2f}".replace(".", ","),
            f"{closing.overtime_hours:.2f}".replace(".", ","),
            f"{closing.sick_days:.1f}".replace(".", ","),
            f"{closing.vacation_days:.1f}".replace(".", ","),
        ])

        closing.status = "EXPORTED"
        closing.exported_at = datetime.utcnow()

    csv_content = output.getvalue()

    from fastapi.responses import Response

    await log_action(
        db, current_user.id, "LOGA_EXPORT", "monthly_closings", 0,
        {"year": year, "month": month, "count": len(closings)},
    )

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=loga_export_{year}_{month:02d}.csv"
        },
    )
