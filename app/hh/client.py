from __future__ import annotations

import httpx
from typing import Any

from config.settings import Settings
from storage.sqlite_impl import Filters


class HHClient:
    __slots__ = ("_settings", "_base", "_ua")

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._base: str = "https://api.hh.ru"
        self._ua: dict[str, str] = {"User-Agent": settings.user_agent}

    async def search_vacancies(
        self, access_token: str, f: Filters, /, page: int = 0, per_page: int = 100
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "page": page,
            "per_page": per_page,
            "order_by": "publication_time",
        }

        if f.get("search_text"):
            params["text"] = f["search_text"]
        if f.get("experience"):
            params["experience"] = ",".join(f["experience"])
        if f.get("min_salary"):
            params.update({"salary": f["min_salary"], "currency": "RUR"})

        headers = {**self._ua, "Authorization": f"Bearer {access_token}"}
        result = []
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base}/vacancies", params=params, headers=headers
            )
            resp.raise_for_status()
            pages = resp.json()["pages"]
            result.extend(resp.json()["items"])
            for i in range(1, pages):
                params["page"] = i
                resp = await client.get(
                    f"{self._base}/vacancies",
                    params=params,
                    headers=headers,
                )
                resp.raise_for_status()
                result.extend(resp.json()["items"])
            return result

    async def apply(
        self,
        access_token: str,
        vacancy_id: str,
        resume_id: str,
        /,
        message: str = "Здравствуйте! Откликаюсь на вакансию.",
    ) -> None:
        headers = {
            **self._ua,
            "Authorization": f"Bearer {access_token}",
        }
        payload: dict[str, tuple[None, str]] = {
            "message": (None, message),
            "vacancy_id": (None, vacancy_id),
            "resume_id": (None, resume_id),
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base}/negotiations",
                files=payload,
                headers=headers,
                timeout=30,
            )

            resp.raise_for_status()

    async def list_resumes(self, access_token: str) -> list[dict[str, Any]]:
        headers = {**self._ua, "Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base}/resumes/mine", headers=headers, timeout=30
            )
            resp.raise_for_status()
            return resp.json()["items"]

    async def get_experience(self, access_token: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._base}/dictionaries", headers=self._ua, timeout=30
            )
            resp.raise_for_status()
            return resp.json()["experience"]
