from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TravelStatus(str, Enum):
    REQUESTED = "REQUESTED"
    MANAGER_APPROVED = "MANAGER_APPROVED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    APPROVED_LEGACY = "APPROVED_LEGACY"


class PlanningMarkerKind(str, Enum):
    DUTY = "DUTY"
    ABSENCE = "ABSENCE"
    INFO = "INFO"


class TravelRequest(Base):
    """Dienstreise mit Genehmigungsstatus."""

    __tablename__ = "travel_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date] = mapped_column(Date, index=True)
    destination: Mapped[str] = mapped_column(String(200))
    purpose: Mapped[str] = mapped_column(String(500))
    cost_center: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    transport_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    estimated_costs: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[TravelStatus] = mapped_column(default=TravelStatus.REQUESTED)
    requested_by: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    manager_approved_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id"), nullable=True
    )
    hr_approved_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id"), nullable=True
    )
    review_notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    employee = relationship("Employee", foreign_keys=[employee_id], lazy="selectin")
    requester = relationship("Employee", foreign_keys=[requested_by], lazy="selectin")
    manager_approver = relationship(
        "Employee", foreign_keys=[manager_approved_by], lazy="selectin"
    )
    hr_approver = relationship("Employee", foreign_keys=[hr_approved_by], lazy="selectin")

    def __repr__(self) -> str:
        return f"<TravelRequest {self.employee_id} {self.start_date}-{self.end_date} {self.status}>"


class PlanningMarker(Base):
    """Importierter Planmarker aus Excel fuer Dienste, Orte und Sonderhinweise."""

    __tablename__ = "planning_markers"
    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "date",
            "code",
            "source",
            name="uq_planning_marker_employee_date_code_source",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    code: Mapped[str] = mapped_column(String(12))
    label: Mapped[str] = mapped_column(String(120))
    kind: Mapped[PlanningMarkerKind] = mapped_column(default=PlanningMarkerKind.INFO)
    color: Mapped[str] = mapped_column(String(7), default="#64748B")
    source: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    employee = relationship("Employee", lazy="selectin")

    def __repr__(self) -> str:
        return f"<PlanningMarker {self.employee_id} {self.date} {self.code}>"
