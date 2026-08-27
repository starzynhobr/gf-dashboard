from __future__ import annotations

from datetime import date

import pytest

from gf_dashboard.application.services import ActivityCompletionService, WorkspaceService
from gf_dashboard.domain.enums import ActivityStatus, RuleStatus
from gf_dashboard.domain.errors import ConflictError, NotFoundError, RuleNotConfirmedError
from gf_dashboard.domain.value_objects import Gold
from tests.helpers import confirmed_dungeon_rule, create_dungeon, create_memory_context


def _prepared_context(*, status: RuleStatus = RuleStatus.CONFIRMED):
    uow, ids, clock = create_memory_context()
    workspace_service = WorkspaceService(uow, ids, clock)
    workspace = workspace_service.create_workspace("Pessoal")
    account = workspace_service.create_account(workspace.id, "Conta Principal", "Valhalla")
    character = workspace_service.create_character(
        workspace.id, account.id, "Star01", "Ranger", 91, 1
    )
    activity = create_dungeon(activity_id=ids.new(), workspace_id=workspace.id)
    with uow:
        uow.activities.save(activity)
        uow.rules.save(
            confirmed_dungeon_rule(
                rule_id=ids.new(),
                workspace_id=workspace.id,
                activity_id=activity.id,
                status=status,
            )
        )
    character_activity = workspace_service.configure_character_activity(
        workspace.id, character.id, activity.id, 5, 1
    )
    return uow, ids, clock, workspace, account, character_activity


def test_complete_activity_generates_five_snapshots_and_catalog_totals() -> None:
    uow, ids, clock, workspace, _, character_activity = _prepared_context()
    service = ActivityCompletionService(uow, ids, clock)

    result = service.complete_activity(workspace.id, character_activity.id, date(2026, 8, 26))

    assert result.already_completed is False
    assert result.entry.status is ActivityStatus.COMPLETED
    assert result.entry.progress_amount == 5
    assert [completion.sequence_no for completion in result.completions] == [1, 2, 3, 4, 5]
    assert result.total_reward.gold == Gold(7000)
    assert result.total_reward.pve_bags == 5


def test_complete_activity_is_idempotent_for_same_character_activity_and_day() -> None:
    uow, ids, clock, workspace, _, character_activity = _prepared_context()
    service = ActivityCompletionService(uow, ids, clock)
    activity_date = date(2026, 8, 26)

    first = service.complete_activity(workspace.id, character_activity.id, activity_date)
    second = service.complete_activity(workspace.id, character_activity.id, activity_date)

    assert first.already_completed is False
    assert second.already_completed is True
    assert second.entry.id == first.entry.id
    assert len(second.completions) == 5
    assert len(uow.state.completions) == 5


def test_reopen_removes_reward_snapshots_and_allows_a_new_completion() -> None:
    uow, ids, clock, workspace, _, character_activity = _prepared_context()
    service = ActivityCompletionService(uow, ids, clock)
    activity_date = date(2026, 8, 26)
    first = service.complete_activity(workspace.id, character_activity.id, activity_date)

    reopened = service.reopen_activity(workspace.id, character_activity.id, activity_date)
    second = service.complete_activity(workspace.id, character_activity.id, activity_date)

    assert reopened.status is ActivityStatus.PENDING
    assert len(uow.state.completions) == 5
    assert second.entry.id == first.entry.id
    assert second.already_completed is False


def test_unconfirmed_rule_cannot_create_daily_entry_or_snapshots() -> None:
    uow, ids, clock, workspace, _, character_activity = _prepared_context(
        status=RuleStatus.INFORMATIONAL
    )
    service = ActivityCompletionService(uow, ids, clock)

    with pytest.raises(RuleNotConfirmedError):
        service.complete_activity(workspace.id, character_activity.id, date(2026, 8, 26))

    assert uow.state.daily_entries == {}
    assert uow.state.completions == {}


def test_workspace_service_prevents_duplicate_account_and_cross_workspace_character() -> None:
    uow, ids, clock, workspace, account, _ = _prepared_context()
    service = WorkspaceService(uow, ids, clock)
    other_workspace = service.create_workspace("Outro")

    with pytest.raises(ConflictError):
        service.create_account(workspace.id, "conta principal", "Valhalla")
    with pytest.raises(NotFoundError):
        service.create_character(other_workspace.id, account.id, "Star02", "Mago", 91, 2)
