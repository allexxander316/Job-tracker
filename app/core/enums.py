from enum import Enum


class Status(str, Enum):
    NEW = "NEW"
    VIEWED = "VIEWED"
    APPLIED = "APPLIED"
    INTERVIEW = "INTERVIEW"
    REJECTED = "REJECTED"
    NOT_SUITABLE = "NOT_SUITABLE"
    NOT_LIKED = "NOT_LIKED"
    ARCHIVED = "ARCHIVED"


class SortField(str, Enum):
    created_at = "created_at"
    updated_at = "updated_at"
    salary_from = "salary_from"
    salary_to = "salary_to"
    header = "header"


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"
