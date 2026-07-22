import re

import httpx
from bs4 import BeautifulSoup

from parsers.base import AbstractParser

VACANCY_ID_RE = re.compile(r"/vacancies/(\d+)")


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

    @staticmethod
    def _parse_card(card) -> dict | None:
        title_el = card.select_one(".vacancy-card__title-link")
        if not title_el:
            return None

        link = title_el.get("href", "")
        match = VACANCY_ID_RE.search(link)
        if not match:
            return None

        header = title_el.get_text(strip=True)

        company_el = card.select_one(".vacancy-card__company a")
        employer_name = company_el.get_text(strip=True) if company_el else "Не указано"

        url = f"https://career.habr.com{link}"

        return {
            "header": header,
            "employer_name": employer_name,
            "url": url,
            "source": "habr",
            "external_id": match.group(1),
        }

    def _parse_page(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select(".vacancy-card")
        return [parsed for c in cards if (parsed := self._parse_card(c))]

    async def get_all_vacancies(self) -> list[dict]:
        html = await self._fetch_page(1)
        vacancies = self._parse_page(html)
        for v in vacancies[:20]:
            print(v)
        return vacancies
