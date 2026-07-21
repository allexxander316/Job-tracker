from unittest.mock import patch

import pytest

from app.vacancies.repository import VacancyRepository
from app.vacancies.services import VacancySyncService
from tests.conftest import make_vacancy_data


class TestVacancySyncService:
    @pytest.mark.asyncio
    @patch("app.vacancies.services.get_vacancies")
    async def test_sync_all_creates_new(self, mock_get_vacancies, session):
        mock_get_vacancies.return_value = [
            make_vacancy_data(external_id="1"),
            make_vacancy_data(external_id="2", header="Go Developer"),
        ]

        service = VacancySyncService(session)
        await service.sync_all()

        repo = VacancyRepository(session)
        v1 = await repo.get_by_source_external_id("hh", "1")
        v2 = await repo.get_by_source_external_id("hh", "2")
        assert v1 is not None
        assert v2 is not None
        assert v2.header == "Go Developer"

    @pytest.mark.asyncio
    @patch("app.vacancies.services.get_vacancies")
    async def test_sync_all_updates_new(self, mock_get_vacancies, session):
        repo = VacancyRepository(session)
        repo.add_vacancy(make_vacancy_data(external_id="1"))
        await session.commit()

        mock_get_vacancies.return_value = [
            make_vacancy_data(external_id="1", header="Senior Python Developer"),
        ]

        service = VacancySyncService(session)
        await service.sync_all()

        updated = await repo.get_by_source_external_id("hh", "1")
        assert updated is not None
        assert updated.header == "Senior Python Developer"
        assert updated.updated_at > updated.created_at

    @pytest.mark.asyncio
    @patch("app.vacancies.services.get_vacancies")
    async def test_sync_all_skips_unchanged(self, mock_get_vacancies, session):
        repo = VacancyRepository(session)
        repo.add_vacancy(make_vacancy_data(external_id="1"))
        await session.commit()

        mock_get_vacancies.return_value = [make_vacancy_data(external_id="1")]

        service = VacancySyncService(session)
        await service.sync_all()

        updated = await repo.get_by_source_external_id("hh", "1")
        assert updated is not None
        assert updated.updated_at == updated.created_at

    @pytest.mark.asyncio
    @patch("app.vacancies.services.get_vacancies")
    async def test_sync_all_different_sources_dont_collide(
        self, mock_get_vacancies, session
    ):
        repo = VacancyRepository(session)
        repo.add_vacancy(
            make_vacancy_data(source="hh", external_id="1", header="HH Vacancy")
        )
        await session.commit()

        mock_get_vacancies.return_value = [
            make_vacancy_data(
                source="linkedin", external_id="1", header="LinkedIn Vacancy"
            ),
        ]

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
    @patch("app.vacancies.services.get_vacancies")
    async def test_sync_all_empty_list(self, mock_get_vacancies, session):
        mock_get_vacancies.return_value = []

        service = VacancySyncService(session)
        await service.sync_all()

        repo = VacancyRepository(session)
        all_v = await repo.select_vacancies()
        assert len(all_v) == 0

    def test_vacancy_has_changed_true(self):
        from_db = type(
            "Vacancy",
            (),
            {
                "header": "Python",
                "description": "desc",
                "url": "url",
                "salary_from": 100,
                "salary_to": 200,
                "area": 113,
                "experience": 2,
            },
        )()

        from_hh = {
            "header": "Python Changed",
            "description": "desc",
            "url": "url",
            "salary_from": 100,
            "salary_to": 200,
            "area": 113,
            "experience": 2,
        }

        assert VacancySyncService._vacancy_has_changed(from_hh, from_db) is True

    def test_vacancy_has_changed_false(self):
        from_db = type(
            "Vacancy",
            (),
            {
                "header": "Python",
                "description": "desc",
                "url": "url",
                "salary_from": 100,
                "salary_to": 200,
                "area": 113,
                "experience": 2,
            },
        )()

        from_hh = {
            "header": "Python",
            "description": "desc",
            "url": "url",
            "salary_from": 100,
            "salary_to": 200,
            "area": 113,
            "experience": 2,
        }

        assert VacancySyncService._vacancy_has_changed(from_hh, from_db) is False

    def test_vacancy_has_changed_ignores_non_comparable(self):
        from_db = type(
            "Vacancy",
            (),
            {
                "header": "Python",
                "description": "desc",
                "url": "url",
                "salary_from": 100,
                "salary_to": 200,
                "area": 113,
                "experience": 2,
            },
        )()

        from_hh = {
            "header": "Python",
            "description": "desc",
            "url": "url",
            "salary_from": 100,
            "salary_to": 200,
            "area": 113,
            "experience": 2,
            "city": "Moscow",
            "status": "VIEWED",
        }

        assert VacancySyncService._vacancy_has_changed(from_hh, from_db) is False
