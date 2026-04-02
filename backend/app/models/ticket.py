from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[TicketStatus] = mapped_column(default=TicketStatus.OPEN)
    priority: Mapped[TicketPriority] = mapped_column(default=TicketPriority.MEDIUM)
    created_by: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    assigned_to: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    creator = relationship("Employee", foreign_keys=[created_by], lazy="selectin")
    assignee = relationship("Employee", foreign_keys=[assigned_to], lazy="selectin")

    def __repr__(self) -> str:
        return f"<Ticket {self.id} '{self.title}' [{self.status}]>"
