import uuid
from db.base import Base
from sqlalchemy import (
    Column,
    Integer,
    Float,
    Boolean,
    Text,
    ForeignKey,
    UUID,
    Index,
)
from sqlalchemy.orm import relationship


class ExerciseSet(Base):
    __tablename__ = "exercise_sets"

    __table_args__ = (
        Index("ix_exercise_sets_session_exercise_set", "session_exercise_id", "set_number"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_exercise_id = Column(
        UUID(as_uuid=True),
        ForeignKey("session_exercises.id", ondelete="CASCADE"),
        nullable=False,
    )
    set_number = Column(Integer, nullable=False)
    weight_kg = Column(Float, nullable=False)
    reps = Column(Integer, nullable=False)
    reps_in_reserve = Column(Integer, nullable=True)
    is_warmup = Column(Boolean, nullable=False, default=False)
    is_dropset = Column(Boolean, nullable=False, default=False)
    description = Column(Text, nullable=True)

    session_exercise = relationship("SessionExercise", back_populates="sets")
