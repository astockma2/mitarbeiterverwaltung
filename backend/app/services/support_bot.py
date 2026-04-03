"""KI-Docs-Bot basierend auf Gemini 2.0 Flash."""

import asyncio
import logging

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """Du bist der MVA Docs-Assistent für die Mitarbeiterverwaltung der IKK Kliniken.
Du hilfst Mitarbeitern beim Erstellen und Formulieren von:
- E-Mails und Anschreiben
- Protokollen und Berichten
- Dokumentationen und Anleitungen
- Formularen und Vorlagen

Antworte immer auf Deutsch, professionell und klar.
Frage nach wenn dir Informationen fehlen um ein gutes Dokument zu erstellen.
"""


async def get_bot_response(user_message: str, conversation_history: list[dict]) -> str:
    """Erzeugt eine Bot-Antwort über Gemini 2.0 Flash."""
    try:
        import google.generativeai as genai
        from app.config import get_settings

        settings = get_settings()
        if not settings.gemini_api_key:
            return (
                "Der KI-Assistent ist momentan nicht verfügbar. "
                "Bitte wenden Sie sich an die IT-Abteilung."
            )

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(
            "gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT,
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
