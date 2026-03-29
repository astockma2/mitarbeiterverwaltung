"""Erstellt Demo-Daten fuer die Entwicklungsumgebung."""

import logging
from datetime import date, time, timedelta

from sqlalchemy import select

from app.database import async_session
from app.models.department import Department
from app.models.employee import Employee, EmploymentType, UserRole
from app.models.shift import ShiftTemplate, ShiftPlan, ShiftAssignment, PlanStatus

logger = logging.getLogger(__name__)


async def seed_demo_data():
    """Legt Demo-Abteilungen und einen Admin-Benutzer an, falls die DB leer ist."""
    async with async_session() as db:
        # Pruefen ob bereits Daten vorhanden
        result = await db.execute(select(Employee).limit(1))
        if result.scalar_one_or_none() is not None:
            logger.info("Datenbank enthaelt bereits Daten, Seed uebersprungen")
            return

        logger.info("Erstelle Demo-Daten...")

        # Abteilungen
        departments = [
            Department(name="Geschaeftsfuehrung", short_name="GF", cost_center="1000"),
            Department(name="Personalabteilung", short_name="HR", cost_center="1100"),
            Department(name="IT-Abteilung", short_name="IT", cost_center="1200"),
            Department(name="Innere Medizin", short_name="IM", cost_center="2000"),
            Department(name="Chirurgie", short_name="CH", cost_center="2100"),
            Department(name="Anaesthesie", short_name="AN", cost_center="2200"),
            Department(name="Notaufnahme", short_name="NA", cost_center="2300"),
            Department(name="Pflege Station 1", short_name="P1", cost_center="3000"),
            Department(name="Pflege Station 2", short_name="P2", cost_center="3100"),
            Department(name="Verwaltung", short_name="VW", cost_center="4000"),
        ]
        for dept in departments:
            db.add(dept)
        await db.flush()

        # Admin-Benutzer (fuer Entwicklung)
        admin = Employee(
            personnel_number="ADMIN001",
            ad_username="admin",
            first_name="System",
            last_name="Administrator",
            email="admin@klinik.local",
            phone="0201 4567-100",
            mobile="0170 1234567",
            date_of_birth=date(1985, 3, 15),
            street="Hospitalstr. 1",
            zip_code="45127",
            city="Essen",
            department_id=departments[2].id,
            role=UserRole.ADMIN,
            job_title="Systemadministrator",
            employment_type=EmploymentType.FULLTIME,
            weekly_hours=38.5,
            hire_date=date(2020, 1, 1),
            vacation_days_per_year=30,
            emergency_contact_name="Lisa Administrator",
            emergency_contact_phone="0170 9876543",
        )

        # HR-Benutzer
        hr_user = Employee(
            personnel_number="HR001",
            ad_username="hr.leitung",
            first_name="Maria",
            last_name="Personalerin",
            email="hr@klinik.local",
            phone="0201 4567-110",
            mobile="0171 2345678",
            date_of_birth=date(1978, 11, 22),
            street="Ruettenscheider Str. 42",
            zip_code="45131",
            city="Essen",
            department_id=departments[1].id,
            role=UserRole.HR,
            job_title="Personalleiterin",
            employment_type=EmploymentType.FULLTIME,
            weekly_hours=38.5,
            hire_date=date(2019, 6, 1),
            vacation_days_per_year=30,
            emergency_contact_name="Peter Personalerin",
            emergency_contact_phone="0171 8765432",
        )

        # Beispiel-Mitarbeiter
        employees = [
            Employee(
                personnel_number="MA001",
                ad_username="m.mueller",
                first_name="Michael",
                last_name="Mueller",
                email="m.mueller@klinik.local",
                phone="0201 4567-200",
                mobile="0172 3456789",
                date_of_birth=date(1970, 5, 8),
                street="Alfredstr. 18",
                zip_code="45130",
                city="Essen",
                department_id=departments[3].id,
                role=UserRole.DEPARTMENT_MANAGER,
                job_title="Chefarzt Innere Medizin",
                employment_type=EmploymentType.FULLTIME,
                weekly_hours=40.0,
                hire_date=date(2015, 3, 1),
                vacation_days_per_year=30,
                emergency_contact_name="Claudia Mueller",
                emergency_contact_phone="0172 1111111",
            ),
            Employee(
                personnel_number="MA002",
                ad_username="s.schmidt",
                first_name="Sabine",
                last_name="Schmidt",
                email="s.schmidt@klinik.local",
                phone="0201 4567-310",
                mobile="0173 4567890",
                date_of_birth=date(1982, 8, 14),
                street="Huyssenallee 55",
                zip_code="45128",
                city="Essen",
                department_id=departments[7].id,
                role=UserRole.TEAM_LEADER,
                job_title="Stationsleitung Pflege",
                employment_type=EmploymentType.FULLTIME,
                weekly_hours=38.5,
                hire_date=date(2018, 9, 15),
                vacation_days_per_year=30,
            ),
            Employee(
                personnel_number="MA003",
                ad_username="t.weber",
                first_name="Thomas",
                last_name="Weber",
                email="t.weber@klinik.local",
                phone="0201 4567-311",
                mobile="0174 5678901",
                date_of_birth=date(1995, 1, 30),
                street="Gladbecker Str. 7",
                zip_code="45141",
                city="Essen",
                department_id=departments[7].id,
                role=UserRole.EMPLOYEE,
                job_title="Gesundheits- und Krankenpfleger",
                employment_type=EmploymentType.FULLTIME,
                weekly_hours=38.5,
                hire_date=date(2021, 2, 1),
                vacation_days_per_year=30,
                emergency_contact_name="Martina Weber",
                emergency_contact_phone="0174 2222222",
            ),
            Employee(
                personnel_number="MA004",
                ad_username="a.fischer",
                first_name="Anna",
                last_name="Fischer",
                email="a.fischer@klinik.local",
                phone="0201 4567-210",
                mobile="0175 6789012",
                date_of_birth=date(1991, 12, 3),
                street="Bredeneyer Str. 29",
                zip_code="45133",
                city="Essen",
                department_id=departments[4].id,
                role=UserRole.EMPLOYEE,
                job_title="Assistenzaerztin Chirurgie",
                employment_type=EmploymentType.FULLTIME,
                weekly_hours=40.0,
                hire_date=date(2023, 7, 1),
                vacation_days_per_year=30,
            ),
            Employee(
                personnel_number="MA005",
                ad_username="k.braun",
                first_name="Klaus",
                last_name="Braun",
                email="k.braun@klinik.local",
                phone="0201 4567-400",
                date_of_birth=date(1988, 7, 19),
                street="Steeler Str. 104",
                zip_code="45138",
                city="Essen",
                department_id=departments[9].id,
                role=UserRole.EMPLOYEE,
                job_title="Sachbearbeiter Patientenaufnahme",
                employment_type=EmploymentType.PARTTIME,
                weekly_hours=20.0,
                hire_date=date(2022, 4, 1),
                vacation_days_per_year=15,
            ),
        ]

        db.add(admin)
        db.add(hr_user)
        for emp in employees:
            db.add(emp)

        # Schichtvorlagen
        shift_templates = [
            ShiftTemplate(
                name="Fruehdienst", short_code="F",
                start_time=time(6, 0), end_time=time(14, 0),
                break_minutes=30, color="#22C55E",
            ),
            ShiftTemplate(
                name="Spaetdienst", short_code="S",
                start_time=time(14, 0), end_time=time(22, 0),
                break_minutes=30, color="#F59E0B",
            ),
            ShiftTemplate(
                name="Nachtdienst", short_code="N",
                start_time=time(22, 0), end_time=time(6, 0),
                break_minutes=45, crosses_midnight=True, color="#6366F1",
            ),
            ShiftTemplate(
                name="Tagdienst", short_code="T",
                start_time=time(8, 0), end_time=time(16, 30),
                break_minutes=30, color="#3B82F6",
            ),
            ShiftTemplate(
                name="Bereitschaftsdienst", short_code="BD",
                start_time=time(16, 30), end_time=time(8, 0),
                break_minutes=60, crosses_midnight=True, color="#EC4899",
            ),
            ShiftTemplate(
                name="Rufbereitschaft", short_code="RB",
                start_time=time(16, 30), end_time=time(8, 0),
                break_minutes=0, crosses_midnight=True, color="#8B5CF6",
            ),
        ]
        for st in shift_templates:
            db.add(st)
        await db.flush()

        # Dienstplaene und Schichtzuweisungen fuer Demo
        today = date.today()
        all_employees = [admin, hr_user] + employees

        # Plaene fuer aktuellen und naechsten Monat erstellen
        for month_offset in range(2):
            m = today.month + month_offset
            y = today.year
            if m > 12:
                m -= 12
                y += 1

            # Fuer jede Abteilung mit Mitarbeitern einen Plan
            for dept in [departments[2], departments[3], departments[4],
                         departments[7], departments[9]]:
                plan = ShiftPlan(
                    department_id=dept.id,
                    year=y,
                    month=m,
                    status=PlanStatus.PUBLISHED,
                    created_by=admin.id,
                )
                db.add(plan)
                await db.flush()

                # Mitarbeiter dieser Abteilung finden
                dept_emps = [e for e in all_employees if e.department_id == dept.id]
                if not dept_emps:
                    continue

                # Schichten zuweisen: Wochentage im Monat durchgehen
                first_day = date(y, m, 1)
                if m == 12:
                    last_day = date(y + 1, 1, 1) - timedelta(days=1)
                else:
                    last_day = date(y, m + 1, 1) - timedelta(days=1)

                current_day = first_day
                shift_rotation = [
                    shift_templates[0],  # F
                    shift_templates[0],  # F
                    shift_templates[1],  # S
                    shift_templates[1],  # S
                    shift_templates[2],  # N
                ]
                day_index = 0
                while current_day <= last_day:
                    weekday = current_day.weekday()  # 0=Mo, 6=So
                    if weekday < 6:  # Mo-Fr Schichten zuweisen
                        for i, emp in enumerate(dept_emps):
                            rot_idx = (day_index + i) % len(shift_rotation)
                            template = shift_rotation[rot_idx]
                            assignment = ShiftAssignment(
                                plan_id=plan.id,
                                employee_id=emp.id,
                                shift_template_id=template.id,
                                date=current_day,
                            )
                            db.add(assignment)
                        day_index += 1
                    current_day += timedelta(days=1)

        await db.commit()
        logger.info(
            "Demo-Daten erstellt: %d Abteilungen, %d Mitarbeiter, %d Schichtvorlagen + Dienstplaene",
            len(departments),
            len(employees) + 2,
            len(shift_templates),
        )
