from datetime import datetime

from db import get_by_external_id, insert_vacancy, update_vacancy
from hh_client import get_vacancies


def sync_all():
    vacancies = get_vacancies()
    for vacancy in vacancies:
        vacancy_from_bd = get_by_external_id(external_id=vacancy["external_id"])

        if vacancy_from_bd is None:
            insert_vacancy(vacancy)
            continue

        comparable = {
            "header",
            "description",
            "url",
            "salary_from",
            "salary_to",
            "area",
            "experience",
        }

        changed = any(
            vacancy.get(field) != vacancy_from_bd.get(field) for field in comparable
        )

        if changed:
            vacancy["updated_at"] = datetime.now()
            vacancy["status"] = vacancy_from_bd["status"]
            update_vacancy(vacancy)
