"""Tests für den Support-Bot-Service."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def reset_claude_path(monkeypatch):
    """Setzt CLAUDE_CLI_PATH vor jedem Test zurück."""
    monkeypatch.setenv("CLAUDE_CLI_PATH", "claude")


def _make_proc(returncode: int, stdout: bytes, stderr: bytes = b""):
    """Erstellt einen Mock-Prozess für asyncio.create_subprocess_exec."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


@pytest.mark.asyncio
async def test_erfolgreiche_antwort():
    """Bot gibt Claude-Antwort zurück wenn CLI erfolgreich ist."""
    from app.services.support_bot import get_bot_response

    proc = _make_proc(0, "Die Zeiterfassung funktioniert über Kommen/Gehen.".encode())

    with patch("asyncio.create_subprocess_exec", return_value=proc) as mock_exec:
        antwort = await get_bot_response("Wie funktioniert die Zeiterfassung?", [])

    assert "Zeiterfassung" in antwort
    mock_exec.assert_called_once()


@pytest.mark.asyncio
async def test_cli_nicht_gefunden():
    """Bot gibt hilfreiche Fehlermeldung zurück wenn Claude CLI nicht gefunden wird."""
    from app.services.support_bot import get_bot_response

    with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError("claude not found")):
        antwort = await get_bot_response("Test-Frage", [])

    assert "nicht verfügbar" in antwort
    assert "IT-Abteilung" in antwort


@pytest.mark.asyncio
async def test_cli_fehlercode():
    """Bot gibt Fehlermeldung zurück wenn CLI mit Fehlercode endet."""
    from app.services.support_bot import get_bot_response

    proc = _make_proc(1, b"", b"Error: authentication failed")

    with patch("asyncio.create_subprocess_exec", return_value=proc):
        antwort = await get_bot_response("Test-Frage", [])

    assert "nicht verfügbar" in antwort


@pytest.mark.asyncio
async def test_timeout():
    """Bot gibt Timeout-Meldung zurück wenn CLI zu lange braucht."""
    from app.services.support_bot import get_bot_response

    proc = MagicMock()
    proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

    with patch("asyncio.create_subprocess_exec", return_value=proc):
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
            antwort = await get_bot_response("Test-Frage", [])

    assert "zu lange" in antwort


@pytest.mark.asyncio
async def test_konversationskontext_wird_uebermittelt():
    """Konversationshistorie wird in den Prompt eingebaut."""
    from app.services.support_bot import get_bot_response

    proc = _make_proc(0, b"Antwort mit Kontext.")
    history = [
        {"content": "Hallo", "is_bot": False},
        {"content": "Hallo! Wie kann ich helfen?", "is_bot": True},
    ]

    with patch("asyncio.create_subprocess_exec", return_value=proc) as mock_exec:
        await get_bot_response("Weitere Frage", history)

    # Prompt muss Konversationshistorie enthalten
    _cli, _flag1, _flag2, prompt_arg = mock_exec.call_args[0]
    assert "Bisheriger Chatverlauf" in prompt_arg
    assert "Hallo" in prompt_arg


@pytest.mark.asyncio
async def test_handbuch_fallback_wenn_datei_fehlt():
    """Fallback-Handbuch wird verwendet wenn Datei nicht existiert."""
    from app.services import support_bot

    with patch.object(support_bot, "HANDBUCH_PFAD", support_bot.HANDBUCH_PFAD / "existiert_nicht"):
        proc = _make_proc(0, b"Antwort.")
        with patch("asyncio.create_subprocess_exec", return_value=proc) as mock_exec:
            await support_bot.get_bot_response("Test", [])

    _cli, _flag1, _flag2, prompt_arg = mock_exec.call_args[0]
    assert "Zeiterfassung" in prompt_arg  # Aus HANDBUCH_FALLBACK


@pytest.mark.asyncio
async def test_cli_pfad_aus_umgebungsvariable(monkeypatch):
    """CLAUDE_CLI_PATH Umgebungsvariable wird als CLI-Pfad verwendet."""
    monkeypatch.setenv("CLAUDE_CLI_PATH", "/opt/claude/bin/claude")

    # Modul neu laden damit die Variable greift
    import importlib
    from app.services import support_bot
    importlib.reload(support_bot)

    proc = _make_proc(0, b"Antwort.")
    with patch("asyncio.create_subprocess_exec", return_value=proc) as mock_exec:
        await support_bot.get_bot_response("Test", [])

    cli_path = mock_exec.call_args[0][0]
    assert cli_path == "/opt/claude/bin/claude"
