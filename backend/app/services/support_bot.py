"""KI-Support-Bot fuer die Mitarbeiterverwaltung."""

import asyncio
import json
import logging
import os
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

HANDBUCH_PFAD = (
    Path(__file__).resolve().parent.parent.parent / "docs" / "benutzerhandbuch.md"
)

SYSTEM_PROMPT = """Du bist der MVA Support-Assistent fuer die Mitarbeiterverwaltung der IKK Kliniken.
Du hilfst Mitarbeitern bei Fragen zur Nutzung der App.
Antworte immer auf Deutsch, kurz und verstaendlich.
Verwende keine technischen Begriffe.
Wenn du etwas nicht weisst, sage: "Das weiss ich leider nicht. Bitte wenden Sie sich an die IT-Abteilung."

Hier ist das Benutzerhandbuch:

{handbuch_inhalt}
"""

HANDBUCH_FALLBACK = """# MVA Benutzerhandbuch (Platzhalter)

Die Mitarbeiterverwaltung (MVA) ermoeglicht:
- Zeiterfassung: Kommen/Gehen erfassen
- Dienstplan: Eigene Schichten einsehen
- Abwesenheiten: Urlaub beantragen
- Chat: Mit Kollegen kommunizieren
- Tickets: IT-Probleme melden

Bei weiteren Fragen wenden Sie sich bitte an die IT-Abteilung.
"""

CLI_TIMEOUT_SECONDS = 60
CLAUDE_CLI_PATH = os.environ.get("CLAUDE_CLI_PATH", "claude")
SUPPORT_BOT_BACKEND = os.environ.get("SUPPORT_BOT_BACKEND", "cli").lower()

GEMI_API_URL = os.environ.get("GEMI_API_URL", "http://host.docker.internal:8085")
GEMI_API_KEY = os.environ.get("GEMI_API_KEY", "gemi2026")

UNAVAILABLE_MESSAGE = (
    "Der KI-Support ist momentan nicht verf\u00fcgbar. "
    "Bitte wenden Sie sich an die IT-Abteilung."
)
TIMEOUT_MESSAGE = "Die Antwort hat zu lange gedauert. Bitte versuchen Sie es erneut."
EMPTY_RESPONSE_MESSAGE = "Entschuldigung, ich konnte keine Antwort generieren."


def _lade_handbuch() -> str:
    try:
        with open(str(HANDBUCH_PFAD), encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        log.warning(
            "Benutzerhandbuch nicht gefunden: %s - verwende Platzhalter",
            HANDBUCH_PFAD,
        )
        return HANDBUCH_FALLBACK


def _build_cli_prompt(user_message: str, conversation_history: list[dict]) -> str:
    prompt_parts = [SYSTEM_PROMPT.format(handbuch_inhalt=_lade_handbuch()).strip()]

    if conversation_history:
        prompt_parts.append("Bisheriger Chatverlauf:")
        for msg in conversation_history[-10:]:
            author = "MVA Support" if msg.get("is_bot") else "Mitarbeiter"
            prompt_parts.append(f"{author}: {msg.get('content', '')}")

    prompt_parts.append(f"Aktuelle Frage:\n{user_message}")
    return "\n\n".join(prompt_parts)


async def _get_cli_response(user_message: str, conversation_history: list[dict]) -> str:
    prompt = _build_cli_prompt(user_message, conversation_history)

    try:
        proc = await asyncio.create_subprocess_exec(
            CLAUDE_CLI_PATH,
            "--print",
            "--dangerously-skip-permissions",
            prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        communicate = proc.communicate()
        stdout, stderr = await asyncio.wait_for(
            communicate,
            timeout=CLI_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        log.error("Claude CLI nicht gefunden: %s", CLAUDE_CLI_PATH)
        return UNAVAILABLE_MESSAGE
    except asyncio.TimeoutError:
        if "communicate" in locals() and hasattr(communicate, "close"):
            try:
                communicate.close()
            except RuntimeError:
                pass
        log.error("Claude CLI Timeout")
        return TIMEOUT_MESSAGE
    except Exception as exc:
        if "communicate" in locals() and hasattr(communicate, "close"):
            try:
                communicate.close()
            except RuntimeError:
                pass
        log.error("Fehler bei Claude CLI: %s", exc, exc_info=True)
        return UNAVAILABLE_MESSAGE

    if proc.returncode != 0:
        stderr_text = stderr.decode("utf-8", errors="replace").strip()
        log.error("Claude CLI Fehler (%s): %s", proc.returncode, stderr_text)
        return UNAVAILABLE_MESSAGE

    answer = stdout.decode("utf-8", errors="replace").strip()
    return answer if answer else EMPTY_RESPONSE_MESSAGE


def _build_http_messages(user_message: str, conversation_history: list[dict]) -> list[dict]:
    system_text = SYSTEM_PROMPT.format(handbuch_inhalt=_lade_handbuch())
    messages = [{"role": "system", "content": system_text}]

    for msg in conversation_history[-10:]:
        role = "assistant" if msg.get("is_bot") else "user"
        messages.append({"role": role, "content": msg.get("content", "")})

    messages.append({"role": "user", "content": user_message})
    return messages


async def _get_http_response(user_message: str, conversation_history: list[dict]) -> str:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=60.0)) as client:
            resp = await client.post(
                f"{GEMI_API_URL}/api/chat",
                headers={
                    "Authorization": f"Bearer {GEMI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "messages": _build_http_messages(user_message, conversation_history),
                    "stream": True,
                },
            )
    except httpx.TimeoutException:
        log.error("Claudi API Timeout")
        return TIMEOUT_MESSAGE
    except Exception as exc:
        log.error("Fehler bei Claudi API: %s", exc, exc_info=True)
        return UNAVAILABLE_MESSAGE

    if resp.status_code != 200:
        log.error("Claudi API Fehler (HTTP %d): %s", resp.status_code, resp.text[:500])
        return UNAVAILABLE_MESSAGE

    answer_parts = []
    for line in resp.text.strip().split("\n"):
        if not line.strip():
            continue
        try:
            chunk = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = chunk.get("message", {}).get("content", "")
        if content:
            answer_parts.append(content)

    answer = "".join(answer_parts).strip()
    return answer if answer else EMPTY_RESPONSE_MESSAGE


async def get_bot_response(user_message: str, conversation_history: list[dict]) -> str:
    """Erzeugt eine Bot-Antwort ueber Claude CLI oder optional den Claudi API-Proxy."""
    if SUPPORT_BOT_BACKEND in {"http", "api", "gemi", "claudi"}:
        return await _get_http_response(user_message, conversation_history)

    return await _get_cli_response(user_message, conversation_history)
