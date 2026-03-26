from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from db.models import TaskStatus


class UserCreate(BaseModel):
    """Schema for creating a new user."""
    tg_id: int = Field(..., description="Telegram user ID")
    full_name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    username: str | None = Field(None, max_length=255, description="Telegram username")


class UserRead(BaseModel):
    """Schema for reading user data."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    tg_id: int
    full_name: str
    username: str | None
    xp: int


class TaskCreate(BaseModel):
    """Schema for creating a new task."""
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: str | None = Field(None, max_length=1000, description="Task description")
    deadline: datetime = Field(..., description="Task deadline")
    creator_tg_id: int = Field(..., description="Telegram ID of the user creating the task")
    group_id: int | None = Field(None, description="Optional group ID to assign task to")


class TaskRead(BaseModel):
    """Schema for reading task data."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    deadline: datetime
    status: TaskStatus
    creator_id: int
    group_id: int | None
    telegram_file_id: str | None


class GroupCreate(BaseModel):
    """Schema for creating a new group."""
    name: str = Field(..., min_length=1, max_length=255, description="Group name")
    creator_tg_id: int = Field(..., description="Telegram ID of the user creating the group")


class GroupRead(BaseModel):
    """Schema for reading group data."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    invite_link: str
