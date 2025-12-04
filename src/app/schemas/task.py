from datetime import datetime
from typing import Annotated, Any, Optional
from enum import Enum as PyEnum

class TaskStatus(PyEnum):
    """Enum for task status"""
    STARTING = "starting"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"

from pydantic import BaseModel, ConfigDict, Field, field_serializer
from ..core.schemas import PersistentDeletion, TimestampSchema, UUIDSchema

class TimestampTaskSchema(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
    started_at: datetime | None = Field(default=None)
    compleated_at: datetime | None = Field(default=None)

    @field_serializer("created_at")
    def serialize_dt(self, created_at: datetime | None, _info: Any) -> str | None:
        if created_at is not None:
            return created_at.isoformat()

        return None

    @field_serializer("started_at")
    def serialize_started_at(self, updated_at: datetime | None, _info: Any) -> str | None:
        if started_at is not None:
            return updated_at.isoformat()

        return None

    @field_serializer("compleated_at")
    def serialize_compleated_at(self, updated_at: datetime | None, _info: Any) -> str | None:
        if compleated_at is not None:
            return compleated_at.isoformat()

        return None

class TaskBase(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=500, examples=["Name of my task"])]
    status: Annotated[TaskStatus, Field(default=TaskStatus.STARTING)]

class Task(TimestampTaskSchema, TaskBase,PersistentDeletion):
    created_by_user_id: int

class TaskRead(BaseModel):
    id: int
    name: Annotated[str, Field(min_length=2, max_length=500, examples=["This is my task"])]
    status: Annotated[TaskStatus, Field(default=TaskStatus.STARTING)]
    created_by_user_id: int

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class TaskCreate(TaskBase):
    model_config = ConfigDict(extra="forbid")

class TaskCreateInternal(TaskCreate):
    created_by_user_id: int


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=2, max_length=500, examples=["This is my task"])]
    status: Annotated[TaskStatus, Field(default=TaskStatus.STARTING)]
    error_message: Optional[str] = None


class TaskUpdateInternal(TaskUpdate):
    updated_at: datetime


class TaskDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_deleted: bool
    deleted_at: datetime
