from datetime import datetime, timezone

import pytest

from app.core.enums import Status, SortField, SortOrder
from app.vacancies.repository import VacancyRepository
from app.vacancies.schemas import VacancyFilterParams, VacancySortParams
from tests.conftest import make_vacancy_data

pytestmark = pytest.mark.asyncio


@pytest.fixture
def repo(session):
    return VacancyRepository(session)


async def test_get_by_source_external_id(session, repo):
    data = make_vacancy_data(source="hh", external_id="10")

    repo.add_vacancy(data)
    await session.commit()

    vacancy = await repo.get_by_source_external_id("hh", "10")
    assert vacancy is not None
    assert vacancy.header == "Python Developer"
    assert vacancy.external_id == "10"
    assert vacancy.source == "hh"
    assert vacancy.city == "Москва"


async def test_get_by_id(session, repo):
    data = make_vacancy_data(source="hh", external_id="10")
    created = repo.add_vacancy(data)
    await session.commit()

    vacancy = await repo.get_by_id(created.id)
    assert vacancy is not None
    assert vacancy.id == created.id
    assert vacancy.external_id == "10"


async def test_source_isolation(session, repo):
    repo.add_vacancy(make_vacancy_data(source="hh", external_id="1"))
    repo.add_vacancy(make_vacancy_data(source="linkedin", external_id="1"))
    await session.commit()

    hh_vacancy = await repo.get_by_source_external_id("hh", "1")
    linkedin_vacancy = await repo.get_by_source_external_id("linkedin", "1")

    assert hh_vacancy is not None
    assert linkedin_vacancy is not None
    assert hh_vacancy.id != linkedin_vacancy.id


async def test_update_vacancy(session, repo):
    data = make_vacancy_data(external_id="7")
    created = repo.add_vacancy(data)
    await session.commit()

    vacancy = await repo.get_by_id(created.id)
    assert vacancy is not None
    old_updated_at = vacancy.updated_at

    repo.update_vacancy(
        vacancy,
        {"header": "Senior Python Developer", "updated_at": datetime.now(timezone.utc)},
    )
    await session.commit()

    updated = await repo.get_by_id(created.id)
    assert updated is not None
    assert updated.header == "Senior Python Developer"
    assert updated.updated_at > old_updated_at


async def test_get_all_by__source_external_ids(session, repo):
    repo.add_vacancy(make_vacancy_data(external_id="1"))
    repo.add_vacancy(make_vacancy_data(external_id="2", header="Go Developer"))
    await session.commit()

    vacancies = await repo.get_all_by_source_external_ids([("hh", "1"), ("hh", "2")])
    assert len(vacancies) == 2

    headers = {v.header for v in vacancies}
    assert headers == {"Python Developer", "Go Developer"}


async def test_select_vacancies(session, repo):
    repo.add_vacancy(make_vacancy_data(external_id="10"))
    repo.add_vacancy(make_vacancy_data(external_id="11"))
    await session.commit()

    query = repo.build_select_query(VacancyFilterParams(), VacancySortParams())
    result = await session.execute(query)
    all_vacancies = result.scalars().all()
    assert len(all_vacancies) == 2


async def test_filter_by_status(session, repo):
    repo.add_vacancy(make_vacancy_data(external_id="1", status="NEW"))
    repo.add_vacancy(make_vacancy_data(external_id="2", status="VIEWED"))
    repo.add_vacancy(make_vacancy_data(external_id="3", status="NEW"))
    await session.commit()

    filters = VacancyFilterParams(status=Status.NEW)
    query = repo.build_select_query(filters, VacancySortParams())
    result = await session.execute(query)
    vacancies = result.scalars().all()
    assert len(vacancies) == 2
    assert all(v.status == "NEW" for v in vacancies)


async def test_filter_by_search(session, repo):
    repo.add_vacancy(make_vacancy_data(external_id="1", header="Python Developer"))
    repo.add_vacancy(make_vacancy_data(external_id="2", header="Go Developer"))
    repo.add_vacancy(make_vacancy_data(external_id="3", header="Java Developer"))
    await session.commit()

    filters = VacancyFilterParams(search="Python")
    query = repo.build_select_query(filters, VacancySortParams())
    result = await session.execute(query)
    vacancies = result.scalars().all()
    assert len(vacancies) == 1
    assert vacancies[0].header == "Python Developer"


async def test_filter_by_salary_min(session, repo):
    v2 = repo.add_vacancy(
        make_vacancy_data(external_id="2", salary_from=100_000, salary_to=150_000)
    )
    v3 = repo.add_vacancy(
        make_vacancy_data(external_id="3", salary_from=120_000, salary_to=200_000)
    )
    await session.commit()

    filters = VacancyFilterParams(salary_min=100_000)
    query = repo.build_select_query(filters, VacancySortParams())
    result = await session.execute(query)
    vacancies = result.scalars().all()
    assert len(vacancies) == 2
    assert {v.id for v in vacancies} == {v2.id, v3.id}


async def test_filter_by_salary_max(session, repo):
    v1 = repo.add_vacancy(
        make_vacancy_data(external_id="1", salary_from=50_000, salary_to=80_000)
    )
    v2 = repo.add_vacancy(
        make_vacancy_data(external_id="2", salary_from=100_000, salary_to=150_000)
    )
    await session.commit()

    filters = VacancyFilterParams(salary_max=100_000)
    query = repo.build_select_query(filters, VacancySortParams())
    result = await session.execute(query)
    vacancies = result.scalars().all()
    assert len(vacancies) == 2
    assert {v.id for v in vacancies} == {v1.id, v2.id}


async def test_include_unknown_salary_false(session, repo):
    v1 = repo.add_vacancy(
        make_vacancy_data(external_id="1", salary_from=100_000, salary_to=150_000)
    )
    await session.commit()

    filters = VacancyFilterParams(salary_min=50_000, include_unknown_salary=False)
    query = repo.build_select_query(filters, VacancySortParams())
    result = await session.execute(query)
    vacancies = result.scalars().all()
    assert len(vacancies) == 1
    assert vacancies[0].id == v1.id


async def test_include_unknown_salary_true(session, repo):
    repo.add_vacancy(
        make_vacancy_data(external_id="1", salary_from=100_000, salary_to=150_000)
    )
    repo.add_vacancy(make_vacancy_data(external_id="2", salary_from=0, salary_to=0))
    await session.commit()

    filters = VacancyFilterParams(salary_min=0, include_unknown_salary=True)
    query = repo.build_select_query(filters, VacancySortParams())
    result = await session.execute(query)
    vacancies = result.scalars().all()
    assert len(vacancies) == 2


async def test_sort_asc(session, repo):
    repo.add_vacancy(make_vacancy_data(external_id="1", salary_from=100_000))
    repo.add_vacancy(make_vacancy_data(external_id="2", salary_from=50_000))
    repo.add_vacancy(make_vacancy_data(external_id="3", salary_from=200_000))
    await session.commit()

    sort = VacancySortParams(sort_by=SortField.salary_from, sort_order=SortOrder.asc)
    query = repo.build_select_query(VacancyFilterParams(), sort)
    result = await session.execute(query)
    vacancies = result.scalars().all()
    assert [v.salary_from for v in vacancies] == [50_000, 100_000, 200_000]


async def test_sort_desc(session, repo):
    repo.add_vacancy(make_vacancy_data(external_id="1", salary_from=100_000))
    repo.add_vacancy(make_vacancy_data(external_id="2", salary_from=50_000))
    repo.add_vacancy(make_vacancy_data(external_id="3", salary_from=200_000))
    await session.commit()

    sort = VacancySortParams(sort_by=SortField.salary_from, sort_order=SortOrder.desc)
    query = repo.build_select_query(VacancyFilterParams(), sort)
    result = await session.execute(query)
    vacancies = result.scalars().all()
    assert [v.salary_from for v in vacancies] == [200_000, 100_000, 50_000]


async def test_combined_filters(session, repo):
    v1 = repo.add_vacancy(
        make_vacancy_data(
            external_id="1", status="NEW", salary_from=50_000, salary_to=80_000
        )
    )
    v2 = repo.add_vacancy(
        make_vacancy_data(
            external_id="2", status="NEW", salary_from=100_000, salary_to=150_000
        )
    )
    await session.commit()

    filters = VacancyFilterParams(status=Status.NEW, salary_min=80_000)
    query = repo.build_select_query(filters, VacancySortParams())
    result = await session.execute(query)
    vacancies = result.scalars().all()
    assert len(vacancies) == 2
    assert {v.id for v in vacancies} == {v1.id, v2.id}


async def test_delete_vacancy(session, repo):
    created = repo.add_vacancy(make_vacancy_data(external_id="10"))
    await session.commit()

    vacancy = await repo.get_by_id(created.id)
    assert vacancy is not None

    await repo.delete_vacancy(vacancy)
    await session.commit()

    deleted = await repo.get_by_id(created.id)
    assert deleted is None
