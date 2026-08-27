from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from bot.database import create_user, get_active_goal, use_promo, set_premium, get_user
from bot.config import WEBAPP_URL

router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message):
    await create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    goal = await get_active_goal(message.from_user.id)

    webapp_url = f"{WEBAPP_URL}?user_id={message.from_user.id}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Открыть панель",
            web_app=WebAppInfo(url=webapp_url)
        )],
        [InlineKeyboardButton(
            text="Новая цель",
            callback_data="new_goal"
        )],
    ])

    if goal:
        progress = (goal["current_value"] / goal["target_value"] * 100) if goal["target_value"] else 0
        target_str = f"{goal['target_value']:.0f}" if goal["target_value"] else "---"
        current_str = f"{goal['current_value']:.0f}" if goal["current_value"] else "0"
        await message.answer(
            f"С возвращением, {message.from_user.first_name}\n\n"
            f"Твоя текущая цель:\n"
            f"<b>{goal['title']}</b>\n\n"
            f"Прогресс: {progress:.1f}%\n"
            f"Собрано: {current_str} / {target_str} {goal['unit']}\n\n"
            f"Открой панель управления для подробной статистики",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"Привет, {message.from_user.first_name}\n\n"
            f"Я помогу тебе достичь твоей мечты.\n"
            f"Поставь цель, и я каждый день буду напоминать о ней.\n\n"
            f"Каждый вечер ты сможешь отметить свой прогресс\n"
            f"и увидишь, как близко ты к своей мечте.\n\n"
            f"Начни с того, что поставь первую цель",
            reply_markup=keyboard,
            parse_mode="HTML"
        )


@router.message(F.text == "/help")
async def cmd_help(message: Message):
    await message.answer(
        "<b>Как пользоваться ботом:</b>\n\n"
        "1. Поставь цель - напиши что ты хочешь достичь\n"
        "2. Каждый день я буду напоминать о твоей цели\n"
        "3. Вечером отмечай сколько ты сделал за день\n"
        "4. Ставь желания на завтра\n\n"
        "<b>Команды:</b>\n"
        "/start - Начать\n"
        "/goal - Моя цель\n"
        "/stats - Статистика\n"
        "/wish - Загадать желание\n"
        "/thought - Записать мысль\n"
        "/panel - Открыть панель\n"
        "/promo - Активировать промокод",
        parse_mode="HTML"
    )


@router.message(F.text == "/panel")
async def cmd_panel(message: Message):
    webapp_url = f"{WEBAPP_URL}?user_id={message.from_user.id}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Открыть панель",
            web_app=WebAppInfo(url=webapp_url)
        )]
    ])
    await message.answer(
        "Панель управления откроется в браузере",
        reply_markup=keyboard
    )


@router.message(F.text == "/promo")
async def cmd_promo(message: Message):
    await message.answer(
        "Введите промокод:\n\n"
        "Промокод можно получить от администратора\n"
        "или в рамках акции"
    )


@router.message(F.text.regexp(r"^[A-Za-z0-9]{3,20}$"))
async def try_promo(message: Message):
    user = await get_user(message.from_user.id)
    if user and user["is_premium"]:
        await message.answer("У тебя уже есть Premium!")
        return

    promo, error = await use_promo(message.text.strip().upper())
    if error:
        return

    await set_premium(message.from_user.id, True)
    await message.answer(
        "Промокод активирован!\n\n"
        "Тебе выдана Premium-подписка.\n"
        "Теперь у тебя:\n"
        "- Без рекламы\n"
        "- Расширенная статистика\n"
        "- Эксклюзивные темы\n"
        "- Экспорт данных\n\n"
        "Спасибо за использование DreamTracker!",
        parse_mode="HTML"
    )
