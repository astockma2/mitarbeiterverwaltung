"""Tests für die Sicherheitsprüfungen im Chat-Modul."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.chat import ConversationCreate, _create_message, create_conversation, register_device
from app.models.message import ConversationType


def make_db_with_member(is_member: bool) -> AsyncMock:
    """Erstellt eine Mock-DB-Session, die Mitgliedschaft simuliert."""
    scalar = MagicMock()
    scalar.scalar_one_or_none.return_value = MagicMock() if is_member else None

    sender_scalar = MagicMock()
    sender = MagicMock()
    sender.first_name = "Max"
    sender.last_name = "Mustermann"
    sender_scalar.scalar_one_or_none.return_value = sender

    db = AsyncMock()
    # Erster execute-Aufruf: Mitgliedschaftsprüfung; zweiter: Sender-Abfrage
    db.execute.side_effect = [scalar, sender_scalar]
    db.flush = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_create_message_verweigert_nicht_mitglied():
    """Nicht-Mitglieder dürfen keine Nachrichten in fremde Konversationen senden."""
    db = make_db_with_member(is_member=False)
    result = await _create_message(db, conversation_id=42, sender_id=99, content="Hallo")
    assert result is None
    # flush darf nicht aufgerufen worden sein (keine Nachricht gespeichert)
    db.flush.assert_not_called()


@pytest.mark.asyncio
async def test_create_message_erlaubt_mitglied():
    """Mitglieder können Nachrichten in ihre Konversationen senden."""
    db = make_db_with_member(is_member=True)

    # Message-Objekt muss beim add simuliert werden
    added_msg = None

    def fake_add(obj):
        nonlocal added_msg
        added_msg = obj
        obj.id = 1
        from datetime import datetime
        obj.created_at = datetime(2026, 1, 1)
        obj.content = "Hallo"
        obj.message_type = "TEXT"

    db.add.side_effect = fake_add

    result = await _create_message(db, conversation_id=42, sender_id=7, content="Hallo")
    assert result is not None
    assert result["type"] == "new_message"
    assert result["conversation_id"] == 42
    assert result["sender_id"] == 7


# ── register_device: FCM-Token Ownership-Check ───────────────────────────────

def _make_device_token_data(fcm_token: str = "token-xyz", device_type: str = "android"):
    data = MagicMock()
    data.fcm_token = fcm_token
    data.device_type = device_type
    return data


def _make_user(user_id: int):
    user = MagicMock()
    user.id = user_id
    return user


def _make_db_with_existing_token(owner_id: int | None):
    """Erstellt eine Mock-DB, die optional einen vorhandenen DeviceToken zurückgibt."""
    db = AsyncMock()
    if owner_id is not None:
        token = MagicMock()
        token.employee_id = owner_id
        token.device_type = "android"
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none.return_value = token
    else:
        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none.return_value = None
    db.execute.return_value = scalar_result
    return db


@pytest.mark.asyncio
async def test_register_device_fremder_token_wird_abgelehnt():
    """Ein FCM-Token eines anderen Benutzers darf nicht übernommen werden."""
    db = _make_db_with_existing_token(owner_id=99)
    current_user = _make_user(user_id=1)
    data = _make_device_token_data()

    with pytest.raises(HTTPException) as exc_info:
        await register_device(data=data, current_user=current_user, db=db)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_register_device_eigener_token_wird_aktualisiert():
    """Eigener FCM-Token kann erneut registriert (device_type aktualisiert) werden."""
    db = _make_db_with_existing_token(owner_id=1)
    current_user = _make_user(user_id=1)
    data = _make_device_token_data(device_type="ios")

    result = await register_device(data=data, current_user=current_user, db=db)

    assert result == {"status": "registered"}
    # device_type wurde aktualisiert
    token = db.execute.return_value.scalar_one_or_none.return_value
    assert token.device_type == "ios"


@pytest.mark.asyncio
async def test_register_device_neuer_token_wird_angelegt():
    """Ein noch nicht registrierter FCM-Token wird neu angelegt."""
    db = _make_db_with_existing_token(owner_id=None)
    current_user = _make_user(user_id=5)
    data = _make_device_token_data()

    result = await register_device(data=data, current_user=current_user, db=db)

    assert result == {"status": "registered"}
    db.add.assert_called_once()
