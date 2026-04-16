import uuid
from sqlalchemy import (
    Column,
    UUID,
    String,
    Integer,
    DateTime,
    ForeignKey,
    func,
    Index,
)
from db.base import Base


class LlmCallLog(Base):
    __tablename__ = "llm_call_logs"

    __table_args__ = (
        Index("ix_llm_call_logs_created_at", "created_at"),
        Index("ix_llm_call_logs_user_id", "user_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    endpoint = Column(String(100), nullable=False)
    model = Column(String(100), nullable=False)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="success")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
