from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Qualification(Base):
    __tablename__ = "qualifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(String(500))
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    document_path: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    employee = relationship("Employee", back_populates="qualifications")

    def __repr__(self) -> str:
        return f"<Qualification {self.name} for Employee {self.employee_id}>"
