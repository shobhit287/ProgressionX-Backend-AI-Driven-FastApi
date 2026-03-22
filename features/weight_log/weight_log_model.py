import uuid
from db.base import Base
from sqlalchemy import (
    Column,
    Float,
    Text,
    Date,
    ForeignKey,
    UUID,
    UniqueConstraint,
    Index,
    func,
)


class WeightLog(Base):
    __tablename__ = "weight_logs"

    __table_args__ = (
        UniqueConstraint("user_id", "logged_at", name="uq_user_logged_at"),
        Index("ix_weight_logs_user_logged_at", "user_id", "logged_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    weight_kg = Column(Float, nullable=False)
    waist_cm = Column(Float, nullable=True)
    body_fat_pct = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    logged_at = Column(Date, nullable=False, server_default=func.current_date())
