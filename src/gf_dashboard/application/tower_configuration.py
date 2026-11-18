from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from typing import Protocol
from uuid import UUID

from gf_dashboard.domain.errors import ValidationError
from gf_dashboard.domain.tower_configuration import (
    MAX_TOWER_ITEMS,
    MAX_TOWER_NAME_LENGTH,
    MAX_TOWER_PARTICIPANTS,
    TowerConfiguration,
    validate_tower_gold,
)
from gf_dashboard.domain.value_objects import EntityId, WorkspaceId


@dataclass(frozen=True, slots=True)
class TowerItemSetting:
    item_name: str
    estimated_unit_value: int | None


@dataclass(frozen=True, slots=True)
class SaveTowerConfiguration:
    workspace_id: WorkspaceId
    idempotency_key: UUID
    guild_name: str
    entry_cost_gold: int
    participant_ids: tuple[EntityId, ...]
    items: tuple[TowerItemSetting, ...]


class TowerConfigurationStore(Protocol):
    def get(self, workspace_id: WorkspaceId) -> TowerConfiguration: ...

    def save(self, command: SaveTowerConfiguration, fingerprint: str) -> TowerConfiguration: ...


class TowerConfigurationService:
    def __init__(self, store: TowerConfigurationStore) -> None:
        self._store = store

    def get(self, workspace_id: WorkspaceId) -> TowerConfiguration:
        return self._store.get(workspace_id)

    def save(self, command: SaveTowerConfiguration) -> TowerConfiguration:
        if not isinstance(command.idempotency_key, UUID):
            raise ValidationError("Chave de idempotência deve ser um UUID válido")
        guild_name = command.guild_name.strip()
        if len(guild_name) > MAX_TOWER_NAME_LENGTH:
            raise ValidationError("Nome da guilda deve ter até 120 caracteres")
        validate_tower_gold(command.entry_cost_gold)
        if len(command.participant_ids) > MAX_TOWER_PARTICIPANTS:
            raise ValidationError("A Torre aceita até 100 personagens configurados")
        if len(set(command.participant_ids)) != len(command.participant_ids):
            raise ValidationError("Personagens da Torre não podem se repetir")
        if not all(isinstance(value, UUID) for value in command.participant_ids):
            raise ValidationError("ID do personagem deve ser um UUID válido")
        if len(command.items) > MAX_TOWER_ITEMS:
            raise ValidationError("A Torre aceita até 100 itens relevantes")
        names: set[str] = set()
        items: list[TowerItemSetting] = []
        for item in command.items:
            name = item.item_name.strip()
            if not name or len(name) > MAX_TOWER_NAME_LENGTH:
                raise ValidationError("Nome do item deve ter entre 1 e 120 caracteres")
            if name.casefold() in names:
                raise ValidationError("Itens relevantes não podem se repetir")
            names.add(name.casefold())
            if item.estimated_unit_value is not None:
                validate_tower_gold(item.estimated_unit_value)
            items.append(TowerItemSetting(name, item.estimated_unit_value))
        normalized = replace(command, guild_name=guild_name, items=tuple(items))
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "guildName": normalized.guild_name,
                    "entryCostGold": normalized.entry_cost_gold,
                    "participantIds": [str(value) for value in normalized.participant_ids],
                    "items": [
                        [item.item_name, item.estimated_unit_value] for item in normalized.items
                    ],
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        return self._store.save(normalized, fingerprint)
