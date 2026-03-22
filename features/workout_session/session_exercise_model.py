import uuid
from db.base import Base
from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    Enum,
    UUID,
    Index,
)
from sqlalchemy.orm import relationship

from features.split_exercise.split_exercise_enum import ExerciseTypeEnum


class SessionExercise(Base):
    __tablename__ = "session_exercises"

    __table_args__ = (
        Index("ix_session_exercises_session_display", "session_id", "display_order"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workout_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    split_exercise_id = Column(
        UUID(as_uuid=True),
        ForeignKey("split_exercises.id", ondelete="SET NULL"),
        nullable=True,
    )
    exercise_name = Column(String(150), nullable=False)
    display_order = Column(Integer, nullable=False)
    exercise_type = Column(
        Enum(ExerciseTypeEnum, name="exercise_type_enum", create_type=False),
        nullable=False,
        default=ExerciseTypeEnum.STANDARD,
    )
    superset_group = Column(Integer, nullable=True)

    session = relationship("WorkoutSession", back_populates="exercises")
    sets = relationship(
        "ExerciseSet",
        back_populates="session_exercise",
        cascade="all, delete-orphan",
        order_by="ExerciseSet.set_number",
    )
