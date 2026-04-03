"""Tests für die Sicherheitsprüfungen im Chat-Modul."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.chat import _create_message, download_file


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


def make_db_with_member_for_download(is_member: bool) -> AsyncMock:
    scalar = MagicMock()
    scalar.scalar_one_or_none.return_value = MagicMock() if is_member else None
    db = AsyncMock()
    db.execute.return_value = scalar
    return db


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
    from datetime import datetime

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

    db.add.side_effect = fake_add

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
