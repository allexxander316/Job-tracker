from typing import Any

from sqlalchemy import select, or_, and_, Select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.vacancies.models import VacancyORM, VacancyChangeORM
from app.core.enums import SortOrder
from app.vacancies.schemas import VacancyFilterParams, VacancySortParams


class VacancyRepository:
    def __init__(self, async_session: AsyncSession) -> None:
        self.async_session = async_session

    async def select_vacancies(self) -> list[VacancyORM]:
        result = await self.async_session.scalars(select(VacancyORM))
        return list(result.all())

    async def get_by_id(self, vacancy_id: int) -> VacancyORM | None:
        stmt = select(VacancyORM).where(VacancyORM.id == vacancy_id)
        vacancy = await self.async_session.execute(stmt)
        return vacancy.scalar_one_or_none()

    async def get_by_source_external_id(
        self, source: str, external_id: str
    ) -> VacancyORM | None:
        stmt = select(VacancyORM).where(
            VacancyORM.source == source, VacancyORM.external_id == external_id
        )
        vacancy = await self.async_session.execute(stmt)
        return vacancy.scalar_one_or_none()

    async def get_all_by_source_external_ids(
        self, pairs: list[tuple[str, str]]
    ) -> list[VacancyORM]:
        stmt = select(VacancyORM).where(
            tuple_(VacancyORM.source, VacancyORM.external_id).in_(pairs)
        )
        result = await self.async_session.execute(stmt)
        return list(result.scalars().all())

    def add_vacancy(self, vacancy_data: dict) -> VacancyORM:
        """Добавляет в сессию без сохранения"""
        vacancy = VacancyORM(**vacancy_data)
        self.async_session.add(vacancy)
        return vacancy

    def update_vacancy(self, vacancy: VacancyORM, vacancy_data: dict) -> None:
        for key, value in vacancy_data.items():
            setattr(vacancy, key, value)

    async def delete_vacancy(self, vacancy: VacancyORM) -> VacancyORM | None:
        await self.async_session.delete(vacancy)
        return vacancy

    def _build_filters(self, filters: VacancyFilterParams) -> list:
        clauses = []

        if filters.status:
            clauses.append(VacancyORM.status == filters.status.value)

        if filters.search:
            pattern = f"%{filters.search}%"
            clauses.append(
                or_(
                    VacancyORM.header.ilike(pattern),
                    VacancyORM.description.ilike(pattern),
                    VacancyORM.employer_name.ilike(pattern),
                    VacancyORM.city.ilike(pattern),
                )
            )

        if filters.salary_min is not None:
            clauses.append(
                (VacancyORM.salary_to >= filters.salary_min)
                | (VacancyORM.salary_from >= filters.salary_min)
            )
        if filters.salary_max is not None:
            clauses.append(VacancyORM.salary_from <= filters.salary_max)

        if not filters.include_unknown_salary and (
            filters.salary_min is not None or filters.salary_max is not None
        ):
            clauses.append((VacancyORM.salary_from != 0) | (VacancyORM.salary_to != 0))

        if filters.city:
            clauses.append(VacancyORM.city.ilike(f"%{filters.city}%"))
        if filters.employer_name:
            clauses.append(VacancyORM.employer_name.ilike(f"%{filters.employer_name}%"))
        if filters.experience:
            clauses.append(VacancyORM.experience == filters.experience)
        if filters.area:
            clauses.append(VacancyORM.area == filters.area)
        if filters.date_from:
            clauses.append(VacancyORM.created_at >= filters.date_from)
        if filters.date_to:
            clauses.append(VacancyORM.created_at <= filters.date_to)

        return clauses

    def build_select_query(
        self, filters: VacancyFilterParams, sort: VacancySortParams
    ) -> Select[Any]:
        query = select(VacancyORM)
        clauses = self._build_filters(filters)
        if clauses:
            query = query.where(and_(*clauses))

        sort_column = getattr(VacancyORM, sort.sort_by.value)
        order = (
            sort_column.asc()
            if sort.sort_order == SortOrder.asc
            else sort_column.desc()
        )
        query = query.order_by(order, VacancyORM.id.asc())
        return query

    async def get_unacknowledged_ids(self, vacancy_ids: list[int]) -> set[int]:
        if not vacancy_ids:
            return set()
        result = await self.async_session.execute(
            select(VacancyChangeORM.vacancy_id).where(
                VacancyChangeORM.vacancy_id.in_(vacancy_ids),
                VacancyChangeORM.acknowledged.is_(False),
            )
        )
        return {row[0] for row in result}
