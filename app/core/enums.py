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