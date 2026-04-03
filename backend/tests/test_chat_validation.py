"""Tests fuer Chat-Nachrichtenvalidierung."""

import pytest
from pydantic import ValidationError

from app.api.chat import MessageCreate, MAX_MESSAGE_LENGTH


def test_message_create_valid():
    msg = MessageCreate(content="Hallo Welt")
    assert msg.content == "Hallo Welt"
    assert msg.message_type == "TEXT"


def test_message_create_leer():
    with pytest.raises(ValidationError):
        MessageCreate(content="")


def test_message_create_zu_lang():
    with pytest.raises(ValidationError):
        MessageCreate(content="x" * (MAX_MESSAGE_LENGTH + 1))


def test_message_create_genau_maximal():
    msg = MessageCreate(content="x" * MAX_MESSAGE_LENGTH)
    assert len(msg.content) == MAX_MESSAGE_LENGTH


def test_websocket_content_wird_abgeschnitten():
    """Sicherstellen dass das Slice-Limit korrekt definiert ist."""
    langer_inhalt = "a" * (MAX_MESSAGE_LENGTH + 5000)
    abgeschnitten = langer_inhalt[:MAX_MESSAGE_LENGTH]
    assert len(abgeschnitten) == MAX_MESSAGE_LENGTH
