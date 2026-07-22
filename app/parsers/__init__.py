from app.parsers.hh_api import get_vacancies as get_hh
from app.parsers.habr_career import get_vacancies as get_habr

PARSERS = [
    ("hh", get_hh),
    ("habr_career", get_habr),
]
