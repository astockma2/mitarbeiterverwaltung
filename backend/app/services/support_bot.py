"""KI-Support-Bot basierend auf Gemini 2.0 Flash."""

import asyncio
import logging

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """Du bist der MVA Support-Assistent für die Mitarbeiterverwaltung der IKK Kliniken.
Du hilfst Mitarbeitern bei Fragen zur Nutzung der App.
Antworte immer auf Deutsch, kurz und verständlich.
Verwende keine technischen Begriffe.
Wenn du etwas nicht weißt, sage: "Das weiß ich leider nicht. Bitte wenden Sie sich an die IT-Abteilung."

Hier ist das Benutzerhandbuch:

{handbuch_inhalt}
"""

from pathlib import Path

HANDBUCH_PFAD = Path(__file__).resolve().parent.parent.parent / "docs" / "benutzerhandbuch.md"

HANDBUCH_FALLBACK = """# MVA Benutzerhandbuch (Platzhalter)

Die Mitarbeiterverwaltung (MVA) ermöglicht:
- Zeiterfassung: Kommen/Gehen erfassen
- Dienstplan: Eigene Schichten einsehen
- Abwesenheiten: Urlaub beantragen
- Chat: Mit Kollegen kommunizieren
- Tickets: IT-Probleme melden

Bei weiteren Fragen wenden Sie sich bitte an die IT-Abteilung.
"""


def _lade_handbuch() -> str:
    try:
        with open(str(HANDBUCH_PFAD), encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        log.warning("Benutzerhandbuch nicht gefunden: %s – verwende Platzhalter", HANDBUCH_PFAD)
        return HANDBUCH_FALLBACK


async def get_bot_response(user_message: str, conversation_history: list[dict]) -> str:
    """Erzeugt eine Bot-Antwort über Gemini 2.0 Flash."""
    try:
        import google.generativeai as genai
        from app.config import get_settings

        settings = get_settings()
        if not settings.gemini_api_key:
            return (
                "Der KI-Support ist momentan nicht verfügbar. "
                "Bitte wenden Sie sich an die IT-Abteilung."
            )

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(
            "gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT.format(handbuch_inhalt=_lade_handbuch()),
        )

        # Letzte 10 Nachrichten als Kontext (ohne aktuelle User-Nachricht)
        history = []
        for msg in conversation_history[-10:]:
            role = "model" if msg.get("is_bot") else "user"
            history.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=history)

        # Synchronen API-Aufruf in Thread-Pool ausführen (nicht blockierend)
        response = await asyncio.to_thread(chat.send_message, user_message)
        return response.text

    except Exception as e:
        log.error("Fehler bei Bot-Antwort: %s", e)
        return (
            "Es ist ein Fehler aufgetreten. Bitte versuchen Sie es später erneut "
            "oder wenden Sie sich an die IT-Abteilung."
        )
