from db.base import Base
from db.uuid import new_uuid
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
        Index("ix_exercise_sets_parent_set_id", "parent_set_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    session_exercise_id = Column(
        UUID(as_uuid=True),
        ForeignKey("session_exercises.id", ondelete="CASCADE"),
        nullable=False,
    )
    set_number = Column(Integer, nullable=False)
    weight_kg = Column(Float, nullable=False)
    reps = Column(Integer, nullable=False)
    reps_in_reserve = Column(Integer, nullable=True)
    # Actual rest taken BEFORE this set, in seconds — the gap between when the
    # previous set of this exercise was logged (its created_at) and this one.
    # Derived from timestamps, not user-entered. NULL on the first set of an
    # exercise, on dropset rows (done back-to-back), and when the gap is
    # implausibly large (> REST_CAP_SECONDS) so a paused session isn't shown
    # as a real rest.
    rest_seconds = Column(Integer, nullable=True)
    is_warmup = Column(Boolean, nullable=False, default=False)
    is_dropset = Column(Boolean, nullable=False, default=False)
    description = Column(Text, nullable=True)
    # For dropsets: points at the top (main) set this drop belongs to.
    # NULL on all standard sets and on the top set of a dropset group.
    parent_set_id = Column(
        UUID(as_uuid=True),
        ForeignKey("exercise_sets.id", ondelete="CASCADE"),
        nullable=True,
    )

    session_exercise = relationship("SessionExercise", back_populates="sets")
