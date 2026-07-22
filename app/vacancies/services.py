from datetime import datetime, timezone

from fastapi_pagination import Page, Params
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import Status as VacancyStatusEnum
from app.core.logger import get_logger
from app.vacancies.models import VacancyORM, VacancyChangeORM
from app.vacancies.repository import VacancyRepository
from app.parsers import PARSERS
from app.vacancies.schemas import (
    VacancySchema,
    VacancyUpdateSchema,
    VacancyFilterParams,
    VacancySortParams,
    VacancyChangeSchema,
)
from app.vacancies.sync_status import sync_tracker
from app.core.database import async_session

logger = get_logger(__name__)


class VacancyNotFoundError(Exception):
    """Вакансия не найдена в бд"""


class VacancyService:
    """CRUD для вакансий"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.vacancy_repository = VacancyRepository(session)

    async def _get_vacancy_or_404(self, vacancy_id: int) -> VacancyORM:
        vacancy = await self.vacancy_repository.get_by_id(vacancy_id)
        if vacancy is None:
            raise VacancyNotFoundError(f"Вакансия с id {vacancy_id} не найдена")
        return vacancy

    async def _update_fields(
        self, vacancy_id: int, data: VacancyUpdateSchema
    ) -> VacancySchema:
        vacancy = await self._get_vacancy_or_404(vacancy_id)
        update_dict = data.model_dump(exclude_unset=True)
        self.vacancy_repository.update_vacancy(vacancy, update_dict)
        await self.session.commit()
        return VacancySchema.model_validate(vacancy)

    async def select_vacancies(
        self, filters: VacancyFilterParams, sort: VacancySortParams, params: Params
    ) -> Page[VacancySchema]:
        query = self.vacancy_repository.build_select_query(filters, sort)
        result = await paginate(self.session, query, params)

        unacked_ids = await self.vacancy_repository.get_unacknowledged_ids(
            [v.id for v in result.items]
        )
        items = [VacancySchema.model_validate(v) for v in result.items]
        for item in items:
            item.has_unacknowledged_changes = item.id in unacked_ids

        return Page(
            items=items,
            total=result.total,
            page=result.page,
            size=result.size,
            pages=result.pages,
        )

    async def insert_vacancy(self, vacancy_data: dict) -> VacancySchema:
        orm = self.vacancy_repository.add_vacancy(vacancy_data)
        await self.session.commit()
        return VacancySchema.model_validate(orm)

    async def update_vacancy(
        self, vacancy_id: int, vacancy_update: VacancyUpdateSchema
    ) -> VacancySchema:
        return await self._update_fields(vacancy_id, vacancy_update)

    async def change_status(
        self, vacancy_id: int, new_status: VacancyStatusEnum
    ) -> VacancySchema:
        vacancy = await self._get_vacancy_or_404(vacancy_id)
        self.vacancy_repository.update_vacancy(vacancy, {"status": new_status})
        await self.session.commit()
        return VacancySchema.model_validate(vacancy)

    async def get_by_id(self, vacancy_id: int) -> VacancySchema:
        vacancy = await self._get_vacancy_or_404(vacancy_id)
        return VacancySchema.model_validate(vacancy)

    async def delete_by_id(self, vacancy_id: int) -> None:
        vacancy = await self._get_vacancy_or_404(vacancy_id)
        await self.vacancy_repository.delete_vacancy(vacancy)
        await self.session.commit()

    async def get_changes(self, vacancy_id: int) -> list[VacancyChangeSchema]:
        await self._get_vacancy_or_404(vacancy_id)
        orm_changes = await self.vacancy_repository.get_changes_by_vacancy(vacancy_id)
        return [VacancyChangeSchema.model_validate(c) for c in orm_changes]

    async def acknowledge_changes(self, vacancy_id: int) -> VacancySchema:
        vacancy = await self._get_vacancy_or_404(vacancy_id)
        await self.vacancy_repository.acknowledge_changes(vacancy_id)
        await self.session.commit()
        return VacancySchema.model_validate(vacancy)


class VacancySyncService:
    """Синхронизация вакансий в бд с HH вакансиями"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.vacancy_repository = VacancyRepository(session)

    @staticmethod
    def _build_diff(old, new: dict) -> dict:
        comparable = {
            "header",
            "description",
            "url",
            "salary_from",
            "salary_to",
            "area",
            "experience",
        }
        diff = {}
        for field in comparable:
            old_val = getattr(old, field, None)
            new_val = new.get(field)
            if old_val != new_val:
                diff[field] = {"old": old_val, "new": new_val}
        return diff

    async def sync_all(self) -> dict:
        """Синхронизирует данные с с выбранных сайтов с данными в бд"""

        all_vacancies = []
        for parser_fn in PARSERS:
            batch = await parser_fn()
            all_vacancies.extend(batch)

        unique = {}
        for v in all_vacancies:
            key = (v["source"], v["external_id"])
            unique[key] = v
        all_vacancies = list(unique.values())

        logger.info("Syncing %s vacancies", len(all_vacancies))

        pairs = [(v["source"], v["external_id"]) for v in all_vacancies]
        existing = await self.vacancy_repository.get_all_by_source_external_ids(pairs)
        existing_map = {(v.source, v.external_id): v for v in existing}

        created = 0
        updated = 0
        skipped = 0

        for vacancy in all_vacancies:
            key = (vacancy["source"], vacancy["external_id"])
            vacancy_from_db = existing_map.get(key)

            if vacancy_from_db is None:
                self.vacancy_repository.add_vacancy(vacancy)
                created += 1
                continue

            diff = self._build_diff(vacancy_from_db, vacancy)

            if diff:
                vacancy_to_db = {
                    **vacancy,
                    "updated_at": datetime.now(timezone.utc),
                    "status": vacancy_from_db.status,
                }

                self.session.add(
                    VacancyChangeORM(
                        vacancy_id=vacancy_from_db.id,
                        changes=diff,
                        changed_at=datetime.now(timezone.utc),
                        acknowledged=False,
                    )
                )

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

    @classmethod
    async def run_sync_in_background(cls) -> None:
        """Обёртка для запуска sync_all в фоне с открытием своей сессии и трекингом статуса"""
        if sync_tracker.is_running():
            logger.warning("Sync already running, skipping duplicate trigger")
            return

        sync_tracker.start()
        try:
            async with async_session() as session:
                service = cls(session)
                report = await service.sync_all()
                sync_tracker.complete(report)
        except Exception as e:
            logger.exception("Background sync failed")
            sync_tracker.fail(str(e))
