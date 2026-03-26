from datetime import datetime, timedelta, timezone
from aiogram import Bot
from sqlalchemy import select, and_

from db.database import async_session_maker
from db.models import Task, TaskStatus, User


async def check_deadlines(bot: Bot):
    """
    Background job that checks for upcoming task deadlines and sends reminders.

    Runs every hour and sends reminders for tasks due in:
    - 7 days
    - 3 days
    - 1 day

    """
    async with async_session_maker() as session:
        now = datetime.now(timezone.utc)

        reminder_windows = [7, 3, 1]

        for days_until_deadline in reminder_windows:
            target_time = now + timedelta(days=days_until_deadline)
            window_start = target_time - timedelta(hours=0.5)
            window_end = target_time + timedelta(hours=0.5)

            one_hour_ago = now - timedelta(hours=1)

            stmt = select(Task).join(User, Task.creator_id == User.id).where(
                and_(
                    Task.status != TaskStatus.DONE,
                    Task.deadline >= window_start,
                    Task.deadline <= window_end,
                    (Task.last_reminder_sent.is_(None) | (Task.last_reminder_sent < one_hour_ago))
                )
            )

            result = await session.execute(stmt)
            tasks = result.scalars().all()

            for task in tasks:
                try:
                    creator = await session.get(User, task.creator_id)
                    if not creator:
                        continue

                    deadline_str = task.deadline.strftime("%d.%m.%Y %H:%M")

                    if days_until_deadline == 7:
                        urgency = "🟡"
                        time_text = "7 днів"
                    elif days_until_deadline == 3:
                        urgency = "🟠"
                        time_text = "3 дні"
                    else:  # 1 day
                        urgency = "🔴"
                        time_text = "1 день"

                    message = (
                        f"{urgency} <b>Нагадування про дедлайн!</b>\n\n"
                        f"📋 Завдання: <b>{task.title}</b>\n"
                        f"⏰ Дедлайн: <code>{deadline_str}</code>\n"
                        f"⚠️ Залишилось: <b>{time_text}</b>\n\n"
                    )

                    if task.description:
                        message += f"📝 Опис: {task.description}\n\n"

                    message += f"ID завдання: <code>{task.id}</code>"

                    await bot.send_message(
                        chat_id=creator.tg_id,
                        text=message,
                        parse_mode="HTML"
                    )

                    task.last_reminder_sent = now
                    await session.commit()

                    print(f"✅ Sent {days_until_deadline}-day reminder for task {task.id} to user {creator.tg_id}")

                except Exception as e:
                    print(f"❌ Error sending reminder for task {task.id}: {str(e)}")
                    continue
