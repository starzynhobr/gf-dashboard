from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path
from uuid import UUID

import pytest

from gf_dashboard.application.catalog import DungeonCatalogService
from gf_dashboard.application.fixtures import create_golden_fixture
from gf_dashboard.application.market_quotes import MarketQuoteService
from gf_dashboard.application.projections import estimate_selected_dungeons
from gf_dashboard.application.services import (
    ActivityCompletionService,
    ManagementService,
    WorkspaceService,
)
from gf_dashboard.application.tower import TOWER_ENTRY_COST, TowerSessionService
from gf_dashboard.domain.enums import ActivityStatus
from gf_dashboard.domain.value_objects import EntityId, Gold
from gf_dashboard.infrastructure.dashboard_reader import SqliteDashboardReader
from gf_dashboard.infrastructure.migrations.runner import load_migrations
from gf_dashboard.infrastructure.persistence import MigrationRunner, SqliteDatabase
from gf_dashboard.infrastructure.sqlite_repositories import SqliteUnitOfWork
from gf_dashboard.presentation.qt_bridge.app_bridge import AppBridge
from tests.helpers import confirmed_dungeon_rule, create_dungeon, create_memory_context


@pytest.mark.integration
def test_sqlite_daily_dungeon_flow_is_atomic_idempotent_and_reopenable(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "farm.sqlite3", test_temporary_root=tmp_path)
    MigrationRunner(database, load_migrations(), app_version="0.1.0-test").migrate()
    _, ids, clock = create_memory_context()
    uow = SqliteUnitOfWork(database)
    workspace_service = WorkspaceService(uow, ids, clock)
    completion_service = ActivityCompletionService(uow, ids, clock)
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
                rule_id=ids.new(), workspace_id=workspace.id, activity_id=activity.id
            )
        )
    character_activity = workspace_service.configure_character_activity(
        workspace.id, character.id, activity.id, 5, 1
    )

    first = completion_service.complete_activity(
        workspace.id, character_activity.id, date(2026, 8, 26)
    )
    second = completion_service.complete_activity(
        workspace.id, character_activity.id, date(2026, 8, 26)
    )
    reopened = completion_service.reopen_activity(
        workspace.id, character_activity.id, date(2026, 8, 26)
    )
    third = completion_service.complete_activity(
        workspace.id, character_activity.id, date(2026, 8, 26)
    )

    assert first.already_completed is False
    assert first.total_reward.gold == Gold(7000)
    assert first.total_reward.pve_bags == 5
    assert second.already_completed is True
    assert reopened.status is ActivityStatus.PENDING
    assert third.already_completed is False
    with uow:
        persisted = uow.completions.list_for_entry(workspace.id, first.entry.id)
    assert [completion.sequence_no for completion in persisted] == [1, 2, 3, 4, 5]
    overview = SqliteDashboardReader(database).today_activity_for_default_workspace(
        date(2026, 8, 26)
    )
    assert overview is not None
    assert overview.runs_completed == 5
    assert overview.monthly_gold_total == Gold(7000)
    assert [(point.activity_date, point.gold) for point in overview.monthly_gold] == [
        (date(2026, 8, 26), Gold(7000))
    ]
    response = json.loads(
        AppBridge(database).invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "activity-overview",
                    "method": "dashboard.todayActivity",
                    "payload": {"activityDate": "2026-08-26"},
                }
            )
        )
    )
    assert response["ok"] is True
    assert response["data"]["runsCompleted"] == 5
    assert response["data"]["monthlyGoldTotal"] == 7000


@pytest.mark.integration
def test_confirmed_catalog_seeds_nine_versioned_dungeons_once(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "farm.sqlite3", test_temporary_root=tmp_path)
    MigrationRunner(database, load_migrations(), app_version="0.1.0-test").migrate()
    _, ids, clock = create_memory_context()
    uow = SqliteUnitOfWork(database)
    workspace = WorkspaceService(uow, ids, clock).create_workspace("Pessoal")
    catalog = DungeonCatalogService(uow, ids, clock)

    created = catalog.seed_confirmed_dungeons(workspace.id)
    repeated = catalog.seed_confirmed_dungeons(workspace.id)

    assert len(created) == 9
    assert repeated == ()
    palacio = next(
        activity for activity in created if activity.name == "Palácio de Proteção do Selo"
    )
    with uow:
        rule = uow.rules.find_effective(workspace.id, palacio.id, date(2026, 8, 26))
    assert rule is not None
    assert rule.reward_for_runs(5).gold == Gold(7000)
    assert rule.reward_for_runs(5).pve_bags == 5


@pytest.mark.integration
def test_golden_fixture_configures_all_nine_dungeons_for_two_accounts_and_ten_characters(
    tmp_path: Path,
) -> None:
    database = SqliteDatabase(tmp_path / "farm.sqlite3", test_temporary_root=tmp_path)
    MigrationRunner(database, load_migrations(), app_version="0.1.0-test").migrate()
    _, ids, clock = create_memory_context()

    fixture = create_golden_fixture(SqliteUnitOfWork(database), ids, clock)

    assert fixture.accounts_count == 2
    assert fixture.characters_count == 10
    assert fixture.selected_dungeons_per_character == 9


@pytest.mark.integration
def test_pve_bag_quote_is_versioned_and_complements_the_dungeon_gold_estimate(
    tmp_path: Path,
) -> None:
    database = SqliteDatabase(tmp_path / "farm.sqlite3", test_temporary_root=tmp_path)
    MigrationRunner(database, load_migrations(), app_version="0.1.0-test").migrate()
    _, ids, clock = create_memory_context()
    uow = SqliteUnitOfWork(database)
    workspace = WorkspaceService(uow, ids, clock).create_workspace("Pessoal")
    activities = DungeonCatalogService(uow, ids, clock).seed_confirmed_dungeons(workspace.id)
    quotes = MarketQuoteService(uow, ids, clock)

    first = quotes.record_pve_bag_quote(workspace.id, Gold(900), "mercado")
    latest = quotes.record_pve_bag_quote(workspace.id, Gold(1000), "mercado")
    current = quotes.current_pve_bag_quote(workspace.id)
    with uow:
        rules = tuple(
            rule
            for activity in activities
            if (rule := uow.rules.find_effective(workspace.id, activity.id, date(2026, 8, 26)))
            is not None
        )

    estimate = estimate_selected_dungeons(rules, current.unit_value_gold if current else None)

    assert current is not None
    assert current.id == latest.id
    assert current.id != first.id
    assert estimate.gold == Gold(46975)
    assert estimate.pve_bags == 45
    assert estimate.pve_bag_market_value == Gold(45000)


@pytest.mark.integration
def test_dashboard_reader_keeps_gold_kpi_separate_from_pve_bag_value(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "farm.sqlite3", test_temporary_root=tmp_path)
    MigrationRunner(database, load_migrations(), app_version="0.1.0-test").migrate()
    _, ids, clock = create_memory_context()
    fixture = create_golden_fixture(SqliteUnitOfWork(database), ids, clock)
    MarketQuoteService(SqliteUnitOfWork(database), ids, clock).record_pve_bag_quote(
        fixture.workspace_id, Gold(1000), "mercado"
    )

    today = SqliteDashboardReader(database).today_estimate(fixture.workspace_id, date(2026, 8, 26))

    assert today.selected_dungeons == 90
    assert today.estimated_gold == Gold(469750)
    assert today.estimated_pve_bags == 450
    assert today.estimated_pve_bag_market_value == Gold(450000)


@pytest.mark.integration
def test_dashboard_reader_lists_fixture_characters_with_daily_progress(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "farm.sqlite3", test_temporary_root=tmp_path)
    MigrationRunner(database, load_migrations(), app_version="0.1.0-test").migrate()
    _, ids, clock = create_memory_context()
    fixture = create_golden_fixture(SqliteUnitOfWork(database), ids, clock)

    characters = SqliteDashboardReader(database).today_characters_for_default_workspace(
        date(2026, 8, 26)
    )

    assert characters is not None
    assert len(characters) == fixture.characters_count
    assert all(character.selected_dungeons == 9 for character in characters)
    assert all(character.completed_dungeons == 0 for character in characters)


@pytest.mark.integration
def test_management_creates_character_with_global_routine_and_saves_day_atomically(
    tmp_path: Path,
) -> None:
    database = SqliteDatabase(tmp_path / "farm.sqlite3", test_temporary_root=tmp_path)
    MigrationRunner(database, load_migrations(), app_version="0.1.0-test").migrate()
    _, ids, clock = create_memory_context()
    uow = SqliteUnitOfWork(database)
    workspace = WorkspaceService(uow, ids, clock).create_workspace("Pessoal")
    DungeonCatalogService(uow, ids, clock).seed_confirmed_dungeons(workspace.id)
    management = ManagementService(uow, ids, clock)
    account = management.create_account(workspace.id, "Conta Principal", "Valhalla")
    character = management.create_character_with_default_activities(
        workspace.id, account.id, "Star01", "Ranger", 91
    )
    reader = SqliteDashboardReader(database)

    overview = reader.management_overview()
    day = reader.character_day_for_default_workspace(character.id, date(2026, 8, 26))

    assert overview is not None
    assert overview.accounts[0].characters[0].name == "Star01"
    assert len(overview.dungeons) == 9
    assert day is not None
    assert len(day.dungeons) == 9

    first_two = tuple(EntityId(UUID(item.character_activity_id)) for item in day.dungeons[:2])
    expected_gold = sum(item.gold.amount for item in day.dungeons[:2])
    completion = ActivityCompletionService(uow, ids, clock)
    saved = completion.save_character_day(workspace.id, character.id, date(2026, 8, 26), first_two)

    assert saved.completed_dungeons == 2
    assert saved.gold == expected_gold
    assert saved.pve_bags == 10
    refreshed = reader.character_day_for_default_workspace(character.id, date(2026, 8, 26))
    assert refreshed is not None
    assert [item.completed for item in refreshed.dungeons[:2]] == [True, True]

    completion.save_character_day(workspace.id, character.id, date(2026, 8, 26), first_two[:1])
    reopened = reader.character_day_for_default_workspace(character.id, date(2026, 8, 26))
    activity = reader.today_activity_for_default_workspace(date(2026, 8, 26))
    assert reopened is not None
    assert [item.completed for item in reopened.dungeons[:2]] == [True, False]
    assert activity is not None
    assert activity.runs_completed == 5

    management.set_dungeon_active(workspace.id, EntityId(UUID(overview.dungeons[0].id)), False)
    disabled = reader.character_day_for_default_workspace(character.id, date(2026, 8, 26))
    assert disabled is not None
    assert len(disabled.dungeons) == 8


@pytest.mark.integration
def test_bridge_contract_covers_registration_character_day_and_dashboard_refresh(
    tmp_path: Path,
) -> None:
    database = SqliteDatabase(tmp_path / "farm.sqlite3", test_temporary_root=tmp_path)
    MigrationRunner(database, load_migrations(), app_version="0.1.0-test").migrate()
    _, ids, clock = create_memory_context()
    workspace = WorkspaceService(SqliteUnitOfWork(database), ids, clock).create_workspace("Pessoal")
    DungeonCatalogService(SqliteUnitOfWork(database), ids, clock).seed_confirmed_dungeons(
        workspace.id
    )
    bridge = AppBridge(database)

    def invoke(method: str, payload: dict[str, object]) -> dict[str, object]:
        response = json.loads(
            bridge.invoke(
                json.dumps(
                    {
                        "version": 1,
                        "requestId": method,
                        "method": method,
                        "payload": payload,
                    }
                )
            )
        )
        assert response["ok"] is True
        return response["data"]

    account = invoke(
        "management.createAccount", {"name": "Conta Principal", "serverName": "Valhalla"}
    )
    character = invoke(
        "management.createCharacter",
        {
            "accountId": account["id"],
            "name": "Star01",
            "className": "Ranger",
            "level": 91,
        },
    )
    renamed_account = invoke(
        "management.updateAccount",
        {"accountId": account["id"], "name": "DK", "serverName": "Servidor Violet"},
    )
    renamed_character = invoke(
        "management.updateCharacter",
        {
            "characterId": character["id"],
            "name": "Sentry1",
            "className": "Druida",
            "level": 100,
        },
    )
    management = invoke("management.overview", {})
    day = invoke(
        "dashboard.characterDay",
        {"characterId": character["id"], "activityDate": "2026-08-26"},
    )
    dungeon_ids = [item["characterActivityId"] for item in day["dungeons"][:2]]
    saved = invoke(
        "dashboard.saveCharacterDay",
        {
            "characterId": character["id"],
            "activityDate": "2026-08-26",
            "completedActivityIds": dungeon_ids,
        },
    )
    characters = invoke("dashboard.todayCharacters", {"activityDate": "2026-08-26"})
    tower = invoke(
        "tower.registerCompleted",
        {
            "activityDate": "2026-08-26",
            "guildName": "Guild Teste",
            "participantIds": [character["id"]],
            "drops": [{"itemName": "Drop raro", "quantity": 2, "estimatedUnitValue": 1500}],
        },
    )
    activity = invoke("dashboard.todayActivity", {"activityDate": "2026-08-26"})
    hidden_layout = invoke(
        "dashboard.setModuleVisible",
        {"moduleKey": "monthly-performance", "enabled": False},
    )
    persisted_layout = invoke("dashboard.layout", {})
    reset_layout = invoke("dashboard.resetLayout", {})

    assert renamed_account["name"] == "DK"
    assert renamed_character["name"] == "Sentry1"
    assert management["accounts"][0]["name"] == "DK"
    assert management["accounts"][0]["characters"][0]["name"] == "Sentry1"
    assert len(management["dungeons"]) == 9
    assert len(day["dungeons"]) == 9
    assert saved["completedDungeons"] == 2
    assert characters["characters"][0]["completedDungeons"] == 2
    assert tower["entryCostGold"] == 25_000
    assert tower["participantCount"] == 1
    assert activity["towerCompleted"] == 1
    assert activity["recentDrops"][0]["itemName"] == "Drop raro"
    assert hidden_layout["visibility"]["monthly-performance"] is False
    assert persisted_layout["visibility"]["monthly-performance"] is False
    assert all(reset_layout["visibility"].values())


@pytest.mark.integration
def test_tower_is_separate_session_with_fixed_single_cost_and_idempotent_completion(
    tmp_path: Path,
) -> None:
    database = SqliteDatabase(tmp_path / "farm.sqlite3", test_temporary_root=tmp_path)
    MigrationRunner(database, load_migrations(), app_version="0.1.0-test").migrate()
    _, ids, clock = create_memory_context()
    uow = SqliteUnitOfWork(database)
    workspace_service = WorkspaceService(uow, ids, clock)
    workspace = workspace_service.create_workspace("Pessoal")
    account = workspace_service.create_account(workspace.id, "Conta", "Valhalla")
    first_character = workspace_service.create_character(
        workspace.id, account.id, "Star01", "Ranger", 91, 1
    )
    second_character = workspace_service.create_character(
        workspace.id, account.id, "Star02", "Mago", 91, 2
    )
    tower = TowerSessionService(uow, ids, clock)

    created = tower.create(
        workspace.id,
        date(2026, 8, 26),
        (first_character.id, second_character.id),
        "Guild Teste",
    )
    first_completion = tower.complete(workspace.id, created.session.id)
    repeated_completion = tower.complete(workspace.id, created.session.id)

    assert created.details.entry_cost == TOWER_ENTRY_COST
    assert len(created.participants) == 2
    assert first_completion.details.completed is True
    assert repeated_completion.already_completed is True
    item_id = ids.new()
    connection = sqlite3.connect(database.path)
    try:
        now = clock.now().isoformat()
        connection.execute(
            "INSERT INTO items (id, workspace_id, name, category, created_at, updated_at) "
            "VALUES (?, ?, 'Drop raro', 'drop', ?, ?)",
            (str(item_id), str(workspace.id), now, now),
        )
        connection.commit()
    finally:
        connection.close()

    drop = tower.record_drop(workspace.id, created.session.id, item_id, 2, Gold(1500))

    assert drop.quantity == 2
    assert drop.estimated_unit_value == Gold(1500)
    overview = SqliteDashboardReader(database).today_activity_for_default_workspace(
        date(2026, 8, 26)
    )
    assert overview is not None
    assert overview.tower_completed == 1
    assert overview.tower_total == 1
    assert [(item.item_name, item.quantity) for item in overview.recent_drops] == [("Drop raro", 2)]
