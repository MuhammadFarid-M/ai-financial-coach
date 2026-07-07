"""
ORM models — the Python mirror of your database tables.

Design notes:
- UUID primary keys (generated in Python with default=uuid.uuid4) so we
  don't depend on any DB extension and IDs are unguessable.
- ondelete="CASCADE" on the foreign keys + cascade="all, delete-orphan" on
  the relationships means deleting a user (or a session) automatically
  cleans up everything that belongs to it.
- The sessions model is named `ChatSession` (not `Session`) to avoid
  clashing with SQLAlchemy's own `Session` class. The table is still
  `sessions` in Postgres.
"""
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)

    profile = relationship(
        "Profile",
        back_populates="user",
        uselist=False,  # one-to-one
        cascade="all, delete-orphan",
    )
    sessions = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )
    insights = relationship(
        "Insight", back_populates="user", cascade="all, delete-orphan"
    )


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # one profile per user
    )
    # Numeric(14, 2) safely stores rupee amounts up to 999,999,999,999.99
    monthly_income = Column(Numeric(14, 2), default=0)
    monthly_expenses = Column(Numeric(14, 2), default=0)
    current_savings = Column(Numeric(14, 2), default=0)  # amount saved to date
    risk_tolerance = Column(String(100), default="Moderate")

    user = relationship("User", back_populates="profile")


class ChatSession(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String(255), nullable=False, default="New Strategy Thread")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="sessions")
    insights = relationship(
        "Insight",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Insight.created_at",
    )


class Insight(Base):
    """One row = one prompt/response pair in a session (chat history)."""

    __tablename__ = "insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_prompt = Column(Text, nullable=False)
    conversational_response = Column(Text, nullable=False)
    chart_bool = Column(Boolean, default=False)
    chart_data = Column(JSONB, nullable=True)  # {"labels": [...], "values": [...]}
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="insights")
    session = relationship("ChatSession", back_populates="insights")
