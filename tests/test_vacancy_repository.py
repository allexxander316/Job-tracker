from datetime import datetime, timezone

import pytest

from app.core.enums import Status, SortField, SortOrder
from app.vacancies.repository import VacancyRepository
from app.vacancies.schemas import VacancyFilterParams, VacancySortParams
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
        vacancy,
        {"header": "Senior Python Developer", "updated_at": datetime.now(timezone.utc)},
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

    query = repo.build_select_query(VacancyFilterParams(), VacancySortParams())
    result = await session.execute(query)
    all_vacancies = result.scalars().all()
    assert len(all_vacancies) == 2


async def test_filter_by_status(session):
    repo = VacancyRepository(session)

    repo.add_vacancy(make_vacancy_data(external_id=1, status="NEW"))
    repo.add_vacancy(make_vacancy_data(external_id=2, status="VIEWED"))
    repo.add_vacancy(make_vacancy_data(external_id=3, status="NEW"))
    await session.commit()

    filters = VacancyFilterParams(status=Status.NEW)
    query = repo.build_select_query(filters, VacancySortParams())
    result = await session.execute(query)
    vacancies = result.scalars().all()
    assert len(vacancies) == 2
    assert all(v.status == "NEW" for v in vacancies)


async def test_filter_by_search(session):
    repo = VacancyRepository(session)

    repo.add_vacancy(make_vacancy_data(external_id=1, header="Python Developer"))
    repo.add_vacancy(make_vacancy_data(external_id=2, header="Go Developer"))
    repo.add_vacancy(make_vacancy_data(external_id=3, header="Java Developer"))
    await session.commit()

    filters = VacancyFilterParams(search="Python")
    query = repo.build_select_query(filters, VacancySortParams())
    result = await session.execute(query)
    vacancies = result.scalars().all()
    assert len(vacancies) == 1
    assert vacancies[0].header == "Python Developer"


async def test_filter_by_salary_min(session):
    repo = VacancyRepository(session)

    repo.add_vacancy(
        make_vacancy_data(external_id=1, salary_from=50_000, salary_to=80_000)
    )
    repo.add_vacancy(
        make_vacancy_data(external_id=2, salary_from=100_000, salary_to=150_000)
    )
    repo.add_vacancy(
        make_vacancy_data(external_id=3, salary_from=120_000, salary_to=200_000)
    )
    await session.commit()

    filters = VacancyFilterParams(salary_min=100_000)
    query = repo.build_select_query(filters, VacancySortParams())
    result = await session.execute(query)
    vacancies = result.scalars().all()
    assert len(vacancies) == 2
    assert all(v.external_id in [2, 3] for v in vacancies)


async def test_filter_by_salary_max(session):
    repo = VacancyRepository(session)

    repo.add_vacancy(
        make_vacancy_data(external_id=1, salary_from=50_000, salary_to=80_000)
    )
    repo.add_vacancy(
        make_vacancy_data(external_id=2, salary_from=100_000, salary_to=150_000)
    )
    repo.add_vacancy(
        make_vacancy_data(external_id=3, salary_from=200_000, salary_to=300_000)
    )
    await session.commit()

    filters = VacancyFilterParams(salary_max=100_000)
    query = repo.build_select_query(filters, VacancySortParams())
    result = await session.execute(query)
    vacancies = result.scalars().all()
    assert len(vacancies) == 2
    assert all(v.external_id in [1, 2] for v in vacancies)


async def test_include_unknown_salary_false(session):
    repo = VacancyRepository(session)

    repo.add_vacancy(
        make_vacancy_data(external_id=1, salary_from=100_000, salary_to=150_000)
    )
    repo.add_vacancy(make_vacancy_data(external_id=2, salary_from=0, salary_to=0))
    await session.commit()

    filters = VacancyFilterParams(salary_min=50_000, include_unknown_salary=False)
    query = repo.build_select_query(filters, VacancySortParams())
    result = await session.execute(query)
    vacancies = result.scalars().all()
    assert len(vacancies) == 1
    assert vacancies[0].external_id == 1


async def test_include_unknown_salary_true(session):
    repo = VacancyRepository(session)

    repo.add_vacancy(
        make_vacancy_data(external_id=1, salary_from=100_000, salary_to=150_000)
    )
    repo.add_vacancy(make_vacancy_data(external_id=2, salary_from=0, salary_to=0))
    await session.commit()

    filters = VacancyFilterParams(salary_min=0, include_unknown_salary=True)
    query = repo.build_select_query(filters, VacancySortParams())
    result = await session.execute(query)
    vacancies = result.scalars().all()
    assert len(vacancies) == 2


async def test_sort_asc(session):
    repo = VacancyRepository(session)

    repo.add_vacancy(make_vacancy_data(external_id=1, salary_from=100_000))
    repo.add_vacancy(make_vacancy_data(external_id=2, salary_from=50_000))
    repo.add_vacancy(make_vacancy_data(external_id=3, salary_from=200_000))
    await session.commit()

    sort = VacancySortParams(sort_by=SortField.salary_from, sort_order=SortOrder.asc)
    query = repo.build_select_query(VacancyFilterParams(), sort)
    result = await session.execute(query)
    vacancies = result.scalars().all()
    assert [v.salary_from for v in vacancies] == [50_000, 100_000, 200_000]


async def test_sort_desc(session):
    repo = VacancyRepository(session)

    repo.add_vacancy(make_vacancy_data(external_id=1, salary_from=100_000))
    repo.add_vacancy(make_vacancy_data(external_id=2, salary_from=50_000))
    repo.add_vacancy(make_vacancy_data(external_id=3, salary_from=200_000))
    await session.commit()

    sort = VacancySortParams(sort_by=SortField.salary_from, sort_order=SortOrder.desc)
    query = repo.build_select_query(VacancyFilterParams(), sort)
    result = await session.execute(query)
    vacancies = result.scalars().all()
    assert [v.salary_from for v in vacancies] == [200_000, 100_000, 50_000]


async def test_combined_filters(session):
    repo = VacancyRepository(session)

    repo.add_vacancy(
        make_vacancy_data(
            external_id=1, status="NEW", salary_from=50_000, salary_to=80_000
        )
    )
    repo.add_vacancy(
        make_vacancy_data(
            external_id=2, status="NEW", salary_from=100_000, salary_to=150_000
        )
    )
    repo.add_vacancy(
        make_vacancy_data(
            external_id=3, status="VIEWED", salary_from=200_000, salary_to=300_000
        )
    )
    await session.commit()

    filters = VacancyFilterParams(status=Status.NEW, salary_min=80_000)
    query = repo.build_select_query(filters, VacancySortParams())
    result = await session.execute(query)
    vacancies = result.scalars().all()
    assert len(vacancies) == 2
    assert all(v.external_id in [1, 2] for v in vacancies)


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
