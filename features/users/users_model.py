import uuid
from sqlalchemy import (
    Column,
    Enum,
    UUID,
    String,
    Text,
    DateTime,
    Integer,
    Float,
    Boolean,
    func,
)

from db.base import Base
from .users_enum import GoalEnum, GenderEnum, TrainingTypeEnum


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)

    age = Column(Integer, nullable=False)
    weight = Column(Float, nullable=False)
    height = Column(Integer, nullable=False)

    goal = Column(Enum(GoalEnum, name="goal_enum"), nullable=False)
    gender = Column(Enum(GenderEnum, name="gender_enum"), nullable=False)
    training_type = Column(
        Enum(TrainingTypeEnum, name="training_type_enum"),
        nullable=False,
        default=TrainingTypeEnum.HYPERTROPHY,
        server_default="HYPERTROPHY",
    )

    activity_level = Column(Text, nullable=True)

    mobile_number = Column(String(20), nullable=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
