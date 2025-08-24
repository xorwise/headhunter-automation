from typing import Any, Awaitable, Callable, Dict
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram import BaseMiddleware
from hh.client import HHClient
from storage.sqlite_impl import SQLiteRepository


class AuthMessageMiddleware(BaseMiddleware):
    def __init__(self, repo: SQLiteRepository, hh_client: HHClient) -> None:
        self.repo = repo
        self.hh_client = hh_client

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        print("testing")
        if not await self.repo.get_token(event.from_user.id):
            await event.answer("Пожалуйста, авторизуйтесь в HH.ru с помощью /connect")
            return
        return await handler(event, data)


class AuthCallbackMiddleware(BaseMiddleware):
    def __init__(self, repo: SQLiteRepository, hh_client: HHClient) -> None:
        self.repo = repo
        self.hh_client = hh_client

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        if not await self.repo.get_token(event.from_user.id):
            await event.message.answer("Пожалуйста, авторизуйтесь в HH.ru с помощью /connect")
            return
        return await handler(event, data)
