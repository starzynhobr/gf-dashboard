from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import NewType
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from gf_dashboard.domain.errors import ValidationError

WorkspaceId = NewType("WorkspaceId", UUID)
EntityId = NewType("EntityId", UUID)


def new_entity_id() -> EntityId:
    return EntityId(uuid4())


def as_entity_id(value: UUID | str) -> EntityId:
    try:
        return EntityId(value if isinstance(value, UUID) else UUID(value))
    except (TypeError, ValueError) as exc:
        raise ValidationError("ID deve ser um UUID válido") from exc


def as_workspace_id(value: UUID | str) -> WorkspaceId:
    return WorkspaceId(as_entity_id(value))


def require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError("Timestamp deve incluir timezone")
    return value.astimezone(UTC)


def operational_date(timestamp: datetime, timezone_name: str) -> date:
    try:
        timezone = ZoneInfo(timezone_name)
    except Exception as exc:  # zoneinfo error types vary by platform installation
        raise ValidationError(f"Timezone inválido: {timezone_name}") from exc
    return require_utc(timestamp).astimezone(timezone).date()


@dataclass(frozen=True, slots=True, order=True)
class Gold:
    amount: int

    def __post_init__(self) -> None:
        if isinstance(self.amount, bool) or not isinstance(self.amount, int):
            raise ValidationError("Gold deve ser inteiro")
        if self.amount < 0:
            raise ValidationError("Gold não pode ser negativo")

    def __add__(self, other: Gold) -> Gold:
        if not isinstance(other, Gold):
            return NotImplemented
        return Gold(self.amount + other.amount)

    def times(self, multiplier: int) -> Gold:
        if isinstance(multiplier, bool) or not isinstance(multiplier, int) or multiplier < 0:
            raise ValidationError("Multiplicador de gold deve ser inteiro não negativo")
        return Gold(self.amount * multiplier)


@dataclass(frozen=True, slots=True)
class Money:
    amount_minor: int
    currency: str = "BRL"

    def __post_init__(self) -> None:
        if isinstance(self.amount_minor, bool) or not isinstance(self.amount_minor, int):
            raise ValidationError("Dinheiro deve usar unidade mínima inteira")
        if self.amount_minor < 0:
            raise ValidationError("Dinheiro não pode ser negativo")
        normalized_currency = self.currency.upper()
        if len(normalized_currency) != 3 or not normalized_currency.isalpha():
            raise ValidationError("Moeda deve usar código ISO de três letras")
        object.__setattr__(self, "currency", normalized_currency)


@dataclass(frozen=True, slots=True)
class RewardSnapshot:
    gold: Gold
    pve_bags: int

    def __post_init__(self) -> None:
        if isinstance(self.pve_bags, bool) or not isinstance(self.pve_bags, int):
            raise ValidationError("Quantidade de sacos PvE deve ser inteira")
        if self.pve_bags < 0:
            raise ValidationError("Quantidade de sacos PvE não pode ser negativa")

    def times(self, multiplier: int) -> RewardSnapshot:
        if isinstance(multiplier, bool) or not isinstance(multiplier, int) or multiplier < 0:
            raise ValidationError("Multiplicador deve ser inteiro não negativo")
        return RewardSnapshot(self.gold.times(multiplier), self.pve_bags * multiplier)
