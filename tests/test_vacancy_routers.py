from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.enums import Status
from app.vacancies.dependencies import get_vacancy_service, get_vacancy_sync_service
from app.vacancies.routers import router as vacancy_router
from app.vacancies.schemas import VacancySchema
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
    app.include_router(vacancy_router)
    app.dependency_overrides[get_vacancy_service] = lambda: mock_vacancy_service
    app.dependency_overrides[get_vacancy_sync_service] = lambda: mock_sync_service
    return TestClient(app)


def make_vacancy_schema(**kwargs) -> VacancySchema:
    data = {
        "id": 1,
        "external_id": 1,
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
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 1, 1),
        "status": Status.NEW,
    }
    data.update(**kwargs)
    return VacancySchema(**data)


class TestVacancyRouters:
    def test_read_vacancies(self, client, mock_vacancy_service):
        mock_vacancy_service.select_vacancies.return_value = [
            make_vacancy_schema(external_id=1, status=Status.NEW),
            make_vacancy_schema(external_id=2, header="Go Developer"),
        ]

        response = client.get("/vacancies")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["header"] == "Python Developer"
        assert data[1]["header"] == "Go Developer"

    def test_read_vacancy_found(self, client, mock_vacancy_service):
        mock_vacancy_service.get_by_external_id.return_value = make_vacancy_schema(
            external_id=42
        )

        response = client.get("/vacancies/42")

        assert response.status_code == 200
        assert response.json()["external_id"] == 42

    def test_read_vacancy_not_found(self, client, mock_vacancy_service):
        mock_vacancy_service.get_by_external_id.side_effect = VacancyNotFoundError

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

    def test_synchronize_vacancies(self, client, mock_sync_service):
        mock_sync_service.sync_all.return_value = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
        }

        response = client.post("/vacancies/sync_all")

        assert response.status_code == 200
        mock_sync_service.sync_all.assert_called_once()
