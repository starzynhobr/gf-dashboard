from __future__ import annotations

from datetime import UTC, date, datetime, time

import pytest

from gf_dashboard.application.projections import estimate_selected_dungeons
from gf_dashboard.domain.entities import ActivityRuleVersion, ActivityWindow, MissionRewardRule
from gf_dashboard.domain.enums import MissionLimitType, RuleStatus
from gf_dashboard.domain.errors import RuleNotConfirmedError, ValidationError
from gf_dashboard.domain.value_objects import Gold, WorkspaceId
from gf_dashboard.infrastructure.in_memory import SequenceIdGenerator


def test_confirmed_rule_calculates_two_missions_for_five_runs() -> None:
    ids = SequenceIdGenerator()
    rule = ActivityRuleVersion(
        id=ids.new(),
        workspace_id=WorkspaceId(ids.new()),
        activity_id=ids.new(),
        effective_from=date(2026, 1, 1),
        effective_to=None,
        max_completions=5,
        target_amount=5,
        status=RuleStatus.CONFIRMED,
        rewards=(
            MissionRewardRule("mission_1", MissionLimitType.LIMITED, Gold(910), 1),
            MissionRewardRule("mission_2", MissionLimitType.UNLIMITED, Gold(490)),
        ),
        created_at=datetime(2026, 8, 26, tzinfo=UTC),
    )

    assert rule.reward_for_runs(5).gold == Gold(7000)
    assert rule.reward_for_runs(5).pve_bags == 5


def test_non_confirmed_rule_cannot_generate_automatic_reward() -> None:
    ids = SequenceIdGenerator()
    rule = ActivityRuleVersion(
        id=ids.new(),
        workspace_id=WorkspaceId(ids.new()),
        activity_id=ids.new(),
        effective_from=date(2026, 1, 1),
        effective_to=None,
        max_completions=5,
        target_amount=5,
        status=RuleStatus.INFORMATIONAL,
        rewards=(MissionRewardRule("mission_1", MissionLimitType.LIMITED, Gold(910), 1),),
        created_at=datetime(2026, 8, 26, tzinfo=UTC),
    )

    with pytest.raises(RuleNotConfirmedError):
        rule.reward_for_runs(1)


def test_rule_rejects_overlapping_mission_keys_and_invalid_period() -> None:
    ids = SequenceIdGenerator()
    with pytest.raises(ValidationError, match="Fim da vigência"):
        ActivityRuleVersion(
            id=ids.new(),
            workspace_id=WorkspaceId(ids.new()),
            activity_id=ids.new(),
            effective_from=date(2026, 2, 1),
            effective_to=date(2026, 1, 1),
            max_completions=5,
            target_amount=5,
            status=RuleStatus.CONFIRMED,
            rewards=(MissionRewardRule("mission_1", MissionLimitType.LIMITED, Gold(1)),),
            created_at=datetime(2026, 8, 26, tzinfo=UTC),
        )


def test_activity_window_rejects_invalid_weekday() -> None:
    ids = SequenceIdGenerator()
    with pytest.raises(ValidationError, match="0 e 6"):
        ActivityWindow(
            id=ids.new(),
            workspace_id=WorkspaceId(ids.new()),
            rule_version_id=ids.new(),
            weekday=7,
            opens_at_local=time(20, 0),
            duration_seconds=7200,
            timezone="America/Sao_Paulo",
        )


def test_selected_dungeon_estimate_does_not_include_tower_cost() -> None:
    ids = SequenceIdGenerator()
    rule = ActivityRuleVersion(
        id=ids.new(),
        workspace_id=WorkspaceId(ids.new()),
        activity_id=ids.new(),
        effective_from=date(2026, 1, 1),
        effective_to=None,
        max_completions=5,
        target_amount=5,
        status=RuleStatus.CONFIRMED,
        rewards=(
            MissionRewardRule("mission_1", MissionLimitType.LIMITED, Gold(910), 1),
            MissionRewardRule("mission_2", MissionLimitType.UNLIMITED, Gold(490)),
        ),
        created_at=datetime(2026, 8, 26, tzinfo=UTC),
    )

    estimate = estimate_selected_dungeons((rule,), Gold(1000))

    assert estimate.gold == Gold(7000)
    assert estimate.pve_bags == 5
    assert estimate.pve_bag_market_value == Gold(5000)
