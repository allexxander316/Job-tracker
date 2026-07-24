# JobTracker

Сервис для парсинга вакансий с [HH.ru](https://hh.ru) и [Хабр Карьеры](https://career.habr.com) и отслеживания изменений.

## Стек

- **Python** 3.12
- **FastAPI** — веб-фреймворк
- **SQLAlchemy** 2.0 (async) — ORM
- **PostgreSQL** 16 — база данных
- **Alembic** — миграции
- **Docker** / **Docker Compose** — контейнеризация
- **pytest** + **testcontainers** — тестирование

## Структура парсеров

```
app/parsers/
  base.py          — AbstractParser (интерфейс)
  hh_api.py        — парсер HH.ru (JSON API)
  habr_career.py   — парсер Хабр Карьеры (HTML, BeautifulSoup)
  __init__.py      — реестр PARSERS для подключения в sync
```

## Быстрый старт

```bash
cp .env.example .env
# Заполнить HH_API_ACCESS_TOKEN (DATABASE_URL подставится из compose автоматически)
docker compose up --build
```

Приложение будет доступно на `http://localhost:8000`.

## Локальный запуск без Docker

```bash
cp .env.example .env
# Заполнить HH_API_ACCESS_TOKEN и DATABASE_URL

uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

## API

| Метод | Путь | Описание                           |
|-------|------|------------------------------------|
| `GET` | `/vacancies` | Список всех вакансий               |
| `GET` | `/vacancies/{id}` | Вакансия по id                     |
| `GET` | `/vacancies/{id}/changes` | История изменений вакансии         |
| `POST` | `/vacancies/{id}/acknowledge_changes` | Отметить изменения прочитанными    |
| `PATCH` | `/vacancies/{id}/status` | Изменить статус вакансии           |
| `POST` | `/vacancies/sync_all` | Запуск синхронизации               |
| `GET` | `/vacancies/sync/status` | Статус выполняющейся синхронизации |

### Статусы вакансий

```
NEW → VIEWED → APPLIED → INTERVIEW → REJECTED / NOT_SUITABLE / NOT_LIKED → ARCHIVED
```

## Переменные окружения

| Переменная | Обязательная | Описание |
|------------|-------------|----------|
| `HH_API_ACCESS_TOKEN` | Да | Токен доступа к API HH.ru |
| `DATABASE_URL` | Да* | Строка подключения к PostgreSQL (не требуется при использовании docker compose, подставляется автоматически) |
| `HH_PROFESSIONAL_ROLE` | Нет | Профессиональная роль для поиска HH (по умолчанию 96) |
| `SEARCH_TEXT` | Нет | Поисковый запрос для всех парсеров (по умолчанию "python") |
| `LOG_LEVEL` | Нет | Уровень логирования (по умолчанию INFO) |

## Тестирование

```bash
uv run pytest tests/ --cov=app
```

Тесты используют testcontainers (требуется Docker).

## CI

На каждый push в `main` запускается GitHub Actions:
- **lint** — проверка кода через ruff
- **test** — прогон тестов с отчётом о покрытии
