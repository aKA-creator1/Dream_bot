from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.database import get_active_goal, add_daily_log, add_wish, add_thought, get_streak

router = Router()


class CheckinStates(StatesGroup):
    waiting_earned = State()
    waiting_note = State()
    waiting_mood = State()
    waiting_wish = State()
    waiting_thought = State()


@router.message(F.text == "/checkin")
@router.callback_query(F.data == "checkin")
async def start_checkin(event: Message | CallbackQuery, state: FSMContext):
    uid = event.from_user.id
    goal = await get_active_goal(uid)
    if not goal:
        text = "У тебя нет активной цели. Сначала создай её через /goal"
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(text)
            await event.answer()
        else:
            await event.answer(text)
        return

    text = (
        f"Отметь свой прогресс за сегодня\n\n"
        f"Цель: <b>{goal['title']}</b>\n"
        f"Текущий прогресс: {goal['current_value'] or 0:.0f} / {goal['target_value'] or 0:.0f} {goal['unit']}\n\n"
        f"Сколько ты сделал сегодня?"
    )
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")
    await state.set_state(CheckinStates.waiting_earned)


@router.message(CheckinStates.waiting_earned)
async def process_earned(message: Message, state: FSMContext):
    try:
        earned = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введи число. Например: 5000")
        return
    await state.update_data(earned=earned)
    await message.answer(
        "Хочешь оставить заметку к этому дню?\n"
        "Напиши что было, что получилось, что нет\n"
        "Или напиши '-' чтобы пропустить"
    )
    await state.set_state(CheckinStates.waiting_note)


@router.message(CheckinStates.waiting_note)
async def process_note(message: Message, state: FSMContext):
    note = message.text if message.text != "-" else None
    await state.update_data(note=note)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1", callback_data="mood_1"),
         InlineKeyboardButton(text="2", callback_data="mood_2"),
         InlineKeyboardButton(text="3", callback_data="mood_3"),
         InlineKeyboardButton(text="4", callback_data="mood_4"),
         InlineKeyboardButton(text="5", callback_data="mood_5")],
        [InlineKeyboardButton(text="6", callback_data="mood_6"),
         InlineKeyboardButton(text="7", callback_data="mood_7"),
         InlineKeyboardButton(text="8", callback_data="mood_8"),
         InlineKeyboardButton(text="9", callback_data="mood_9"),
         InlineKeyboardButton(text="10", callback_data="mood_10")],
    ])
    await message.answer("Какое у тебя сегодня настроение? (1-10)", reply_markup=keyboard)
    await state.set_state(CheckinStates.waiting_mood)


@router.callback_query(F.data.startswith("mood_"))
async def process_mood(callback: CallbackQuery, state: FSMContext):
    mood = int(callback.data.replace("mood_", ""))
    data = await state.get_data()
    goal = await get_active_goal(callback.from_user.id)

    if not goal:
        await callback.message.edit_text("Цель не найдена")
        await callback.answer()
        await state.clear()
        return

    await add_daily_log(
        user_id=callback.from_user.id,
        goal_id=goal["id"],
        earned=data["earned"],
        note=data.get("note"),
        mood=mood
    )

    streak = await get_streak(callback.from_user.id)
    new_progress = (goal["current_value"] or 0) + data["earned"]
    target = goal["target_value"] or 0
    progress_pct = (new_progress / target * 100) if target > 0 else 0

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Загадать желание", callback_data="make_wish")],
        [InlineKeyboardButton(text="Записать мысль", callback_data="make_thought")],
    ])

    motivation = ""
    if progress_pct >= 100:
        motivation = "\nТЫ СДЕЛАЛ ЭТО! ЦЕЛЬ ДОСТИГНУТА!"
    elif progress_pct >= 75:
        motivation = "\nПочти рядом! Осталось совсем немного"
    elif progress_pct >= 50:
        motivation = "\nСередина пути! Продолжай в том же духе"
    elif progress_pct >= 25:
        motivation = "\nХорошее начало! Ты на правильном пути"

    streak_text = ""
    if streak and streak["current_streak"] > 1:
        streak_text = f"\nСерия дней: {streak['current_streak']}"

    target_str = f"{target:.0f}" if target else "---"
    await callback.message.edit_text(
        f"Прогресс записан!\n\n"
        f"Заработано сегодня: {data['earned']:.0f} {goal['unit']}\n"
        f"Общий прогресс: {new_progress:.0f} / {target_str} {goal['unit']} ({progress_pct:.1f}%){streak_text}{motivation}\n\n"
        f"Загадай желание на завтра или запиши мысли",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()
    await state.clear()


@router.message(F.text == "/wish")
@router.callback_query(F.data == "make_wish")
async def start_wish(event: Message | CallbackQuery, state: FSMContext):
    text = "Загадай желание на завтра\n\nО чем ты мечтаешь? Чего хочешь достичь завтра?"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text)
        await event.answer()
    else:
        await event.answer(text)
    await state.set_state(CheckinStates.waiting_wish)


@router.message(CheckinStates.waiting_wish)
async def process_wish(message: Message, state: FSMContext):
    await add_wish(message.from_user.id, message.text)
    await message.answer(
        "Желание записано!\n\n"
        "Завтра я напомню тебе о нём.\n"
        "Верь в себя и действуй",
        parse_mode="HTML"
    )
    await state.clear()


@router.message(F.text == "/thought")
@router.callback_query(F.data == "make_thought")
async def start_thought(event: Message | CallbackQuery, state: FSMContext):
    text = "Запиши свою мысль\n\nЧто ты думаешь о своём пути? Какие идеи приходят?"
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text)
        await event.answer()
    else:
        await event.answer(text)
    await state.set_state(CheckinStates.waiting_thought)


@router.message(CheckinStates.waiting_thought)
async def process_thought(message: Message, state: FSMContext):
    await add_thought(message.from_user.id, message.text)
    await message.answer(
        "Мысль сохранена!\n\n"
        "Иногда одна мысль меняет весь путь.\n"
        "Продолжай думать и действовать",
        parse_mode="HTML"
    )
    await state.clear()
