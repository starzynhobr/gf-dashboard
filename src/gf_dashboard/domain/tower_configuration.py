from __future__ import annotations

from dataclasses import dataclass

from gf_dashboard.domain.errors import ValidationError
from gf_dashboard.domain.value_objects import EntityId, Gold

MAX_SAFE_INTEGER = 9_007_199_254_740_991
MAX_TOWER_ITEMS = 100
MAX_TOWER_PARTICIPANTS = 100
MAX_TOWER_NAME_LENGTH = 120


def validate_tower_gold(value: int) -> Gold:
    gold = Gold(value)
    if gold.amount > MAX_SAFE_INTEGER:
        raise ValidationError("Valor em gold excede o limite permitido")
    return gold


@dataclass(frozen=True, slots=True)
class TowerRelevantItem:
    item_id: EntityId
    item_name: str
    estimated_unit_value: Gold | None


@dataclass(frozen=True, slots=True)
class TowerConfiguration:
    guild_name: str
    entry_cost: Gold
    participant_ids: tuple[EntityId, ...]
    items: tuple[TowerRelevantItem, ...]
