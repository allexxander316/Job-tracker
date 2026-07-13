from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.vacancies.models import VacancyORM
from app.vacancies.repository import VacancyRepository
from app.parsers.hh_api import get_vacancies
from app.vacancies.schemas import VacancySchema, VacancyUpdateSchema


class VacancyNotFoundError(Exception):
    """Вакансия не найдена в бд"""


class VacancyService:
    """CRUD для вакансий"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.vacancy_repository = VacancyRepository(session)

    async def select_vacancies(self) -> list[VacancySchema]:
        vacancies_orm = await self.vacancy_repository.select_vacancies()
        return [VacancySchema.model_validate(vacancy) for vacancy in vacancies_orm]

    async def insert_vacancy(self, vacancy_data: dict) -> None:
        self.vacancy_repository.add_vacancy(vacancy_data)
        await self.session.commit()

    async def update_vacancy(self, external_id: str, vacancy_update: VacancyUpdateSchema) -> None:
        vacancy = await self.vacancy_repository.get_by_external_id(int(external_id))
        if vacancy is None:
            raise VacancyNotFoundError(f"Вакансия с id {external_id} не найдена")
        update_dict = vacancy_update.model_dump(exclude_unset=True)
        self.vacancy_repository.update_vacancy(vacancy, update_dict)
        await self.session.commit()

    async def get_by_external_id(self, external_id: str) -> VacancySchema:
        vacancy = await self.vacancy_repository.get_by_external_id(int(external_id))
        if vacancy is None:
            raise VacancyNotFoundError(f"Вакансия с id {external_id} не найдена")
        return VacancySchema.model_validate(vacancy)

    async def delete_by_external_id(self, external_id: str) -> None:
        vacancy_for_delete = await self.vacancy_repository.get_by_external_id(int(external_id))
        if vacancy_for_delete is None:
            raise VacancyNotFoundError(f"Вакансия с id {external_id} не найдена")
        await self.vacancy_repository.delete_vacancy(vacancy_for_delete)
        await self.session.commit()


class VacancySyncService:
    """Синхронизация вакансий в бд с HH вакансиями"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.vacancy_repository = VacancyRepository(session)

    @staticmethod
    def _vacancy_has_changed(vacancy_from_hh: dict, vacancy_from_db) -> bool:
        """Проверяет, изменились ли значимые поля вакансии"""

        comparable = {"header", "description", "url", "salary_from", "salary_to", "area", "experience"}
        return any(
            vacancy_from_hh.get(field) != getattr(vacancy_from_db, field, None)
            for field in comparable
        )

    async def sync_all(self) -> None:
        """Синхронизирует данные с hh.ru с данными в бд"""

        hh_vacancies = await get_vacancies()
        existing_ids = [v["external_id"] for v in hh_vacancies]
        existing = await self.vacancy_repository.get_all_by_external_ids(existing_ids)
        existing_map = {v.external_id: v for v in existing}
        for vacancy in hh_vacancies:
            vacancy_from_db = existing_map.get(vacancy["external_id"])

            if vacancy_from_db is None:
                self.vacancy_repository.add_vacancy(vacancy)
                continue

            if self._vacancy_has_changed(vacancy, vacancy_from_db):
                vacancy_to_db = {
                    **vacancy,
                    "updated_at": datetime.now(),
                    "status": vacancy_from_db.status
                }

                self.vacancy_repository.update_vacancy(vacancy_from_db, vacancy_to_db)

        await self.session.commit()
