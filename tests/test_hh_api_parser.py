from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.parsers.hh_api import HHApiParser, get_vacancies


def make_raw_vacancy(**kwargs) -> dict:
    data = {
        "id": "123",
        "name": "Python Developer",
        "alternate_url": "https://hh.ru/vacancy/123",
        "salary": {"from": 100_000, "to": 200_000},
        "snippet": {
            "requirement": "Требования к разработчику",
            "responsibility": "Обязанности разработчика",
        },
        "area": {"id": "113", "name": "Россия"},
        "address": {"city": "Москва"},
        "experience": {"id": "between1And3"},
        "work_format": [{"name": "Полный день"}, {"name": "Удаленно"}],
        "employer": {"name": "Яндекс"},
        "created_at": "2024-01-01T10:00:00+03:00",
    }
    data.update(**kwargs)
    return data


@pytest.fixture
def parser():
    return HHApiParser(
        access_token="fake_token",
        base_url="https://api.hh.ru/vacancies",
        professional_role=96,
        text="Python",
    )


class TestToDbFormat:
    def test_full_data(self, parser):
        raw = make_raw_vacancy()
        result = parser._to_db_format(raw)

        assert result["header"] == "Python Developer"
        assert result["external_id"] == 123
        assert result["salary_from"] == 100_000
        assert result["salary_to"] == 200_000
        assert result["city"] == "Москва"
        assert result["work_format"] == "Полный день, Удаленно"
        assert result["employer_name"] == "Яндекс"

    def test_cleans_highlight_tags(self, parser):
        raw = make_raw_vacancy(
            snippet={
                "requirement": "<highlighttext>Python</highlighttext>",
                "responsibility": "Тест</highlighttext>",
            }
        )
        result = parser._to_db_format(raw)
        assert "<highlighttext>" not in result["description"]
        assert "</highlighttext>" not in result["description"]

    def test_missing_salary(self, parser):
        raw = make_raw_vacancy(salary=None)
        result = parser._to_db_format(raw)
        assert result["salary_from"] == 0
        assert result["salary_to"] == 0

    def test_no_work_format(self, parser):
        raw = make_raw_vacancy(work_format=[])
        result = parser._to_db_format(raw)
        assert result["work_format"] == "Не указан"

    def test_no_address_falls_back_to_area_name(self, parser):
        raw = make_raw_vacancy(address=None)
        result = parser._to_db_format(raw)
        assert result["city"] == "Россия"


class TestValidateResponse:
    def test_too_many_vacancies(self, parser):
        with pytest.raises(ValueError, match="более строгий поиск"):
            parser._validate_response({"found": 2001, "items": []})

    def test_zero_vacancies(self, parser):
        with pytest.raises(ValueError, match="Нет записей"):
            parser._validate_response({"found": 0, "items": []})

    def test_valid_response(self, parser):
        parser._validate_response({"found": 100, "items": []})


def mock_httpx_response(json_data, is_error=False, status_code=200, text=""):
    response = MagicMock(spec=httpx.Response)
    response.is_error = is_error
    response.status_code = status_code
    response.text = text
    response.json = MagicMock(return_value=json_data)
    if is_error:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"{status_code} {text}", request=MagicMock(), response=response
        )
    else:
        response.raise_for_status = MagicMock()
    return response


def install_mock_client(
    parser, json_data=None, is_error=False, status_code=200, text=""
):
    mock_response = mock_httpx_response(json_data, is_error, status_code, text)
    parser._async_client = MagicMock()
    parser._async_client.get = AsyncMock(return_value=mock_response)
    return parser._async_client.get


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_success(self, parser):
        mock_get = install_mock_client(parser, {"found": 10, "items": []})

        result = await parser._search({"page": 0})
        assert result == {"found": 10, "items": []}
        mock_get.assert_called_once_with(
            url="https://api.hh.ru/vacancies", params={"page": 0}
        )

    @pytest.mark.asyncio
    async def test_search_http_error(self, parser):
        install_mock_client(
            parser, None, is_error=True, status_code=403, text="Forbidden"
        )

        with pytest.raises(httpx.HTTPStatusError):
            await parser._search({"page": 0})


class TestGetAllVacancies:
    @pytest.mark.asyncio
    async def test_single_page(self, parser):
        page_data = {"found": 50, "pages": 1, "items": [{"id": "1"}, {"id": "2"}]}
        install_mock_client(parser, page_data)

        result = await parser.get_all_vacancies()
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_multiple_pages(self, parser):
        responses = [
            {"found": 250, "pages": 3, "items": [{"id": str(i)} for i in range(100)]},
            {
                "found": 250,
                "pages": 3,
                "items": [{"id": str(i)} for i in range(100, 200)],
            },
            {
                "found": 250,
                "pages": 3,
                "items": [{"id": str(i)} for i in range(200, 250)],
            },
        ]
        mock_response = mock_httpx_response(responses[0])
        mock_response.json = MagicMock(side_effect=responses)
        parser._async_client = MagicMock()
        parser._async_client.get = AsyncMock(return_value=mock_response)

        result = await parser.get_all_vacancies()
        assert len(result) == 250


class TestGetVacanciesModule:
    @pytest.mark.asyncio
    @patch("app.parsers.hh_api.settings.hh_access_token", "fake_token")
    @patch("app.parsers.hh_api.HHApiParser")
    async def test_get_vacancies(self, mock_parser_class):
        mock_parser = MagicMock()
        mock_parser.get_all_vacancies = AsyncMock(return_value=[{"id": "1"}])
        mock_parser.all_vacancies_to_db_format = MagicMock(
            return_value=[{"header": "Dev", "external_id": 1}]
        )
        mock_parser_class.return_value.__aenter__.return_value = mock_parser

        result = await get_vacancies()
        assert result == [{"header": "Dev", "external_id": 1}]
