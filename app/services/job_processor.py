from __future__ import annotations

import asyncio

from datetime import datetime, timezone
from typing import Any
import time

from aiogram import Bot

from storage.sqlite_impl import SQLiteRepository, Filters
from hh.client import HHClient, TestRequired


class JobProcessor:
    def __init__(self, repo: SQLiteRepository, hh: HHClient, bot: Bot, /, per_page: int = 100) -> None:
        self._repo = repo
        self._hh = hh
        self._bot = bot
        self._per_page = per_page


    async def run_once(self) -> None:
        async for token in self._repo.iter_tokens():
            if token.expires_at <= datetime.now(timezone.utc):
                # TODO: refresh_token flow
                continue

            filters = await self._repo.get_filters(token.telegram_user_id)
            vacancies = await self._hh.search_vacancies(token.access_token, filters, per_page=self._per_page)
            applied_cnt = 0
            for v in vacancies:
                vacancy_id: str = v["id"]
                if await self._repo.is_applied(token.telegram_user_id, vacancy_id):
                    continue

                try:
                    if not filters.get("resume_id"):
                        #TODO: add resume selection after registration
                        break
                    await self._hh.apply(token.access_token, vacancy_id, filters.get("resume_id"))
                except TestRequired as e:
                    continue
                except Exception as e:
                    await self._bot.send_message(token.telegram_user_id, f"Не удалось откликнуться на вакансию {vacancy_id}: {e}")
                    continue
                else:
                    await self._repo.mark_applied(token.telegram_user_id, vacancy_id)
                    applied_cnt += 1
                finally:
                    time.sleep(2)


            if applied_cnt > 0:
                await self._bot.send_message(token.telegram_user_id, f"Откликнулись на {applied_cnt} вакансий")

    async def loop(self, period_sec: int = 300) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(period_sec)
