from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from gf_dashboard.application.ports import Clock, FarmUnitOfWork, IdGenerator
from gf_dashboard.domain.entities import Activity, ActivityRuleVersion, MissionRewardRule
from gf_dashboard.domain.enums import (
    ActivityCategory,
    ActivityFrequency,
    MissionLimitType,
    RuleStatus,
)
from gf_dashboard.domain.value_objects import Gold, WorkspaceId


@dataclass(frozen=True, slots=True)
class DungeonDefinition:
    name: str
    mission_one_gold: int
    mission_two_gold: int


CONFIRMED_DUNGEONS: tuple[DungeonDefinition, ...] = (
    DungeonDefinition("Palácio de Proteção do Selo", 910, 490),
    DungeonDefinition("Câmara Secreta do Ritual das Trevas", 910, 490),
    DungeonDefinition("Destruidor do Vazio", 780, 420),
    DungeonDefinition("Igreja Subterrânea de Carso", 780, 420),
    DungeonDefinition("Santuário Maldito", 520, 280),
    DungeonDefinition("Dimensão Distorcida", 650, 350),
    DungeonDefinition("Primata", 650, 350),
    DungeonDefinition("Kaslow Ardente", 300, 295),
    DungeonDefinition("Ilha Condenada", 520, 280),
)


class DungeonCatalogService:
    def __init__(self, uow: FarmUnitOfWork, ids: IdGenerator, clock: Clock) -> None:
        self._uow = uow
        self._ids = ids
        self._clock = clock

    def seed_confirmed_dungeons(self, workspace_id: WorkspaceId) -> tuple[Activity, ...]:
        created: list[Activity] = []
        with self._uow:
            for definition in CONFIRMED_DUNGEONS:
                if self._uow.activities.exists_by_name(workspace_id, definition.name):
                    continue
                activity = Activity(
                    id=self._ids.new(),
                    workspace_id=workspace_id,
                    name=definition.name,
                    category=ActivityCategory.DUNGEON,
                    frequency=ActivityFrequency.DAILY,
                    default_target_amount=5,
                    created_at=self._clock.now(),
                )
                rule = ActivityRuleVersion(
                    id=self._ids.new(),
                    workspace_id=workspace_id,
                    activity_id=activity.id,
                    effective_from=date(2026, 8, 26),
                    effective_to=None,
                    max_completions=5,
                    target_amount=5,
                    status=RuleStatus.CONFIRMED,
                    rewards=(
                        MissionRewardRule(
                            "mission_1",
                            MissionLimitType.LIMITED,
                            Gold(definition.mission_one_gold),
                            1,
                        ),
                        MissionRewardRule(
                            "mission_2",
                            MissionLimitType.UNLIMITED,
                            Gold(definition.mission_two_gold),
                        ),
                    ),
                    created_at=self._clock.now(),
                    source="Catálogo confirmado em 2026-08-26",
                )
                self._uow.activities.save(activity)
                self._uow.rules.save(rule)
                created.append(activity)
        return tuple(created)
