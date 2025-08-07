from datetime import datetime, timedelta, timezone
import aiosqlite
from typing import AsyncGenerator, Optional, TypedDict
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class Token:
    telegram_user_id: int
    access_token: str
    refresh_token: str
    expires_at: datetime


class Filters(TypedDict, total=False):
    is_applying: bool
    resume_id: str
    cover_letter: str
    keywords: list[str]
    min_salary: int | None
    experience: list[str]


class SQLiteRepository:
    _db_path: Path

    def __init__(self, db_url: str) -> None:
        if str(db_url).startswith("sqlite+aiosqlite:///"):
            db_url = db_url.removeprefix("sqlite+aiosqlite:///")
        self._db_path = Path(db_url).expanduser().resolve()

    async def init(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                    CREATE TABLE IF NOT EXISTS oauth_state (
                        id TEXT PRIMARY KEY,
                        telegram_user_id INTEGER NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
            )
            await db.execute(
                """
                    CREATE TABLE IF NOT EXISTS token (
                        telegram_user_id INTEGER PRIMARY KEY,
                        access_token TEXT NOT NULL,
                        refresh_token TEXT NOT NULL,
                        expires_at TEXT NOT NULL
                    )
                     """
            )
            await db.execute(
                """
                    CREATE TABLE IF NOT EXISTS user_filters (
                        telegram_user_id INTEGER PRIMARY KEY,
                        is_applying INTEGER DEFAULT 0,
                        resume_id TEXT,
                        cover_letter TEXT,
                        keywords TEXT,
                        min_salary INTEGER,
                        experience TEXT
                    )
                    """
            )

            await db.execute(
                """
                    CREATE TABLE IF NOT EXISTS applied_vacancy (
                        telegram_user_id INTEGER NOT NULL,
                        vacancy_id TEXT NOT NULL,
                        PRIMARY KEY (telegram_user_id, vacancy_id)
                        )
                    """
            )

            await db.commit()

    async def save_state(self, state: str, tg_id: int) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                    INSERT OR REPLACE INTO oauth_state (id, telegram_user_id, created_at)
                    VALUES (?, ?, ?)
                    """,
                (state, tg_id, created_at),
            )
            await db.commit()

    async def pop_state(self, state: str) -> Optional[int]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT telegram_user_id FROM oauth_state WHERE id = ?", (state,)
            ) as cur:
                row = await cur.fetchone()
            await db.execute("DELETE FROM oauth_state WHERE id = ?", (state,))
            await db.commit()
            return row["telegram_user_id"] if row else None

    async def save_token(
        self, tg_id: int, access: str, refresh: str, expires_in: int
    ) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                    INSERT INTO token (telegram_user_id, access_token, refresh_token, expires_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(telegram_user_id) DO UPDATE SET
                        access_token=excluded.access_token,
                        refresh_token=excluded.refresh_token,
                        expires_at=excluded.expires_at
                    """,
                (tg_id, access, refresh, expires_at.isoformat()),
            )
            await db.commit()

    async def get_token(self, tg_id: int) -> Optional[Token]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM token WHERE telegram_user_id = ?", (tg_id,)
            ) as cur:
                row = await cur.fetchone()
            if not row:
                return None
            expires_at = datetime.fromisoformat(row["expires_at"])

            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            return Token(
                telegram_user_id=row["telegram_user_id"],
                access_token=row["access_token"],
                refresh_token=row["refresh_token"],
                expires_at=expires_at,
            )

    async def get_filters(self, tg_id: int) -> Filters | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                "SELECT * FROM user_filters WHERE telegram_user_id = ?", (tg_id,)
            )
            row = await cur.fetchone()
        if not row:
            return None

        return Filters(
            resume_id=row["resume_id"],
            is_applying=bool(row["is_applying"]),
            cover_letter=row["cover_letter"],
            keywords=_deserialize_list(row["keywords"]),
            min_salary=row["min_salary"],
            experience=_deserialize_list(row["experience"]),
        )

    async def set_filters(self, tg_id: int, f: Filters) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                    INSERT INTO user_filters
                    (telegram_user_id, resume_id, is_applying, cover_letter, keywords, min_salary, experience)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(telegram_user_id) DO UPDATE SET
                        resume_id=excluded.resume_id,
                        is_applying=excluded.is_applying,
                        cover_letter=excluded.cover_letter,
                        keywords=excluded.keywords,
                        min_salary=excluded.min_salary,
                        experience=excluded.experience
                    """,
                (
                    tg_id,
                    f.get("resume_id"),
                    int(f.get("is_applying")),
                    f.get("cover_letter"),
                    _serialize_list(f.get("keywords")),
                    f.get("min_salary"),
                    _serialize_list(f.get("experience")),
                ),
            )
            await db.commit()

    async def iter_tokens(self) -> AsyncGenerator[Token, None]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM token") as cur:
                async for row in cur:
                    yield Token(
                        telegram_user_id=row["telegram_user_id"],
                        access_token=row["access_token"],
                        refresh_token=row["refresh_token"],
                        expires_at=datetime.fromisoformat(row["expires_at"]),
                    )

    async def is_applied(self, tg_id: int, vacancy_id: str) -> bool:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM applied_vacancy WHERE telegram_user_id = ? AND vacancy_id = ?",
                (tg_id, vacancy_id),
            ) as cur:
                return bool(await cur.fetchone())

    async def mark_applied(self, tg_id: int, vacancy_id: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO applied_vacancy (telegram_user_id, vacancy_id) VALUES (?, ?)",
                (tg_id, vacancy_id),
            )
            await db.commit()


def _serialize_list(lst: list[str] | None) -> str | None:
    return ",".join(lst) if lst else None


def _deserialize_list(s: str | None) -> list[str]:
    lst = []
    if not s:
        return lst
    for x in s.split(","):
        strip = x.strip()
        if strip:
            lst.append(strip)

    return lst
