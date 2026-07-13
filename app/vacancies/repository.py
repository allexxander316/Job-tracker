from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.vacancies.models import VacancyORM

class VacancyRepository:
    def __init__(self, async_session: AsyncSession) -> None:
        self.async_session = async_session

    async def select_vacancies(self) -> list[VacancyORM]:
        result = await self.async_session.scalars(select(VacancyORM))
        return list(result.all())

    async def get_by_external_id(self, external_id: int) -> VacancyORM | None:
        stmt = (
            select(VacancyORM)
            .where(VacancyORM.external_id == external_id)
        )

        vacancy = await self.async_session.execute(stmt)
        return vacancy.scalar_one_or_none()

    async def get_all_by_external_ids(self, external_ids: list[int]) -> list[VacancyORM]:
        stmt = select(VacancyORM).where(VacancyORM.external_id.in_(external_ids))
        result = await self.async_session.execute(stmt)
        return list(result.scalars().all())

    def add_vacancy(self, vacancy_data: dict) -> None:
        """Добавляет в сессию без сохранения"""
        self.async_session.add(VacancyORM(**vacancy_data))

    def update_vacancy(self, vacancy: VacancyORM, vacancy_data: dict) -> None:
        for key, value in vacancy_data.items():
            setattr(vacancy, key, value)

    async def delete_vacancy(self, external_id: int) -> VacancyORM | None:
        vacancy = await self.get_by_external_id(external_id)
        if vacancy is None:
            return None
        await self.async_session.delete(vacancy)
        return vacancy