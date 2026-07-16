from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from testcontainers.postgres import PostgresContainer
from app.core.database import Base


@pytest.fixture(scope="session")
def postgres_container():
    """Поднимаем контейнер один раз на всю сессию тестов"""
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def async_db_url(postgres_container) -> str:
    """Конвертируем sync URL контейнера в async (asyncpg)"""
    url = postgres_container.get_connection_url()
    return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")


@pytest_asyncio.fixture(scope="session")
async def engine(async_db_url):
    """Движок — один на всю сессию"""
    engine = create_async_engine(async_db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def session(engine):
    """Изолированная сессия с откатом всех изменений после теста"""
    connection = await engine.connect()
    transaction = await connection.begin()

    session_factory = async_sessionmaker(
        bind=connection, class_=AsyncSession, expire_on_commit=False
    )
    session = session_factory()

    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


def make_vacancy_data(external_id: int = 1, **kwargs) -> dict:
    data = {
        "header": "Python Developer",
        "description": "Описание вакансии",
        "url": f"https://hh.ru/vacancy/{external_id}",
        "external_id": external_id,
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 1, 1),
        "status": "NEW",
        "salary_from": 100_000,
        "salary_to": 200_000,
        "area": 113,
        "experience": 2,
        "city": "Москва",
        "employer_name": "Яндекс",
        "work_format": "Полный день",
    }
    data.update(**kwargs)
    return data
