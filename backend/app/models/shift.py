from datetime import datetime, date, time
from enum import Enum
from typing import Optional

from sqlalchemy import Date, ForeignKey, JSON, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ShiftStatus(str, Enum):
    PLANNED = "PLANNED"
    CONFIRMED = "CONFIRMED"
    SWAPPED = "SWAPPED"
    CANCELLED = "CANCELLED"


class CoverageStatus(str, Enum):
    OPEN = "OPEN"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"


class SwapStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class PlanStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class ShiftTemplate(Base):
    """Schichtvorlage (z.B. Fruehdienst, Spaetdienst, Nachtdienst)."""
    __tablename__ = "shift_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    short_code: Mapped[str] = mapped_column(String(5))  # F, S, N, BD, RB
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    break_minutes: Mapped[int] = mapped_column(default=30)
    crosses_midnight: Mapped[bool] = mapped_column(default=False)
    color: Mapped[str] = mapped_column(String(7), default="#3B82F6")  # Hex
    department_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    department = relationship("Department", lazy="selectin")

    @property
    def duration_hours(self) -> float:
        """Brutto-Stunden der Schicht."""
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        if self.crosses_midnight:
            total = (1440 - start_minutes) + end_minutes
        else:
            total = end_minutes - start_minutes
        return round(total / 60, 2)

    @property
    def net_hours(self) -> float:
        return round(self.duration_hours - self.break_minutes / 60, 2)

    def __repr__(self) -> str:
        return f"<ShiftTemplate {self.short_code} {self.start_time}-{self.end_time}>"


class ShiftPlan(Base):
    """Dienstplan fuer einen Monat und eine Abteilung."""
    __tablename__ = "shift_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    year: Mapped[int] = mapped_column()
    month: Mapped[int] = mapped_column()
    status: Mapped[PlanStatus] = mapped_column(default=PlanStatus.DRAFT)
    created_by: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    published_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    department = relationship("Department", lazy="selectin")
    assignments = relationship("ShiftAssignment", back_populates="plan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ShiftPlan {self.department_id} {self.year}-{self.month:02d}>"


class ShiftAssignment(Base):
    """Zuweisung eines Mitarbeiters zu einer Schicht an einem Tag."""
    __tablename__ = "shift_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("shift_plans.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    shift_template_id: Mapped[int] = mapped_column(
        ForeignKey("shift_templates.id"), index=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[ShiftStatus] = mapped_column(default=ShiftStatus.PLANNED)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    plan = relationship("ShiftPlan", back_populates="assignments")
    employee = relationship("Employee", lazy="selectin")
    shift_template = relationship("ShiftTemplate", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ShiftAssignment {self.employee_id} {self.date} {self.shift_template_id}>"


class DutyPlanEntry(Base):
    """Jahres-Dienstplanungscode fuer einen Mitarbeiter an einem Kalendertag."""
    __tablename__ = "duty_plan_entries"
    __table_args__ = (
        UniqueConstraint("employee_id", "date", name="uq_duty_plan_employee_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    code: Mapped[str] = mapped_column(String(8))
    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id"), nullable=True
    )
    updated_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    employee = relationship("Employee", foreign_keys=[employee_id], lazy="selectin")
    creator = relationship("Employee", foreign_keys=[created_by], lazy="selectin")
    updater = relationship("Employee", foreign_keys=[updated_by], lazy="selectin")

    def __repr__(self) -> str:
        return f"<DutyPlanEntry {self.employee_id} {self.date} {self.code}>"


class ShiftRequirement(Base):
    """Mindestbesetzung pro Schicht und Wochentag."""
    __tablename__ = "shift_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    shift_template_id: Mapped[int] = mapped_column(ForeignKey("shift_templates.id"))
    weekday: Mapped[int] = mapped_column()  # 0=Montag, 6=Sonntag
    min_staff: Mapped[int] = mapped_column(default=1)
    required_qualifications: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    department = relationship("Department", lazy="selectin")
    shift_template = relationship("ShiftTemplate", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ShiftRequirement {self.department_id} {self.shift_template_id} day={self.weekday}>"


class CoverageRequest(Base):
    """Vertretungsanfrage bei Ausfall."""
    __tablename__ = "coverage_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("shift_assignments.id"), index=True
    )
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[CoverageStatus] = mapped_column(default=CoverageStatus.OPEN)
    filled_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id"), nullable=True
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    assignment = relationship("ShiftAssignment", lazy="selectin")
    filler = relationship("Employee", foreign_keys=[filled_by], lazy="selectin")

    def __repr__(self) -> str:
        return f"<CoverageRequest {self.id} {self.status}>"


class SwapRequest(Base):
    """Diensttausch-Anfrage zwischen zwei Mitarbeitern."""
    __tablename__ = "swap_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_assignment_id: Mapped[int] = mapped_column(
        ForeignKey("shift_assignments.id")
    )
    target_assignment_id: Mapped[int] = mapped_column(
        ForeignKey("shift_assignments.id")
    )
    requester_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    target_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[SwapStatus] = mapped_column(default=SwapStatus.PENDING)
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    requester_assignment = relationship(
        "ShiftAssignment", foreign_keys=[requester_assignment_id], lazy="selectin"
    )
    target_assignment = relationship(
        "ShiftAssignment", foreign_keys=[target_assignment_id], lazy="selectin"
    )
    requester = relationship("Employee", foreign_keys=[requester_id], lazy="selectin")
    target = relationship("Employee", foreign_keys=[target_id], lazy="selectin")

    def __repr__(self) -> str:
        return f"<SwapRequest {self.requester_id}<->{self.target_id}>"
