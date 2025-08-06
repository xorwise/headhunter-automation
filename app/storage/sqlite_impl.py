from datetime import datetime, timedelta, timezone
import aiosqlite
from typing import Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class Token:
    telegram_user_id: int
    access_token: str
    refresh_token: str
    expires_at: datetime


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
