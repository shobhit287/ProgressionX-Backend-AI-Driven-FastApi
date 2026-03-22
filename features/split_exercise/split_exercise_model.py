import uuid
from db.base import Base
from sqlalchemy import Column, String, Integer, Text, ForeignKey, Enum, UUID, Index
from sqlalchemy.orm import relationship

from .split_exercise_enum import ExerciseTypeEnum


class SplitExercise(Base):
    __tablename__ = "split_exercises"

    __table_args__ = (
        Index("ix_split_exercises_split_id_display_order", "split_id", "display_order"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    split_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workout_splits.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(150), nullable=False)
    display_order = Column(Integer, nullable=False)
    default_sets = Column(Integer, nullable=False, default=3)
    exercise_type = Column(
        Enum(ExerciseTypeEnum, name="exercise_type_enum"),
        nullable=False,
        default=ExerciseTypeEnum.STANDARD,
    )
    superset_group = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    rest_seconds = Column(Integer, nullable=False, default=90)

    split = relationship("WorkoutSplit", back_populates="exercises")
