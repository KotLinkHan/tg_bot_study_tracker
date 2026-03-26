from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_session
from api.schemas import UserCreate, UserRead, TaskCreate, TaskRead, GroupCreate, GroupRead
from db import crud

router = APIRouter()


@router.post("/users/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new user.

    """
    existing_user = await crud.get_user_by_tg_id(session, user_in.tg_id)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Користувач з ID {user_in.tg_id} вже існує"
        )

    user = await crud.create_user(session, user_in)
    return user


@router.get("/users/{tg_id}/tasks", response_model=list[TaskRead])
async def get_user_tasks(
    tg_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    Get all tasks for a specific Telegram user.

    """
    user = await crud.get_user_by_tg_id(session, tg_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Користувача з ID {tg_id} не знайдено"
        )

    tasks = await crud.get_user_tasks(session, user.id)
    return tasks


@router.post("/tasks/", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: TaskCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new task.

    """
    user = await crud.get_user_by_tg_id(session, task_in.creator_tg_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Користувача з ID {task_in.creator_tg_id} не знайдено"
        )

    task = await crud.create_task(session, task_in, user.id)
    return task


@router.patch("/tasks/{task_id}/complete", response_model=TaskRead)
async def complete_task(
    task_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    Mark a task as completed and award XP to the creator.

    """
    task = await crud.complete_task(session, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Завдання з ID {task_id} не знайдено"
        )
    return task


@router.get("/users/{tg_id}/tasks/history", response_model=list[TaskRead])
async def get_user_task_history(
    tg_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    Get completed tasks for a specific Telegram user.

    """
    user = await crud.get_user_by_tg_id(session, tg_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Користувача з ID {tg_id} не знайдено"
        )

    tasks = await crud.get_finished_tasks(session, user.id)
    return tasks


@router.post("/groups/", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
async def create_group(
    group_in: GroupCreate,
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new group.

    """
    user = await crud.get_user_by_tg_id(session, group_in.creator_tg_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Користувача з ID {group_in.creator_tg_id} не знайдено"
        )

    group = await crud.create_group(session, group_in.name, user.id)
    return group


@router.post("/groups/{group_id}/add-user/{tg_id}", status_code=status.HTTP_200_OK)
async def add_user_to_group(
    group_id: int,
    tg_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    Add a user to a group by their Telegram ID.

    """
    user = await crud.get_user_by_tg_id(session, tg_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Користувача з ID {tg_id} не знайдено"
        )

    success = await crud.add_user_to_group(session, user.id, group_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Групи з ID {group_id} не знайдено"
        )

    return {"message": f"Користувача {tg_id} додано до групи {group_id} успішно"}


@router.get("/groups/{group_id}/tasks", response_model=list[TaskRead])
async def get_group_tasks(
    group_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    Get all tasks for a specific group.

    """
    group = await crud.get_group_by_id(session, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Групи з ID {group_id} не знайдено"
        )

    tasks = await crud.get_group_tasks(session, group_id)
    return tasks


@router.get("/users/{tg_id}/groups", response_model=list[GroupRead])
async def get_user_groups(
    tg_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    Get all groups that a user belongs to.

    """
    user = await crud.get_user_by_tg_id(session, tg_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Користувача з ID {tg_id} не знайдено"
        )

    groups = await crud.get_user_groups(session, user.id)
    return groups


@router.get("/groups/{group_id}/members", response_model=list[UserRead])
async def get_group_members(
    group_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    Get all members of a specific group.

    """
    group = await crud.get_group_by_id(session, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Групу з ID {group_id} не знайдено"
        )

    members = await crud.get_group_members(session, group_id)
    return members


@router.delete("/groups/{group_id}", status_code=status.HTTP_200_OK)
async def delete_group(
    group_id: int,
    tg_id: int,
    session: AsyncSession = Depends(get_session)
):
    """
    Delete a group. Only the creator can delete the group.

    """
    group = await crud.get_group_by_id(session, group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Групу з ID {group_id} не знайдено"
        )

    user = await crud.get_user_by_tg_id(session, tg_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Користувача з ID {tg_id} не знайдено"
        )

    if group.creator_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Тільки творець може видалити цю групу"
        )

    success = await crud.delete_group(session, group_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Видалення групи не вдалось"
        )

    return {"message": f"Група {group_id} видалена успішно"}
