"""Tests für die Sicherheitsprüfungen im Chat-Modul (Issue #10: IDOR im WebSocket)."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.chat import _create_message


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
