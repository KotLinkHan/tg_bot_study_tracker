from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import User, Task, Group, TaskStatus
from api.schemas import UserCreate, TaskCreate


async def get_user_by_tg_id(session: AsyncSession, tg_id: int) -> User | None:
    """
    Retrieve a user by their Telegram ID.

    """
    stmt = select(User).where(User.tg_id == tg_id).options(selectinload(User.groups))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, user_in: UserCreate) -> User:
    """
    Create a new user in the database.

    """
    user = User(
        tg_id=user_in.tg_id,
        full_name=user_in.full_name,
        username=user_in.username
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_task(session: AsyncSession, task_in: TaskCreate, creator_id: int) -> Task:
    """
    Create a new task in the database.

    """
    task = Task(
        title=task_in.title,
        description=task_in.description,
        deadline=task_in.deadline,
        creator_id=creator_id,
        group_id=task_in.group_id
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def get_user_tasks(session: AsyncSession, user_id: int) -> list[Task]:
    """
    Retrieve all tasks created by a specific user.

    """
    stmt = select(Task).where(Task.creator_id == user_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_group(session: AsyncSession, name: str, creator_id: int) -> Group:
    """
    Create a new group and automatically add the creator to it.

    """
    import uuid
    from core.config import settings
    invite_link = f"https://t.me/{settings.BOT_USERNAME}?start=group_{uuid.uuid4().hex[:8]}"

    group = Group(name=name, invite_link=invite_link)
    session.add(group)
    await session.flush()

    stmt = (
        select(User)
        .where(User.id == creator_id)
        .options(selectinload(User.groups))
    )
    result = await session.execute(stmt)
    creator = result.scalar_one_or_none()

    if creator is not None:
        group.creator_id = creator.id
        creator.groups.append(group)

    await session.commit()
    await session.refresh(group)
    return group


async def add_user_to_group(session: AsyncSession, user_id: int, group_id: int) -> bool:
    """
    Add a user to a group via the association table.

    """
    user = await session.get(User, user_id, options=[selectinload(User.groups)])
    group = await session.get(Group, group_id)

    if not user or not group:
        return False

    if group not in user.groups:
        user.groups.append(group)
        await session.commit()

    return True


async def complete_task(session: AsyncSession, task_id: int) -> Task | None:
    """
    Mark a task as completed and award 10 XP to the creator.

    """
    stmt = select(Task).where(Task.id == task_id)
    result = await session.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        return None

    task.status = TaskStatus.DONE

    creator = await session.get(User, task.creator_id)
    if creator:
        creator.xp += 10

    await session.commit()
    await session.refresh(task)
    return task


async def get_finished_tasks(session: AsyncSession, user_id: int) -> list[Task]:
    """
    Retrieve all completed tasks for a specific user.

    """
    stmt = select(Task).where(
        Task.creator_id == user_id,
        Task.status == TaskStatus.DONE
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_group_tasks(session: AsyncSession, group_id: int) -> list[Task]:
    """
    Retrieve all tasks assigned to a specific group.

    """
    stmt = select(Task).where(Task.group_id == group_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_group_by_id(session: AsyncSession, group_id: int) -> Group | None:
    """
    Retrieve a group by its ID.

    """
    return await session.get(Group, group_id)


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    """
    Retrieve a user by their internal ID.

    """
    return await session.get(User, user_id)


async def get_group_by_invite_link(session: AsyncSession, invite_link: str) -> Group | None:
    """
    Retrieve a group by its invite link.

    """
    stmt = select(Group).where(Group.invite_link == invite_link)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_groups(session: AsyncSession, user_id: int) -> list[Group]:
    user = await session.get(User, user_id, options=[selectinload(User.groups)])
    if not user:
        return []

    # Access groups via the relationship
    return list(user.groups)


async def get_group_members(session: AsyncSession, group_id: int) -> list[User]:
    stmt = select(User).where(User.groups.any(Group.id == group_id))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def delete_group(session: AsyncSession, group_id: int) -> bool:
    group = await session.get(Group, group_id)
    if not group:
        return False

    await session.delete(group)
    await session.commit()
    return True
