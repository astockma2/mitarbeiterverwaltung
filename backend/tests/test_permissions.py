"""Tests für die Berechtigungsprüfung can_view_employee."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth.permissions import can_view_employee
from app.models.employee import Employee, UserRole


def make_employee(id: int, role: UserRole, department_id: int | None = None) -> Employee:
    emp = MagicMock(spec=Employee)
    emp.id = id
    emp.role = role
    emp.department_id = department_id
    return emp


def make_db(target_employee: Employee | None) -> AsyncMock:
    """Erstellt eine Mock-DB-Session, die den Ziel-Mitarbeiter zurückgibt."""
    scalar = MagicMock()
    scalar.scalar_one_or_none.return_value = target_employee
    db = AsyncMock()
    db.execute.return_value = scalar
    return db


@pytest.mark.asyncio
async def test_admin_sieht_alle():
    admin = make_employee(1, UserRole.ADMIN, department_id=1)
    db = make_db(make_employee(99, UserRole.EMPLOYEE, department_id=2))
    assert await can_view_employee(db, admin, 99) is True


@pytest.mark.asyncio
async def test_hr_sieht_alle():
    hr = make_employee(2, UserRole.HR, department_id=1)
    db = make_db(make_employee(99, UserRole.EMPLOYEE, department_id=2))
    assert await can_view_employee(db, hr, 99) is True


@pytest.mark.asyncio
async def test_mitarbeiter_sieht_eigene_daten():
    emp = make_employee(5, UserRole.EMPLOYEE, department_id=3)
    db = make_db(None)  # DB wird nicht aufgerufen
    assert await can_view_employee(db, emp, 5) is True


@pytest.mark.asyncio
async def test_mitarbeiter_sieht_nicht_andere():
    emp = make_employee(5, UserRole.EMPLOYEE, department_id=3)
    db = make_db(make_employee(99, UserRole.EMPLOYEE, department_id=3))
    assert await can_view_employee(db, emp, 99) is False


@pytest.mark.asyncio
async def test_team_leader_sieht_eigene_abteilung():
    leader = make_employee(10, UserRole.TEAM_LEADER, department_id=7)
    target = make_employee(20, UserRole.EMPLOYEE, department_id=7)
    db = make_db(target)
    assert await can_view_employee(db, leader, 20) is True


@pytest.mark.asyncio
async def test_team_leader_sieht_nicht_andere_abteilung():
    leader = make_employee(10, UserRole.TEAM_LEADER, department_id=7)
    target = make_employee(20, UserRole.EMPLOYEE, department_id=99)
    db = make_db(target)
    assert await can_view_employee(db, leader, 20) is False


@pytest.mark.asyncio
async def test_dept_manager_sieht_eigene_abteilung():
    manager = make_employee(11, UserRole.DEPARTMENT_MANAGER, department_id=4)
    target = make_employee(30, UserRole.EMPLOYEE, department_id=4)
    db = make_db(target)
    assert await can_view_employee(db, manager, 30) is True


@pytest.mark.asyncio
async def test_dept_manager_sieht_nicht_andere_abteilung():
    manager = make_employee(11, UserRole.DEPARTMENT_MANAGER, department_id=4)
    target = make_employee(30, UserRole.EMPLOYEE, department_id=5)
    db = make_db(target)
    assert await can_view_employee(db, manager, 30) is False


@pytest.mark.asyncio
async def test_team_leader_ziel_nicht_vorhanden():
    leader = make_employee(10, UserRole.TEAM_LEADER, department_id=7)
    db = make_db(None)
    assert await can_view_employee(db, leader, 999) is False
