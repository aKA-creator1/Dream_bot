from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.config import ADMIN_IDS
from bot.database import (
    is_admin, set_premium, get_user, get_all_users, get_premium_users,
    get_user_count, get_premium_count, search_user, create_promo,
    use_promo, get_all_promos
)

router = Router()


def admin_only(func):
    async def wrapper(event: Message | CallbackQuery, **kwargs):
        user_id = event.from_user.id
        if not await is_admin(user_id):
            text = "Нет доступа"
            if isinstance(event, Message):
                await event.answer(text)
            else:
                await event.answer(text, show_alert=True)
            return
        return await func(event, **kwargs)
    return wrapper


class AdminStates(StatesGroup):
    waiting_user_id = State()
    waiting_premium_days = State()
    waiting_promo_code = State()
    waiting_promo_days = State()
    waiting_promo_uses = State()
    waiting_broadcast = State()
    waiting_search = State()


@router.message(F.text == "/admin")
@admin_only
async def cmd_admin(message: Message):
    user_count = await get_user_count()
    premium_count = await get_premium_count()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Пользователи ({user_count})", callback_data="admin_users")],
        [InlineKeyboardButton(text=f"Premium ({premium_count})", callback_data="admin_premium")],
        [InlineKeyboardButton(text="Выдать Premium", callback_data="admin_give_premium")],
        [InlineKeyboardButton(text="Промокоды", callback_data="admin_promos")],
        [InlineKeyboardButton(text="Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="Поиск пользователя", callback_data="admin_search")],
    ])

    await message.answer(
        "<b>Админ-панель</b>\n\n"
        f"Пользователей: {user_count}\n"
        f"Premium: {premium_count}\n\n"
        "Выбери действие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_give_premium")
@admin_only
async def admin_give_premium(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите Telegram ID пользователя\n"
        "или @username для выдачи Premium:\n\n"
        "Для возврата нажми /admin"
    )
    await callback.answer()
    await state.set_state(AdminStates.waiting_user_id)


@router.message(AdminStates.waiting_user_id)
@admin_only
async def process_user_id(message: Message, state: FSMContext):
    text = message.text.strip()

    if text.startswith("@"):
        users = await search_user(text[1:])
        if not users:
            await message.answer("Пользователь не найден. Попробуйте другой запрос:")
            return
        if len(users) > 1:
            result = "Найдено несколько пользователей:\n\n"
            for u in users[:10]:
                result += f"ID: {u['user_id']} | {u['first_name'] or '---'} | @{u['username'] or '---'}\n"
            result += "\nВведите точный ID:"
            await message.answer(result)
            return
        user_id = users[0]["user_id"]
    else:
        try:
            user_id = int(text)
        except ValueError:
            await message.answer("Введите число (Telegram ID) или @username:")
            return

    user = await get_user(user_id)
    if not user:
        await message.answer("Пользователь не найден в базе. Попробуйте другой ID:")
        return

    await state.update_data(target_user=user_id)
    prem_status = "Premium" if user["is_premium"] else "Обычный"
    await message.answer(
        f"Пользователь: {user['first_name'] or '---'} (@{user['username'] or '---'})\n"
        f"ID: {user_id}\n"
        f"Текущий статус: {prem_status}\n\n"
        "На сколько дней выдать Premium?\n"
        "Введите количество дней или 'навсегда':"
    )
    await state.set_state(AdminStates.waiting_premium_days)


@router.message(AdminStates.waiting_premium_days)
@admin_only
async def process_premium_days(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data["target_user"]

    text = message.text.strip().lower()
    if text in ("навсегда", "forever", "бессрочно"):
        days = 36500
    else:
        try:
            days = int(text)
        except ValueError:
            await message.answer("Введите число дней или 'навсегда':")
            return

    await set_premium(user_id, True)

    user = await get_user(user_id)
    await message.answer(
        f"Premium выдан!\n\n"
        f"Пользователь: {user['first_name'] or '---'} (@{user['username'] or '---'})\n"
        f"ID: {user_id}\n"
        f"Срок: {days} дней"
    )

    try:
        from aiogram import Bot
        from bot.config import BOT_TOKEN
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(
            user_id,
            "У тебя Premium!\n\n"
            "Тебе выдана Premium-подписка.\n"
            "Теперь у тебя:\n"
            "- Без рекламы\n"
            "- Расширенная статистика\n"
            "- Эксклюзивные темы\n"
            "- Экспорт данных\n"
            "- Приоритетная поддержка\n\n"
            "Спасибо за использование DreamTracker!"
        )
    except Exception:
        pass

    await state.clear()


@router.callback_query(F.data == "admin_promos")
@admin_only
async def admin_promos(callback: CallbackQuery):
    promos = await get_all_promos()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Создать промокод", callback_data="admin_create_promo")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_back")],
    ])

    if promos:
        text = "<b>Промокоды:</b>\n\n"
        for p in promos:
            text += (
                f"<code>{p['code']}</code>\n"
                f"   Дней: {p['days']} | Использований: {p['used_uses']}/{p['total_uses']}\n\n"
            )
    else:
        text = "Промокодов пока нет"

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_create_promo")
@admin_only
async def admin_create_promo(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите код промокода (латиница, без пробелов):\n\n"
        "Например: DREAM2024, START, FREE30"
    )
    await callback.answer()
    await state.set_state(AdminStates.waiting_promo_code)


@router.message(AdminStates.waiting_promo_code)
@admin_only
async def process_promo_code(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    if len(code) < 3 or len(code) > 20:
        await message.answer("Код должен быть от 3 до 20 символов:")
        return
    await state.update_data(promo_code=code)
    await message.answer("На сколько дней действует промокод?")
    await state.set_state(AdminStates.waiting_promo_days)


@router.message(AdminStates.waiting_promo_days)
@admin_only
async def process_promo_days(message: Message, state: FSMContext):
    try:
        days = int(message.text.strip())
    except ValueError:
        await message.answer("Введите число дней:")
        return
    await state.update_data(promo_days=days)
    await message.answer("Сколько раз можно использовать промокод?")
    await state.set_state(AdminStates.waiting_promo_uses)


@router.message(AdminStates.waiting_promo_uses)
@admin_only
async def process_promo_uses(message: Message, state: FSMContext):
    try:
        uses = int(message.text.strip())
    except ValueError:
        await message.answer("Введите количество использований:")
        return

    data = await state.get_data()
    await create_promo(data["promo_code"], data["promo_days"], uses)

    await message.answer(
        f"Промокод создан!\n\n"
        f"Код: <code>{data['promo_code']}</code>\n"
        f"Дней: {data['promo_days']}\n"
        f"Использований: {uses}\n\n"
        f"Раздай пользователям, они активируют через /promo",
        parse_mode="HTML"
    )
    await state.clear()


@router.callback_query(F.data == "admin_users")
@admin_only
async def admin_users(callback: CallbackQuery):
    users = await get_all_users()
    text = f"<b>Все пользователи ({len(users)}):</b>\n\n"
    for u in users[:20]:
        prem = " [PREMIUM]" if u["is_premium"] else ""
        text += f"ID: <code>{u['user_id']}</code> | {u['first_name'] or '---'} | @{u['username'] or '---'}{prem}\n"

    if len(users) > 20:
        text += f"\n... и ещё {len(users) - 20}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="admin_back")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_premium")
@admin_only
async def admin_premium_list(callback: CallbackQuery):
    users = await get_premium_users()
    if users:
        text = f"<b>Premium пользователи ({len(users)}):</b>\n\n"
        for u in users:
            text += f"ID: <code>{u['user_id']}</code> | {u['first_name'] or '---'} | @{u['username'] or '---'}\n"
    else:
        text = "Premium пользователей пока нет"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад", callback_data="admin_back")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_search")
@admin_only
async def admin_search(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите Telegram ID или @username для поиска:"
    )
    await callback.answer()
    await state.set_state(AdminStates.waiting_search)


@router.message(AdminStates.waiting_search)
@admin_only
async def process_search(message: Message, state: FSMContext):
    query = message.text.strip()
    users = await search_user(query)

    if not users:
        await message.answer("Пользователи не найдены")
    else:
        text = f"<b>Результаты поиска ({len(users)}):</b>\n\n"
        for u in users[:10]:
            prem = " [Premium]" if u["is_premium"] else ""
            text += (
                f"ID: <code>{u['user_id']}</code>\n"
                f"Имя: {u['first_name'] or '---'}\n"
                f"Username: @{u['username'] or '---'}\n"
                f"Статус: {prem or 'Обычный'}\n"
                f"Зарегистрирован: {u['created_at']}\n\n"
            )
    await state.clear()


@router.callback_query(F.data == "admin_broadcast")
@admin_only
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите текст рассылки:\n\n"
        "Все пользователи получат это сообщение.\n"
        "Для отмены: /cancel"
    )
    await callback.answer()
    await state.set_state(AdminStates.waiting_broadcast)


@router.message(AdminStates.waiting_broadcast)
@admin_only
async def process_broadcast(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await message.answer("Рассылка отменена")
        await state.clear()
        return

    users = await get_all_users()
    sent = 0
    failed = 0

    from aiogram import Bot
    from bot.config import BOT_TOKEN
    bot = Bot(token=BOT_TOKEN)

    for user in users:
        try:
            await bot.send_message(user["user_id"], message.text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1

    await message.answer(
        f"Рассылка завершена!\n\n"
        f"Отправлено: {sent}\n"
        f"Ошибок: {failed}"
    )
    await state.clear()


@router.callback_query(F.data == "admin_back")
@admin_only
async def admin_back(callback: CallbackQuery):
    user_count = await get_user_count()
    premium_count = await get_premium_count()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Пользователи ({user_count})", callback_data="admin_users")],
        [InlineKeyboardButton(text=f"Premium ({premium_count})", callback_data="admin_premium")],
        [InlineKeyboardButton(text="Выдать Premium", callback_data="admin_give_premium")],
        [InlineKeyboardButton(text="Промокоды", callback_data="admin_promos")],
        [InlineKeyboardButton(text="Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="Поиск пользователя", callback_data="admin_search")],
    ])

    await callback.message.edit_text(
        "<b>Админ-панель</b>\n\n"
        f"Пользователей: {user_count}\n"
        f"Premium: {premium_count}\n\n"
        "Выбери действие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()
