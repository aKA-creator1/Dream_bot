from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.database import create_goal, get_active_goal, get_all_goals

router = Router()


class GoalStates(StatesGroup):
    waiting_title = State()
    waiting_target = State()
    waiting_unit = State()
    waiting_deadline = State()


@router.message(F.text == "/goal")
@router.callback_query(F.data == "new_goal")
async def start_new_goal(event: Message | CallbackQuery, state: FSMContext):
    if isinstance(event, CallbackQuery):
        await event.message.edit_text(
            "Какую цель ты хочешь достичь?\n\n"
            "Напиши одним предложением, чего ты хочешь добиться.\n"
            "Например: Заработать на путешествие, Выучить английский"
        )
        await event.answer()
    else:
        await event.answer(
            "Какую цель ты хочешь достичь?\n\n"
            "Напиши одним предложением, чего ты хочешь добиться.\n"
            "Например: Заработать на путешествие, Выучить английский"
        )
    await state.set_state(GoalStates.waiting_title)


@router.message(GoalStates.waiting_title)
async def process_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer(
        "Отлично!\n\n"
        "Какое числовое значение твоей цели?\n"
        "Например: 100000, 1000, 50\n"
        "Или напиши 0 если цель не поддается измерению"
    )
    await state.set_state(GoalStates.waiting_target)


@router.message(GoalStates.waiting_target)
async def process_target(message: Message, state: FSMContext):
    try:
        target = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введи число. Например: 100000")
        return
    await state.update_data(target=target)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Рубли", callback_data="unit_руб"),
         InlineKeyboardButton(text="Подписчики", callback_data="unit_подписчиков")],
        [InlineKeyboardButton(text="Километры", callback_data="unit_км"),
         InlineKeyboardButton(text="Часы", callback_data="unit_часов")],
        [InlineKeyboardButton(text="Книги", callback_data="unit_книг"),
         InlineKeyboardButton(text="Тренировки", callback_data="unit_тренировок")],
        [InlineKeyboardButton(text="Другое", callback_data="unit_шт")],
    ])
    await message.answer("В какой единице измерять прогресс?", reply_markup=keyboard)
    await state.set_state(GoalStates.waiting_unit)


@router.callback_query(F.data.startswith("unit_"))
async def process_unit(callback: CallbackQuery, state: FSMContext):
    unit = callback.data.replace("unit_", "")
    await state.update_data(unit=unit)
    await callback.message.edit_text(
        "Поставь дедлайн\n\n"
        "Напиши дату в формате ДД.ММ.ГГГГ\n"
        "Или напиши 'без срока'"
    )
    await callback.answer()
    await state.set_state(GoalStates.waiting_deadline)


@router.message(GoalStates.waiting_deadline)
async def process_deadline(message: Message, state: FSMContext):
    data = await state.get_data()
    deadline = None
    if message.text.lower() not in ("без срока", "нет", "skip"):
        try:
            parts = message.text.split(".")
            deadline = f"{parts[2]}-{parts[1]}-{parts[0]}"
        except (IndexError, ValueError):
            await message.answer("Неверный формат. Напиши ДД.ММ.ГГГГ или 'без срока'")
            return

    await create_goal(
        user_id=message.from_user.id,
        title=data["title"],
        target_value=data["target"] if data["target"] > 0 else None,
        unit=data["unit"],
        deadline=deadline
    )

    deadline_text = f"до {deadline}" if deadline else "без срока"
    target_text = f"{data['target']:.0f} {data['unit']}" if data["target"] > 0 else "без числового значения"

    await message.answer(
        f"Цель создана!\n\n"
        f"<b>{data['title']}</b>\n\n"
        f"Целевое значение: {target_text}\n"
        f"Дедлайн: {deadline_text}\n\n"
        f"Я каждый день буду напоминать о твоей цели.\n"
        f"Вечером не забудь отметить свой прогресс!",
        parse_mode="HTML"
    )
    await state.clear()


@router.message(F.text == "/mygoals")
async def cmd_mygoals(message: Message):
    goals = await get_all_goals(message.from_user.id)
    if not goals:
        await message.answer("У тебя пока нет целей. Напиши /goal чтобы создать первую")
        return

    text = "<b>Твои цели:</b>\n\n"
    for g in goals:
        status = "[DONE]" if not g["is_active"] else "[ACTIVE]"
        progress = ""
        if g["target_value"] and g["target_value"] > 0:
            p = g["current_value"] / g["target_value"] * 100
            progress = f" ({p:.0f}%)"
        target_val = f"{g['target_value']:.0f}" if g["target_value"] else "0"
        current_val = f"{g['current_value']:.0f}" if g["current_value"] else "0"
        text += f"{status} <b>{g['title']}</b>{progress}\n"
        text += f"   {current_val} / {target_val} {g['unit']}\n\n"

    await message.answer(text, parse_mode="HTML")
