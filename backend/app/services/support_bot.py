"""KI-Support-Bot basierend auf Claude Code CLI."""

import asyncio
import logging
import os
import shutil
from pathlib import Path

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

# Claude CLI-Pfad: über Umgebungsvariable konfigurierbar, sonst PATH-Suche
_CLAUDE_CLI_PATH = os.environ.get("CLAUDE_CLI_PATH") or shutil.which("claude") or "claude"


def _lade_handbuch() -> str:
    try:
        with open(str(HANDBUCH_PFAD), encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        log.warning("Benutzerhandbuch nicht gefunden: %s – verwende Platzhalter", HANDBUCH_PFAD)
        return HANDBUCH_FALLBACK


async def get_bot_response(user_message: str, conversation_history: list[dict]) -> str:
    """Erzeugt eine Bot-Antwort über Claude Code CLI (nutzt Claude Max Abo)."""
    try:
        # Konversations-Kontext aufbauen
        context_parts = []
        for msg in conversation_history[-10:]:
            role = "Assistent" if msg.get("is_bot") else "Benutzer"
            context_parts.append(f"{role}: {msg['content']}")

        context = "\n".join(context_parts)

        prompt = SYSTEM_PROMPT.format(handbuch_inhalt=_lade_handbuch())
        if context:
            prompt += f"\n\nBisheriger Chatverlauf:\n{context}\n"
        prompt += f"\nBenutzer: {user_message}\n\nAntworte als MVA Support-Assistent:"

        # Claude CLI aufrufen
        log.debug("Rufe Claude CLI auf: %s", _CLAUDE_CLI_PATH)
        proc = await asyncio.create_subprocess_exec(
            _CLAUDE_CLI_PATH, "--print", "-p", prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

        if proc.returncode != 0:
            err = stderr.decode().strip()
            log.error("Claude CLI Fehler (exit %d): %s", proc.returncode, err)
            return (
                "Der KI-Support ist momentan nicht verfügbar. "
                "Bitte wenden Sie sich an die IT-Abteilung."
            )

        return stdout.decode().strip()

    except FileNotFoundError:
        log.error(
            "Claude CLI nicht gefunden unter '%s'. "
            "Bitte Umgebungsvariable CLAUDE_CLI_PATH setzen oder claude im Container-PATH bereitstellen.",
            _CLAUDE_CLI_PATH,
        )
        return (
            "Der KI-Support ist momentan nicht verfügbar. "
            "Bitte wenden Sie sich an die IT-Abteilung."
        )
    except asyncio.TimeoutError:
        log.error("Claude CLI Timeout nach 30s")
        return "Die Antwort hat zu lange gedauert. Bitte versuchen Sie es erneut."
    except Exception as e:
        log.error("Fehler bei Bot-Antwort: %s", e, exc_info=True)
        return (
            "Es ist ein Fehler aufgetreten. Bitte versuchen Sie es später erneut "
            "oder wenden Sie sich an die IT-Abteilung."
        )
