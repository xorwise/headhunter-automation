import asyncio
from services.job_processor import JobProcessor


async def start_scheduler(proc: JobProcessor, period_sec: int = 300) -> None:
    asyncio.create_task(proc.loop(period_sec))
