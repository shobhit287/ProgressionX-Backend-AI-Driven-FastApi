from sqlalchemy import Column, UUID, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

from db.base import Base
from db.uuid import new_uuid


class DietPlan(Base):
    __tablename__ = "diet_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = Column(Text, nullable=False)  # Full diet text entered by user
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
