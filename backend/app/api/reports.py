"""API-Endpoints fuer erweiterte Auswertungen und Reports."""

import csv
import io
from calendar import monthrange
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.jwt import get_current_user
from app.auth.permissions import is_hr
from app.database import get_db
from app.models.employee import Employee
from app.models.department import Department
from app.models.time_entry import (
    TimeEntry, Surcharge, Absence, AbsenceStatus, AbsenceType, MonthlyClosing,
)
from app.services.time_calculator import (
    calculate_monthly_target_hours, get_holidays,
)

router = APIRouter(prefix="/reports", tags=["Auswertungen"])


@router.get("/yearly-overview")
async def yearly_overview(
    year: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Jahresuebersicht: Stunden, Ueberstunden, Abwesenheiten pro Mitarbeiter."""
    if not is_hr(current_user):
        raise HTTPException(403, "Keine Berechtigung")

    emps = await db.execute(
        select(Employee).where(Employee.is_active == True)
        .order_by(Employee.last_name)
    )
    employees = emps.scalars().all()

    result = []
    for emp in employees:
        # Monatsabschluesse laden
        closings_q = await db.execute(
            select(MonthlyClosing).where(
                MonthlyClosing.employee_id == emp.id,
                MonthlyClosing.year == year,
            ).order_by(MonthlyClosing.month)
        )
        closings = closings_q.scalars().all()

        # Abwesenheiten laden
        abs_q = await db.execute(
            select(Absence).where(
                Absence.employee_id == emp.id,
                Absence.status == AbsenceStatus.APPROVED,
                Absence.start_date >= date(year, 1, 1),
                Absence.end_date <= date(year, 12, 31),
            )
        )
        absences = abs_q.scalars().all()

        total_hours = sum(c.total_hours for c in closings)
        target_hours = sum(c.target_hours for c in closings)
        overtime = sum(c.overtime_hours for c in closings)
        sick_days = sum(a.days for a in absences if a.type == AbsenceType.SICK)
        vacation_days = sum(a.days for a in absences if a.type == AbsenceType.VACATION)
        training_days = sum(a.days for a in absences if a.type == AbsenceType.TRAINING)

        months_data = {}
        for c in closings:
            months_data[c.month] = {
                "total_hours": c.total_hours,
                "target_hours": c.target_hours,
                "overtime": c.overtime_hours,
            }

        result.append({
            "employee_id": emp.id,
            "personnel_number": emp.personnel_number,
            "name": f"{emp.first_name} {emp.last_name}",
            "department": emp.department.name if emp.department else None,
            "weekly_hours": emp.weekly_hours,
            "total_hours": round(total_hours, 2),
            "target_hours": round(target_hours, 2),
            "overtime_hours": round(overtime, 2),
            "sick_days": sick_days,
            "vacation_days": vacation_days,
            "training_days": training_days,
            "months": months_data,
        })

    return {
        "year": year,
        "employees": result,
        "summary": {
            "total_employees": len(result),
            "total_hours": round(sum(e["total_hours"] for e in result), 2),
            "total_overtime": round(sum(e["overtime_hours"] for e in result), 2),
            "total_sick_days": sum(e["sick_days"] for e in result),
            "total_vacation_days": sum(e["vacation_days"] for e in result),
        },
    }


@router.get("/department-summary")
async def department_summary(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Auswertung nach Abteilung fuer einen Monat."""
    if not is_hr(current_user):
        raise HTTPException(403, "Keine Berechtigung")

    depts = await db.execute(select(Department).order_by(Department.name))
    departments = depts.scalars().all()

    result = []
    for dept in departments:
        # Mitarbeiter der Abteilung
        emp_q = await db.execute(
            select(Employee).where(
                Employee.department_id == dept.id,
                Employee.is_active == True,
            )
        )
        emps = emp_q.scalars().all()
        if not emps:
            continue

        emp_ids = [e.id for e in emps]

        # Monatsabschluesse
        closings_q = await db.execute(
            select(MonthlyClosing).where(
                MonthlyClosing.employee_id.in_(emp_ids),
                MonthlyClosing.year == year,
                MonthlyClosing.month == month,
            )
        )
        closings = closings_q.scalars().all()

        total_hours = sum(c.total_hours for c in closings)
        target_hours = sum(c.target_hours for c in closings)
        overtime = sum(c.overtime_hours for c in closings)

        # Abwesenheiten
        _, last_day = monthrange(year, month)
        abs_q = await db.execute(
            select(Absence).where(
                Absence.employee_id.in_(emp_ids),
                Absence.status == AbsenceStatus.APPROVED,
                Absence.start_date <= date(year, month, last_day),
                Absence.end_date >= date(year, month, 1),
            )
        )
        absences = abs_q.scalars().all()
        sick_days = sum(a.days for a in absences if a.type == AbsenceType.SICK)

        result.append({
            "department_id": dept.id,
            "department_name": dept.name,
            "cost_center": dept.cost_center,
            "employee_count": len(emps),
            "total_hours": round(total_hours, 2),
            "target_hours": round(target_hours, 2),
            "overtime_hours": round(overtime, 2),
            "sick_days": sick_days,
            "coverage_rate": round(
                (len(closings) / len(emps) * 100) if emps else 0, 1
            ),
        })

    return {
        "year": year,
        "month": month,
        "departments": result,
    }


@router.get("/surcharge-summary")
async def surcharge_summary(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Zuschlagsauswertung fuer einen Monat."""
    if not is_hr(current_user):
        raise HTTPException(403, "Keine Berechtigung")

    _, last_day = monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, last_day)

    # Alle Zuschlaege mit Zeiteintraegen laden
    entries_q = await db.execute(
        select(TimeEntry)
        .options(selectinload(TimeEntry.surcharges))
        .where(
            TimeEntry.date >= start,
            TimeEntry.date <= end,
        )
    )
    entries = entries_q.scalars().unique().all()

    # Nach Typ aggregieren
    type_totals: dict[str, float] = {}
    employee_surcharges: dict[int, dict[str, float]] = {}

    for entry in entries:
        for s in entry.surcharges:
            type_totals[s.type] = type_totals.get(s.type, 0) + s.hours
            if entry.employee_id not in employee_surcharges:
                employee_surcharges[entry.employee_id] = {}
            emp_s = employee_surcharges[entry.employee_id]
            emp_s[s.type] = emp_s.get(s.type, 0) + s.hours

    # Mitarbeiternamen laden
    if employee_surcharges:
        emp_q = await db.execute(
            select(Employee).where(Employee.id.in_(employee_surcharges.keys()))
        )
        emp_map = {
            e.id: f"{e.first_name} {e.last_name}"
            for e in emp_q.scalars().all()
        }
    else:
        emp_map = {}

    return {
        "year": year,
        "month": month,
        "totals": {k: round(v, 2) for k, v in type_totals.items()},
        "by_employee": [
            {
                "employee_id": eid,
                "name": emp_map.get(eid, ""),
                "surcharges": {k: round(v, 2) for k, v in surchs.items()},
            }
            for eid, surchs in employee_surcharges.items()
        ],
    }


@router.get("/absence-statistics")
async def absence_statistics(
    year: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Abwesenheitsstatistik fuer ein Jahr."""
    if not is_hr(current_user):
        raise HTTPException(403, "Keine Berechtigung")

    abs_q = await db.execute(
        select(Absence).where(
            Absence.status == AbsenceStatus.APPROVED,
            Absence.start_date >= date(year, 1, 1),
            Absence.end_date <= date(year, 12, 31),
        )
    )
    absences = abs_q.scalars().all()

    # Nach Typ
    by_type: dict[str, dict] = {}
    for a in absences:
        t = a.type.value if hasattr(a.type, 'value') else a.type
        if t not in by_type:
            by_type[t] = {"count": 0, "days": 0}
        by_type[t]["count"] += 1
        by_type[t]["days"] += a.days

    # Nach Monat
    by_month: dict[int, int] = {}
    for a in absences:
        m = a.start_date.month
        by_month[m] = by_month.get(m, 0) + a.days

    # Mitarbeiter mit meisten Krankheitstagen
    sick_by_emp: dict[int, int] = {}
    for a in absences:
        t = a.type.value if hasattr(a.type, 'value') else a.type
        if t == "SICK":
            sick_by_emp[a.employee_id] = sick_by_emp.get(a.employee_id, 0) + a.days

    # Top Krankheitstage
    if sick_by_emp:
        emp_ids = list(sick_by_emp.keys())
        emp_q = await db.execute(select(Employee).where(Employee.id.in_(emp_ids)))
        emp_map = {
            e.id: f"{e.first_name} {e.last_name}"
            for e in emp_q.scalars().all()
        }
        top_sick = sorted(
            [{"name": emp_map.get(eid, ""), "days": days}
             for eid, days in sick_by_emp.items()],
            key=lambda x: x["days"], reverse=True,
        )[:10]
    else:
        top_sick = []

    return {
        "year": year,
        "by_type": by_type,
        "by_month": {str(m): days for m, days in sorted(by_month.items())},
        "top_sick_days": top_sick,
        "total_sick_days": sum(
            d["days"] for t, d in by_type.items() if t == "SICK"
        ),
        "total_vacation_days": sum(
            d["days"] for t, d in by_type.items() if t == "VACATION"
        ),
    }


@router.get("/export-extended")
async def export_extended_csv(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Erweiterter CSV-Export mit Zuschlaegen und Abwesenheitsdetails."""
    if not is_hr(current_user):
        raise HTTPException(403, "Keine Berechtigung")

    _, last_day = monthrange(year, month)
    start = date(year, month, 1)
    end = date(year, month, last_day)

    emps_q = await db.execute(
        select(Employee).where(Employee.is_active == True)
        .order_by(Employee.last_name)
    )
    employees = emps_q.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "Personalnummer", "Nachname", "Vorname", "Abteilung", "Kostenstelle",
        "Soll-Stunden", "Ist-Stunden", "Ueberstunden",
        "Nachtstunden", "Sonntagsstunden", "Feiertagsstunden",
        "Krankheitstage", "Urlaubstage", "Fortbildungstage", "Sonderurlaub",
        "Status",
    ])

    for emp in employees:
        # Monatsabschluss
        closing_q = await db.execute(
            select(MonthlyClosing).where(
                MonthlyClosing.employee_id == emp.id,
                MonthlyClosing.year == year,
                MonthlyClosing.month == month,
            )
        )
        closing = closing_q.scalar_one_or_none()

        # Zuschlaege
        entries_q = await db.execute(
            select(TimeEntry)
            .options(selectinload(TimeEntry.surcharges))
            .where(
                TimeEntry.employee_id == emp.id,
                TimeEntry.date >= start,
                TimeEntry.date <= end,
            )
        )
        entries = entries_q.scalars().unique().all()

        night_hours = 0.0
        sunday_hours = 0.0
        holiday_hours = 0.0
        for entry in entries:
            for s in entry.surcharges:
                if s.type == "NIGHT":
                    night_hours += s.hours
                elif s.type == "SUNDAY":
                    sunday_hours += s.hours
                elif s.type == "HOLIDAY":
                    holiday_hours += s.hours

        # Abwesenheiten
        abs_q = await db.execute(
            select(Absence).where(
                Absence.employee_id == emp.id,
                Absence.status == AbsenceStatus.APPROVED,
                Absence.start_date <= end,
                Absence.end_date >= start,
            )
        )
        absences = abs_q.scalars().all()
        sick = sum(a.days for a in absences if a.type == AbsenceType.SICK)
        vacation = sum(a.days for a in absences if a.type == AbsenceType.VACATION)
        training = sum(a.days for a in absences if a.type == AbsenceType.TRAINING)
        special = sum(a.days for a in absences if a.type == AbsenceType.SPECIAL)

        total_h = closing.total_hours if closing else sum(e.net_hours or 0 for e in entries)
        target_h = closing.target_hours if closing else calculate_monthly_target_hours(emp.weekly_hours, year, month)
        overtime_h = closing.overtime_hours if closing else round(total_h - target_h, 2)
        status = closing.status if closing else "OFFEN"

        dept_name = emp.department.name if emp.department else ""
        cost_center = emp.department.cost_center if emp.department else ""

        def fmt(val):
            return f"{val:.2f}".replace(".", ",")

        writer.writerow([
            emp.personnel_number, emp.last_name, emp.first_name,
            dept_name, cost_center,
            fmt(target_h), fmt(total_h), fmt(overtime_h),
            fmt(night_hours), fmt(sunday_hours), fmt(holiday_hours),
            fmt(sick), fmt(vacation), fmt(training), fmt(special),
            status,
        ])

    csv_content = output.getvalue()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=report_{year}_{month:02d}.csv"
        },
    )
