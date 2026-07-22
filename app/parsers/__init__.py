from app.parsers.hh_api import get_vacancies as get_hh
from app.parsers.habr_career import get_vacancies as get_habr

PARSERS = [get_hh, get_habr]
