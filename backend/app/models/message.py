"""Chat-Modelle: Konversationen, Teilnehmer, Nachrichten."""

from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SAEnum,
)
from sqlalchemy.orm import relationship

from app.database import Base

import enum


class ConversationType(str, enum.Enum):
    DIRECT = "DIRECT"
    GROUP = "GROUP"
    DEPARTMENT = "DEPARTMENT"
    ANNOUNCEMENT = "ANNOUNCEMENT"


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(20), nullable=False, default=ConversationType.DIRECT)
    name = Column(String(100), nullable=True)  # Gruppenname
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("employees.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    members = relationship("ConversationMember", back_populates="conversation", lazy="selectin")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")


class ConversationMember(Base):
    __tablename__ = "conversation_members"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_read_at = Column(DateTime, nullable=True)
    is_muted = Column(Boolean, default=False)

    conversation = relationship("Conversation", back_populates="members")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="TEXT")  # TEXT, IMAGE, FILE, SYSTEM
    file_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    edited_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False)

    conversation = relationship("Conversation", back_populates="messages")


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    fcm_token = Column(String(500), nullable=False, unique=True)
    device_type = Column(String(20), default="android")  # android, web
    created_at = Column(DateTime, default=datetime.utcnow)
