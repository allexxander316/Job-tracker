import httpx

from parsers.base import AbstractParser


class HabrCareerParser(AbstractParser):
    BASE_URL = "https://career.habr.com/vacancies"

    def __init__(self):
        self._client = httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (compatible; JobTracker/1.0)"}
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.aclose()

    async def get_all_vacancies(self) -> list[dict]:
        return []
