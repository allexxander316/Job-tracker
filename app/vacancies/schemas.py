from datetime import datetime, date

from fastapi import Query
from pydantic import BaseModel, ConfigDict, model_validator

from app.core.enums import Status, SortField, SortOrder


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
    external_id: str
    source: str
    created_at: datetime
    updated_at: datetime
    status: Status = Status.NEW
    has_unacknowledged_changes: bool = False


class VacancyFilterParams(BaseModel):
    status: Status | None = None
    salary_min: int | None = Query(None, ge=0)
    salary_max: int | None = Query(None, ge=0)
    include_unknown_salary: bool = False
    city: str | None = None
    employer_name: str | None = None
    experience: str | None = None
    area: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    search: str | None = None
    has_unacknowledged_changes: bool | None = None

    @model_validator(mode="after")
    def validate_ranges(self):
        if self.salary_min and self.salary_max and self.salary_min > self.salary_max:
            raise ValueError("salary_min > salary_max")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from > date_to")
        return self


class VacancySortParams(BaseModel):
    sort_by: SortField = SortField.created_at
    sort_order: SortOrder = SortOrder.desc


class VacancyChangeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vacancy_id: int
    changes: dict
    changed_at: datetime
    acknowledged: bool
