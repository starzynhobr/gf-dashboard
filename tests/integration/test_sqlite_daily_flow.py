from __future__ import annotations

import json
import sqlite3
from datetime import UTC, date, datetime
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
from gf_dashboard.infrastructure.daily_operations import SqliteDailyOperations
from gf_dashboard.infrastructure.dashboard_reader import SqliteDashboardReader
from gf_dashboard.infrastructure.migrations.runner import load_migrations
from gf_dashboard.infrastructure.persistence import MigrationRunner, SqliteDatabase
from gf_dashboard.infrastructure.sqlite_repositories import SqliteUnitOfWork
from gf_dashboard.presentation.qt_bridge.app_bridge import AppBridge
from tests.helpers import confirmed_dungeon_rule, create_dungeon, create_memory_context


@pytest.mark.integration
def test_manual_expenses_and_work_routine_are_persisted_as_operational_facts(
    tmp_path: Path,
) -> None:
    database = SqliteDatabase(tmp_path / "routine.sqlite3", test_temporary_root=tmp_path)
    MigrationRunner(database, load_migrations(), app_version="0.1.0-test").migrate()
    _, ids, clock = create_memory_context()
    workspace = WorkspaceService(SqliteUnitOfWork(database), ids, clock).create_workspace("Pessoal")
    operations = SqliteDailyOperations(database)

    expense_id = operations.record_expense(
        str(workspace.id), "upgrade", 42_000, datetime(2026, 8, 30, tzinfo=UTC), "Pedra de arma"
    )
    replacement_expense_id = operations.update_manual_expense(
        str(workspace.id),
        expense_id,
        "upgrade",
        44_000,
        datetime(2026, 8, 30, tzinfo=UTC),
        "Pedra de arma corrigida",
    )
    started = operations.start_work_routine(str(workspace.id))
    paused = operations.pause_work_routine(str(workspace.id))
    resumed = operations.resume_work_routine(str(workspace.id))
    stopped = operations.stop_work_routine(str(workspace.id))

    assert expense_id
    assert started["status"] == "running"
    assert paused["status"] == "paused"
    assert resumed["status"] == "running"
    assert stopped["status"] == "completed"
    assert operations.get_work_routine(str(workspace.id)) is None
    bridge = AppBridge(database)
    bridge_response = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "expense-contract",
                    "method": "expenses.record",
                    "payload": {
                        "category": "consumable",
                        "amountGold": 500,
                        "occurredOn": "2026-08-30",
                    },
                }
            )
        )
    )
    assert bridge_response["ok"] is True
    assert bridge_response["data"]["transactionId"]
    connection = database.connect()
    try:
        original = connection.execute(
            "SELECT deleted_at FROM transactions WHERE id = ?", (expense_id,)
        ).fetchone()
        replacement = connection.execute(
            "SELECT category, amount_gold, description FROM transactions WHERE id = ?",
            (replacement_expense_id,),
        ).fetchone()
        audit = connection.execute(
            "SELECT action, before_json, after_json FROM audit_log WHERE entity_id = ?",
            (expense_id,),
        ).fetchone()
        assert original["deleted_at"] is not None
        assert tuple(replacement) == ("upgrade", 44_000, "Pedra de arma corrigida")
        assert audit["action"] == "corrected"
        assert json.loads(audit["before_json"])["amountGold"] == 42_000
        assert json.loads(audit["after_json"])["replacementTransactionId"] == replacement_expense_id
        expense_amounts = [
            expense["amount_gold"] for expense in operations.list_manual_expenses(str(workspace.id))
        ]
        assert expense_amounts == [500, 44_000]
        operations.void_manual_expense(str(workspace.id), replacement_expense_id)
        active_expense_amounts = [
            expense["amount_gold"] for expense in operations.list_manual_expenses(str(workspace.id))
        ]
        assert active_expense_amounts == [500]
        assert connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 3
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM work_routine_sessions WHERE status = 'completed'"
            ).fetchone()[0]
            == 1
        )
    finally:
        connection.close()


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
    assert overview.pve_bags_earned_today == 5
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
    assert response["data"]["pveBagsEarnedToday"] == 5


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
    assert not any(character.daily_mission_completed for character in characters)

    first_character = characters[0]
    operations = SqliteDailyOperations(database)
    assert operations.set_character_daily_mission(
        str(fixture.workspace_id), first_character.id, date(2026, 8, 26), True
    )
    operations.set_monthly_target(str(fixture.workspace_id), "2026-08", 30_000_000)
    expires_at = operations.save_character_vip(
        str(fixture.workspace_id),
        first_character.id,
        100_000,
        30,
        0,
        current_time=datetime(2026, 8, 26, 12, tzinfo=UTC),
    )
    assert expires_at == datetime(2026, 9, 25, 12, tzinfo=UTC)

    refreshed = SqliteDashboardReader(database).today_characters_for_default_workspace(
        date(2026, 8, 26)
    )
    reports = SqliteDashboardReader(database).reports_overview_for_default_workspace(
        date(2026, 8, 26)
    )

    assert refreshed is not None
    assert refreshed[0].daily_mission_completed is True
    assert refreshed[0].vip_expires_at == datetime(2026, 9, 25, 12, tzinfo=UTC)
    assert reports is not None
    assert reports.monthly_target.target_month == "2026-08"
    assert reports.monthly_target.target_gold == Gold(30_000_000)
    assert reports.financial_summary.vip_expenses_gold == Gold(100_000)

    operations.save_character_vip(
        str(fixture.workspace_id),
        first_character.id,
        100_000,
        27,
        10,
        current_time=datetime(2026, 8, 26, 13, tzinfo=UTC),
    )
    adjusted = SqliteDashboardReader(database).today_characters_for_default_workspace(
        date(2026, 8, 26)
    )
    adjusted_reports = SqliteDashboardReader(database).reports_overview_for_default_workspace(
        date(2026, 8, 26)
    )
    assert adjusted is not None
    assert adjusted[0].vip_expires_at == datetime(2026, 9, 22, 23, tzinfo=UTC)
    assert adjusted_reports is not None
    assert adjusted_reports.financial_summary.vip_expenses_gold == Gold(100_000)


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
    vip = invoke(
        "vip.save",
        {
            "characterId": character["id"],
            "paidGold": 100_000,
            "remainingDays": 27,
            "remainingHours": 10,
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
    assert vip["paidGold"] == 100_000
    assert vip["expiresAt"] == characters["characters"][0]["vipExpiresAt"]
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
    assert overview.tower_completed == 1
    assert overview.tower_total == 1
    assert [(item.item_name, item.quantity) for item in overview.recent_drops] == [("Drop raro", 2)]


@pytest.mark.integration
def test_history_overview_and_day_detail_query_and_bridge(tmp_path: Path) -> None:
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
    completion_service.complete_activity(workspace.id, character_activity.id, date(2026, 8, 25))
    completion_service.complete_activity(workspace.id, character_activity.id, date(2026, 8, 26))

    with database.connect() as conn:
        conn.execute(
            """
            INSERT INTO work_routine_sessions (
                id, workspace_id, status, started_at, finished_at,
                accumulated_seconds, created_at, updated_at
            ) VALUES (?, ?, 'completed', '2026-08-26T10:00:00Z', '2026-08-26T16:39:00Z',
                23940, '2026-08-26T10:00:00Z', '2026-08-26T16:39:00Z')
            """,
            (str(ids.new()), str(workspace.id)),
        )
        conn.commit()

    bridge = AppBridge(database)
    overview_res = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "req-hist-1",
                    "method": "history.overview",
                    "payload": {},
                }
            )
        )
    )
    assert overview_res["ok"] is True
    days = overview_res["data"]["days"]
    assert len(days) == 2
    assert days[0]["activityDate"] == "2026-08-26"
    assert days[0]["runsCompleted"] == 5
    assert days[0]["goldEarned"] == 7000
    assert days[0]["routineDurationSeconds"] == 23940
    assert days[1]["activityDate"] == "2026-08-25"
    assert days[1]["routineDurationSeconds"] == 0

    detail_res = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "req-hist-2",
                    "method": "history.dayDetail",
                    "payload": {"activityDate": "2026-08-26"},
                }
            )
        )
    )
    assert detail_res["ok"] is True
    detail = detail_res["data"]
    assert detail["activityDate"] == "2026-08-26"
    assert detail["runsCompleted"] == 5
    assert detail["goldEarned"] == 7000
    assert detail["routineDurationSeconds"] == 23940
    assert len(detail["characters"]) == 1
    assert detail["characters"][0]["name"] == "Star01"
    assert detail["characters"][0]["completedDungeons"] == 1
    assert detail["characters"][0]["dungeons"][0]["completed"] is True


@pytest.mark.integration
def test_pve_bag_quote_recording_and_dashboard_today_update(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "farm.sqlite3", test_temporary_root=tmp_path)
    MigrationRunner(database, load_migrations(), app_version="0.1.0-test").migrate()
    _, ids, clock = create_memory_context()
    uow = SqliteUnitOfWork(database)
    workspace = WorkspaceService(uow, ids, clock).create_workspace("Pessoal")
    DungeonCatalogService(uow, ids, clock).seed_confirmed_dungeons(workspace.id)

    bridge = AppBridge(database)
    acc_res = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "acc-1",
                    "method": "management.createAccount",
                    "payload": {"name": "Conta Principal", "serverName": "Valhalla"},
                }
            )
        )
    )
    assert acc_res["ok"] is True
    char_res = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "char-1",
                    "method": "management.createCharacter",
                    "payload": {
                        "accountId": acc_res["data"]["id"],
                        "name": "Star01",
                        "className": "Ranger",
                        "level": 91,
                    },
                }
            )
        )
    )
    assert char_res["ok"] is True

    # Record a PVE bag quote of 1,250 gold
    quote_res = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "quote-1",
                    "method": "market.recordPveBagQuote",
                    "payload": {"unitValueGold": 1250, "source": "auction"},
                }
            )
        )
    )
    assert quote_res["ok"] is True
    assert quote_res["data"]["unitValueGold"] == 1250

    # Query today to check market value calculation
    today_res = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "today-1",
                    "method": "dashboard.today",
                    "payload": {"activityDate": "2026-08-26"},
                }
            )
        )
    )
    assert today_res["ok"] is True
    assert today_res["data"]["estimatedPveBags"] == 45
    assert today_res["data"]["pveBagUnitValueGold"] == 1250
    assert today_res["data"]["estimatedPveBagMarketValue"] == 45 * 1250


@pytest.mark.integration
def test_reports_overview_aggregates_monthly_kpis_and_character_rankings(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "farm.sqlite3", test_temporary_root=tmp_path)
    MigrationRunner(database, load_migrations(), app_version="0.1.0-test").migrate()
    _, ids, clock = create_memory_context()
    uow = SqliteUnitOfWork(database)
    workspace = WorkspaceService(uow, ids, clock).create_workspace("Pessoal")
    DungeonCatalogService(uow, ids, clock).seed_confirmed_dungeons(workspace.id)

    bridge = AppBridge(database)
    acc = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "acc-1",
                    "method": "management.createAccount",
                    "payload": {"name": "Conta 1", "serverName": "Valhalla"},
                }
            )
        )
    )["data"]
    char = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "char-1",
                    "method": "management.createCharacter",
                    "payload": {
                        "accountId": acc["id"],
                        "name": "Sentry1",
                        "className": "Druida",
                        "level": 100,
                    },
                }
            )
        )
    )["data"]

    # Complete activities for character on 2026-08-26
    char_day = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "cday-1",
                    "method": "dashboard.characterDay",
                    "payload": {"characterId": char["id"], "activityDate": "2026-08-26"},
                }
            )
        )
    )["data"]
    act_ids = [d["characterActivityId"] for d in char_day["dungeons"][:3]]
    json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "save-1",
                    "method": "dashboard.saveCharacterDay",
                    "payload": {
                        "characterId": char["id"],
                        "activityDate": "2026-08-26",
                        "completedActivityIds": act_ids,
                    },
                }
            )
        )
    )

    connection = database.connect()
    try:
        routine_rows = [
            ("routine-previous", "2026-08-20T18:00:00+00:00", "2026-08-20T18:30:00+00:00", 1_800),
            ("routine-week-1", "2026-08-26T18:00:00+00:00", "2026-08-26T19:00:00+00:00", 3_600),
            ("routine-week-2", "2026-08-27T18:00:00+00:00", "2026-08-27T20:00:00+00:00", 7_200),
        ]
        for routine_id, started_at, finished_at, seconds in routine_rows:
            connection.execute(
                """INSERT INTO work_routine_sessions
                (id, workspace_id, status, started_at, finished_at, accumulated_seconds,
                 created_at, updated_at)
                VALUES (?, ?, 'completed', ?, ?, ?, ?, ?)""",
                (
                    routine_id,
                    str(workspace.id),
                    started_at,
                    finished_at,
                    seconds,
                    started_at,
                    finished_at,
                ),
            )
        connection.commit()
    finally:
        connection.close()

    # Query reports
    rep_res = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "rep-1",
                    "method": "reports.overview",
                    "payload": {"referenceDate": "2026-08-27"},
                }
            )
        )
    )
    assert rep_res["ok"] is True
    data = rep_res["data"]
    assert data["state"] == "ready"
    assert data["kpis"]["monthlyFarmGold"] > 0
    assert data["kpis"]["allTimeFarmGold"] > 0
    assert data["kpis"]["dailyAverageGold"] == data["kpis"]["monthlyFarmGold"]
    assert data["kpis"]["monthlyPveBagsEarned"] == 15
    assert data["monthlyTarget"]["currentPveBags"] == 15
    assert data["monthlyTarget"]["currentTotalValueGold"] == (
        data["monthlyTarget"]["currentGold"]
        + data["monthlyTarget"]["currentPveBags"]
        * (data["monthlyTarget"]["pveBagUnitValueGold"] or 0)
    )
    assert data["monthlyTarget"]["percentage"] >= 0
    assert len(data["recentMovements"]) == 3
    assert {movement["kind"] for movement in data["recentMovements"]} == {"dungeon"}
    assert data["workRoutineHistory"]["monthSeconds"] == 12_600
    assert data["workRoutineHistory"]["weekSeconds"] == 10_800
    assert data["workRoutineHistory"]["previousWeekSeconds"] == 1_800
    assert data["workRoutineHistory"]["monthSessionCount"] == 3
    assert data["workRoutineHistory"]["activeDaysInMonth"] == 3
    assert data["workRoutineHistory"]["recentSessions"][0]["id"] == "routine-week-2"


@pytest.mark.integration
def test_currency_rates_and_sales_flow(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "farm.sqlite3", test_temporary_root=tmp_path)
    MigrationRunner(database, load_migrations(), app_version="0.1.0-test").migrate()
    _, ids, clock = create_memory_context()
    uow = SqliteUnitOfWork(database)
    workspace = WorkspaceService(uow, ids, clock).create_workspace("Pessoal")
    DungeonCatalogService(uow, ids, clock).seed_confirmed_dungeons(workspace.id)

    bridge = AppBridge(database)

    # 1. Fetch currency rate
    rate_res = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "rate-1",
                    "method": "currency.getRate",
                    "payload": {
                        "baseCurrency": "USD",
                        "quoteCurrency": "BRL",
                        "date": "2026-08-27",
                    },
                }
            )
        )
    )
    assert rate_res["ok"] is True
    assert rate_res["data"]["baseCurrency"] == "USD"
    assert rate_res["data"]["quoteCurrency"] == "BRL"
    assert rate_res["data"]["rateMicros"] > 0

    # 2. Record a sale in USD
    sale_res = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "sale-1",
                    "method": "sales.record",
                    "payload": {
                        "saleType": "pve_bag",
                        "itemDescription": "Saco de Cristal (PvE)",
                        "quantity": 10,
                        "originalAmountMinor": 2500,
                        "currency": "USD",
                        "exchangeRateMicros": 5_430_000,
                        "exchangeRateSource": "manual",
                        "idempotencyKey": "0dc2a3dc-21b0-4c96-a5d5-03e894f98d47",
                        "soldAt": "2026-08-27T14:00:00+00:00",
                    },
                }
            )
        )
    )
    assert sale_res["ok"] is True
    assert sale_res["data"]["realAmountMinor"] == 13575

    # 3. Check today activity returns today sales
    today_act = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "act-1",
                    "method": "dashboard.todayActivity",
                    "payload": {"activityDate": "2026-08-27"},
                }
            )
        )
    )
    assert today_act["ok"] is True
    assert today_act["data"]["todaySalesMinor"] == 13575

    # Replays keep one sale and one financial transaction.
    replay_res = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "sale-2",
                    "method": "sales.record",
                    "payload": {
                        "saleType": "pve_bag",
                        "itemDescription": "Saco de Cristal (PvE)",
                        "quantity": 10,
                        "originalAmountMinor": 2500,
                        "currency": "USD",
                        "exchangeRateMicros": 5_430_000,
                        "exchangeRateSource": "manual",
                        "idempotencyKey": "0dc2a3dc-21b0-4c96-a5d5-03e894f98d47",
                        "soldAt": "2026-08-27T14:00:00+00:00",
                    },
                }
            )
        )
    )
    assert replay_res["ok"] is True
    assert replay_res["data"]["alreadyRecorded"] is True
    gold_sale = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "sale-gold",
                    "method": "sales.record",
                    "payload": {
                        "saleType": "gold",
                        "itemDescription": "Gold",
                        "quantity": 950_500,
                        "originalAmountMinor": 7604,
                        "currency": "BRL",
                        "exchangeRateMicros": 1_000_000,
                        "exchangeRateSource": "manual",
                        "idempotencyKey": "411e94b7-9d34-4e9d-bae4-b0041fa79a85",
                        "soldAt": "2026-08-27T15:00:00+00:00",
                    },
                }
            )
        )
    )
    assert gold_sale["ok"] is True
    reports = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "sales-reports",
                    "method": "reports.overview",
                    "payload": {"referenceDate": "2026-08-27"},
                }
            )
        )
    )
    assert reports["data"]["financialSummary"]["itemsSoldCount"] == 10
    assert reports["data"]["financialSummary"]["goldConvertedTotal"] == 950_500
    connection = database.connect(read_only=True)
    try:
        assert connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0] == 2
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM transactions WHERE category = 'sale'"
            ).fetchone()[0]
            == 2
        )
    finally:
        connection.close()


@pytest.mark.integration
def test_reports_monthly_comparison_equivalent_period_and_sales_history(tmp_path: Path) -> None:
    database = SqliteDatabase(tmp_path / "farm.sqlite3", test_temporary_root=tmp_path)
    MigrationRunner(database, load_migrations(), app_version="0.1.0-test").migrate()
    _, ids, clock = create_memory_context()
    uow = SqliteUnitOfWork(database)
    workspace = WorkspaceService(uow, ids, clock).create_workspace("Pessoal")
    DungeonCatalogService(uow, ids, clock).seed_confirmed_dungeons(workspace.id)

    bridge = AppBridge(database)
    acc = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "acc-1",
                    "method": "management.createAccount",
                    "payload": {"name": "Conta 1", "serverName": "Valhalla"},
                }
            )
        )
    )["data"]
    char = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "char-1",
                    "method": "management.createCharacter",
                    "payload": {
                        "accountId": acc["id"],
                        "name": "Sentry1",
                        "className": "Druida",
                        "level": 100,
                    },
                }
            )
        )
    )["data"]

    # Activity completions
    # 2026-08-03: within 1-7 Aug -> 500k gold, 10 bags
    # 2026-08-20: outside 1-7 Aug -> 1000k gold, 20 bags
    # 2026-09-02: within 1-7 Sept -> 600k gold, 12 bags
    connection = database.connect()
    try:
        connection.execute(
            """INSERT INTO farm_sessions
            (id, workspace_id, session_type, primary_character_id, status,
             activity_date, gold_earned, pve_bags_earned, runs_count,
             created_at, updated_at)
            VALUES
            ('fs-aug-early', ?, 'activity', ?, 'completed', '2026-08-03',
             500000, 10, 5, '2026-08-03T12:00:00Z', '2026-08-03T12:00:00Z'),
            ('fs-aug-late', ?, 'activity', ?, 'completed', '2026-08-20',
             1000000, 20, 10, '2026-08-20T12:00:00Z', '2026-08-20T12:00:00Z'),
            ('fs-sep-early', ?, 'activity', ?, 'completed', '2026-09-02',
             600000, 12, 6, '2026-09-02T12:00:00Z', '2026-09-02T12:00:00Z')""",
            (
                str(workspace.id),
                char["id"],
                str(workspace.id),
                char["id"],
                str(workspace.id),
                char["id"],
            ),
        )

        # Sales:
        # 2026-08-04: within 1-7 Aug -> R$ 100,00 (10000 minor)
        # 2026-08-25: outside 1-7 Aug -> R$ 300,00 (30000 minor)
        # 2026-09-03: within 1-7 Sept -> R$ 150,00 (15000 minor)
        connection.execute(
            """INSERT INTO sales
            (id, workspace_id, sale_type, status, real_amount_minor, currency,
             item_quantity, sold_at, created_at, updated_at)
            VALUES
            ('sale-aug-early', ?, 'pve_bag', 'completed', 10000, 'BRL', 5,
             '2026-08-04T14:00:00Z', '2026-08-04T14:00:00Z', '2026-08-04T14:00:00Z'),
            ('sale-aug-late', ?, 'gold', 'completed', 30000, 'BRL', 1,
             '2026-08-25T14:00:00Z', '2026-08-25T14:00:00Z', '2026-08-25T14:00:00Z'),
            ('sale-sep-early', ?, 'item', 'completed', 15000, 'BRL', 2,
             '2026-09-03T14:00:00Z', '2026-09-03T14:00:00Z', '2026-09-03T14:00:00Z')""",
            (str(workspace.id), str(workspace.id), str(workspace.id)),
        )
        connection.commit()
    finally:
        connection.close()

    # Query 1: Partial month (2026-09-07) -> compares 1-7 Sept vs 1-7 Aug
    res = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "rep-sep",
                    "method": "reports.overview",
                    "payload": {"referenceDate": "2026-09-07"},
                }
            )
        )
    )["data"]

    kpis = res["kpis"]
    # Sales: Sept (1-7) has 15000 minor; Aug (1-7) has 10000 minor (not 40000!)
    assert kpis["monthlySalesMinor"] == 15000
    assert kpis["previousSalesMinor"] == 10000
    assert kpis["salesChangePercent"] == 50  # +50%
    assert kpis["salesChangeStatus"] == "valid"

    # Farm: Sept (1-7) has 600_000 gold; Aug (1-7) has 500_000 gold (not 1_500_000!)
    assert kpis["monthlyFarmGold"] == 600000
    assert kpis["previousFarmGold"] == 500000
    assert kpis["farmGoldChangePercent"] == 20  # +20%
    assert kpis["farmGoldChangeStatus"] == "valid"

    # Monthly comparison
    comp = res["monthlyComparison"]
    assert comp["isPartial"] is True
    assert comp["growthPercent"] == 20
    assert comp["growthStatus"] == "valid"
    assert comp["currentMonthName"] == "Set (1-7)"
    assert comp["previousMonthName"] == "Ago (1-7)"
    assert comp["currentPeriodLabel"] == "1 - 7 de setembro"
    assert comp["previousPeriodLabel"] == "1 - 7 de agosto"

    # Monthly sales history: chronological order, proper labels and isPartial flag
    sales_hist = res["monthlySalesHistory"]
    assert len(sales_hist) >= 2
    assert sales_hist[-2]["monthKey"] == "2026-08"
    assert sales_hist[-2]["salesAmountMinor"] == 40000  # Total Aug sales: 10000 + 30000
    assert sales_hist[-2]["salesCount"] == 2
    assert sales_hist[-2]["isPartial"] is False

    assert sales_hist[-1]["monthKey"] == "2026-09"
    assert sales_hist[-1]["salesAmountMinor"] == 15000
    assert sales_hist[-1]["salesCount"] == 1
    assert sales_hist[-1]["isPartial"] is True

    # Query 2: Absence of data in previous period (2026-08-07 vs July 1-7 which has 0)
    res_aug = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "rep-aug",
                    "method": "reports.overview",
                    "payload": {"referenceDate": "2026-08-07"},
                }
            )
        )
    )["data"]
    assert res_aug["kpis"]["monthlySalesMinor"] == 10000
    assert res_aug["kpis"]["previousSalesMinor"] == 0
    assert res_aug["kpis"]["salesChangePercent"] is None
    assert res_aug["kpis"]["salesChangeStatus"] == "no_baseline"
    assert res_aug["monthlyComparison"]["growthStatus"] == "no_baseline"

    # Query 3: Closed month vs closed month (2026-08-31 vs July 1-31)
    res_closed = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "rep-closed",
                    "method": "reports.overview",
                    "payload": {"referenceDate": "2026-08-31"},
                }
            )
        )
    )["data"]
    assert res_closed["kpis"]["isPartialMonth"] is False
    assert res_closed["monthlyComparison"]["isPartial"] is False
    assert res_closed["monthlyComparison"]["currentMonthName"] == "Ago/26"

    # Query 4: Year wrap (2027-01-05 vs Dec 2026)
    res_wrap = json.loads(
        bridge.invoke(
            json.dumps(
                {
                    "version": 1,
                    "requestId": "rep-wrap",
                    "method": "reports.overview",
                    "payload": {"referenceDate": "2027-01-05"},
                }
            )
        )
    )["data"]
    assert res_wrap["monthlyComparison"]["currentPeriodLabel"] == "1 - 5 de janeiro"
    assert res_wrap["monthlyComparison"]["previousPeriodLabel"] == "1 - 5 de dezembro"
