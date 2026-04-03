"""Produktions-Seed: Legt systemkritische Einträge an (idempotent)."""

import logging
from datetime import date

from sqlalchemy import select

from app.database import async_session
from app.models.employee import Employee, EmploymentType, UserRole

logger = logging.getLogger(__name__)


_BOT_DEFINITIONS = [
    ("BOT001", "support-bot", "MVA", "Support"),
    ("BOT002", "docs-bot", "MVA", "Docs"),
]


async def seed_bot_user():
    """Stellt sicher dass alle Bot-User existieren (idempotent)."""
    async with async_session() as db:
        for personnel_number, ad_username, first_name, last_name in _BOT_DEFINITIONS:
            existing = await db.execute(
                select(Employee).where(Employee.personnel_number == personnel_number)
            )
            if existing.scalar_one_or_none() is not None:
                logger.info("Bot '%s' bereits vorhanden, übersprungen", personnel_number)
                continue

            bot = Employee(
                personnel_number=personnel_number,
                ad_username=ad_username,
                first_name=first_name,
                last_name=last_name,
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
            logger.info("Bot-User '%s' angelegt", personnel_number)
        await db.commit()
