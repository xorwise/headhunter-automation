from aiogram import Router, types
from aiogram.filters import Command, CommandObject

from hh.client import HHClient
from storage.sqlite_impl import SQLiteRepository, Filters

router = Router()


# ---------- helpers ---------------------------------------------------------
def _parse_comma_list(arg: str) -> list[str]:
    return [x.strip() for x in arg.split(",") if x.strip()]


def _format_filters(f: Filters) -> str:
    if not f:
        return "Фильтры не заданы."

    parts: list[str] = []
    if f.get("keywords"):
        parts.append(f"🔑 Ключевые слова: <code>{', '.join(f['keywords'])}</code>")
    if f.get("min_salary") or f.get("max_salary"):
        parts.append(
            f"💰 Зарплата: {f.get('min_salary') or '…'} – {f.get('max_salary') or '…'} ₽"
        )
    if f.get("resume_id"):
        parts.append(f"📄 Резюме-ID: <code>{f['resume_id']}</code>")
    if f.get("experience"):
        parts.append(f"🕑 Опыт: <code>{f['experience']}</code>")

    return "\n".join(parts)


# ---------- command handlers ------------------------------------------------
def setup(repo: SQLiteRepository, hh_client: HHClient) -> Router:
    # /filters  → показать текущие
    @router.message(Command("filters"))
    async def cmd_filters(msg: types.Message) -> None:
        f = await repo.get_filters(msg.from_user.id)
        await msg.answer(_format_filters(f))

    # /set_keywords python, backend
    @router.message(Command("set_keywords"))
    async def cmd_set_keywords(msg: types.Message, command: CommandObject) -> None:
        if not command.args:
            await msg.answer("Формат: /set_keywords python, backend")
            return
        keywords = _parse_comma_list(command.args)
        f = await repo.get_filters(msg.from_user.id)
        f["keywords"] = keywords
        await repo.set_filters(msg.from_user.id, f)
        await msg.answer("✅ Ключевые слова обновлены.")

    # /set_locations Москва, Санкт-Петербург
    @router.message(Command("set_locations"))
    async def cmd_set_locations(msg: types.Message, command: CommandObject) -> None:
        if not command.args:
            await msg.answer("Формат: /set_locations Москва, Санкт-Петербург")
            return
        locations = _parse_comma_list(command.args)
        f = await repo.get_filters(msg.from_user.id)
        f["locations"] = locations
        await repo.set_filters(msg.from_user.id, f)
        await msg.answer("✅ Локации обновлены.")

    # /set_salary 120000 250000
    @router.message(Command("set_salary"))
    async def cmd_set_salary(msg: types.Message, command: CommandObject) -> None:
        if not command.args:
            await msg.answer("Формат: /set_salary <MIN> <MAX>")
            return
        parts = command.args.split()
        if len(parts) != 2 or not all(p.isdigit() for p in parts):
            await msg.answer("Нужно указать две суммы: /set_salary 120000 250000")
            return
        min_s, max_s = sorted(map(int, parts))
        f = await repo.get_filters(msg.from_user.id)
        f["min_salary"] = min_s
        await repo.set_filters(msg.from_user.id, f)
        await msg.answer("✅ Диапазон зарплаты обновлён.")

    @router.message(Command("set_resume"))
    async def cmd_set_resume(msg: types.Message) -> None:
        access_token = await repo.get_token(msg.from_user.id)
        resumes = await hh_client.list_resumes(access_token)

        r_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=resume["title"], callback_data=f"resume:{resume['id']}"
                    )
                ]
                for resume in resumes
            ]
        )

        await msg.answer("Выберите резюме для автоотклика:", reply_markup=r_kb)

    @router.message(Command("set_experience"))
    async def cmd_set_experience(msg: types.Message) -> None:
        access_token = await repo.get_token(msg.from_user.id)
        experiences = await hh_client.get_experience(access_token)
        e_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text=exp["name"], callback_data=f"exp:{exp['id']}"
                    )
                ]
                for exp in experiences
            ]
        )

        await msg.answer("Выберите опыт для поиска:", reply_markup=e_kb)

    @router.message(Command("set_cover_letter"))
    async def cmd_set_cover_letter(msg: types.Message, command: CommandObject) -> None:
        if not command.args:
            await msg.answer("Формат: /set_cover_letter Текст сопроводительного письма")
            return
        f = await repo.get_filters(msg.from_user.id)
        if not f:
            f = Filters()
        f["cover_letter"] = command.args

        await repo.set_filters(msg.from_user.id, f)
        await msg.answer("Сопроводительное письмо успешно установлено!")

    @router.message(Command("toggle_applying"))
    async def cmd_toggle_applying(msg: types.Message) -> None:
        f = await repo.get_filters(msg.from_user.id)
        if not f:
            f = Filters()
            f["is_applying"] = True
        elif f["is_applying"]:
            f["is_applying"] = False
        else:
            f["is_applying"] = True

        await repo.set_filters(msg.from_user.id, f)
        await msg.answer(
            f"Автоотклик {'запущен' if f["is_applying"] else 'остановлен'}!"
        )

    # /clear_filters
    @router.message(Command("clear_filters"))
    async def cmd_clear(msg: types.Message) -> None:
        await repo.set_filters(msg.from_user.id, Filters())  # пусто
        await msg.answer("🗑️ Фильтры сброшены.")

    return router
