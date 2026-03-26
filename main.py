import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
from aiogram import Bot, Dispatcher

from api.routes import router
from bot.handlers import router as bot_router
from bot.reminders import check_deadlines
from core.config import settings


async def reminder_loop(bot: Bot):
    while True:
        try:
            await check_deadlines(bot)
        except Exception as e:
            print(f"❌ Error in reminder loop: {str(e)}")
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):

    bot = Bot(token=settings.BOT_TOKEN)

    dp = Dispatcher()
    dp.include_router(bot_router)

    polling_task = asyncio.create_task(dp.start_polling(bot))

    reminder_task = asyncio.create_task(reminder_loop(bot))

    yield

    if not reminder_task.done():
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
    print("🛑 Reminder loop stopped")

    await dp.stop_polling()
    await bot.session.close()

    if not polling_task.done():
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass

    print("🛑 Telegram bot stopped gracefully")
    print("🛑 FastAPI server shutting down")

app = FastAPI(
    title="Study Tracker API",
    description="API for tracking study tasks with Telegram bot integration",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(router, prefix="/api", tags=["users", "tasks"])


@app.get("/")
async def root():
    return {"message": "Система працює", "status": "ok"}


@app.get("/webapp", response_class=HTMLResponse)
async def webapp():

    html_path = Path(__file__).parent / "templates" / "index.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return html_content


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)