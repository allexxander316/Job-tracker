from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_pagination import Page, add_pagination

from app.core.enums import Status
from app.vacancies.dependencies import get_vacancy_service, get_vacancy_sync_service
from app.vacancies.routers import router as vacancy_router
from app.vacancies.schemas import (
    VacancyChangeSchema,
    VacancyFilterParams,
    VacancySchema,
)
from app.vacancies.services import VacancyNotFoundError


@pytest.fixture
def mock_vacancy_service():
    return AsyncMock()


@pytest.fixture
def mock_sync_service():
    return AsyncMock()


@pytest.fixture
def client(mock_vacancy_service, mock_sync_service):
    app = FastAPI()
    add_pagination(app)
    app.include_router(vacancy_router)
    app.dependency_overrides[get_vacancy_service] = lambda: mock_vacancy_service
    app.dependency_overrides[get_vacancy_sync_service] = lambda: mock_sync_service
    return TestClient(app)


def make_vacancy_schema(**kwargs) -> VacancySchema:
    data = {
        "id": 1,
        "source": "hh",
        "external_id": "1",
        "header": "Python Developer",
        "description": "Описание вакансии",
        "url": "https://hh.ru/vacancy/1",
        "salary_from": 100_000,
        "salary_to": 200_000,
        "area": 113,
        "experience": "between1And3",
        "city": "Москва",
        "employer_name": "Яндекс",
        "work_format": "Полный день",
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
        "updated_at": datetime(2026, 1, 1, tzinfo=UTC),
        "status": Status.NEW,
        "has_unacknowledged_changes": False,
    }
    data.update(**kwargs)
    return VacancySchema(**data)


def make_vacancy_changes_schema(**kwargs) -> VacancyChangeSchema:
    from app.vacancies.schemas import VacancyChangeSchema

    data = {
        "id": 1,
        "vacancy_id": 1,
        "changes": {"header": {"old": "Python", "new": "Senior"}},
        "changed_at": datetime(2026, 1, 1, tzinfo=UTC),
        "acknowledged": False,
    }
    data.update(**kwargs)
    return VacancyChangeSchema(**data)


class TestVacancyRouters:
    def test_read_vacancies(self, client, mock_vacancy_service):
        mock_vacancy_service.select_vacancies.return_value = Page(
            items=[
                make_vacancy_schema(source="hh", external_id="1", status=Status.NEW),
                make_vacancy_schema(
                    source="hh", external_id="2", header="Go Developer"
                ),
            ],
            total=2,
            page=1,
            size=50,
            pages=1,
        )

        response = client.get("/vacancies")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["items"][0]["header"] == "Python Developer"
        assert data["items"][1]["header"] == "Go Developer"
        assert data["total"] == 2

    def test_read_vacancy_found(self, client, mock_vacancy_service):
        mock_vacancy_service.get_by_id.return_value = make_vacancy_schema(
            id=42,
        )

        response = client.get("/vacancies/42")

        assert response.status_code == 200
        assert response.json()["id"] == 42

    def test_read_vacancy_not_found(self, client, mock_vacancy_service):
        mock_vacancy_service.get_by_id.side_effect = VacancyNotFoundError

        response = client.get("/vacancies/999")

        assert response.status_code == 404

    def test_change_status(self, client, mock_vacancy_service):
        mock_vacancy_service.change_status.return_value = make_vacancy_schema(
            status=Status.VIEWED
        )

        response = client.patch("/vacancies/1/status", params={"new_status": "VIEWED"})

        assert response.status_code == 200
        assert response.json()["status"] == "VIEWED"
        mock_vacancy_service.change_status.assert_called_once()

    def test_change_status_not_found(self, client, mock_vacancy_service):
        mock_vacancy_service.change_status.side_effect = VacancyNotFoundError

        response = client.patch("/vacancies/1/status", params={"new_status": "VIEWED"})

        assert response.status_code == 404

    def test_change_status_invalid_payload(self, client, mock_vacancy_service):
        response = client.patch("/vacancies/1/status", params={"new_status": "INVALID"})

        assert response.status_code == 422

    @patch("app.vacancies.routers.VacancySyncService.run_sync_in_background")
    def test_synchronize_vacancies(self, mock_run_sync, client):
        response = client.post("/vacancies/sync_all")
        assert response.status_code == 202
        mock_run_sync.assert_called_once()

    def test_filter_validation_salary_min_greater_than_max(self):
        with pytest.raises(ValueError, match="salary_min > salary_max"):
            VacancyFilterParams(salary_min=200_000, salary_max=100_000)

    def test_filter_validation_date_from_greater_than_to(self):
        with pytest.raises(ValueError, match="date_from > date_to"):
            VacancyFilterParams(date_from=date(2026, 6, 1), date_to=date(2026, 1, 1))

    def test_read_changes(self, client, mock_vacancy_service):
        mock_vacancy_service.get_changes.return_value = [
            make_vacancy_changes_schema(),
        ]
        response = client.get("/vacancies/1/changes")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_read_changes_not_found(self, client, mock_vacancy_service):
        mock_vacancy_service.get_changes.side_effect = VacancyNotFoundError
        response = client.get("/vacancies/999/changes")
        assert response.status_code == 404

    def test_acknowledge_changes(self, client, mock_vacancy_service):
        mock_vacancy_service.acknowledge_changes.return_value = make_vacancy_schema()
        response = client.post("/vacancies/1/acknowledge_changes")
        assert response.status_code == 200

    def test_acknowledge_changes_not_found(self, client, mock_vacancy_service):
        mock_vacancy_service.acknowledge_changes.side_effect = VacancyNotFoundError
        response = client.post("/vacancies/999/acknowledge_changes")
        assert response.status_code == 404
