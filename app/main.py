import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

from bot.handlers import menu as menu_handlers
from config.settings import Settings
from hh.client import HHClient
from services.job_processor import JobProcessor
from storage.sqlite_impl import SQLiteRepository
from auth.oauth import OAuthManager
from bot.commands.connect import build_router
from bot.commands import filters as filters_cmds
from bot.commands import menu
from tasks.scheduler import start_scheduler


async def main() -> None:
    settings = Settings()

    repo = SQLiteRepository(settings.database_url)
    await repo.init()

    bot = Bot(
        token=settings.telegram_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    hh_client = HHClient(settings)

    oauth = OAuthManager(settings, repo, bot, hh_client)
    processor = JobProcessor(repo, hh_client, bot, oauth)

    await start_scheduler(processor, period_sec=settings.poll_interval_minutes * 60)

    dp = Dispatcher()
    dp.include_router(build_router(oauth))
    dp.include_router(filters_cmds.setup(repo, hh_client))
    dp.include_router(menu.setup(repo, hh_client))
    dp.include_router(menu_handlers.setup(repo, hh_client, bot))

    app = web.Application()
    app.add_routes([web.get("/oauth/callback", oauth.callback)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

    print("Starting bot...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
