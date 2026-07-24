from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.vacancies.models import VacancyChangeORM, VacancyORM
from app.vacancies.repository import VacancyRepository
from app.vacancies.services import VacancySyncService
from tests.conftest import make_vacancy_data


class TestVacancySyncService:
    @pytest.mark.asyncio
    async def test_sync_all_creates_new(self, session):
        async def mock_hh():
            return [
                make_vacancy_data(external_id="1"),
                make_vacancy_data(external_id="2", header="Go Developer"),
            ]

        with patch("app.vacancies.services.PARSERS", [("hh", mock_hh)]):
            service = VacancySyncService(session)
            await service.sync_all()

        repo = VacancyRepository(session)
        v1 = await repo.get_by_source_external_id("hh", "1")
        v2 = await repo.get_by_source_external_id("hh", "2")
        assert v1 is not None
        assert v2 is not None
        assert v2.header == "Go Developer"

    @pytest.mark.asyncio
    async def test_sync_all_updates_new(self, session):
        repo = VacancyRepository(session)
        repo.add_vacancy(make_vacancy_data(external_id="1"))
        await session.commit()

        async def mock_hh():
            return [
                make_vacancy_data(external_id="1", header="Senior Python Developer")
            ]

        with patch("app.vacancies.services.PARSERS", [("hh", mock_hh)]):
            service = VacancySyncService(session)
            await service.sync_all()

        updated = await repo.get_by_source_external_id("hh", "1")
        assert updated is not None
        assert updated.header == "Senior Python Developer"
        assert updated.updated_at > updated.created_at

    @pytest.mark.asyncio
    async def test_sync_all_skips_unchanged(self, session):
        repo = VacancyRepository(session)
        repo.add_vacancy(make_vacancy_data(external_id="1"))
        await session.commit()

        async def mock_hh():
            return [make_vacancy_data(external_id="1")]

        with patch("app.vacancies.services.PARSERS", [("hh", mock_hh)]):
            service = VacancySyncService(session)
            await service.sync_all()

        updated = await repo.get_by_source_external_id("hh", "1")
        assert updated is not None
        assert updated.updated_at == updated.created_at

    @pytest.mark.asyncio
    async def test_sync_all_different_sources_dont_collide(self, session):
        repo = VacancyRepository(session)
        repo.add_vacancy(
            make_vacancy_data(source="hh", external_id="1", header="HH Vacancy")
        )
        await session.commit()

        async def mock_parser():
            return [
                make_vacancy_data(
                    source="linkedin", external_id="1", header="LinkedIn Vacancy"
                )
            ]

        with patch("app.vacancies.services.PARSERS", [("linkedin", mock_parser)]):
            service = VacancySyncService(session)
            await service.sync_all()

        hh_vacancy = await repo.get_by_source_external_id("hh", "1")
        linkedin_vacancy = await repo.get_by_source_external_id("linkedin", "1")

        assert hh_vacancy is not None
        assert hh_vacancy.header == "HH Vacancy"
        assert linkedin_vacancy is not None
        assert linkedin_vacancy.header == "LinkedIn Vacancy"
        assert hh_vacancy.id != linkedin_vacancy.id

    @pytest.mark.asyncio
    async def test_sync_all_empty_list(self, session):
        async def mock_hh():
            return []

        with patch("app.vacancies.services.PARSERS", [("hh", mock_hh)]):
            service = VacancySyncService(session)
            await service.sync_all()

        repo = VacancyRepository(session)
        all_v = await repo.select_vacancies()
        assert len(all_v) == 0

    def test_build_diff_detects_changes(self):
        old = VacancyORM(
            header="Python",
            description="desc",
            url="url",
            salary_from=100,
            salary_to=200,
            area=113,
            experience="between1And3",
        )
        new = {
            "header": "Python Changed",
            "description": "desc",
            "url": "url",
            "salary_from": 100,
            "salary_to": 200,
            "area": 113,
            "experience": "between1And3",
        }
        diff = VacancySyncService._build_diff(old, new)
        assert diff == {"header": {"old": "Python", "new": "Python Changed"}}

    def test_build_diff_empty_when_no_changes(self):
        old = VacancyORM(
            header="Python",
            description="desc",
            url="url",
            salary_from=100,
            salary_to=200,
            area=113,
            experience="between1And3",
        )
        new = {
            k: getattr(old, k)
            for k in (
                "header",
                "description",
                "url",
                "salary_from",
                "salary_to",
                "area",
                "experience",
            )
        }
        diff = VacancySyncService._build_diff(old, new)
        assert diff == {}

    def test_build_diff_ignores_non_comparable(self):
        old = VacancyORM(
            header="Python",
            description="desc",
            url="url",
            salary_from=100,
            salary_to=200,
            area=113,
            experience="between1And3",
        )
        new = {
            "header": "Python",
            "description": "desc",
            "url": "url",
            "salary_from": 100,
            "salary_to": 200,
            "area": 113,
            "experience": "between1And3",
            "city": "Moscow",
            "status": "VIEWED",
        }
        diff = VacancySyncService._build_diff(old, new)
        assert diff == {}

    @pytest.mark.asyncio
    async def test_sync_all_creates_change_record(self, session):
        repo = VacancyRepository(session)
        repo.add_vacancy(make_vacancy_data(external_id="1"))
        await session.commit()

        async def mock_hh():
            return [
                make_vacancy_data(external_id="1", header="Senior Python Developer")
            ]

        with patch("app.vacancies.services.PARSERS", [("hh", mock_hh)]):
            service = VacancySyncService(session)
            report = await service.sync_all()

        assert report["updated"] == 1
        assert report["created"] == 0
        assert report["skipped"] == 0

        stmt = select(VacancyChangeORM)
        result = await session.execute(stmt)
        changes = result.scalars().all()
        assert len(changes) == 1
        assert changes[0].changes["header"]["old"] == "Python Developer"
        assert changes[0].changes["header"]["new"] == "Senior Python Developer"
        assert changes[0].acknowledged is False
