from dataclasses import dataclass
from datetime import datetime


@dataclass
class Vacancy:
    header: str
    description: str
    url: str
    external_id: int
    created_at: datetime
    updated_at: datetime
    status: str = "NEW"
    salary_from: int = 0
    salary_to: int = 0
    area: int = 0
    experience: int | None = None
    id: int | None = None
