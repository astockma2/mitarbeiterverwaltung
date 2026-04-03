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
