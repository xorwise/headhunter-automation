from aiogram import types, Router
from aiogram.filters import Command, CommandObject

from bot.middlewares.auth import AuthMessageMiddleware
from hh.client import HHClient
from storage.sqlite_impl import SQLiteRepository


router = Router()


def setup(repo: SQLiteRepository, hh_client: HHClient) -> Router:
    router.message.middleware(AuthMessageMiddleware(repo, hh_client))


    @router.message(Command("menu"))
    async def cmd_menu(msg: types.Message) -> None:
        filters = await repo.get_filters(msg.from_user.id)
        message = f"""Привет, {msg.from_user.full_name}!

Выбери одну из опций:"""

        menu_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="Фильтры поиска⚙️", callback_data="filters"
                    ),
                    types.InlineKeyboardButton(
                        text=f"Автоотклик {'✅' if filters.get('is_applying') else '❌'}",
                        callback_data="toggle_applying",
                    ),
                ],
            ]
        )
        await msg.answer(message, reply_markup=menu_kb)

    return router
