import asyncio
import urllib.parse
from aiohttp import web
import httpx
from aiogram import Bot

from datetime import datetime, timezone, timedelta
from config.settings import Settings
from hh.client import HHClient
from storage.sqlite_impl import SQLiteRepository, Token
from auth.state import generage_state


class OAuthManager:
    def __init__(
        self, settings: Settings, repo: SQLiteRepository, bot: Bot, hh_client: HHClient
    ) -> None:
        self.settings = settings
        self.repo = repo
        self.bot = bot
        self.hh_client = hh_client

    def build_authorize_url(self, tg_id: int) -> str:
        state = generage_state()

        asyncio.create_task(self.repo.save_state(state, tg_id))

        params = {
            "response_type": "code",
            "client_id": self.settings.hh_client_id,
            "state": state,
            "redirect_uri": str(self.settings.oauth_redirect_uri),
        }

        return f"https://hh.ru/oauth/authorize?{urllib.parse.urlencode(params)}"

    async def callback(self, request: web.Request) -> web.Response:
        code = request.query.get("code")
        state = request.query.get("state")
        if not code or not state:
            return web.Response(status=400, text="Missing code or state")

        tg_id = await self.repo.pop_state(state)
        if tg_id is None:
            return web.Response(status=400, text="Invalid state")

        token_payload = await self._exchange_code(code)
        await self.repo.save_token(
            tg_id,
            token_payload["access_token"],
            token_payload["refresh_token"],
            token_payload["expires_in"],
        )

        await self.bot.send_message(tg_id, "HH авторизация успешно завершена")
        return web.Response(status=200, text="Success! You can close this tab.")

    async def _exchange_code(self, code: str) -> dict:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.settings.hh_client_id,
            "client_secret": self.settings.hh_client_secret,
            "redirect_uri": str(self.settings.oauth_redirect_uri),
        }

        headers = {"User-Agent": "headhunter-xorbot/1.0"}
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://hh.ru/oauth/token", data=data, headers=headers
            )
            r.raise_for_status()
            return r.json()

    async def refresh_token(self, tg_id: int) -> Token | None:
        token = await self.repo.get_token(tg_id)
        if not token:
            return None
        refresh_token = token.refresh_token

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        headers = {"User-Agent": "headhunter-xorbot/1.0"}

        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://hh.ru/oauth/token", data=data, headers=headers
            )
            r.raise_for_status()
            token = r.json()
            await self.repo.save_token(
                tg_id,
                token["access_token"],
                token["refresh_token"],
                token["expires_in"],
            )
            expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=token["expires_in"]
            )
            return Token(
                telegram_user_id=tg_id,
                access_token=token["access_token"],
                refresh_token=token["refresh_token"],
                expires_at=expires_at,
            )
