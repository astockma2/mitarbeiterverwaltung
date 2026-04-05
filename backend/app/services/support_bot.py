"""KI-Support-Bot basierend auf Gemini API."""

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

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def _lade_handbuch() -> str:
    try:
        with open(str(HANDBUCH_PFAD), encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        log.warning("Benutzerhandbuch nicht gefunden: %s – verwende Platzhalter", HANDBUCH_PFAD)
        return HANDBUCH_FALLBACK


async def get_bot_response(user_message: str, conversation_history: list[dict]) -> str:
    """Erzeugt eine Bot-Antwort ueber die Gemini API."""
    if not GEMINI_API_KEY:
        log.error("GEMINI_API_KEY nicht gesetzt")
        return (
            "Der KI-Support ist momentan nicht verfügbar. "
            "Bitte wenden Sie sich an die IT-Abteilung."
        )

    try:
        # Konversations-Kontext aufbauen
        contents = []

        # System-Instruktion als erster User-Turn
        system_text = SYSTEM_PROMPT.format(handbuch_inhalt=_lade_handbuch())

        # Bisherigen Chatverlauf einfuegen
        for msg in conversation_history[-10:]:
            role = "model" if msg.get("is_bot") else "user"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        # Aktuelle Nachricht
        contents.append({"role": "user", "parts": [{"text": user_message}]})

        payload = {
            "system_instruction": {"parts": [{"text": system_text}]},
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": 1024,
                "temperature": 0.7,
            },
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                GEMINI_URL,
                params={"key": GEMINI_API_KEY},
                json=payload,
            )

        if resp.status_code != 200:
            log.error("Gemini API Fehler (HTTP %d): %s", resp.status_code, resp.text[:500])
            return (
                "Der KI-Support ist momentan nicht verfügbar. "
                "Bitte wenden Sie sich an die IT-Abteilung."
            )

        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    except httpx.TimeoutException:
        log.error("Gemini API Timeout nach 30s")
        return "Die Antwort hat zu lange gedauert. Bitte versuchen Sie es erneut."
    except Exception as e:
        log.error("Fehler bei Bot-Antwort: %s", e, exc_info=True)
        return (
            "Es ist ein Fehler aufgetreten. Bitte versuchen Sie es später erneut "
            "oder wenden Sie sich an die IT-Abteilung."
        )
