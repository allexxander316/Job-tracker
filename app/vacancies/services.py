from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from .models import VacancyORM
from .repository import VacancyRepository
from app.parsers.hh_api import get_vacancies
from app.vacancies.schemas import VacancySchema


class VacancyService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.vacancy_repository = VacancyRepository(session)

    async def select_vacancies(self) -> list[VacancySchema]:
        vacancies_orm = await self.vacancy_repository.select_vacancies()
        return [VacancySchema.model_validate(vacancy) for vacancy in vacancies_orm]

    def insert_vacancy_without_saving(self, vacancy_data: dict) -> None:
        self.vacancy_repository.add_vacancy(vacancy_data)

    async def insert_vacancy(self, vacancy_data: dict) -> None:
        self.vacancy_repository.add_vacancy(vacancy_data)
        await self.session.commit()

    async def get_by_external_id(self, external_id: str) -> VacancySchema | None:
        vacancy_orm = await self.vacancy_repository.get_by_external_id(int(external_id))
        if vacancy_orm is None:
            return None
        return VacancySchema.model_validate(vacancy_orm)

    def update_vacancy_without_saving(self, vacancy: VacancyORM, vacancy_data: dict) -> None:
       self.vacancy_repository.update_vacancy(vacancy, vacancy_data)

    async def delete_by_external_id(self, external_id: str) -> None:
        await self.vacancy_repository.delete_vacancy(int(external_id))
        await self.session.commit()

    async def sync_all(self):
        hh_vacancies = await get_vacancies()
        existing = await self.vacancy_repository.get_all_by_external_ids(
            [v["external_id"] for v in hh_vacancies]
        )
        existing_map = {v.external_id: v for v in existing}
        for vacancy in hh_vacancies:
            vacancy_from_db = existing_map.get(vacancy["external_id"])
            if vacancy_from_db is None:
                self.insert_vacancy_without_saving(vacancy)
                continue

            comparable = {"header", "description", "url", "salary_from", "salary_to", "area", "experience"}

            changed = any(
                vacancy.get(field) != getattr(vacancy_from_db, field, None)
                for field in comparable
            )

            if changed:
                vacancy_to_db = {
                    **vacancy,
                    "updated_at": datetime.now(),
                    "status": vacancy_from_db.status
                }

                self.update_vacancy_without_saving(vacancy_from_db, vacancy_to_db)

        await self.session.commit()