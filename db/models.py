from datetime import datetime
from enum import Enum as PyEnum
from typing import List

from sqlalchemy import BigInteger, String, Integer, DateTime, ForeignKey, Table, Enum, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


class TaskStatus(str, PyEnum):
    TO_DO = "to_do"
    IN_PROGRESS = "in_progress"
    DONE = "done"


user_group_association = Table(
    "user_group_association",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    groups: Mapped[List["Group"]] = relationship(
        secondary=user_group_association,
        back_populates="users"
    )

    created_tasks: Mapped[List["Task"]] = relationship(
        back_populates="creator",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, tg_id={self.tg_id}, username={self.username})>"


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    invite_link: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)

    creator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    users: Mapped[List["User"]] = relationship(
        secondary=user_group_association,
        back_populates="groups"
    )

    tasks: Mapped[List["Task"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan"
    )

    creator: Mapped["User | None"] = relationship(foreign_keys=[creator_id])

    def __repr__(self) -> str:
        return f"<Group(id={self.id}, name={self.name})>"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, native_enum=False),
        default=TaskStatus.TO_DO,
        nullable=False
    )
    telegram_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_reminder_sent: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    group_id: Mapped[int | None] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"), nullable=True)

    creator: Mapped["User"] = relationship(back_populates="created_tasks")

    group: Mapped["Group | None"] = relationship(back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title={self.title}, status={self.status.value})>"
