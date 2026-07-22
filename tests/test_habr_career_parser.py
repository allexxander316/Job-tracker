from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from app.parsers.habr_career import HabrCareerParser, get_vacancies

CARD_HTML = """
<div class="vacancy-card">
  <div class="vacancy-card__date">
    <time class="basic-date" datetime="2026-07-22T17:53:51+03:00">22 июля</time>
  </div>
  <a class="vacancy-card__icon-link" href="/vacancies/1000165352">
    <img class="vacancy-card__icon" src="https://example.com/logo.png" />
  </a>
  <div class="vacancy-card__info">
    <div class="vacancy-card__company">
      <a class="link-comp link-comp--appearance-dark" href="/companies/psb">Яндекс</a>
    </div>
    <div class="vacancy-card__title">
      <a class="vacancy-card__title-link" href="/vacancies/1000165352">Python Developer</a>
    </div>
    <div class="vacancy-card__salary">
      <div class="basic-salary">от 150 000 ₽</div>
    </div>
    <div class="vacancy-card__meta">
      <div class="vacancy-meta">
        <div class="basic-chip basic-chip--color-ui-gray-4">
          <div class="chip-with-icon__icon chip-with-icon__icon--color-ui-gray-4">
            <svg class="svg-icon"><use xlink:href="/images/icons-sprite.svg#format"></use></svg>
          </div>
          <div class="chip-with-icon__text">Можно удалённо</div>
        </div>
        <div class="basic-chip basic-chip--color-ui-gray-4">
          <div class="chip-with-icon__icon chip-with-icon__icon--color-ui-gray-4">
            <svg class="svg-icon"><use xlink:href="/images/icons-sprite.svg#placemark"></use></svg>
          </div>
          <div class="chip-with-icon__text">Москва</div>
        </div>
      </div>
    </div>
    <div class="vacancy-card__skills">
      <a class="vacancy-card__skills-chip" href="/vacancies/skills/python">Python</a>
      <a class="vacancy-card__skills-chip" href="/vacancies/skills/django">Django</a>
    </div>
  </div>
</div>
"""

PAGE_HTML = f"""
<html><body>
{CARD_HTML}
{CARD_HTML}
<div class="paginator">
  <div class="pagination">
    <a class="page current" href="/vacancies?type=all">1</a>
    <a class="page next" href="/vacancies?page=2&type=all" rel="next">2</a>
    <a class="next_page" href="/vacancies?page=2&type=all">Next ›</a>
  </div>
</div>
</body></html>
"""


@pytest.fixture
def parser():
    return HabrCareerParser(search_text="python")


class TestParseSalary:
    def test_none(self):
        assert HabrCareerParser._parse_salary(None) == (0, 0)

    def test_empty(self):
        assert HabrCareerParser._parse_salary("") == (0, 0)

    def test_from_only(self):
        assert HabrCareerParser._parse_salary("от 150 000 ₽") == (150000, 0)

    def test_to_only(self):
        assert HabrCareerParser._parse_salary("до 250 000 ₽") == (0, 250000)

    def test_range(self):
        assert HabrCareerParser._parse_salary("150 000 – 250 000 ₽") == (150000, 250000)

    def test_predicted_ignored(self):
        assert HabrCareerParser._parse_salary(
            "Похожие специалисты получают 100 000"
        ) == (100000, 0)

    def test_random_text(self):
        assert HabrCareerParser._parse_salary("Зарплата не указана") == (0, 0)


class TestParseCard:
    def test_full_card(self, parser):
        soup = BeautifulSoup(CARD_HTML, "lxml")
        card = soup.select_one(".vacancy-card")

        result = parser._parse_card(card)

        assert result is not None
        assert result["header"] == "Python Developer"
        assert result["employer_name"] == "Яндекс"
        assert result["url"] == "https://career.habr.com/vacancies/1000165352"
        assert result["external_id"] == "1000165352"
        assert result["salary_from"] == 150000
        assert result["salary_to"] == 0
        assert result["city"] == "Москва"
        assert result["work_format"] == "Удалённо"
        assert result["experience"] == "Не указано"
        assert result["description"] == "Python, Django"
        assert result["source"] == "habr_career"
        assert result["status"] == "NEW"
        assert result["area"] == 0
        assert isinstance(result["created_at"], datetime)
        assert result["created_at"] == result["updated_at"]

    def test_missing_title_returns_none(self, parser):
        html = '<div class="vacancy-card"><div>No title</div></div>'
        soup = BeautifulSoup(html, "lxml")
        assert parser._parse_card(soup.select_one(".vacancy-card")) is None

    def test_no_salary(self, parser):
        html = """
        <div class="vacancy-card">
          <div class="vacancy-card__title">
            <a class="vacancy-card__title-link" href="/vacancies/999">Dev</a>
          </div>
        </div>
        """
        soup = BeautifulSoup(html, "lxml")
        result = parser._parse_card(soup.select_one(".vacancy-card"))
        assert result is not None
        assert result["salary_from"] == 0
        assert result["salary_to"] == 0

    def test_work_format_default(self, parser):
        html = """
        <div class="vacancy-card">
          <div class="vacancy-card__title">
            <a class="vacancy-card__title-link" href="/vacancies/999">Dev</a>
          </div>
          <div class="vacancy-card__meta">
            <div class="vacancy-meta">
              <div class="basic-chip">
                <div class="chip-with-icon__icon"><svg><use xlink:href="#placemark"></use></svg></div>
                <div class="chip-with-icon__text">Moscow</div>
              </div>
            </div>
          </div>
        </div>
        """
        soup = BeautifulSoup(html, "lxml")
        result = parser._parse_card(soup.select_one(".vacancy-card"))
        assert result["work_format"] == "На месте работодателя"

    def test_no_company(self, parser):

        html = """
        <div class="vacancy-card">
          <div class="vacancy-card__title">
            <a class="vacancy-card__title-link" href="/vacancies/999">Dev</a>
          </div>
        </div>
        """
        soup = BeautifulSoup(html, "lxml")
        result = parser._parse_card(soup.select_one(".vacancy-card"))
        assert result["employer_name"] == "Не указано"


class TestParsePage:
    def test_multiple_cards(self, parser):

        # _parse_page внутри сам делает soup, но мы тестируем напрямую
        result = parser._parse_page(PAGE_HTML)
        assert len(result) == 2

    def test_no_cards(self, parser):
        result = parser._parse_page("<html><body></body></html>")
        assert result == []


class TestGetAllVacancies:
    @pytest.mark.asyncio
    async def test_single_page(self, parser):
        page1_html = """
        <html><body>
        <div class="vacancy-card">
          <div class="vacancy-card__title">
            <a class="vacancy-card__title-link" href="/vacancies/1">Dev</a>
          </div>
        </div>
        </body></html>
        """
        parser._fetch_page = AsyncMock(return_value=page1_html)

        result = await parser.get_all_vacancies()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_multiple_pages(self, parser):
        page1_html = """
        <html><body>
        <div class="vacancy-card">
          <div class="vacancy-card__title">
            <a class="vacancy-card__title-link" href="/vacancies/1">Dev 1</a>
          </div>
        </div>
        <div class="paginator">
          <div class="pagination">
            <a class="page current" href="/vacancies">1</a>
            <a class="page next" href="/vacancies?page=2" rel="next">2</a>
            <a class="next_page" href="/vacancies?page=2">Next ›</a>
          </div>
        </div>
        </body></html>
        """
        page2_html = """
        <html><body>
        <div class="vacancy-card">
          <div class="vacancy-card__title">
            <a class="vacancy-card__title-link" href="/vacancies/2">Dev 2</a>
          </div>
        </div>
        </body></html>
        """
        parser._fetch_page = AsyncMock(side_effect=[page1_html, page2_html])

        result = await parser.get_all_vacancies()
        assert len(result) == 2
        assert result[0]["external_id"] == "1"
        assert result[1]["external_id"] == "2"
        assert parser._fetch_page.call_count == 2


class TestGetVacanciesModule:
    @pytest.mark.asyncio
    @patch("app.parsers.habr_career.settings")
    @patch("app.parsers.habr_career.HabrCareerParser")
    async def test_get_vacancies(self, mock_parser_class, mock_settings):
        mock_settings.search_text = "python"
        mock_parser = MagicMock()
        mock_parser.get_all_vacancies = AsyncMock(
            return_value=[{"header": "Dev", "source": "habr", "external_id": "1"}]
        )
        mock_parser_class.return_value.__aenter__.return_value = mock_parser

        result = await get_vacancies()

        assert result == [{"header": "Dev", "source": "habr", "external_id": "1"}]
