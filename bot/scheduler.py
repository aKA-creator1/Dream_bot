import random
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from bot.database import get_all_active_users, get_active_goal
from bot.config import REMINDER_HOUR, REMINDER_MINUTE

scheduler = AsyncIOScheduler()


async def send_daily_reminder(bot: Bot, user_id: int):
    try:
        goal = await get_active_goal(user_id)
        if not goal:
            return

        progress = (goal["current_value"] / goal["target_value"] * 100) if goal["target_value"] else 0

        reminders = [
            f"День не пройдет даром!\n\nТвоя цель: {goal['title']}\nПрогресс: {progress:.1f}%\n\nЧто ты сделал сегодня для своей мечты?",
            f"Каждый день — шаг к цели\n\n{goal['title']}\nПрогресс: {progress:.1f}%\n\nНе забудь отметить свой прогресс вечером",
            f"Ты помнишь о своей мечте?\n\n{goal['title']}\nПрогресс: {progress:.1f}%\n\nПродолжай идти. Я верю в тебя",
            f"Время работает на тебя\n\nЦель: {goal['title']}\nПрогресс: {progress:.1f}%\n\nСделай сегодня хотя бы один шаг",
            f"Утро — время действовать\n\n{goal['title']}\nПрогресс: {progress:.1f}%\n\nТы ближе чем вчера",
        ]

        text = random.choice(reminders)

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отметить прогресс", callback_data="checkin")]
        ])

        await bot.send_message(user_id, text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        pass


async def send_evening_reminder(bot: Bot, user_id: int):
    try:
        goal = await get_active_goal(user_id)
        if not goal:
            return

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отметить прогресс", callback_data="checkin")],
            [InlineKeyboardButton(text="Загадать желание", callback_data="make_wish")],
        ])

        await bot.send_message(
            user_id,
            "Вечернее напоминание\n\n"
            "Как прошёл твой день?\n"
            "Отметь свой прогресс и загадай желание на завтра",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception:
        pass


async def check_all_users(bot: Bot):
    users = await get_all_active_users()
    for user in users:
        await send_daily_reminder(bot, user["user_id"])


async def check_evening(bot: Bot):
    users = await get_all_active_users()
    for user in users:
        await send_evening_reminder(bot, user["user_id"])


def setup_scheduler(bot: Bot):
    morning_hour = REMINDER_HOUR
    morning_minute = (REMINDER_MINUTE - 30) % 60
    if REMINDER_MINUTE >= 30:
        morning_hour = (REMINDER_HOUR - 1) % 24

    scheduler.add_job(
        check_all_users,
        CronTrigger(hour=morning_hour, minute=morning_minute),
        args=[bot],
        id="morning_reminder",
        replace_existing=True
    )
    scheduler.add_job(
        check_evening,
        CronTrigger(hour=REMINDER_HOUR, minute=REMINDER_MINUTE),
        args=[bot],
        id="evening_reminder",
        replace_existing=True
    )
    scheduler.start()
