from datetime import datetime, timedelta, timezone
import sqlite3
import os
from typing import Generator, Optional, TypedDict
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
    search_text: str
    min_salary: Optional[int]
    experience: list[str]
    frequency: int


class SQLiteRepository:
    _db_path: str

    def __init__(self, db_url: str) -> None:
        os.makedirs(db_url, exist_ok=True)
        self._db_path = os.path.join(db_url, "app.db")

    async def init(self) -> None:
        db = sqlite3.connect(self._db_path, timeout=30)
        db.execute(
            """
                CREATE TABLE IF NOT EXISTS oauth_state (
                    id TEXT PRIMARY KEY,
                    telegram_user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
        )
        db.execute(
            """
                CREATE TABLE IF NOT EXISTS token (
                    telegram_user_id INTEGER PRIMARY KEY,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                 """
        )
        db.execute(
            """
                CREATE TABLE IF NOT EXISTS user_filters (
                    telegram_user_id INTEGER PRIMARY KEY,
                    is_applying INTEGER DEFAULT 0,
                    resume_id TEXT,
                    cover_letter TEXT,
                    search_text TEXT,
                    min_salary INTEGER,
                    experience TEXT,
                    frequency INTEGER DEFAULT 10 CHECK (frequency > 0 AND frequency <= 100)
                )
                """
        )

        db.execute(
            """
                CREATE TABLE IF NOT EXISTS applied_vacancy (
                    telegram_user_id INTEGER NOT NULL,
                    vacancy_id TEXT NOT NULL,
                    PRIMARY KEY (telegram_user_id, vacancy_id)
                    )
                """
        )
        db.execute(
            """
                CREATE TABLE IF NOT EXISTS user_applied_count (
                    telegram_user_id INTEGER NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    last_applied TEXT NOT NULL,
                    PRIMARY KEY (telegram_user_id)
                )
                """
        )

        db.commit()

    async def save_state(self, state: str, tg_id: int) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        db = sqlite3.connect(self._db_path)
        db.execute(
            """
                INSERT OR REPLACE INTO oauth_state (id, telegram_user_id, created_at)
                VALUES (?, ?, ?)
                """,
            (state, tg_id, created_at),
        )
        db.commit()

    async def pop_state(self, state: str) -> Optional[int]:
        db = sqlite3.connect(self._db_path)
        db.row_factory = sqlite3.Row
        cur = db.execute(
            "SELECT telegram_user_id FROM oauth_state WHERE id = ?", (state,)
        )
        row = cur.fetchone()
        db.execute("DELETE FROM oauth_state WHERE id = ?", (state,))
        db.commit()
        return row["telegram_user_id"] if row else None

    async def save_token(
        self, tg_id: int, access: str, refresh: str, expires_in: int
    ) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        db = sqlite3.connect(self._db_path)
        db.execute(
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
        db.commit()

    async def get_token(self, tg_id: int) -> Optional[Token]:
        db = sqlite3.connect(self._db_path)
        db.row_factory = sqlite3.Row
        cur = db.execute("SELECT * FROM token WHERE telegram_user_id = ?", (tg_id,))
        row = cur.fetchone()
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

    async def get_filters(self, tg_id: int) -> Filters:
        db = sqlite3.connect(self._db_path)
        db.row_factory = sqlite3.Row
        cur = db.execute(
            "SELECT * FROM user_filters WHERE telegram_user_id = ?", (tg_id,)
        )
        row = cur.fetchone()

        if not row:
            return Filters()

        return Filters(
            resume_id=row["resume_id"],
            is_applying=bool(row["is_applying"]),
            cover_letter=row["cover_letter"],
            search_text=row["search_text"],
            min_salary=row["min_salary"],
            experience=_deserialize_list(row["experience"]),
            frequency=row["frequency"],
        )

    async def set_filters(self, tg_id: int, f: Filters) -> None:
        db = sqlite3.connect(self._db_path)
        is_applying = False
        if f.get("is_applying"):
            is_applying = f.get("is_applying")
        db.execute(
            """
                INSERT INTO user_filters
                (telegram_user_id, resume_id, is_applying, cover_letter, search_text, min_salary, experience, frequency)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    resume_id=excluded.resume_id,
                    is_applying=excluded.is_applying,
                    cover_letter=excluded.cover_letter,
                    search_text=excluded.search_text,
                    min_salary=excluded.min_salary,
                    experience=excluded.experience,
                    frequency=excluded.frequency
                """,
            (
                tg_id,
                f.get("resume_id"),
                int(is_applying),
                f.get("cover_letter"),
                f.get("search_text"),
                f.get("min_salary"),
                _serialize_list(f.get("experience")),
                f.get("frequency") if f.get("frequency") else 10,
            ),
        )
        db.commit()

    def iter_tokens(self) -> Generator[Token, None]:
        db = sqlite3.connect(self._db_path)
        db.row_factory = sqlite3.Row
        cur = db.execute("SELECT * FROM token")
        for row in cur:
            yield Token(
                telegram_user_id=row["telegram_user_id"],
                access_token=row["access_token"],
                refresh_token=row["refresh_token"],
                expires_at=datetime.fromisoformat(row["expires_at"]),
            )

    async def is_applied(self, tg_id: int, vacancy_id: str) -> bool:
        db = sqlite3.connect(self._db_path)
        db.row_factory = sqlite3.Row
        cur = db.execute(
            "SELECT * FROM applied_vacancy WHERE telegram_user_id = ? AND vacancy_id = ?",
            (tg_id, vacancy_id),
        )
        return bool(cur.fetchone())

    async def mark_applied(self, tg_id: int, vacancy_id: str) -> None:
        db = sqlite3.connect(self._db_path)
        db.execute(
            "INSERT OR IGNORE INTO applied_vacancy (telegram_user_id, vacancy_id) VALUES (?, ?)",
            (tg_id, vacancy_id),
        )
        db.commit()

    async def update_applied_count(self, tg_id: int, count: int) -> None:
        db = sqlite3.connect(self._db_path)
        db.execute(
            "INSERT OR REPLACE INTO user_applied_count (telegram_user_id, count, last_applied) VALUES (?, ?, ?)",
            (tg_id, count, datetime.now(timezone.utc).isoformat()),
        )
        db.commit()

    async def get_applied_count(self, tg_id: int) -> tuple[int, datetime]:
        db = sqlite3.connect(self._db_path)
        db.row_factory = sqlite3.Row
        cur = db.execute(
            "SELECT * FROM user_applied_count WHERE telegram_user_id = ?", (tg_id,)
        )
        row = cur.fetchone()
        if not row:
            return 0, datetime.now(timezone.utc)
        return (row["count"], datetime.fromisoformat(row["LAST_APPLIED"]))


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
