from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from sqlalchemy import select

from db.database import async_session_maker
from db import crud
from db.models import Task
from api.schemas import UserCreate
from core.config import settings

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Handle /start command. Register new users or greet existing ones.

    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Відкрити Трекер 🚀",
                    web_app=WebAppInfo(url=settings.WEBAPP_URL)
                )
            ]
        ]
    )

    async with async_session_maker() as session:
        user = await crud.get_user_by_tg_id(session, message.from_user.id)

        if not user:
            user_data = UserCreate(
                tg_id=message.from_user.id,
                full_name=message.from_user.full_name,
                username=message.from_user.username
            )
            user = await crud.create_user(session, user_data)

        command_args = message.text.split(maxsplit=1)
        if len(command_args) > 1:
            deep_link_arg = command_args[1]

            if deep_link_arg.startswith("file_"):
                try:
                    task_id = int(deep_link_arg.replace("file_", ""))

                    stmt = select(Task).where(Task.id == task_id)
                    result = await session.execute(stmt)
                    task = result.scalar_one_or_none()

                    if not task:
                        await message.answer(
                            f"❌ Завдання з ID {task_id} не знайдено.\n\n"
                            f"Можливо, воно було видалено."
                        )
                        return

                    if task.creator_id != user.id:
                        await message.answer(
                            "❌ Ви можете отримувати файли тільки зі своїх завдань."
                        )
                        return

                    if not task.telegram_file_id:
                        await message.answer(
                            f"❌ До завдання '{task.title}' не прикріплено файл."
                        )
                        return

                    caption = f"📁 Файл до завдання: {task.title}"

                    try:
                        await message.answer_document(
                            task.telegram_file_id,
                            caption=caption
                        )
                    except Exception:
                        try:
                            await message.answer_photo(
                                task.telegram_file_id,
                                caption=caption
                            )
                        except Exception as e:
                            await message.answer(
                                f"❌ Не вдалося надіслати файл.\n\n"
                                f"Можливо, файл застарів або був видалений з серверів Telegram.\n\n"
                                f"Спробуйте прикріпити файл заново командою:\n"
                                f"#file_{task.id}"
                            )
                            return

                    await message.answer(
                        "✅ Файл успішно надіслано!\n\n"
                        "Натисніть кнопку нижче, щоб повернутися до трекера 👇",
                        reply_markup=keyboard
                    )

                except ValueError:
                    await message.answer(
                        "❌ Невірний формат посилання на файл."
                    )
                return

            if deep_link_arg.startswith("group_"):
                group_hex_id = deep_link_arg
                invite_link = f"https://t.me/{settings.BOT_USERNAME}?start={group_hex_id}"

                group = await crud.get_group_by_invite_link(session, invite_link)

                if group:
                    success = await crud.add_user_to_group(session, user.id, group.id)

                    if success:
                        await message.answer(
                            f"✅ Успіх! Ви приєдналися до групи '{group.name}'!\n\n"
                            f"Тепер ви можете переглядати завдання групи та співпрацювати з іншими учасниками.\n\n"
                            f"Натисніть кнопку нижче, щоб відкрити трекер завдань! 👇",
                            reply_markup=keyboard
                        )
                    else:
                        await message.answer(
                            f"ℹ️ Ви вже є учасником групи '{group.name}'!\n\n"
                            f"Натисніть кнопку нижче, щоб відкрити трекер завдань! 👇",
                            reply_markup=keyboard
                        )
                else:
                    await message.answer(
                        f"❌ Посилання для запрошення недійсне або група була видалена.\n\n"
                        f"Натисніть кнопку нижче, щоб відкрити трекер завдань! 👇",
                        reply_markup=keyboard
                    )
                return

        if user.xp == 0:
            await message.answer(
                f"👋 Вітаю, {user.full_name}!\n\n"
                f"Ви успішно зареєстровані в системі відстеження навчальних завдань.\n"
                f"Ваш XP: {user.xp}\n\n"
                f"Натисніть кнопку нижче, щоб відкрити трекер завдань! 👇",
                reply_markup=keyboard
            )
        else:
            await message.answer(
                f"👋 З поверненням, {user.full_name}!\n\n"
                f"Ваш поточний XP: {user.xp}\n\n"
                f"Натисніть кнопку нижче, щоб відкрити трекер завдань! 👇",
                reply_markup=keyboard
            )


@router.message(Command("my_tasks"))
async def cmd_my_tasks(message: types.Message):
    """
    Handle /my_tasks command. Display all tasks for the user.

    """
    async with async_session_maker() as session:
        user = await crud.get_user_by_tg_id(session, message.from_user.id)

        if not user:
            await message.answer(
                "❌ Ви ще не зареєстровані в системі.\n"
                "Натисніть /start для реєстрації."
            )
            return

        tasks = await crud.get_user_tasks(session, user.id)

        if not tasks:
            await message.answer(
                "✅ У вас немає активних завдань!\n"
                "Ви впоралися з усім. Чудова робота! 🎉"
            )
            return

        task_list = ["📋 Ваші завдання:\n"]

        for idx, task in enumerate(tasks, start=1):
            deadline_str = task.deadline.strftime("%d.%m.%Y %H:%M")

            status_emoji = {
                "to_do": "⏳",
                "in_progress": "🔄",
                "done": "✅"
            }.get(task.status.value, "❓")

            task_info = (
                f"\n{idx}. {status_emoji} {task.title}\n"
                f"   📝 {task.description or 'Без опису'}\n"
                f"   ⏰ Дедлайн: {deadline_str}\n"
                f"   Статус: {task.status.value}\n"
                f"   ID: {task.id}"
            )

            if task.telegram_file_id:
                task_info += f"\n   📎 Отримати файл: /start file_{task.id}"

            task_list.append(task_info)

        await message.answer("".join(task_list))


@router.message(Command("create_group"))
async def cmd_create_group(message: types.Message):
    """
    Handle /create_group command. Create a new study group.

    Usage: /create_group [group_name]

    """
    async with async_session_maker() as session:
        user = await crud.get_user_by_tg_id(session, message.from_user.id)

        if not user:
            await message.answer(
                "❌ Ви ще не зареєстровані в системі.\n"
                "Натисніть /start для реєстрації."
            )
            return

        command_parts = message.text.split(maxsplit=1)
        if len(command_parts) < 2:
            await message.answer(
                "❌ Будь ласка, вкажіть назву групи.\n\n"
                "Використання: /create_group [назва групи]\n"
                "Приклад: /create_group Python Study Group"
            )
            return

        group_name = command_parts[1].strip()

        if not group_name:
            await message.answer("❌ Назва групи не може бути порожньою.")
            return

        try:
            group = await crud.create_group(session, group_name, user.id)

            await message.answer(
                f"✅ Група '{group.name}' успішно створена!\n\n"
                f"🔗 Посилання для запрошення:\n{group.invite_link}\n\n"
                f"ID групи: {group.id}\n\n"
                f"Для додавання користувачів використовуйте:\n"
                f"/add_friend {group.id} [telegram_id]"
            )
        except Exception as e:
            await message.answer(f"❌ Помилка при створенні групи: {str(e)}")


@router.message(Command("add_friend"))
async def cmd_add_friend(message: types.Message):
    """
    Handle /add_friend command. Add a user to a group.

    Usage: /add_friend [group_id] [friend_telegram_id]

    """
    async with async_session_maker() as session:
        user = await crud.get_user_by_tg_id(session, message.from_user.id)

        if not user:
            await message.answer(
                "❌ Ви ще не зареєстровані в системі.\n"
                "Натисніть /start для реєстрації."
            )
            return

        command_parts = message.text.split()
        if len(command_parts) < 3:
            await message.answer(
                "❌ Недостатньо аргументів.\n\n"
                "Використання: /add_friend [group_id] [telegram_id]\n"
                "Приклад: /add_friend 1 123456789"
            )
            return

        try:
            group_id = int(command_parts[1])
            friend_tg_id = int(command_parts[2])
        except ValueError:
            await message.answer("❌ ID групи та Telegram ID мають бути числами.")
            return

        group = await crud.get_group_by_id(session, group_id)
        if not group:
            await message.answer(f"❌ Група з ID {group_id} не знайдена.")
            return

        friend = await crud.get_user_by_tg_id(session, friend_tg_id)
        if not friend:
            await message.answer(
                f"❌ Користувач з Telegram ID {friend_tg_id} не знайдений.\n"
                f"Попросіть їх спочатку натиснути /start у боті."
            )
            return

        success = await crud.add_user_to_group(session, friend.id, group_id)

        if success:
            await message.answer(
                f"✅ Користувача {friend.full_name} (@{friend.username or 'немає username'}) "
                f"успішно додано до групи '{group.name}'!"
            )
        else:
            await message.answer("❌ Не вдалося додати користувача до групи.")


@router.message(F.document | F.photo)
async def handle_file(message: types.Message):
    """
    Handle file and photo uploads from users.

    """
    async with async_session_maker() as session:
        user = await crud.get_user_by_tg_id(session, message.from_user.id)

        if not user:
            await message.answer(
                "❌ Ви ще не зареєстровані в системі.\n"
                "Натисніть /start для реєстрації."
            )
            return

        if not message.caption or not message.caption.startswith("#file_"):
            await message.answer(
                "❌ Для прикріплення файлу або фото до завдання додайте підпис:\n"
                "#file_[ID завдання]\n\n"
                "Приклад: #file_5\n\n"
                "Дізнатися ID завдання можна командою /my_tasks"
            )
            return

        try:
            task_id = int(message.caption.replace("#file_", "").strip())
        except ValueError:
            await message.answer("❌ Невірний формат ID завдання.")
            return

        stmt = select(Task).where(Task.id == task_id)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()

        if not task:
            await message.answer(f"❌ Завдання з ID {task_id} не знайдено.")
            return

        if task.creator_id != user.id:
            await message.answer("❌ Ви можете прикріплювати файли тільки до своїх завдань.")
            return

        if message.document:
            file_id = message.document.file_id
            file_name = message.document.file_name or "Файл"
        else:
            file_id = message.photo[-1].file_id
            file_name = "Фотографію"

        task.telegram_file_id = file_id
        await session.commit()

        await message.answer(
            f"✅ {file_name} успішно прикріплено до завдання:\n"
            f"📋 {task.title}\n\n"
            f"Тепер ви можете завантажити його через /my_tasks або Mini App."
        )
