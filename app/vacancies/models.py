from datetime import datetime

from sqlalchemy import DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.enums import Status


class VacancyORM(Base):
    __tablename__ = "vacancies"

    id: Mapped[int] = mapped_column(primary_key=True)
    header: Mapped[str]
    description: Mapped[str]
    url: Mapped[str]
    source: Mapped[str]
    external_id: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(default=Status.NEW)
    salary_from: Mapped[int] = mapped_column(default=0)
    salary_to: Mapped[int] = mapped_column(default=0)
    area: Mapped[int] = mapped_column(default=0)
    experience: Mapped[str | None]
    city: Mapped[str | None]
    employer_name: Mapped[str | None]
    work_format: Mapped[str] = mapped_column(default="Не указан")

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_vacancy_source_external_id"),
    )
