from enum import StrEnum


class ActivityCategory(StrEnum):
    DUNGEON = "dungeon"
    SPECIAL = "special"


class ActivityFrequency(StrEnum):
    DAILY = "daily"
    OCCASIONAL = "occasional"


class ActivityStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class RuleStatus(StrEnum):
    CONFIRMED = "confirmed"
    INFORMATIONAL = "informational"
    UNKNOWN = "unknown"


class MissionLimitType(StrEnum):
    LIMITED = "limited"
    UNLIMITED = "unlimited"


class SessionType(StrEnum):
    ACTIVITY = "activity"
    TOWER = "tower"


class SessionStatus(StrEnum):
    PLANNED = "planned"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MovementType(StrEnum):
    ACQUISITION = "acquisition"
    SALE = "sale"
    ADJUSTMENT = "adjustment"


class SaleStatus(StrEnum):
    DRAFT = "draft"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TransactionType(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"
    ADJUSTMENT = "adjustment"
