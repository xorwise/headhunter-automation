from aiogram import F, Bot, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from bot.middlewares.auth import AuthCallbackMiddleware
from hh.client import HHClient
from storage.sqlite_impl import SQLiteRepository

router = Router()


class SearchTextState(StatesGroup):
    SEARCHTEXT = State()


class CoverLetterState(StatesGroup):
    COVER_LETTER = State()


class MinSalaryState(StatesGroup):
    MIN_SALARY = State()


class ExperienceState(StatesGroup):
    EXPERIENCE = State()


class ResumeState(StatesGroup):
    RESUME = State()


class FrequencyState(StatesGroup):
    FREQUENCY = State()


def setup(repo: SQLiteRepository, hh_client: HHClient, bot: Bot) -> Router:
    router.callback_query.middleware(AuthCallbackMiddleware(repo, hh_client))
    @router.callback_query(F.data == "menu")
    async def menu(q: types.CallbackQuery, state: FSMContext) -> None:
        filters = await repo.get_filters(q.from_user.id)
        message = f"""Привет, {q.from_user.full_name}!

Выбери одну из опций:"""

        menu_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="Фильтры поиска⚙️", callback_data="filters"
                    ),
                    types.InlineKeyboardButton(
                        text=f"Автоотклик {'🔔' if filters.get('is_applying') else '❌'}",
                        callback_data="toggle_applying",
                    ),
                ],
            ]
        )
        await q.message.answer(message, reply_markup=menu_kb)
        await q.answer()

    @router.callback_query(F.data == "filters")
    async def show_filters(q: types.CallbackQuery):
        filters_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="Сопровод-ное письмо📝", callback_data="cover_letter"
                    ),
                    types.InlineKeyboardButton(
                        text="Текст поиска🔑", callback_data="search_text"
                    ),
                ],
                [
                    types.InlineKeyboardButton(
                        text="Минимальная зарплата💰", callback_data="min_salary"
                    ),
                    types.InlineKeyboardButton(
                        text="Опыт работы👔", callback_data="experience"
                    ),
                ],
                [
                    types.InlineKeyboardButton(text="Резюме📄", callback_data="resume"),
                    types.InlineKeyboardButton(
                        text="Частота откликов📅", callback_data="frequency"
                    ),
                ],
                [
                    types.InlineKeyboardButton(text="Меню📋", callback_data="menu"),
                ],
            ]
        )
        await q.message.answer(
            "Выбери одну из команд:", reply_markup=filters_kb, show_alert=False
        )
        await q.answer()

    @router.callback_query(F.data == "cancel_filters")
    async def cancel_filters(q: types.CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await show_filters(q)

    @router.callback_query(F.data == "search_text")
    async def ask_search_text(q: types.CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await state.set_state(SearchTextState.SEARCHTEXT)

        search_text_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="Отмена❌", callback_data="cancel_filters"
                    ),
                ],
            ],
        )
        f = await repo.get_filters(q.from_user.id)
        if f.get("search_text"):
            message = f"Текущий текст поиска:\n\n{f['search_text']}"
        else:
            message = "Текущий текст поиска: нет"

        message += "\n\nВведи новый текст поиска:"

        await q.message.answer(message, reply_markup=search_text_kb)
        await q.answer()

    @router.message(SearchTextState.SEARCHTEXT)
    async def set_search_text(msg: types.Message, state: FSMContext) -> None:
        filters = await repo.get_filters(msg.from_user.id)
        filters["search_text"] = msg.text or ""
        await repo.set_filters(msg.from_user.id, filters)
        await state.clear()
        search_text_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="Меню📋", callback_data="menu"),
                ],
            ],
        )
        await msg.answer("Текст поиска успешно изменен", reply_markup=search_text_kb)

    @router.callback_query(F.data == "cover_letter")
    async def ask_cover_letter(q: types.CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await state.set_state(CoverLetterState.COVER_LETTER)

        cover_letter_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="Отмена❌", callback_data="cancel_filters"
                    ),
                ],
            ],
        )
        f = await repo.get_filters(q.from_user.id)
        if f.get("cover_letter"):
            message = f"Текущее сопроводительное письмо:\n\n{f['cover_letter']}"
        else:
            message = "Текущее сопроводительное письмо: нет"

        message += "\n\nВведи сопроводительное письмо:"

        await q.message.answer(message, reply_markup=cover_letter_kb)
        await q.answer()

    @router.message(CoverLetterState.COVER_LETTER)
    async def set_cover_letter(msg: types.Message, state: FSMContext) -> None:
        filters = await repo.get_filters(msg.from_user.id)
        filters["cover_letter"] = msg.text
        await repo.set_filters(msg.from_user.id, filters)
        await state.clear()
        cover_letter_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="Меню📋", callback_data="menu"),
                ],
            ],
        )
        await msg.answer(
            "Сопроводительное письмо успешно изменено", reply_markup=cover_letter_kb
        )

    @router.callback_query(F.data == "min_salary")
    async def ask_min_salary(q: types.CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await state.set_state(MinSalaryState.MIN_SALARY)

        min_salary_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="Отмена❌", callback_data="cancel_filters"
                    ),
                ],
            ],
        )
        f = await repo.get_filters(q.from_user.id)
        if f.get("min_salary"):
            message = f"Текущая минимальная зарплата:\n\n{f['min_salary']}"
        else:
            message = "Текущая минимальная зарплата: нет"

        message += "\n\nВведи минимальную зарплату:"

        await q.message.answer(message, reply_markup=min_salary_kb)
        await q.answer()

    @router.message(MinSalaryState.MIN_SALARY)
    async def set_min_salary(msg: types.Message, state: FSMContext) -> None:
        filters = await repo.get_filters(msg.from_user.id)
        filters["min_salary"] = msg.text
        await repo.set_filters(msg.from_user.id, filters)
        await state.clear()
        min_salary_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="Меню📋", callback_data="menu"),
                ],
            ],
        )
        await msg.answer(
            "Минимальная зарплата успешно изменена", reply_markup=min_salary_kb
        )

    @router.callback_query(F.data == "experience")
    async def ask_experience(q: types.CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await state.set_state(ExperienceState.EXPERIENCE)

        access_token = await repo.get_token(q.from_user.id)
        experiences = await hh_client.get_experience(access_token.access_token)
        experiences_btns = [
            [
                types.InlineKeyboardButton(
                    text=exp["name"], callback_data=f"exp:{exp['id']}"
                )
            ]
            for exp in experiences
        ]

        experience_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                *experiences_btns,
                [
                    types.InlineKeyboardButton(
                        text="Все опыты работы", callback_data="exp:0"
                    ),
                ],
                [
                    types.InlineKeyboardButton(
                        text="Отмена❌", callback_data="cancel_filters"
                    ),
                ],
            ],
        )
        f = await repo.get_filters(q.from_user.id)
        if f.get("experience"):
            message = f"Текущий опыт работы:\n\n{f['experience']}"
        else:
            message = "Текущий опыт работы: нет"

        message += "\n\Выбери опыт работы:"

        await q.message.answer(message, reply_markup=experience_kb)
        await q.answer()

    @router.callback_query(ExperienceState.EXPERIENCE)
    async def set_experience(q: types.CallbackQuery, state: FSMContext) -> None:
        f = await repo.get_filters(q.from_user.id)
        exp = q.data.split(":")[1]
        if exp == "0":
            f["experience"] = None
        else:
            f["experience"] = exp
        await repo.set_filters(q.from_user.id, f)
        await state.clear()

        experience_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="Меню📋", callback_data="menu"),
                ],
            ],
        )
        await q.message.answer(
            "Опыт работы успешно изменен", reply_markup=experience_kb
        )
        await q.answer()

    @router.callback_query(F.data == "resume")
    async def ask_resume(q: types.CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await state.set_state(ResumeState.RESUME)

        access_token = await repo.get_token(q.from_user.id)
        resumes = await hh_client.list_resumes(access_token.access_token)
        resumes_btns = [
            [
                types.InlineKeyboardButton(
                    text=resume["title"], callback_data=f"resume:{resume['id']}"
                )
            ]
            for resume in resumes
        ]

        resume_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                *resumes_btns,
                [
                    types.InlineKeyboardButton(
                        text="Отмена❌", callback_data="cancel_filters"
                    ),
                ],
            ],
        )
        f = await repo.get_filters(q.from_user.id)
        if f.get("resume_id"):
            for resume in resumes:
                if resume["id"] == f["resume_id"]:
                    message = f"Текущий резюме:\n\n{resume['title']}"
                    break
        else:
            message = "Текущий резюме: нет"

        message += "\n\nВыбери резюме:"

        await q.message.answer(message, reply_markup=resume_kb)
        await q.answer()

    @router.callback_query(ResumeState.RESUME)
    async def set_resume(q: types.CallbackQuery, state: FSMContext) -> None:
        f = await repo.get_filters(q.from_user.id)
        resume = q.data.split(":")[1]
        if resume == "0":
            f["resume_id"] = None
        else:
            f["resume_id"] = resume
        await repo.set_filters(q.from_user.id, f)
        await state.clear()

        resume_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="Меню📋", callback_data="menu"),
                ],
            ],
        )
        await q.message.answer("Резюме успешно изменено", reply_markup=resume_kb)
        await q.answer()

    @router.callback_query(F.data == "toggle_applying")
    async def toggle_applying(q: types.CallbackQuery) -> None:
        f = await repo.get_filters(q.from_user.id)
        if f.get("is_applying"):
            f["is_applying"] = False
        else:
            if not f.get("resume_id") or not f.get("search_text"):
                await q.message.answer("Выберите резюме и настройте текст для поиска!")
                await q.answer()
                return
            f["is_applying"] = True

        await repo.set_filters(q.from_user.id, f)
        await menu(q, State())
        await q.answer()

    @router.callback_query(F.data == "frequency")
    async def ask_frequency(q: types.CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await state.set_state(FrequencyState.FREQUENCY)

        frequency_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="Отмена❌", callback_data="cancel_filters"
                    ),
                ],
            ],
        )
        f = await repo.get_filters(q.from_user.id)
        if f.get("frequency"):
            message = f"Текущая частота откликов:\n\n{f['frequency']} откликов в день."
        else:
            message = "Текущая частота откликов: нет"

        message += "\n\nВведи частоту:"

        await q.message.answer(message, reply_markup=frequency_kb)
        await q.answer()

    @router.message(FrequencyState.FREQUENCY)
    async def set_frequency(msg: types.Message, state: FSMContext) -> None:
        filters = await repo.get_filters(msg.from_user.id)
        if not msg.text.isdigit():
            await msg.answer("Введите число откликов в день (целое число от 1 до 100)")
            return
        filters["frequency"] = int(msg.text)
        await repo.set_filters(msg.from_user.id, filters)
        await state.clear()
        frequency_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="Меню📋", callback_data="menu"),
                ],
            ],
        )
        await msg.answer("Частота откликов успешно изменена", reply_markup=frequency_kb)

    return router
