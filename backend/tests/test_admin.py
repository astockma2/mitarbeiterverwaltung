"""Tests für die Admin-API Endpoints (Berechtigungsprüfung)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.admin import dashboard, trigger_ad_sync
from app.models.employee import Employee, UserRole


def make_user(role: UserRole) -> Employee:
    user = MagicMock(spec=Employee)
    user.role = role
    return user


def make_db() -> AsyncMock:
    scalar = MagicMock()
    scalar.scalar.return_value = 0
    db = AsyncMock()
    db.execute.return_value = scalar
    return db


@pytest.mark.asyncio
async def test_dashboard_mitarbeiter_erhaelt_403():
    """Ein normaler Mitarbeiter darf das Dashboard nicht sehen."""
    user = make_user(UserRole.EMPLOYEE)
    db = make_db()
    with pytest.raises(HTTPException) as exc_info:
        await dashboard(db=db, current_user=user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_dashboard_team_leader_erhaelt_403():
    """Ein Team-Leader darf das Dashboard nicht sehen."""
    user = make_user(UserRole.TEAM_LEADER)
    db = make_db()
    with pytest.raises(HTTPException) as exc_info:
        await dashboard(db=db, current_user=user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_dashboard_hr_hat_zugriff():
    """HR darf das Dashboard sehen."""
    user = make_user(UserRole.HR)
    db = make_db()
    result = await dashboard(db=db, current_user=user)
    assert "employees_total" in result


@pytest.mark.asyncio
async def test_dashboard_admin_hat_zugriff():
    """Admin darf das Dashboard sehen."""
    user = make_user(UserRole.ADMIN)
    db = make_db()
    result = await dashboard(db=db, current_user=user)
    assert "employees_total" in result


@pytest.mark.asyncio
async def test_ad_sync_mitarbeiter_erhaelt_403():
    """Ein normaler Mitarbeiter darf die AD-Synchronisation nicht auslösen."""
    user = make_user(UserRole.EMPLOYEE)
    db = make_db()
    with pytest.raises(HTTPException) as exc_info:
        await trigger_ad_sync(db=db, current_user=user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_ad_sync_hr_erhaelt_403():
    """HR darf die AD-Synchronisation nicht auslösen (nur Admin)."""
    user = make_user(UserRole.HR)
    db = make_db()
    with pytest.raises(HTTPException) as exc_info:
        await trigger_ad_sync(db=db, current_user=user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_ad_sync_admin_hat_zugriff():
    """Admin darf die AD-Synchronisation auslösen."""
    user = make_user(UserRole.ADMIN)
    db = make_db()
    mock_result = {"synced": 5, "errors": 0, "updated_fields": 2}
    with patch("app.api.admin.sync_all_employees", AsyncMock(return_value=mock_result)):
        result = await trigger_ad_sync(db=db, current_user=user)
    assert result["synced"] == 5
    assert "message" in result
