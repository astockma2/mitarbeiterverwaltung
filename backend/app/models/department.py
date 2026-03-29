from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    short_name: Mapped[Optional[str]] = mapped_column(String(20))
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"))
    cost_center: Mapped[Optional[str]] = mapped_column(String(20))
    manager_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Beziehungen
    parent = relationship("Department", remote_side="Department.id", lazy="selectin")
    manager = relationship("Employee", foreign_keys=[manager_id], lazy="selectin")
    employees = relationship(
        "Employee",
        back_populates="department",
        foreign_keys="Employee.department_id",
    )

    def __repr__(self) -> str:
        return f"<Department {self.name}>"
