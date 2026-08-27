from aiogram import Router, F
from aiogram.types import Message
from bot.database import get_user_stats, get_logs_for_goal, get_active_goal

router = Router()


@router.message(F.text == "/stats")
async def cmd_stats(message: Message):
    stats = await get_user_stats(message.from_user.id)
    if not stats or not stats["goal"]:
        await message.answer("Сначала создай цель через /goal")
        return

    goal = stats["goal"]
    target = goal["target_value"] or 0
    current = goal["current_value"] or 0
    progress = (current / target * 100) if target > 0 else 0

    days_left = ""
    if goal.get("deadline"):
        from datetime import datetime, date
        try:
            dl = datetime.strptime(goal["deadline"], "%Y-%m-%d").date()
            diff = (dl - date.today()).days
            days_left = f"\nОсталось дней: {diff}"
            if diff > 0 and target > 0:
                per_day = (target - current) / diff
                days_left += f"\nНужно в день: {per_day:.0f} {goal['unit']}"
        except ValueError:
            pass

    bar_filled = int(progress / 5)
    bar_empty = 20 - bar_filled
    bar = "#" * bar_filled + "-" * bar_empty

    streak = stats["streak"]
    streak_text = (
        f"\nСерия дней: {streak.get('current_streak', 0)}\n"
        f"Лучшая серия: {streak.get('best_streak', 0)}"
    )

    target_str = f"{target:.0f}" if target else "0"
    await message.answer(
        f"<b>Статистика</b>\n\n"
        f"Цель: {goal['title']}\n\n"
        f"Прогресс: [{bar}] {progress:.1f}%\n"
        f"Собрано: {current:.0f} / {target_str} {goal['unit']}\n"
        f"Активных дней: {stats['active_days']}"
        f"{streak_text}{days_left}\n\n"
        f"Продолжай идти к своей мечте!",
        parse_mode="HTML"
    )


@router.message(F.text == "/logs")
async def cmd_logs(message: Message):
    goal = await get_active_goal(message.from_user.id)
    if not goal:
        await message.answer("Нет активной цели")
        return

    logs = await get_logs_for_goal(goal["id"], limit=10)
    if not logs:
        await message.answer("Пока нет записей. Отметь прогресс через /checkin")
        return

    text = "<b>Последние записи:</b>\n\n"

    for log in logs:
        note = f"\n   {log['note']}" if log["note"] else ""
        text += f"{log['log_date']}\n"
        text += f"   {log['earned']:.0f} {goal['unit']} (настроение: {log['mood']}/10){note}\n\n"

    await message.answer(text, parse_mode="HTML")
