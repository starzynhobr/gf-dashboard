from __future__ import annotations

from datetime import UTC, date, datetime

from gf_dashboard.domain.entities import Activity, ActivityRuleVersion, MissionRewardRule
from gf_dashboard.domain.enums import (
    ActivityCategory,
    ActivityFrequency,
    MissionLimitType,
    RuleStatus,
)
from gf_dashboard.domain.value_objects import Gold, WorkspaceId
from gf_dashboard.infrastructure.in_memory import (
    FixedClock,
    InMemoryUnitOfWork,
    SequenceIdGenerator,
)


def fixed_now() -> datetime:
    return datetime(2026, 8, 26, 15, 30, tzinfo=UTC)


def confirmed_dungeon_rule(
    *,
    rule_id: object,
    workspace_id: WorkspaceId,
    activity_id: object,
    status: RuleStatus = RuleStatus.CONFIRMED,
) -> ActivityRuleVersion:
    return ActivityRuleVersion(
        id=rule_id,  # type: ignore[arg-type]
        workspace_id=workspace_id,
        activity_id=activity_id,  # type: ignore[arg-type]
        effective_from=date(2026, 1, 1),
        effective_to=None,
        max_completions=5,
        target_amount=5,
        status=status,
        rewards=(
            MissionRewardRule("mission_1", MissionLimitType.LIMITED, Gold(910), 1),
            MissionRewardRule("mission_2", MissionLimitType.UNLIMITED, Gold(490), 0),
        ),
        created_at=fixed_now(),
        source="catálogo confirmado",
    )


def create_memory_context() -> tuple[InMemoryUnitOfWork, SequenceIdGenerator, FixedClock]:
    return InMemoryUnitOfWork(), SequenceIdGenerator(), FixedClock(fixed_now())


def create_dungeon(*, activity_id: object, workspace_id: WorkspaceId) -> Activity:
    return Activity(
        id=activity_id,  # type: ignore[arg-type]
        workspace_id=workspace_id,
        name="Palácio de Proteção do Selo",
        category=ActivityCategory.DUNGEON,
        frequency=ActivityFrequency.DAILY,
        default_target_amount=5,
        created_at=fixed_now(),
    )
