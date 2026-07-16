from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.vacancies.services import VacancyService, VacancySyncService

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_vacancy_service(db: DbSession) -> VacancyService:
    """Функция для инъекции зависимости VacancyService"""
    return VacancyService(db)


def get_vacancy_sync_service(db: DbSession) -> VacancySyncService:
    """Функция для инъекции зависимости VacancyService"""
    return VacancySyncService(db)


VacancyServiceDep = Annotated[VacancyService, Depends(get_vacancy_service)]
VacancySyncServiceDep = Annotated[VacancySyncService, Depends(get_vacancy_sync_service)]
