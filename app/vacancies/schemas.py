from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import Status


class VacancySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    header: str
    description: str
    url: str
    external_id: int
    created_at: datetime
    updated_at: datetime
    status: Status = Status.NEW
    salary_from: int = 0
    salary_to: int = 0
    area: int = 0
    experience: int | None = None


class ChangeStatusSchema(BaseModel):
    status: Status
