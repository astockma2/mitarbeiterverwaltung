from datetime import datetime, date
from enum import Enum
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, String, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EntryType(str, Enum):
    REGULAR = "REGULAR"
    CORRECTION = "CORRECTION"
    MANUAL = "MANUAL"


class EntryStatus(str, Enum):
    OPEN = "OPEN"
    APPROVED = "APPROVED"
    LOCKED = "LOCKED"


class AbsenceType(str, Enum):
    VACATION = "VACATION"
    SICK = "SICK"
    TRAINING = "TRAINING"
    SPECIAL = "SPECIAL"
    COMP_TIME = "COMP_TIME"  # Freizeitausgleich


class AbsenceStatus(str, Enum):
    REQUESTED = "REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class CorrectionStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class SurchargeType(str, Enum):
    NIGHT = "NIGHT"
    SUNDAY = "SUNDAY"
    HOLIDAY = "HOLIDAY"
    SATURDAY = "SATURDAY"
    OVERTIME = "OVERTIME"


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    clock_in: Mapped[datetime] = mapped_column(DateTime)
    clock_out: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    break_minutes: Mapped[int] = mapped_column(default=0)
    entry_type: Mapped[EntryType] = mapped_column(default=EntryType.REGULAR)
    status: Mapped[EntryStatus] = mapped_column(default=EntryStatus.OPEN)
    approved_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Beziehungen
    employee = relationship("Employee", foreign_keys=[employee_id], lazy="selectin")
    surcharges = relationship("Surcharge", back_populates="time_entry", lazy="selectin")

    @property
    def net_hours(self) -> Optional[float]:
        if self.clock_out is None:
            return None
        total_seconds = (self.clock_out - self.clock_in).total_seconds()
        net_seconds = total_seconds - (self.break_minutes * 60)
        return round(max(0, net_seconds / 3600), 2)

    def __repr__(self) -> str:
        return f"<TimeEntry {self.employee_id} {self.date} {self.clock_in}-{self.clock_out}>"


class Surcharge(Base):
    __tablename__ = "surcharges"

    id: Mapped[int] = mapped_column(primary_key=True)
    time_entry_id: Mapped[int] = mapped_column(
        ForeignKey("time_entries.id"), index=True
    )
    type: Mapped[SurchargeType] = mapped_column()
    hours: Mapped[float] = mapped_column(Float)
    rate_percent: Mapped[float] = mapped_column(Float)  # z.B. 25.0 fuer 25%
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    time_entry = relationship("TimeEntry", back_populates="surcharges")

    def __repr__(self) -> str:
        return f"<Surcharge {self.type} {self.hours}h @ {self.rate_percent}%>"


class Absence(Base):
    __tablename__ = "absences"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    type: Mapped[AbsenceType] = mapped_column()
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    days: Mapped[float] = mapped_column(Float)  # Arbeitstage
    status: Mapped[AbsenceStatus] = mapped_column(default=AbsenceStatus.REQUESTED)
    approved_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id"), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    employee = relationship("Employee", foreign_keys=[employee_id], lazy="selectin")

    def __repr__(self) -> str:
        return f"<Absence {self.type} {self.start_date}-{self.end_date}>"


class CorrectionRequest(Base):
    __tablename__ = "correction_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    time_entry_id: Mapped[int] = mapped_column(
        ForeignKey("time_entries.id"), index=True
    )
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    field: Mapped[str] = mapped_column(String(50))  # clock_in, clock_out, break_minutes
    old_value: Mapped[str] = mapped_column(String(100))
    new_value: Mapped[str] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[CorrectionStatus] = mapped_column(default=CorrectionStatus.PENDING)
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    time_entry = relationship("TimeEntry", lazy="selectin")
    employee = relationship("Employee", foreign_keys=[employee_id], lazy="selectin")

    def __repr__(self) -> str:
        return f"<CorrectionRequest {self.id} {self.field}: {self.old_value}->{self.new_value}>"


class MonthlyClosing(Base):
    __tablename__ = "monthly_closings"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    year: Mapped[int] = mapped_column()
    month: Mapped[int] = mapped_column()
    total_hours: Mapped[float] = mapped_column(Float, default=0)
    target_hours: Mapped[float] = mapped_column(Float, default=0)
    overtime_hours: Mapped[float] = mapped_column(Float, default=0)
    sick_days: Mapped[float] = mapped_column(Float, default=0)
    vacation_days: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")  # OPEN, CLOSED, EXPORTED
    closed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id"), nullable=True
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    exported_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    employee = relationship("Employee", foreign_keys=[employee_id], lazy="selectin")

    def __repr__(self) -> str:
        return f"<MonthlyClosing {self.employee_id} {self.year}-{self.month:02d}>"
