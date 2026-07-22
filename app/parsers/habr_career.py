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

    async def _fetch_page(self, page: int) -> str:
        resp = await self._client.get(
            self.BASE_URL, params={"page": page, "type": "all"}
        )
        resp.raise_for_status()
        return resp.text

    async def get_all_vacancies(self) -> list[dict]:
        html = await self._fetch_page(1)
        print(html[:500])
        return []
