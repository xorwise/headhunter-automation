from __future__ import annotations

import asyncio

from datetime import datetime, timezone, timedelta
import time

from aiogram import Bot

from storage.sqlite_impl import SQLiteRepository
from hh.client import HHClient
from auth.oauth import OAuthManager


class JobProcessor:
    def __init__(
        self,
        repo: SQLiteRepository,
        hh: HHClient,
        bot: Bot,
        oauth: OAuthManager,
        /,
        per_page: int = 100,
    ) -> None:
        self._repo = repo
        self._hh = hh
        self._bot = bot
        self._oauth = oauth
        self._per_page = per_page

    async def run_once(self) -> None:
        applied_cnt = 0
        async for token in self._repo.iter_tokens():
            if token.expires_at <= datetime.now(timezone.utc):
                token = await self._oauth.refresh_token(token.telegram_user_id)

            filters = await self._repo.get_filters(token.telegram_user_id)
            if not filters.get("is_applying"):
                continue
            vacancies = await self._hh.search_vacancies(
                token.access_token, filters, per_page=self._per_page
            )
            applied_cnt, last_applied = await self._repo.get_applied_count(
                token.telegram_user_id
            )
            applied_cnt = _update_last_applied(last_applied, applied_cnt)
            if filters.get("frequency") and applied_cnt >= filters["frequency"]:
                continue

            for v in vacancies:
                filters = await self._repo.get_filters(token.telegram_user_id)
                if not filters.get("is_applying"):
                    break
                if filters.get("frequency") and applied_cnt >= filters["frequency"]:
                    break
                vacancy_id: str = v["id"]
                if (
                    await self._repo.is_applied(token.telegram_user_id, vacancy_id)
                    or v["has_test"]
                ):
                    continue

                try:
                    await self._hh.apply(
                        token.access_token,
                        vacancy_id,
                        filters.get("resume_id"),
                        message=filters.get("cover_letter") or "",
                    )
                except Exception:
                    await self._bot.send_message(
                        token.telegram_user_id,
                        f"Не удалось откликнуться на вакансию {v['name']}:\nСсылка на вакансию: {v['alternate_url']}\n",
                    )
                    continue
                else:
                    await self._repo.mark_applied(token.telegram_user_id, vacancy_id)
                    applied_cnt += 1
                    await self._repo.update_applied_count(
                        token.telegram_user_id, applied_cnt
                    )
                finally:
                    time.sleep(2)

            if applied_cnt > 0:
                await self._bot.send_message(
                    token.telegram_user_id, f"Откликнулись на {applied_cnt} вакансий"
                )

    async def loop(self, period_sec: int = 300) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(period_sec)


def _update_last_applied(last_applied: datetime, count: int) -> int:
    if last_applied.replace(hour=0, minute=0, second=0) <= (
        datetime.now(timezone.utc) - timedelta(days=1)
    ).replace(hour=0, minute=0, second=0):
        return 0
    return count
