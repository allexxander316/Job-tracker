from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.database import async_session
from app.vacancies.services import VacancySyncService


async def synchronize_vacancies_job() -> None:
    """Задача: синхронизировать все вакансии"""
    async with async_session() as session:
        service = VacancySyncService(session)
        await service.sync_all()


def setup_scheduler() -> AsyncIOScheduler:
    """Создает и настраивает планировщик."""
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        synchronize_vacancies_job,
        trigger=CronTrigger(hour=10, minute=0),
        id="sync_vacancies",
        replace_existing=True,
    )

    return scheduler
