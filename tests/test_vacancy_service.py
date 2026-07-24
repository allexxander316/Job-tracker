from datetime import UTC

import pytest
import pytest_asyncio

from app.core.enums import Status
from app.vacancies.schemas import VacancyUpdateSchema
from app.vacancies.services import VacancyNotFoundError, VacancyService
from tests.conftest import make_vacancy_data

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def service(session):
    return VacancyService(session)


class TestVacancyService:
    async def test_insert(self, session, service, mocker):
        created = await service.insert_vacancy(
            make_vacancy_data(external_id="2", header="Go Developer")
        )
        assert created.external_id == "2"
        assert created.header == "Go Developer"
        with pytest.raises(VacancyNotFoundError):
            await service.get_by_id(created.id + 1)

    async def test_get_by_id_found(self, session, service):
        created = await service.insert_vacancy(
            make_vacancy_data(header="Python Developer")
        )
        vacancy = await service.get_by_id(created.id)
        assert vacancy.id == created.id
        assert vacancy.header == "Python Developer"

    async def test_get_by_id_not_found(self, session, service):
        with pytest.raises(VacancyNotFoundError):
            await service.get_by_id(999)

    async def test_update_vacancy(self, session, service):
        created = await service.insert_vacancy(make_vacancy_data())

        updated = await service.update_vacancy(
            created.id, VacancyUpdateSchema(header="Senior Python Developer")
        )
        assert updated.header == "Senior Python Developer"

        vacancy = await service.get_by_id(created.id)
        assert vacancy.header == "Senior Python Developer"

    async def test_change_status(self, session, service):
        created = await service.insert_vacancy(make_vacancy_data())

        result = await service.change_status(created.id, Status.VIEWED)
        assert result.status == Status.VIEWED

    async def test_delete_by_id(self, session, service):
        created = await service.insert_vacancy(make_vacancy_data())
        await service.delete_by_id(created.id)
        with pytest.raises(VacancyNotFoundError):
            await service.get_by_id(created.id)

    async def test_update_not_found(self, session, service):
        with pytest.raises(VacancyNotFoundError):
            await service.update_vacancy(999, VacancyUpdateSchema(header="Developer"))

    async def test_change_status_not_found(self, session, service):
        with pytest.raises(VacancyNotFoundError):
            await service.change_status(999, Status.VIEWED)

    async def test_get_changes(self, session, service):
        from datetime import datetime

        from app.vacancies.models import VacancyChangeORM

        created = await service.insert_vacancy(make_vacancy_data())
        change = VacancyChangeORM(
            vacancy_id=created.id,
            changes={"header": {"old": "Python", "new": "Senior"}},
            changed_at=datetime.now(UTC),
            acknowledged=False,
        )
        session.add(change)
        await session.commit()

        changes = await service.get_changes(created.id)
        assert len(changes) == 1
        assert changes[0].changes["header"]["old"] == "Python"

    async def test_get_changes_not_found(self, session, service):
        with pytest.raises(VacancyNotFoundError):
            await service.get_changes(999)

    async def test_acknowledge_changes(self, session, service):
        from datetime import datetime

        from app.vacancies.models import VacancyChangeORM

        created = await service.insert_vacancy(make_vacancy_data())
        change = VacancyChangeORM(
            vacancy_id=created.id,
            changes={"header": {"old": "Python", "new": "Senior"}},
            changed_at=datetime.now(UTC),
            acknowledged=False,
        )
        session.add(change)
        await session.commit()

        result = await service.acknowledge_changes(created.id)
        assert result.id == created.id

        changes = await service.get_changes(created.id)
        assert changes[0].acknowledged is True

    async def test_acknowledge_changes_not_found(self, session, service):
        with pytest.raises(VacancyNotFoundError):
            await service.acknowledge_changes(999)
