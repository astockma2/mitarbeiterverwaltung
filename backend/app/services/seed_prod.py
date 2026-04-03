"""Produktions-Seed: Legt systemkritische Einträge an (idempotent)."""

import logging
from datetime import date

from sqlalchemy import select

from app.database import async_session
from app.models.employee import Employee, EmploymentType, UserRole

logger = logging.getLogger(__name__)


async def seed_bot_user():
    """Stellt sicher dass der Docs-Bot-User existiert (idempotent)."""
    async with async_session() as db:
        existing = await db.execute(
            select(Employee).where(Employee.personnel_number == "BOT001")
        )
        if existing.scalar_one_or_none() is not None:
            logger.info("Docs-Bot bereits vorhanden, übersprungen")
            return

        bot = Employee(
            personnel_number="BOT001",
            ad_username="support-bot",
            first_name="MVA",
            last_name="Docs",
            role=UserRole.EMPLOYEE,
            job_title="KI-Assistent",
            is_active=True,
            department_id=None,
            employment_type=EmploymentType.FULLTIME,
            weekly_hours=0.0,
            hire_date=date(2024, 1, 1),
            vacation_days_per_year=0,
        )
        db.add(bot)
        await db.commit()
        logger.info("Docs-Bot-User 'BOT001' angelegt")
