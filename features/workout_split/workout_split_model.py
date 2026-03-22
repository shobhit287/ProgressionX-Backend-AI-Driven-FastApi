import uuid
from db.base import Base
from sqlalchemy import Column, String, ForeignKey, Enum, UUID, UniqueConstraint
from sqlalchemy.orm import relationship

from .workout_split_enum import DayEnum

class WorkoutSplit(Base):
    __tablename__ = "workout_splits"

    __table_args__ = (
        UniqueConstraint("user_id", "day", name="uq_user_day"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    day = Column(Enum(DayEnum, name="days_enum"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    description = Column(String, nullable=True)

    exercises = relationship(
        "SplitExercise",
        back_populates="split",
        cascade="all, delete-orphan",
        order_by="SplitExercise.display_order",
    )