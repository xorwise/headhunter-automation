import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

from config.settings import Settings
from storage.sqlite_impl import SQLiteRepository
from auth.oauth import OAuthManager
from bot.commands.connect import build_router


async def main() -> None:
    settings = Settings()
    print(settings.hh_client_secret)
    print(settings.hh_client_id)

    repo = SQLiteRepository(settings.database_url)
    await repo.init()

    bot = Bot(
        token=settings.telegram_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    oauth = OAuthManager(settings, repo, bot)

    dp = Dispatcher()
    dp.include_router(build_router(oauth))

    app = web.Application()
    app.add_routes([web.get("/oauth/callback", oauth.callback)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 8080)
    await site.start()

    print("Starting bot...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
