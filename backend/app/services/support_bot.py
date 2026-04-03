"""KI-Support-Bot basierend auf Claude (Anthropic API)."""

import logging
from pathlib import Path

import anthropic

from app.config import get_settings

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


def _lade_handbuch() -> str:
    try:
        with open(str(HANDBUCH_PFAD), encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        log.warning("Benutzerhandbuch nicht gefunden: %s – verwende Platzhalter", HANDBUCH_PFAD)
        return HANDBUCH_FALLBACK


async def get_bot_response(user_message: str, conversation_history: list[dict]) -> str:
    """Erzeugt eine Bot-Antwort ueber Claude (Anthropic API)."""
    try:
        settings = get_settings()
        if not settings.anthropic_api_key:
            return (
                "Der KI-Support ist momentan nicht verfuegbar. "
                "Bitte wenden Sie sich an die IT-Abteilung."
            )

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        # Conversation History als Claude Messages aufbauen
        messages = []
        for msg in conversation_history[-10:]:
            role = "assistant" if msg.get("is_bot") else "user"
            messages.append({"role": role, "content": msg["content"]})

        # Aktuelle Frage
        messages.append({"role": "user", "content": user_message})

        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT.format(handbuch_inhalt=_lade_handbuch()),
            messages=messages,
        )

        return response.content[0].text

    except anthropic.AuthenticationError as e:
        log.error("Anthropic Auth-Fehler (API Key ungültig?): %s", e)
        return (
            "Der KI-Support ist momentan nicht verfügbar. "
            "Bitte wenden Sie sich an die IT-Abteilung."
        )
    except anthropic.RateLimitError as e:
        log.warning("Anthropic Rate-Limit erreicht: %s", e)
        return (
            "Der KI-Support ist momentan überlastet. "
            "Bitte versuchen Sie es in einigen Minuten erneut."
        )
    except anthropic.APIError as e:
        log.error("Anthropic API-Fehler (status=%s): %s", e.status_code, e)
        return (
            "Es ist ein Fehler aufgetreten. Bitte versuchen Sie es später erneut "
            "oder wenden Sie sich an die IT-Abteilung."
        )
    except Exception as e:
        log.error("Unbekannter Fehler bei Bot-Antwort: %s", e, exc_info=True)
        return (
            "Es ist ein Fehler aufgetreten. Bitte versuchen Sie es später erneut "
            "oder wenden Sie sich an die IT-Abteilung."
        )
