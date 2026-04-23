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
from db.uuid import new_uuid
from .users_enum import GoalEnum, GenderEnum, TrainingTypeEnum, ExperienceLevelEnum, RoleEnum


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)

    # Fitness fields — nullable so Google-OAuth users can exist before
    # completing their profile. Guard any code that dereferences these with
    # `if user.X is not None` or a fallback.
    age = Column(Integer, nullable=True)
    weight = Column(Float, nullable=True)
    height = Column(Integer, nullable=True)

    goal = Column(Enum(GoalEnum, name="goal_enum"), nullable=True)
    gender = Column(Enum(GenderEnum, name="gender_enum"), nullable=True)
    training_type = Column(
        Enum(TrainingTypeEnum, name="training_type_enum"),
        nullable=False,
        default=TrainingTypeEnum.HYPERTROPHY,
        server_default="HYPERTROPHY",
    )

    activity_level = Column(Text, nullable=True)

    experience_level = Column(
        Enum(ExperienceLevelEnum, name="experience_level_enum"),
        nullable=False,
        default=ExperienceLevelEnum.BEGINNER,
        server_default="BEGINNER",
    )

    mobile_number = Column(String(20), nullable=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    # hashed_password is NULL for Google-only accounts.
    hashed_password = Column(String(255), nullable=True)

    # Google OAuth — `sub` claim from Google's ID token. Unique per Google
    # account. NULL for password-only users.
    google_id = Column(String(255), nullable=True, unique=True, index=True)

    # False only while a Google-signed-up user hasn't filled in age/weight/
    # height/goal/gender yet. Existing rows default to True (server_default).
    is_profile_complete = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    role = Column(
        Enum(RoleEnum, values_callable=lambda x: [e.value for e in x], name="role_enum"),
        nullable=False,
        default=RoleEnum.USER,
        server_default="user",
    )

    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
