"""Beanie documents are validated Python objects backed by MongoDB."""

from datetime import datetime, timezone
from enum import Enum

from beanie import Document
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Match MongoDB's millisecond precision so API timestamps survive round trips."""
    now = datetime.now(timezone.utc)
    return now.replace(microsecond=(now.microsecond // 1000) * 1000)


class Status(str, Enum):
    todo = "todo"
    doing = "doing"
    done = "done"


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class TaskInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    title: str = Field(min_length=1, max_length=120)
    notes: str = Field(default="", max_length=2000)
    status: Status = Status.todo
    priority: Priority = Priority.medium


class Task(Document):
    title: str
    notes: str = ""
    status: Status = Status.todo
    priority: Priority = Priority.medium
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        name = "tasks"
        indexes = ["created_at", "status"]


class TaskOutput(TaskInput):
    id: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_document(cls, task: Task) -> "TaskOutput":
        return cls(**task.model_dump(exclude={"id", "revision_id"}), id=str(task.id))
