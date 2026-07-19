from datetime import datetime, timezone

from fastapi_pagination import Page, paginate
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import Status as VacancyStatusEnum
from app.core.logger import get_logger
from app.vacancies.models import VacancyORM
from app.vacancies.repository import VacancyRepository
from app.parsers.hh_api import get_vacancies
from app.vacancies.schemas import VacancySchema, VacancyUpdateSchema
from vacancies.schemas import VacancyFilterParams, VacancySortParams

logger = get_logger(__name__)


class VacancyNotFoundError(Exception):
    """Вакансия не найдена в бд"""


class VacancyService:
    """CRUD для вакансий"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.vacancy_repository = VacancyRepository(session)

    async def _get_vacancy_or_404(self, external_id: int) -> VacancyORM:
        vacancy = await self.vacancy_repository.get_by_external_id(external_id)
        if vacancy is None:
            raise VacancyNotFoundError(f"Вакансия с id {external_id} не найдена")
        return vacancy

    async def _update_fields(
        self, external_id: int, data: VacancyUpdateSchema
    ) -> VacancySchema:
        vacancy = await self._get_vacancy_or_404(external_id)
        update_dict = data.model_dump(exclude_unset=True)
        self.vacancy_repository.update_vacancy(vacancy, update_dict)
        await self.session.commit()
        return VacancySchema.model_validate(vacancy)

    async def select_vacancies(
        self, filters: VacancyFilterParams, sort: VacancySortParams
    ) -> Page[VacancySchema]:
        query = self.vacancy_repository.build_select_query(filters, sort)
        return await paginate(self.session, query)

    async def insert_vacancy(self, vacancy_data: dict) -> None:
        self.vacancy_repository.add_vacancy(vacancy_data)
        await self.session.commit()

    async def update_vacancy(
        self, external_id: int, vacancy_update: VacancyUpdateSchema
    ) -> VacancySchema:
        return await self._update_fields(external_id, vacancy_update)

    async def change_status(
        self, external_id: int, new_status: VacancyStatusEnum
    ) -> VacancySchema:
        vacancy = await self._get_vacancy_or_404(external_id)
        self.vacancy_repository.update_vacancy(vacancy, {"status": new_status})
        await self.session.commit()
        return VacancySchema.model_validate(vacancy)

    async def get_by_external_id(self, external_id: int) -> VacancySchema:
        vacancy = await self._get_vacancy_or_404(external_id)
        return VacancySchema.model_validate(vacancy)

    async def delete_by_external_id(self, external_id: int) -> None:
        vacancy = await self._get_vacancy_or_404(external_id)
        await self.vacancy_repository.delete_vacancy(vacancy)
        await self.session.commit()


class VacancySyncService:
    """Синхронизация вакансий в бд с HH вакансиями"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.vacancy_repository = VacancyRepository(session)

    @staticmethod
    def _vacancy_has_changed(vacancy_from_hh: dict, vacancy_from_db) -> bool:
        """Проверяет, изменились ли значимые поля вакансии"""

        comparable = {
            "header",
            "description",
            "url",
            "salary_from",
            "salary_to",
            "area",
            "experience",
        }
        return any(
            vacancy_from_hh.get(field) != getattr(vacancy_from_db, field, None)
            for field in comparable
        )

    async def sync_all(self) -> dict:
        """Синхронизирует данные с hh.ru с данными в бд"""

        hh_vacancies = await get_vacancies()
        logger.info("Syncing %s vacancies", len(hh_vacancies))

        existing_ids = [v["external_id"] for v in hh_vacancies]
        existing = await self.vacancy_repository.get_all_by_external_ids(existing_ids)
        existing_map = {v.external_id: v for v in existing}

        created = 0
        updated = 0
        skipped = 0

        for vacancy in hh_vacancies:
            vacancy_from_db = existing_map.get(vacancy["external_id"])

            if vacancy_from_db is None:
                self.vacancy_repository.add_vacancy(vacancy)
                created += 1
                continue

            if self._vacancy_has_changed(vacancy, vacancy_from_db):
                vacancy_to_db = {
                    **vacancy,
                    "updated_at": datetime.now(timezone.utc),
                    "status": vacancy_from_db.status,
                }

                self.vacancy_repository.update_vacancy(vacancy_from_db, vacancy_to_db)
                updated += 1
            else:
                skipped += 1

        await self.session.commit()
        logger.info(
            "Sync done: created=%s, updated=%s, skipped=%s", created, updated, skipped
        )
        report = {"created": created, "updated": updated, "skipped": skipped}
        return report
