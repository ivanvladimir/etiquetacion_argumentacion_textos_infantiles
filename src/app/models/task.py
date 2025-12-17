import uuid as uuid_pkg
from datetime import UTC, datetime

from sqlalchemy import UUID, DateTime, ForeignKey, String, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from uuid6 import uuid7
from typing import Optional

from enum import Enum as PyEnum

from ..core.db.database import Base

class TaskStatus(PyEnum):
    """Enum for task status"""
    STARTING = "starting"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"


class Task(Base):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column("id", autoincrement=True, nullable=False, unique=True, primary_key=True, init=False)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    document_id: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.STARTING)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=func.now(UTC), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    def __repr__(self):
        return f"<Task(id={self.id}, name='{self.name}', status={self.status.value})>"

    def mark_running(self):
        """Mark task as running"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()

    def mark_finished(self):
        """Mark task as finished"""
        self.status = TaskStatus.FINISHED
        self.completed_at = datetime.utcnow()

    def mark_error(self, error_message):
        """Mark task as errored with message"""
        self.status = TaskStatus.ERROR
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
