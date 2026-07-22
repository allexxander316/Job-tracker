import asyncio
import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from app.config.settings import settings
from app.parsers.base import AbstractParser
from app.core.logger import get_logger

VACANCY_ID_RE = re.compile(r"/vacancies/(\d+)")
logger = get_logger(__name__)


class HabrCareerParser(AbstractParser):
    BASE_URL = "https://career.habr.com/vacancies"

    def __init__(self, search_text: str):
        self._client = httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (compatible; JobTracker/1.0)"}
        )
        self.search_text = search_text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._client.aclose()

    async def _fetch_page(self, page: int) -> str:
        resp = await self._client.get(
            self.BASE_URL, params={"page": page, "type": "all", "q": self.search_text}
        )
        resp.raise_for_status()
        return resp.text

    @staticmethod
    def _parse_salary(text: str | None) -> tuple[int, int]:
        if not text:
            return 0, 0
        text = text.replace("\u202f", "").replace(" ", "").replace("₽", "")
        numbers = re.findall(r"\d+", text)
        if len(numbers) == 2:
            return int(numbers[0]), int(numbers[1])
        if len(numbers) == 1:
            if "от" in text:
                return int(numbers[0]), 0
            if "до" in text:
                return 0, int(numbers[0])
            return int(numbers[0]), 0
        return 0, 0

    def _parse_card(self, card) -> dict | None:
        title_el = card.select_one(".vacancy-card__title-link")
        if not title_el:
            return None

        link = title_el.get("href", "")
        match = VACANCY_ID_RE.search(link)
        if not match:
            return None

        header = title_el.get_text(strip=True)

        company_link = card.select_one(".vacancy-card__company a")
        employer_name = (
            company_link.get_text(strip=True) if company_link else "Не указано"
        )

        salary_el = card.select_one(".basic-salary")
        salary_from, salary_to = self._parse_salary(
            salary_el.get_text(strip=True) if salary_el else None
        )

        city = "Не указан"
        experience = "Не указано"
        work_format = "На месте работодателя"

        meta = card.select_one(".vacancy-card__meta")
        if meta:
            for chip in meta.select(".basic-chip"):
                icon_use = chip.select_one(".chip-with-icon__icon use")
                text_el = chip.select_one(".chip-with-icon__text")
                if not text_el or not icon_use:
                    continue
                content = text_el.get_text(strip=True)
                href = icon_use.get("xlink:href", "")

                if "placemark" in href:
                    city = content
                elif "удален" in content.lower().replace("ё", "е"):
                    work_format = "Удалённо"

        description = ", ".join(
            a.get_text(strip=True) for a in card.select(".vacancy-card__skills a")
        )

        time_el = card.select_one("time")
        created_at = None
        if time_el and time_el.has_attr("datetime"):
            created_at = datetime.fromisoformat(time_el["datetime"]).astimezone(
                timezone.utc
            )

        url = f"https://career.habr.com{link}"

        return {
            "header": header,
            "description": description,
            "url": url,
            "source": "habr",
            "external_id": match.group(1),
            "salary_from": salary_from,
            "salary_to": salary_to,
            "area": 0,
            "experience": experience,
            "created_at": created_at or datetime.now(timezone.utc),
            "updated_at": created_at or datetime.now(timezone.utc),
            "status": "NEW",
            "city": city,
            "work_format": work_format,
            "employer_name": employer_name,
        }

    def _parse_page(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select(".vacancy-card")
        return [parsed for c in cards if (parsed := self._parse_card(c))]

    async def get_all_vacancies(self) -> list[dict]:
        logger.info("Starting fetch: search_text='%s'", self.search_text)
        all_vacancies = []
        page = 1

        while True:
            html = await self._fetch_page(page)
            vacancies = self._parse_page(html)
            all_vacancies.extend(vacancies)
            logger.info("Page %s - %s vacancies so far", page, len(all_vacancies))

            soup = BeautifulSoup(html, "lxml")
            if not soup.select_one("a.next_page"):
                break

            page += 1
            await asyncio.sleep(1)

        logger.info("Fetch complete: %s total vacancies", len(all_vacancies))
        return all_vacancies


async def get_vacancies() -> list[dict]:
    async with HabrCareerParser(settings.search_text) as parser:
        return await parser.get_all_vacancies()
