"""Push-Notifications via Firebase Cloud Messaging."""

import logging
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import DeviceToken

log = logging.getLogger(__name__)

# Firebase wird lazy initialisiert
_firebase_app = None


def init_firebase():
    """Firebase Admin SDK initialisieren (nur wenn google-services.json vorhanden)."""
    global _firebase_app
    try:
        import firebase_admin
        from firebase_admin import credentials
        import os

        cred_path = os.environ.get("FIREBASE_CREDENTIALS", "/app/firebase-credentials.json")
        if not os.path.exists(cred_path):
            log.info("Firebase-Credentials nicht gefunden (%s), Push deaktiviert", cred_path)
            return False

        cred = credentials.Certificate(cred_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        log.info("Firebase initialisiert")
        return True
    except ImportError:
        log.info("firebase-admin nicht installiert, Push deaktiviert")
        return False
    except Exception as e:
        log.warning("Firebase-Initialisierung fehlgeschlagen: %s", e)
        return False


async def send_push_notification(
    db: AsyncSession,
    recipient_ids: list[int],
    sender_name: str,
    message_content: str,
    conversation_id: int,
    message_type: str = "TEXT",
    exclude_online: Optional[list[int]] = None,
):
    """Push-Notification an alle registrierten Geraete der Empfaenger senden."""
    if _firebase_app is None:
        return

    try:
        from firebase_admin import messaging
    except ImportError:
        return

    # Online-User ausschliessen (die bekommen die Nachricht per WebSocket)
    target_ids = [uid for uid in recipient_ids if not exclude_online or uid not in exclude_online]
    if not target_ids:
        return

    # Device-Tokens laden
    result = await db.execute(
        select(DeviceToken).where(DeviceToken.employee_id.in_(target_ids))
    )
    tokens = result.scalars().all()
    if not tokens:
        return

    # Notification-Body
    if message_type == "IMAGE":
        body = f"{sender_name}: Bild"
    elif message_type == "FILE":
        body = f"{sender_name}: Datei"
    else:
        body = f"{sender_name}: {message_content[:100]}"

    # An alle Tokens senden
    invalid_tokens = []
    for token in tokens:
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title="MVA Chat",
                    body=body,
                ),
                data={
                    "conversation_id": str(conversation_id),
                    "sender_name": sender_name,
                    "type": "chat_message",
                },
                token=token.fcm_token,
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        channel_id="chat_messages",
                        click_action="FLUTTER_NOTIFICATION_CLICK",
                    ),
                ),
            )
            messaging.send(message)
        except messaging.UnregisteredError:
            invalid_tokens.append(token.id)
        except Exception as e:
            log.warning("Push-Fehler fuer Token %s: %s", token.fcm_token[:20], e)

    # Ungueltige Tokens entfernen
    if invalid_tokens:
        await db.execute(
            delete(DeviceToken).where(DeviceToken.id.in_(invalid_tokens))
        )
        await db.flush()
        log.info("%d ungueltige FCM-Tokens entfernt", len(invalid_tokens))
