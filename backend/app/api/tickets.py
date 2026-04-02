"""API-Endpunkte für das Ticketsystem."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user
from app.auth.permissions import is_hr
from app.database import get_db
from app.models.employee import Employee
from app.models.ticket import Ticket, TicketPriority, TicketStatus
from app.services.audit import log_action

router = APIRouter(prefix="/tickets", tags=["Tickets"])


# === Schemas ===


class TicketCreateRequest(BaseModel):
    title: str
    description: str
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    assigned_to: Optional[int] = None


class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    status: str
    priority: str
    created_by: int
    creator_name: Optional[str] = None
    assigned_to: Optional[int] = None
    assignee_name: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# === Endpunkte ===


@router.post("", response_model=TicketResponse, status_code=201)
async def create_ticket(
    request: TicketCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Neues Support-Ticket erstellen."""
    ticket = Ticket(
        title=request.title,
        description=request.description,
        priority=request.priority,
        created_by=current_user.id,
    )
    db.add(ticket)
    await db.flush()
    await log_action(db, current_user.id, "CREATE", "tickets", ticket.id)
    return _ticket_to_response(ticket)


@router.get("", response_model=list[TicketResponse])
async def list_tickets(
    status: Optional[TicketStatus] = None,
    priority: Optional[TicketPriority] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Tickets auflisten. ADMIN/HR sehen alle, Mitarbeiter nur eigene."""
    query = select(Ticket)

    if not is_hr(current_user):
        query = query.where(Ticket.created_by == current_user.id)

    if status:
        query = query.where(Ticket.status == status)
    if priority:
        query = query.where(Ticket.priority == priority)

    query = query.order_by(Ticket.created_at.desc())
    result = await db.execute(query)
    tickets = result.scalars().all()
    return [_ticket_to_response(t) for t in tickets]


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Einzelnes Ticket abrufen."""
    ticket = await _get_ticket_or_404(db, ticket_id)
    _check_read_permission(current_user, ticket)
    return _ticket_to_response(ticket)


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: int,
    request: TicketUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Ticket bearbeiten (ADMIN, HR oder Ersteller)."""
    ticket = await _get_ticket_or_404(db, ticket_id)
    _check_write_permission(current_user, ticket)

    if request.title is not None:
        ticket.title = request.title
    if request.description is not None:
        ticket.description = request.description
    if request.status is not None:
        ticket.status = request.status
    if request.priority is not None:
        ticket.priority = request.priority
    if request.assigned_to is not None:
        ticket.assigned_to = request.assigned_to

    await log_action(db, current_user.id, "UPDATE", "tickets", ticket_id)
    return _ticket_to_response(ticket)


@router.delete("/{ticket_id}", status_code=204)
async def close_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
):
    """Ticket schließen (Status auf 'closed' setzen)."""
    ticket = await _get_ticket_or_404(db, ticket_id)
    _check_write_permission(current_user, ticket)

    ticket.status = TicketStatus.CLOSED
    await log_action(db, current_user.id, "CLOSED", "tickets", ticket_id)


# === Hilfsfunktionen ===


async def _get_ticket_or_404(db: AsyncSession, ticket_id: int) -> Ticket:
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket nicht gefunden")
    return ticket


def _check_read_permission(user: Employee, ticket: Ticket) -> None:
    if not is_hr(user) and ticket.created_by != user.id:
        raise HTTPException(status_code=403, detail="Keine Berechtigung")


def _check_write_permission(user: Employee, ticket: Ticket) -> None:
    if not is_hr(user) and ticket.created_by != user.id:
        raise HTTPException(status_code=403, detail="Keine Berechtigung")


def _ticket_to_response(ticket: Ticket) -> TicketResponse:
    creator_name = ticket.creator.full_name if ticket.creator else None
    assignee_name = ticket.assignee.full_name if ticket.assignee else None

    return TicketResponse(
        id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status.value,
        priority=ticket.priority.value,
        created_by=ticket.created_by,
        creator_name=creator_name,
        assigned_to=ticket.assigned_to,
        assignee_name=assignee_name,
        created_at=ticket.created_at.isoformat(),
        updated_at=ticket.updated_at.isoformat(),
    )
