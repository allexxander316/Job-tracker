from datetime import datetime

from pydantic import BaseModel

from app.core.enums import Status


class VacancySchema(BaseModel):
    id: int
    header: str
    description: str
    url: str
    external_id: int
    created_at: datetime
    updated_at: datetime
    status: str = Status.NEW.value
    salary_from: int = 0
    salary_to: int = 0
    area: int = 0
    experience: int | None = None


class ChangeStatusSchema(BaseModel):
    status: Status
