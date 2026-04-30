"""Tests für die Sicherheitsprüfungen im Chat-Modul."""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.chat import ConversationCreate, _create_message, create_conversation, download_file, register_device
from app.models.message import ConversationType


def _make_execute_result(scalar_value):
    """Erstellt ein Mock-Ergebnis für db.execute mit scalar_one_or_none."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = scalar_value
    return r


def _make_all_result(rows):
    """Erstellt ein Mock-Ergebnis für db.execute mit .all()."""
    r = MagicMock()
    r.all.return_value = rows
    return r


def _make_db(is_member: bool) -> AsyncMock:
    """Mock-DB-Session für _create_message.

    Aufruf-Reihenfolge von db.execute:
      1. Mitgliedschaftsprüfung  → scalar_one_or_none
      2. Sender-Abfrage          → scalar_one_or_none
      3. _get_member_ids         → .all()
    """
    member_obj = MagicMock() if is_member else None

    sender = MagicMock()
    sender.first_name = "Max"
    sender.last_name = "Mustermann"

    db = AsyncMock()
    db.execute.side_effect = [
        _make_execute_result(member_obj),      # Mitgliedschaftsprüfung
        _make_execute_result(sender),          # Sender-Abfrage
        _make_all_result([]),                  # _get_member_ids
    ]
    # db.add ist synchron (kein await im Produktionscode)
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_create_message_verweigert_nicht_mitglied():
    """Nicht-Mitglieder dürfen keine Nachrichten in fremde Konversationen senden."""
    db = _make_db(is_member=False)
    result = await _create_message(db, conversation_id=42, sender_id=99, content="Hallo")
    assert result is None
    # Keine Nachricht darf gespeichert worden sein
    db.add.assert_not_called()
    db.flush.assert_not_called()


@pytest.mark.asyncio
async def test_create_message_erlaubt_mitglied():
    """Mitglieder können Nachrichten in ihre Konversationen senden."""
    db = _make_db(is_member=True)

    # created_at und id werden normalerweise von der DB nach flush gesetzt
    def _set_msg_fields(obj):
        obj.id = 1
        obj.created_at = datetime(2026, 1, 1, 12, 0, 0)
        obj.content = "Hallo"
        obj.message_type = "TEXT"

    db.add.side_effect = _set_msg_fields

    with (
        patch("app.api.chat.manager") as mock_manager,
        patch("app.api.chat.send_push_notification", new_callable=AsyncMock),
    ):
        mock_manager.get_online_users.return_value = set()
        result = await _create_message(db, conversation_id=42, sender_id=7, content="Hallo")

    assert result is not None
    assert result["type"] == "new_message"
    assert result["conversation_id"] == 42
    assert result["sender_id"] == 7
    assert result["sender_name"] == "Max Mustermann"
    db.flush.assert_called_once()


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
    db.add = MagicMock()
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


def make_db_with_member_for_download(is_member: bool) -> AsyncMock:
    scalar = MagicMock()
    scalar.scalar_one_or_none.return_value = MagicMock() if is_member else None
    db = AsyncMock()
    db.execute.return_value = scalar
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


# ── Path Traversal & Push Notification Tests ─────────────────────────────────

@pytest.mark.asyncio
async def test_download_file_path_traversal_blockiert():
    """Path-Traversal-Angriffe müssen mit HTTP 400 abgewiesen werden."""
    fake_user = MagicMock()
    fake_user.id = 1
    db = make_db_with_member_for_download(is_member=True)

    fake_settings = MagicMock()
    fake_settings.upload_dir = "/opt/mva/uploads"

    with patch("app.api.chat.get_settings", return_value=fake_settings):
        with pytest.raises(HTTPException) as exc_info:
            await download_file(
                file_path="chat/1/../../../etc/passwd",
                current_user=fake_user,
                db=db,
            )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_download_file_gueltig_akzeptiert(tmp_path):
    """Gültige Pfade innerhalb des Upload-Verzeichnisses werden akzeptiert."""
    fake_user = MagicMock()
    fake_user.id = 1
    db = make_db_with_member_for_download(is_member=True)

    upload_dir = tmp_path / "uploads"
    chat_dir = upload_dir / "chat" / "1"
    chat_dir.mkdir(parents=True)
    test_file = chat_dir / "test.txt"
    test_file.write_text("Testinhalt")

    fake_settings = MagicMock()
    fake_settings.upload_dir = str(upload_dir)

    with patch("app.api.chat.get_settings", return_value=fake_settings):
        response = await download_file(
            file_path="chat/1/test.txt",
            current_user=fake_user,
            db=db,
        )
    assert response.path == str(test_file)


@pytest.mark.asyncio
async def test_send_message_ruft_push_notification_auf():
    """REST-Endpoint send_message muss send_push_notification für Offline-User aufrufen."""
    from fastapi import BackgroundTasks
    from app.api.chat import send_message
    from app.models.message import MessageCreate

    current_user = MagicMock()
    current_user.id = 1
    current_user.first_name = "Max"
    current_user.last_name = "Mustermann"

    member_check = MagicMock()
    member_check.scalar_one_or_none.return_value = MagicMock()

    member_rows = MagicMock()
    member_rows.scalars.return_value.all.return_value = [1, 2]

    db = AsyncMock()
    db.execute.side_effect = [member_check, member_rows]
    db.flush = AsyncMock()

    def fake_add(obj):
        obj.id = 10
        obj.created_at = datetime(2026, 1, 1)
        obj.content = "Hallo Welt"
        obj.message_type = "TEXT"
        obj.file_path = None

    db.add = MagicMock(side_effect=fake_add)

    data = MessageCreate(content="Hallo Welt", message_type="TEXT")
    background_tasks = BackgroundTasks()

    with (
        patch("app.api.chat.manager") as mock_manager,
        patch("app.api.chat.send_push_notification", new_callable=AsyncMock) as mock_push,
        patch("app.api.chat._find_bot_in_direct_conv", new_callable=AsyncMock, return_value=None),
    ):
        mock_manager.send_to_conversation = AsyncMock()
        mock_manager.get_online_users.return_value = set()

        result = await send_message(
            conversation_id=5,
            data=data,
            background_tasks=background_tasks,
            current_user=current_user,
            db=db,
        )

    assert result["content"] == "Hallo Welt"
    mock_push.assert_awaited_once()
    call_kwargs = mock_push.call_args.kwargs
    # Sender darf keine eigene Push-Notification erhalten
    assert current_user.id not in call_kwargs["recipient_ids"]
    assert call_kwargs["conversation_id"] == 5
