"""KI-Support-Bot basierend auf Claudi API-Proxy (Claude Opus 4.6)."""

import json
import logging
import os
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

HANDBUCH_PFAD = Path(__file__).resolve().parent.parent.parent / "docs" / "benutzerhandbuch.md"

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

GEMI_API_URL = os.environ.get("GEMI_API_URL", "http://host.docker.internal:8085")
GEMI_API_KEY = os.environ.get("GEMI_API_KEY", "gemi2026")


def _lade_handbuch() -> str:
    try:
        with open(str(HANDBUCH_PFAD), encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        log.warning("Benutzerhandbuch nicht gefunden: %s – verwende Platzhalter", HANDBUCH_PFAD)
        return HANDBUCH_FALLBACK


async def get_bot_response(user_message: str, conversation_history: list[dict]) -> str:
    """Erzeugt eine Bot-Antwort ueber den Claudi API-Proxy (Claude Opus 4.6)."""
    try:
        system_text = SYSTEM_PROMPT.format(handbuch_inhalt=_lade_handbuch())

        # Messages aufbauen: System + History + aktuelle Frage
        messages = [{"role": "system", "content": system_text}]

        for msg in conversation_history[-10:]:
            role = "assistant" if msg.get("is_bot") else "user"
            messages.append({"role": role, "content": msg["content"]})

        messages.append({"role": "user", "content": user_message})

        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=60.0)) as client:
            resp = await client.post(
                f"{GEMI_API_URL}/api/chat",
                headers={
                    "Authorization": f"Bearer {GEMI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"messages": messages, "stream": True},
            )

        if resp.status_code != 200:
            log.error("Claudi API Fehler (HTTP %d): %s", resp.status_code, resp.text[:500])
            return (
                "Der KI-Support ist momentan nicht verfügbar. "
                "Bitte wenden Sie sich an die IT-Abteilung."
            )

        # Streaming NDJSON Response zusammenbauen
        answer_parts = []
        for line in resp.text.strip().split("\n"):
            if not line.strip():
                continue
            try:
                chunk = json.loads(line)
                content = chunk.get("message", {}).get("content", "")
                if content:
                    answer_parts.append(content)
            except json.JSONDecodeError:
                continue

        answer = "".join(answer_parts).strip()
        return answer if answer else "Entschuldigung, ich konnte keine Antwort generieren."

    except httpx.TimeoutException:
        log.error("Claudi API Timeout")
        return "Die Antwort hat zu lange gedauert. Bitte versuchen Sie es erneut."
    except Exception as e:
        log.error("Fehler bei Bot-Antwort: %s", e, exc_info=True)
        return (
            "Es ist ein Fehler aufgetreten. Bitte versuchen Sie es später erneut "
            "oder wenden Sie sich an die IT-Abteilung."
        )
