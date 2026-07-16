from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.enums import Status


class VacancyUpdateSchema(BaseModel):
    header: str | None = None
    description: str | None = None
    url: str | None = None
    salary_from: int | None = None
    salary_to: int | None = None
    area: int | None = None
    experience: str | None = None
    city: str | None = None
    work_format: str | None = None
    employer_name: str | None = None


class VacancySchema(VacancyUpdateSchema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: int
    created_at: datetime
    updated_at: datetime
    status: Status = Status.NEW


class ChangeStatusSchema(BaseModel):
    status: Status
