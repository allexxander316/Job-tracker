from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.database import async_session
from app.core.logger import get_logger
from app.vacancies.services import VacancySyncService

logger = get_logger(__name__)


async def synchronize_vacancies_job() -> None:
    """Задача: синхронизировать все вакансии"""

    logger.info("Starting vacancy synchronization job")
    try:
        async with async_session() as session:
            service = VacancySyncService(session)
            await service.sync_all()
        logger.info("Vacancy synchronization completed successfully")
    except Exception:
        logger.exception("Vacancy synchronization failed")
        raise


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
