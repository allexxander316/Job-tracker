# JobTracker

Сервис для парсинга вакансий с [HH.ru](https://hh.ru) и отслеживания статусов откликов. Автоматическая ежедневная синхронизация в 10:00.

## Стек

- **Python** 3.12
- **FastAPI** — веб-фреймворк
- **SQLAlchemy** 2.0 (async) — ORM
- **PostgreSQL** 16 — база данных
- **Alembic** — миграции
- **APScheduler** — планировщик синхронизации
- **Docker** / **Docker Compose** — контейнеризация
- **pytest** + **testcontainers** — тестирование

## Быстрый старт

```bash
cp .env.example .env
# Заполнить HH_API_ACCESS_TOKEN и (опционально) DATABASE_URL
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

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/vacancies` | Список всех вакансий |
| `GET` | `/vacancies/{id}` | Вакансия по external_id |
| `PATCH` | `/vacancies/{id}/status` | Изменить статус вакансии |
| `POST` | `/vacancies/sync_all` | Ручной запуск синхронизации с HH.ru |

### Статусы вакансий

```
NEW → VIEWED → APPLIED → INTERVIEW → REJECTED / NOT_SUITABLE / NOT_LIKED → ARCHIVED
```

## Переменные окружения

| Переменная | Обязательная | Описание |
|------------|-------------|----------|
| `HH_API_ACCESS_TOKEN` | Да | Токен доступа к API HH.ru |
| `DATABASE_URL` | Да | Строка подключения к PostgreSQL |
| `LOG_LEVEL` | Нет | Уровень логирования (по умолчанию INFO) |

## Тестирование

```bash
uv run pytest tests/ --cov=app
```

Тесты используют testcontainers (требуется Docker). Покрытие кода — 86%.

## CI

На каждый push в `main` запускается GitHub Actions:
- **lint** — проверка кода через ruff
- **test** — прогон тестов с отчётом о покрытии
