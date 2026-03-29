from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EmploymentType(str, Enum):
    FULLTIME = "FULLTIME"
    PARTTIME = "PARTTIME"
    MINI = "MINI"
    TRAINEE = "TRAINEE"


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    HR = "HR"
    DEPARTMENT_MANAGER = "DEPARTMENT_MANAGER"
    TEAM_LEADER = "TEAM_LEADER"
    EMPLOYEE = "EMPLOYEE"


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    personnel_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    ad_username: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, index=True
    )

    # Persoenliche Daten
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    mobile: Mapped[Optional[str]] = mapped_column(String(50))
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Adresse
    street: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Organisation
    department_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id")
    )
    role: Mapped[UserRole] = mapped_column(default=UserRole.EMPLOYEE)
    job_title: Mapped[Optional[str]] = mapped_column(String(200))

    # Vertrag
    employment_type: Mapped[EmploymentType] = mapped_column(
        default=EmploymentType.FULLTIME
    )
    weekly_hours: Mapped[float] = mapped_column(default=38.5)
    hire_date: Mapped[date] = mapped_column(Date)
    exit_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    vacation_days_per_year: Mapped[int] = mapped_column(default=30)

    # Notfallkontakt
    emergency_contact_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    emergency_contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Beziehungen
    department = relationship(
        "Department",
        back_populates="employees",
        foreign_keys=[department_id],
        lazy="selectin",
    )
    qualifications = relationship(
        "Qualification", back_populates="employee", lazy="selectin"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Employee {self.personnel_number} {self.full_name}>"
