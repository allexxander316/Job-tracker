import pytest

from app.core.enums import Status
from app.vacancies.schemas import VacancyUpdateSchema
from app.vacancies.services import VacancyService, VacancyNotFoundError
from tests.conftest import make_vacancy_data

pytestmark = pytest.mark.asyncio


class TestVacancyService:
    async def test_insert(self, session, mocker):
        service = VacancyService(session)
        await service.insert_vacancy(
            make_vacancy_data(external_id=2, header="Go Developer")
        )
        with pytest.raises(VacancyNotFoundError):
            await service.get_by_external_id(1)

    async def test_get_by_external_id_found(self, session):
        service = VacancyService(session)
        await service.insert_vacancy(make_vacancy_data(external_id=42))

        vacancy = await service.get_by_external_id(42)
        assert vacancy.external_id == 42
        assert vacancy.header == "Python Developer"

    async def test_get_by_external_id_not_found(self, session):
        service = VacancyService(session)
        with pytest.raises(VacancyNotFoundError):
            await service.get_by_external_id(999)

    async def test_update_vacancy(self, session):
        service = VacancyService(session)
        await service.insert_vacancy(make_vacancy_data(external_id=1))

        updated = await service.update_vacancy(
            1, VacancyUpdateSchema(header="Senior Python Developer")
        )
        assert updated.header == "Senior Python Developer"

        vacancy = await service.get_by_external_id(1)
        assert vacancy.header == "Senior Python Developer"

    async def test_change_status(self, session):
        service = VacancyService(session)
        await service.insert_vacancy(make_vacancy_data(external_id=1))

        result = await service.change_status(1, Status.VIEWED)
        assert result.status == Status.VIEWED

    async def test_delete_by_external_id(self, session):
        service = VacancyService(session)
        await service.insert_vacancy(make_vacancy_data(external_id=1))
        await service.delete_by_external_id(1)
        with pytest.raises(VacancyNotFoundError):
            await service.get_by_external_id(1)

    async def test_update_not_found(self, session):
        service = VacancyService(session)
        with pytest.raises(VacancyNotFoundError):
            await service.update_vacancy(999, VacancyUpdateSchema(header="Developer"))

    async def test_change_status_not_found(self, session):
        service = VacancyService(session)
        with pytest.raises(VacancyNotFoundError):
            await service.change_status(999, Status.VIEWED)
