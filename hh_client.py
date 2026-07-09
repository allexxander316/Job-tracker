import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("HH_API_ACCESS_TOKEN")
URL = "https://api.hh.ru/vacancies"
PROFESSIONAL_ROLE = 96
TEXT = "python"


class HHClient:
    def __init__(self, access_token: str, base_url: str,
                 professional_role: int, text: str):
        self._session = requests.Session()
        self._session.headers.update({
            "HH-User-Agent": "MyApp/1.1 (allexxander316@gmail.com)",
            "Authorization": f"Bearer {access_token}",
        })
        self.base_url = base_url
        self.professional_role = professional_role
        self.text = text

    def _search(self, params: dict | None = None) -> dict:
        response = self._session.get(self.base_url, params=params)
        response.raise_for_status()
        return response.json()

    def _validate_response(self, response: dict) -> None:
        found_vacancies = response["found"]
        if found_vacancies > 2000:
            raise ValueError("Не все записи могут быть получены, сделайте более строгий поиск")

        if found_vacancies == 0:
            raise ValueError("Нет записей по запросу")

    def get_all_vacancies(self) -> list[dict]:
        params = {
            "professional_role": self.professional_role,
            "text": self.text,
            "per_page": 100,
            "page": 0,
        }

        result = self._search(params)
        vacancies = result["items"]
        pages = result["pages"]
        self._validate_response(result)

        for page in range(1, pages + 1):
            params["page"] = page
            result = self._search(params)
            vacancies.extend(result["items"])
            time.sleep(0.5)

        return vacancies


def get_vacancies() -> list[dict]:
    if ACCESS_TOKEN is None:
        raise ValueError("ACCESS_TOKEN must be provided")

    hh_client = HHClient(ACCESS_TOKEN, URL, PROFESSIONAL_ROLE, TEXT)
    return hh_client.get_all_vacancies()
