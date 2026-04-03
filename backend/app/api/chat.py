"""Chat-API: Konversationen, Nachrichten, WebSocket-Echtzeit."""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.jwt import get_current_user
from app.database import async_session, get_db
from app.models.employee import Employee
from app.models.message import Conversation, ConversationMember, Message

router = APIRouter(prefix="/chat", tags=["Chat"])
log = logging.getLogger(__name__)

# Referenz auf laufende Bot-Tasks (verhindert Garbage Collection)
_bot_tasks: set[asyncio.Task] = set()


# ── WebSocket Connection Manager ──────────────────────────────────

class ConnectionManager:
    """Verwaltet aktive WebSocket-Verbindungen pro Benutzer."""

    def __init__(self):
        # employee_id -> list of WebSocket connections
        self.connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, employee_id: int):
        if employee_id not in self.connections:
            self.connections[employee_id] = []
        self.connections[employee_id].append(websocket)
        log.info("WebSocket verbunden: Mitarbeiter %d", employee_id)

    def disconnect(self, websocket: WebSocket, employee_id: int):
        if employee_id in self.connections:
            self.connections[employee_id] = [
                ws for ws in self.connections[employee_id] if ws != websocket
            ]
            if not self.connections[employee_id]:
                del self.connections[employee_id]
        log.info("WebSocket getrennt: Mitarbeiter %d", employee_id)

    async def send_to_user(self, employee_id: int, data: dict):
        if employee_id in self.connections:
            dead = []
            for ws in self.connections[employee_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.connections[employee_id].remove(ws)

    async def send_to_conversation(self, member_ids: list[int], data: dict):
        for uid in member_ids:
            await self.send_to_user(uid, data)

    def get_online_users(self) -> list[int]:
        return list(self.connections.keys())


manager = ConnectionManager()


# ── Pydantic-Schemas ──────────────────────────────────────────────

class ConversationCreate(BaseModel):
    type: str = "DIRECT"
    name: Optional[str] = None
    member_ids: list[int]

class MessageCreate(BaseModel):
    content: str
    message_type: str = "TEXT"


# ── WebSocket-Endpoint ───────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket-Verbindung für Echtzeit-Chat.

    Authentifizierung erfolgt über die erste JSON-Nachricht nach dem Handshake:
    {"action": "auth", "token": "<JWT>"}

    Das Token wird damit nicht in der URL übertragen und erscheint nicht in
    Server-Logs, Browser-History oder Proxy-Logs.
    """
    from app.auth.jwt import decode_token

    await websocket.accept()

    try:
        auth_msg = await websocket.receive_json()
        if auth_msg.get("action") != "auth":
            await websocket.close(code=4001, reason="Authentifizierung erwartet")
            return
        token = auth_msg.get("token", "")
        payload = decode_token(token)
        employee_id = int(payload["sub"])
    except Exception:
        await websocket.close(code=4001, reason="Ungültig")
        return

    await manager.connect(websocket, employee_id)

    # Online-Status an alle senden
    await _broadcast_online_status()

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "message":
                conv_id = data.get("conversation_id")
                content = data.get("content", "").strip()
                if conv_id and content:
                    async for db in get_db():
                        msg = await _create_message(
                            db, conv_id, employee_id, content
                        )
                        if msg:
                            members = await _get_member_ids(db, conv_id)
                            await manager.send_to_conversation(members, msg)
                            bot_id = await _find_bot_in_direct_conv(db, conv_id)
                            if bot_id:
                                task = asyncio.create_task(
                                    _handle_bot_response(conv_id, content, bot_id, members)
                                )
                                _bot_tasks.add(task)
                                task.add_done_callback(_bot_tasks.discard)

            elif action == "typing":
                conv_id = data.get("conversation_id")
                if conv_id:
                    async for db in get_db():
                        members = await _get_member_ids(db, conv_id)
                        await manager.send_to_conversation(
                            [m for m in members if m != employee_id],
                            {
                                "type": "typing",
                                "conversation_id": conv_id,
                                "employee_id": employee_id,
                            },
                        )

            elif action == "read":
                conv_id = data.get("conversation_id")
                if conv_id:
                    async for db in get_db():
                        await _mark_read(db, conv_id, employee_id)

    except WebSocketDisconnect:
        manager.disconnect(websocket, employee_id)
        await _broadcast_online_status()
    except Exception as e:
        log.error("WebSocket Fehler: %s", e)
        manager.disconnect(websocket, employee_id)
        await _broadcast_online_status()


async def _broadcast_online_status():
    online = manager.get_online_users()
    data = {"type": "online_status", "online_users": online}
    for uid in online:
        await manager.send_to_user(uid, data)


# ── Bot-Hilfsfunktionen ──────────────────────────────────────────

BOT_PERSONNEL_NUMBER = "BOT001"


async def _get_bot_employee_id(db: AsyncSession) -> int | None:
    """Gibt die Datenbank-ID des Support-Bots zurück."""
    result = await db.execute(
        select(Employee.id).where(
            Employee.personnel_number == BOT_PERSONNEL_NUMBER,
            Employee.is_active == True,
        )
    )
    return result.scalar_one_or_none()


async def _find_bot_in_direct_conv(db: AsyncSession, conversation_id: int) -> int | None:
    """Gibt die Bot-ID zurück wenn die Konversation eine DIRECT-Unterhaltung mit dem Bot ist."""
    conv_q = await db.execute(
        select(Conversation.type).where(Conversation.id == conversation_id)
    )
    conv_type = conv_q.scalar_one_or_none()
    if conv_type != "DIRECT":
        return None

    bot_q = await db.execute(
        select(Employee.id)
        .join(ConversationMember, Employee.id == ConversationMember.employee_id)
        .where(
            ConversationMember.conversation_id == conversation_id,
            Employee.personnel_number == BOT_PERSONNEL_NUMBER,
        )
    )
    return bot_q.scalar_one_or_none()


async def _handle_bot_response(
    conv_id: int, user_message: str, bot_id: int, member_ids: list[int]
):
    """Generiert die Bot-Antwort und speichert/sendet sie asynchron."""
    from app.services.support_bot import get_bot_response

    try:
        async with async_session() as db:
            # Letzte 10 Nachrichten als Kontext laden
            history_q = await db.execute(
                select(Message)
                .where(Message.conversation_id == conv_id, Message.is_deleted == False)
                .order_by(Message.created_at.desc())
                .limit(10)
            )
            history_msgs = list(reversed(history_q.scalars().all()))
            history = [
                {"content": m.content, "is_bot": m.sender_id == bot_id}
                for m in history_msgs[:-1]
            ]

            response_text = await get_bot_response(user_message, history)

            bot_msg = Message(
                conversation_id=conv_id,
                sender_id=bot_id,
                content=response_text,
                message_type="TEXT",
            )
            db.add(bot_msg)
            await db.commit()
            await db.refresh(bot_msg)

            await manager.send_to_conversation(
                member_ids,
                {
                    "type": "new_message",
                    "id": bot_msg.id,
                    "conversation_id": conv_id,
                    "sender_id": bot_id,
                    "sender_name": "MVA Support",
                    "content": response_text,
                    "message_type": "TEXT",
                    "created_at": bot_msg.created_at.isoformat(),
                },
            )
    except Exception as e:
        log.error("Fehler bei Bot-Antwort für Konversation %d: %s", conv_id, e)


# ── REST-Endpoints ───────────────────────────────────────────────

@router.get("/conversations")
async def list_conversations(
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Alle Konversationen des aktuellen Benutzers."""
    result = await db.execute(
        select(Conversation)
        .join(ConversationMember)
        .where(ConversationMember.employee_id == current_user.id)
        .options(selectinload(Conversation.members))
        .order_by(Conversation.created_at.desc())
    )
    convs = result.scalars().unique().all()

    response = []
    for conv in convs:
        # Letzten Nachricht holen
        last_msg_q = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id, Message.is_deleted == False)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_msg = last_msg_q.scalar_one_or_none()

        # Ungelesene zaehlen
        my_member = next(
            (m for m in conv.members if m.employee_id == current_user.id), None
        )
        unread = 0
        if my_member and my_member.last_read_at:
            unread_q = await db.execute(
                select(func.count(Message.id)).where(
                    Message.conversation_id == conv.id,
                    Message.created_at > my_member.last_read_at,
                    Message.sender_id != current_user.id,
                    Message.is_deleted == False,
                )
            )
            unread = unread_q.scalar() or 0
        elif my_member:
            unread_q = await db.execute(
                select(func.count(Message.id)).where(
                    Message.conversation_id == conv.id,
                    Message.sender_id != current_user.id,
                    Message.is_deleted == False,
                )
            )
            unread = unread_q.scalar() or 0

        # Teilnehmer-Namen
        member_ids = [m.employee_id for m in conv.members]
        members_q = await db.execute(
            select(Employee).where(Employee.id.in_(member_ids))
        )
        members = members_q.scalars().all()
        member_names = {
            e.id: f"{e.first_name} {e.last_name}" for e in members
        }

        # Anzeigename: bei DIRECT den anderen Teilnehmer
        display_name = conv.name
        if conv.type == "DIRECT" and not display_name:
            other = [m for m in conv.members if m.employee_id != current_user.id]
            if other:
                display_name = member_names.get(other[0].employee_id, "Unbekannt")

        response.append({
            "id": conv.id,
            "type": conv.type,
            "name": display_name or "Gruppe",
            "members": [
                {"id": m.employee_id, "name": member_names.get(m.employee_id, "")}
                for m in conv.members
            ],
            "last_message": {
                "content": last_msg.content if last_msg else None,
                "sender_id": last_msg.sender_id if last_msg else None,
                "sender_name": member_names.get(last_msg.sender_id, "") if last_msg else None,
                "created_at": last_msg.created_at.isoformat() if last_msg else None,
            } if last_msg else None,
            "unread_count": unread,
            "created_at": conv.created_at.isoformat(),
        })

    # Sortieren: Konversationen mit neuester Nachricht zuerst
    response.sort(
        key=lambda c: c["last_message"]["created_at"] if c.get("last_message") and c["last_message"]["created_at"] else "",
        reverse=True,
    )

    return response


@router.post("/conversations")
async def create_conversation(
    data: ConversationCreate,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Neue Konversation erstellen."""
    # Bei DIRECT: pruefen ob schon eine existiert
    if data.type == "DIRECT" and len(data.member_ids) == 1:
        other_id = data.member_ids[0]
        existing = await db.execute(
            select(Conversation)
            .join(ConversationMember)
            .where(
                Conversation.type == "DIRECT",
                ConversationMember.employee_id == current_user.id,
            )
        )
        for conv in existing.scalars().all():
            member_q = await db.execute(
                select(ConversationMember.employee_id).where(
                    ConversationMember.conversation_id == conv.id
                )
            )
            member_ids_existing = {r[0] for r in member_q.all()}
            if member_ids_existing == {current_user.id, other_id}:
                return {"id": conv.id, "existing": True}

    conv = Conversation(
        type=data.type,
        name=data.name,
        created_by=current_user.id,
    )
    db.add(conv)
    await db.flush()

    # Ersteller als Mitglied
    all_member_ids = set(data.member_ids) | {current_user.id}
    for mid in all_member_ids:
        db.add(ConversationMember(
            conversation_id=conv.id,
            employee_id=mid,
        ))
    await db.flush()

    # System-Nachricht
    if data.type != "DIRECT":
        db.add(Message(
            conversation_id=conv.id,
            sender_id=current_user.id,
            content="Gruppe erstellt",
            message_type="SYSTEM",
        ))

    return {"id": conv.id, "existing": False}


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: int,
    before: Optional[datetime] = Query(None),
    limit: int = Query(50, le=100),
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Nachrichten einer Konversation laden (paginiert)."""
    # Pruefen ob Mitglied
    member = await db.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.employee_id == current_user.id,
        )
    )
    if not member.scalar_one_or_none():
        raise HTTPException(403, "Kein Mitglied dieser Konversation")

    query = (
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.is_deleted == False,
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    if before:
        query = query.where(Message.created_at < before)

    result = await db.execute(query)
    messages = result.scalars().all()

    # Sender-Namen laden
    sender_ids = {m.sender_id for m in messages}
    if sender_ids:
        senders_q = await db.execute(
            select(Employee).where(Employee.id.in_(sender_ids))
        )
        sender_map = {
            e.id: f"{e.first_name} {e.last_name}"
            for e in senders_q.scalars().all()
        }
    else:
        sender_map = {}

    # Als gelesen markieren
    await _mark_read(db, conversation_id, current_user.id)

    return [
        {
            "id": m.id,
            "conversation_id": m.conversation_id,
            "sender_id": m.sender_id,
            "sender_name": sender_map.get(m.sender_id, ""),
            "content": m.content,
            "message_type": m.message_type,
            "created_at": m.created_at.isoformat(),
            "edited_at": m.edited_at.isoformat() if m.edited_at else None,
        }
        for m in reversed(messages)  # Chronologisch
    ]


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: int,
    data: MessageCreate,
    background_tasks: BackgroundTasks,
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Nachricht senden (REST-Fallback, WebSocket bevorzugt)."""
    member = await db.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.employee_id == current_user.id,
        )
    )
    if not member.scalar_one_or_none():
        raise HTTPException(403, "Kein Mitglied dieser Konversation")

    msg = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=data.content.strip(),
        message_type=data.message_type,
    )
    db.add(msg)
    await db.flush()

    sender_name = f"{current_user.first_name} {current_user.last_name}"

    response = {
        "id": msg.id,
        "conversation_id": conversation_id,
        "sender_id": current_user.id,
        "sender_name": sender_name,
        "content": msg.content,
        "message_type": msg.message_type,
        "created_at": msg.created_at.isoformat(),
    }

    # Per WebSocket an alle Mitglieder senden
    member_ids = await _get_member_ids(db, conversation_id)
    await manager.send_to_conversation(member_ids, {
        "type": "new_message",
        **response,
    })

    # Bot-Antwort auslösen falls Empfänger der Support-Bot ist
    bot_id = await _find_bot_in_direct_conv(db, conversation_id)
    if bot_id:
        background_tasks.add_task(
            _handle_bot_response,
            conversation_id,
            data.content.strip(),
            bot_id,
            member_ids,
        )

    return response


@router.get("/support-bot-id")
async def get_support_bot_id(
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Gibt die Employee-ID des Support-Bots zurück."""
    bot_id = await _get_bot_employee_id(db)
    if not bot_id:
        raise HTTPException(404, "Support-Bot nicht gefunden")
    return {"id": bot_id}


@router.get("/employees")
async def list_chat_employees(
    current_user: Employee = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Alle Mitarbeiter fuer neue Konversation auflisten (ohne Support-Bot)."""
    result = await db.execute(
        select(Employee)
        .where(
            Employee.is_active == True,
            Employee.id != current_user.id,
            Employee.personnel_number != BOT_PERSONNEL_NUMBER,
        )
        .order_by(Employee.last_name, Employee.first_name)
    )
    employees = result.scalars().all()

    online = manager.get_online_users()

    return [
        {
            "id": e.id,
            "name": f"{e.first_name} {e.last_name}",
            "role": e.role.value if hasattr(e.role, 'value') else e.role,
            "department_id": e.department_id,
            "department_name": e.department.name if e.department else None,
            "online": e.id in online,
        }
        for e in employees
    ]


@router.get("/online")
async def get_online_users(
    current_user: Employee = Depends(get_current_user),
):
    """Aktuell online verbundene Benutzer."""
    return {"online_users": manager.get_online_users()}


# ── Hilfsfunktionen ──────────────────────────────────────────────

async def _get_member_ids(db: AsyncSession, conversation_id: int) -> list[int]:
    result = await db.execute(
        select(ConversationMember.employee_id).where(
            ConversationMember.conversation_id == conversation_id
        )
    )
    return [r[0] for r in result.all()]


async def _mark_read(db: AsyncSession, conversation_id: int, employee_id: int):
    result = await db.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.employee_id == employee_id,
        )
    )
    member = result.scalar_one_or_none()
    if member:
        member.last_read_at = datetime.utcnow()


async def _create_message(
    db: AsyncSession, conversation_id: int, sender_id: int, content: str
) -> dict | None:
    """Nachricht erstellen und als dict zurückgeben."""
    # Mitgliedschaftsprüfung: Sender muss Mitglied der Konversation sein
    member_check = await db.execute(
        select(ConversationMember).where(
            ConversationMember.conversation_id == conversation_id,
            ConversationMember.employee_id == sender_id,
        )
    )
    if not member_check.scalar_one_or_none():
        log.warning(
            "Unbefugter Nachrichtenversand verhindert: Employee %s ist kein Mitglied von Konversation %s",
            sender_id,
            conversation_id,
        )
        return None

    msg = Message(
        conversation_id=conversation_id,
        sender_id=sender_id,
        content=content,
        message_type="TEXT",
    )
    db.add(msg)
    await db.flush()

    # Sender-Name
    sender_q = await db.execute(select(Employee).where(Employee.id == sender_id))
    sender = sender_q.scalar_one_or_none()
    sender_name = f"{sender.first_name} {sender.last_name}" if sender else ""

    return {
        "type": "new_message",
        "id": msg.id,
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "sender_name": sender_name,
        "content": msg.content,
        "message_type": msg.message_type,
        "created_at": msg.created_at.isoformat(),
    }
