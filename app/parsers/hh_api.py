import asyncio

import httpx

from app.config.settings import settings
from app.parsers.base import AbstractParser


class HHApiParser(AbstractParser):
    def __init__(self, access_token: str, base_url: str,
                 professional_role: int, text: str):
        self._async_client = httpx.AsyncClient(headers={
            "HH-User-Agent": "MyApp/1.1 (allexxander316@gmail.com)",
            "Authorization": f"Bearer {access_token}",
        })
        self.base_url = base_url
        self.professional_role = professional_role
        self.text = text

    async def __aenter__(self) -> "HHApiParser":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._async_client.aclose()

    async def _search(self, params: dict | None = None) -> dict:
        response = await self._async_client.get(url=self.base_url, params=params)
        response.raise_for_status()
        return response.json()

    def _validate_response(self, response: dict) -> None:
        found_vacancies = response["found"]
        if found_vacancies > 2000:
            raise ValueError("Не все записи могут быть получены, сделайте более строгий поиск")

        if found_vacancies == 0:
            raise ValueError("Нет записей по запросу")

    def _to_db_format(self, raw: dict) -> dict:
        salary = raw.get("salary") or {}
        snippet = raw.get("snippet") or {}
        description = "\n".join(filter(None, [
            snippet.get("requirement"),
            snippet.get("responsibility"),
        ]))

        db_vacancy = {
            "header": raw["name"],
            "description": description,
            "url": raw["alternate_url"],
            "external_id": int(raw["id"]),
            "salary_from": salary.get("from") or 0,
            "salary_to": salary.get("to") or 0,
            "area": raw.get("area", {}).get("id") or 0,
            "experience": raw.get("experience", {}).get("id"),
            "created_at": raw["created_at"],
            "updated_at": raw["created_at"],
            "status": "NEW",
        }

        return db_vacancy

    def all_vacancies_to_db_format(self, raw_vacancies: list[dict]) -> list[dict]:
        return [self._to_db_format(raw) for raw in raw_vacancies]

    async def get_all_vacancies(self) -> list[dict]:
        params = {
            "professional_role": self.professional_role,
            "text": self.text,
            "per_page": 100,
            "page": 0,
        }

        result = await self._search(params)
        self._validate_response(result)
        vacancies = result["items"]
        pages = result["pages"]

        for page in range(1, pages):
            params["page"] = page
            result = await self._search(params)
            vacancies.extend(result["items"])
            await asyncio.sleep(0.5)

        return vacancies


async def get_vacancies() -> list[dict]:
    if settings.hh_access_token is None:
        raise ValueError("ACCESS_TOKEN must be provided")

    async with HHApiParser(
            settings.hh_access_token,
            settings.hh_base_url,
            settings.hh_professional_role,
            settings.hh_search_text,
    ) as hh_api_parser:
        raw_vacancies = await hh_api_parser.get_all_vacancies()
        vacancies = hh_api_parser.all_vacancies_to_db_format(raw_vacancies)
        return vacancies
