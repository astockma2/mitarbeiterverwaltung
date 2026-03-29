from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id"))
    action: Mapped[str] = mapped_column(String(50))  # CREATE, UPDATE, DELETE
    entity_type: Mapped[str] = mapped_column(String(100))  # employees, departments
    entity_id: Mapped[int] = mapped_column()
    changes: Mapped[Optional[dict]] = mapped_column(JSON)  # {field: {old, new}}
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
