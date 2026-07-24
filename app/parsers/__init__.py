from app.parsers.habr_career import get_vacancies as get_habr
from app.parsers.hh_api import get_vacancies as get_hh

PARSERS = [
    ("hh", get_hh),
    ("habr", get_habr),
]
