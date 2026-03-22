import uuid
from db.base import Base
from sqlalchemy import (
    Column,
    String,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    Enum,
    UUID,
    Index,
    func,
)
from sqlalchemy.orm import relationship

from .workout_session_enum import SessionStatusEnum


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    __table_args__ = (
        Index("ix_workout_sessions_user_started", "user_id", "started_at"),
        Index("ix_workout_sessions_user_split", "user_id", "split_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    split_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workout_splits.id"),
        nullable=False,
    )
    started_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    status = Column(
        Enum(SessionStatusEnum, name="session_status_enum"),
        nullable=False,
        default=SessionStatusEnum.IN_PROGRESS,
    )
    notes = Column(Text, nullable=True)

    exercises = relationship(
        "SessionExercise",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionExercise.display_order",
    )
    split = relationship("WorkoutSplit")
