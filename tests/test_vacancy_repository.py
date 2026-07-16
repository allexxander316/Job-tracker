from datetime import datetime

import pytest

from app.vacancies.repository import VacancyRepository
from tests.conftest import make_vacancy_data

pytestmark = pytest.mark.asyncio


async def test_create_and_get_by_external_id(session):
    repo = VacancyRepository(session)
    data = make_vacancy_data(external_id=10)

    repo.add_vacancy(data)
    await session.commit()

    vacancy = await repo.get_by_external_id(10)
    assert vacancy is not None
    assert vacancy.header == "Python Developer"
    assert vacancy.external_id == 10
    assert vacancy.city == "Москва"


async def test_update_vacancy(session):
    repo = VacancyRepository(session)
    data = make_vacancy_data(external_id=7)

    repo.add_vacancy(data)
    await session.commit()

    vacancy = await repo.get_by_external_id(7)
    assert vacancy is not None
    old_updated_at = vacancy.updated_at

    repo.update_vacancy(
        vacancy, {"header": "Senior Python Developer", "updated_at": datetime.now()}
    )
    await session.commit()

    updated = await repo.get_by_external_id(7)
    assert updated is not None
    assert updated.header == "Senior Python Developer"
    assert updated.updated_at > old_updated_at


async def test_get_all_by_external_ids(session):
    repo = VacancyRepository(session)

    repo.add_vacancy(make_vacancy_data(external_id=1))
    repo.add_vacancy(make_vacancy_data(external_id=2, header="Go Developer"))
    await session.commit()

    vacancies = await repo.get_all_by_external_ids([1, 2])
    assert len(vacancies) == 2

    headers = {v.header for v in vacancies}
    assert headers == {"Python Developer", "Go Developer"}


async def test_select_vacancies(session):
    repo = VacancyRepository(session)

    repo.add_vacancy(make_vacancy_data(external_id=10))
    repo.add_vacancy(make_vacancy_data(external_id=11))
    await session.commit()

    all_vacancies = await repo.select_vacancies()
    assert len(all_vacancies) == 2


async def test_delete_vacancy(session):
    repo = VacancyRepository(session)

    repo.add_vacancy(make_vacancy_data(external_id=10))
    await session.commit()

    vacancy = await repo.get_by_external_id(10)
    assert vacancy is not None

    await repo.delete_vacancy(vacancy)
    await session.commit()

    deleted = await repo.get_by_external_id(10)
    assert deleted is None
