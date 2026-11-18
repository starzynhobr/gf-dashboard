from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest

from gf_dashboard.application.services import WorkspaceService
from gf_dashboard.application.tower import TowerDropInput, TowerSessionService
from gf_dashboard.application.tower_configuration import (
    SaveTowerConfiguration,
    TowerConfigurationService,
    TowerItemSetting,
)
from gf_dashboard.domain.errors import ConflictError, NotFoundError
from gf_dashboard.domain.value_objects import EntityId, Gold, WorkspaceId
from gf_dashboard.infrastructure.in_memory import SystemClock, UUIDGenerator
from gf_dashboard.infrastructure.migrations.runner import load_migrations
from gf_dashboard.infrastructure.persistence import (
    Migration,
    MigrationFailedError,
    MigrationRunner,
    SqliteDatabase,
)
from gf_dashboard.infrastructure.sqlite_repositories import SqliteUnitOfWork
from gf_dashboard.infrastructure.tower_configuration import SqliteTowerConfigurationStore
from gf_dashboard.presentation.qt_bridge.app_bridge import AppBridge


def setup_workspace(
    tmp_path: Path, version: int = 10
) -> tuple[SqliteDatabase, WorkspaceId, EntityId]:
    database = SqliteDatabase(tmp_path / "tower.sqlite3", test_temporary_root=tmp_path)
    MigrationRunner(database, load_migrations()[:version], app_version="test").migrate()
    service = WorkspaceService(SqliteUnitOfWork(database), UUIDGenerator(), SystemClock())
    workspace = service.create_workspace("Teste")
    account = service.create_account(workspace.id, "Conta", "Servidor")
    character = service.create_character(workspace.id, account.id, "Personagem", "Classe", 91, 0)
    return database, workspace.id, character.id


def settings(workspace: WorkspaceId, character: EntityId) -> SaveTowerConfiguration:
    return SaveTowerConfiguration(
        workspace,
        uuid4(),
        "Guilda",
        30_000,
        (character,),
        (TowerItemSetting("Astúcia", 200_000), TowerItemSetting("Sem preço", None)),
    )


def counts(database: SqliteDatabase) -> tuple[int, int, int, int]:
    connection = database.connect(read_only=True)
    try:
        return tuple(
            connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "farm_sessions",
                "farm_session_items",
                "transactions",
                "market_price_quotes",
            )
        )
    finally:
        connection.close()


@pytest.mark.integration
def test_configuration_persists_without_farming_facts_and_replays_original_response(
    tmp_path: Path,
) -> None:
    database, workspace, character = setup_workspace(tmp_path)
    service = TowerConfigurationService(SqliteTowerConfigurationStore(database))
    initial = settings(workspace, character)

    saved = service.save(initial)
    replayed = service.save(initial)

    assert replayed == saved
    assert counts(database) == (0, 0, 0, 1)
    assert saved.entry_cost == Gold(30_000)
    assert saved.participant_ids == (character,)
    assert saved.items[1].estimated_unit_value is None
    changed = replace(
        initial,
        idempotency_key=uuid4(),
        guild_name="Outra",
        entry_cost_gold=0,
        items=(TowerItemSetting("Astúcia", 210_000),),
    )
    service.save(changed)
    assert counts(database) == (0, 0, 0, 2)
    assert service.save(initial) == saved
    assert (
        TowerConfigurationService(SqliteTowerConfigurationStore(database)).get(workspace).guild_name
        == "Outra"
    )
    with pytest.raises(ConflictError):
        service.save(replace(initial, guild_name="Chave reutilizada"))
    assert counts(database) == (0, 0, 0, 2)


@pytest.mark.integration
def test_legacy_catalog_prefills_and_empty_save_does_not_reimport_history(tmp_path: Path) -> None:
    database, workspace, character = setup_workspace(tmp_path)
    tower = TowerSessionService(SqliteUnitOfWork(database), UUIDGenerator(), SystemClock())
    first = tower.register_completed(
        workspace,
        date(2026, 10, 20),
        (character,),
        "Antiga",
        (TowerDropInput("Astúcia", 2, Gold(190_000)),),
    )
    tower.register_completed(
        workspace,
        date(2026, 10, 21),
        (),
        "Atual",
        (TowerDropInput("Astúcia", 1, Gold(200_000)), TowerDropInput("Sem preço")),
    )
    service = TowerConfigurationService(SqliteTowerConfigurationStore(database))

    legacy = service.get(workspace)

    assert legacy.guild_name == "Atual"
    assert legacy.participant_ids == ()
    assert legacy.items[0].estimated_unit_value == Gold(200_000)
    assert legacy.items[1].estimated_unit_value is None
    assert counts(database)[:3] == (2, 3, 0)
    service.save(SaveTowerConfiguration(workspace, uuid4(), "", 25_000, (), ()))
    assert service.get(workspace).items == ()
    assert service.get(workspace).guild_name == ""
    with SqliteUnitOfWork(database) as uow:
        original = uow.tower_sessions.get(workspace, first.session.id)
        assert original is not None
        assert original[1].guild_name_snapshot == "Antiga"
        assert uow.tower_sessions.list_drops(workspace, first.session.id)[
            0
        ].estimated_unit_value == Gold(190_000)


@pytest.mark.integration
def test_configuration_changes_preserve_names_prices_costs_and_session_replay(
    tmp_path: Path,
) -> None:
    database, workspace, character = setup_workspace(tmp_path)
    service = TowerConfigurationService(SqliteTowerConfigurationStore(database))
    command = settings(workspace, character)
    service.save(command)
    tower = TowerSessionService(SqliteUnitOfWork(database), UUIDGenerator(), SystemClock())
    key = uuid4()
    original = tower.register_completed(
        workspace,
        date(2026, 10, 21),
        (character,),
        "Guilda",
        (TowerDropInput("Astúcia", 2, Gold(200_000)),),
        key,
    )
    service.save(
        replace(
            command,
            idempotency_key=uuid4(),
            entry_cost_gold=40_000,
            items=(TowerItemSetting("Novo nome", 250_000),),
        )
    )

    replay = tower.register_completed(
        workspace,
        date(2026, 10, 21),
        (character,),
        "Guilda",
        (TowerDropInput("Astúcia", 2, Gold(200_000)),),
        key,
    )
    newer = tower.register_completed(workspace, date(2026, 10, 21), idempotency_key=uuid4())

    assert replay.session.id == original.session.id
    assert replay.entry_cost == original.entry_cost == Gold(30_000)
    assert newer.entry_cost == Gold(40_000)
    assert counts(database)[:3] == (2, 1, 0)
    connection = database.connect(read_only=True)
    try:
        snapshot = connection.execute(
            "SELECT i.name, fsi.estimated_unit_value_at_drop FROM farm_session_items fsi "
            "JOIN items i ON i.id = fsi.item_id WHERE fsi.farm_session_id = ?",
            (str(original.session.id),),
        ).fetchone()
        assert tuple(snapshot) == ("Astúcia", 200_000)
    finally:
        connection.close()
    with pytest.raises(ConflictError):
        tower.register_completed(workspace, date(2026, 10, 21), idempotency_key=key)


@pytest.mark.integration
def test_workspace_isolation_and_invalid_character_do_not_partially_save(tmp_path: Path) -> None:
    database, workspace, character = setup_workspace(tmp_path)
    other = WorkspaceService(
        SqliteUnitOfWork(database), UUIDGenerator(), SystemClock()
    ).create_workspace("Outro")
    service = TowerConfigurationService(SqliteTowerConfigurationStore(database))
    first = service.save(settings(workspace, character))

    with pytest.raises(NotFoundError):
        service.save(replace(settings(other.id, character), guild_name="Falha"))

    assert service.get(workspace) == first
    assert service.get(other.id).items == ()
    assert service.get(other.id).entry_cost == Gold(25_000)
    assert counts(database) == (0, 0, 0, 1)


@pytest.mark.integration
def test_upgrade_v9_preserves_tower_rows_and_backup_and_allows_new_cost(tmp_path: Path) -> None:
    database, workspace, character = setup_workspace(tmp_path, 9)
    connection = database.connect()
    now = "2026-10-20T12:00:00+00:00"
    session_id = str(uuid4())
    try:
        connection.execute(
            "INSERT INTO farm_sessions "
            "(id, workspace_id, session_type, activity_date, status, created_at, updated_at) "
            "VALUES (?, ?, 'tower', '2026-10-20', 'completed', ?, ?)",
            (session_id, str(workspace), now, now),
        )
        connection.execute(
            "INSERT INTO tower_session_details "
            "(farm_session_id, workspace_id, guild_name_snapshot, opened_at, "
            "entry_cost_gold_snapshot, completed, completed_at, created_at, updated_at) "
            "VALUES (?, ?, 'Guilda antiga', ?, 25000, 1, ?, ?, ?)",
            (session_id, str(workspace), now, now, now, now),
        )
        participant_id, item_id, drop_id = (str(uuid4()) for _ in range(3))
        connection.execute(
            "INSERT INTO farm_session_participants "
            "(id, workspace_id, farm_session_id, character_id, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (participant_id, str(workspace), session_id, str(character), now, now),
        )
        connection.execute(
            "INSERT INTO items (id, workspace_id, name, category, created_at, updated_at) "
            "VALUES (?, ?, 'Astúcia antiga', 'tower_drop', ?, ?)",
            (item_id, str(workspace), now, now),
        )
        connection.execute(
            "INSERT INTO farm_session_items (id, workspace_id, farm_session_id, item_id, "
            "quantity, estimated_unit_value_at_drop, obtained_at, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, 2, 190000, ?, ?, ?)",
            (drop_id, str(workspace), session_id, item_id, now, now, now),
        )
        connection.commit()
        before = tuple(connection.execute("SELECT * FROM tower_session_details").fetchone())
        participants_before = connection.execute(
            "SELECT * FROM farm_session_participants"
        ).fetchall()
        drops_before = connection.execute("SELECT * FROM farm_session_items").fetchall()
    finally:
        connection.close()
    runner = MigrationRunner(database, load_migrations(), app_version="test")

    assert runner.migrate() == 10
    assert runner.migrate() == 10

    backup = next((tmp_path / "backups").glob("*.sqlite3"))
    backup_connection = sqlite3.connect(backup)
    try:
        assert (
            backup_connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
            == 9
        )
        assert backup_connection.execute("SELECT * FROM tower_session_details").fetchone() == before
    finally:
        backup_connection.close()
    connection = database.connect()
    try:
        assert tuple(connection.execute("SELECT * FROM tower_session_details").fetchone()) == before
        assert (
            connection.execute("SELECT * FROM farm_session_participants").fetchall()
            == participants_before
        )
        assert connection.execute("SELECT * FROM farm_session_items").fetchall() == drops_before
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE tower_session_details SET entry_cost_gold_snapshot = -1")
    finally:
        connection.close()
    service = TowerConfigurationService(SqliteTowerConfigurationStore(database))
    imported = service.get(workspace)
    assert imported.guild_name == "Guilda antiga"
    assert imported.participant_ids == (character,)
    assert imported.items[0].item_name == "Astúcia antiga"
    assert imported.items[0].estimated_unit_value == Gold(190_000)
    service.save(settings(workspace, character))
    result = TowerSessionService(
        SqliteUnitOfWork(database), UUIDGenerator(), SystemClock()
    ).register_completed(workspace, date(2026, 10, 21))
    assert result.entry_cost == Gold(30_000)


@pytest.mark.integration
def test_failed_tower_upgrade_rolls_back_and_verified_backup_can_restore(tmp_path: Path) -> None:
    database, _, _ = setup_workspace(tmp_path, 9)
    original = load_migrations()[-1]
    broken = Migration(original.version, original.name, original.sql + "\nINVALID SQL;")
    runner = MigrationRunner(database, (*load_migrations()[:-1], broken), app_version="test")

    with pytest.raises(MigrationFailedError) as failure:
        runner.migrate()

    assert runner.current_version() == 9
    connection = database.connect(read_only=True)
    try:
        assert (
            connection.execute(
                "SELECT name FROM sqlite_master WHERE name = 'tower_configurations'"
            ).fetchone()
            is None
        )
    finally:
        connection.close()
    assert failure.value.backup_path is not None
    recovery = runner.restore_verified_backup(failure.value.backup_path)
    assert recovery.exists()
    assert MigrationRunner(database, load_migrations(), app_version="test").migrate() == 10


@pytest.mark.integration
def test_tower_bridge_contract_validates_and_preserves_optional_registration_key(
    tmp_path: Path,
) -> None:
    database, _, character = setup_workspace(tmp_path)
    bridge = AppBridge(database)

    def invoke(method: str, payload: dict[str, object]) -> dict[str, object]:
        return json.loads(
            bridge.invoke(
                json.dumps(
                    {
                        "version": 1,
                        "requestId": "tower-contract",
                        "method": method,
                        "payload": payload,
                    }
                )
            )
        )

    defaults = invoke("tower.getConfiguration", {})
    assert defaults["data"] == {
        "guildName": "",
        "entryCostGold": 25_000,
        "participantIds": [],
        "items": [],
    }
    payload = {
        "guildName": "Guilda",
        "entryCostGold": 0,
        "participantIds": [str(character)],
        "items": [{"itemName": "Astúcia", "estimatedUnitValue": 0}],
        "idempotencyKey": str(uuid4()),
    }
    saved = invoke("tower.saveConfiguration", payload)
    assert saved["ok"] is True
    assert invoke("tower.saveConfiguration", payload)["data"] == saved["data"]
    data = saved["data"]
    assert data["items"][0]["itemName"] == "Astúcia"
    assert data["items"][0]["estimatedUnitValue"] == 0
    invalid = invoke("tower.saveConfiguration", {**payload, "entryCostGold": 1.5})
    assert invalid["ok"] is False
    registration = {"activityDate": "2026-10-21", "drops": [], "idempotencyKey": str(uuid4())}
    completed = invoke("tower.registerCompleted", registration)
    assert completed["ok"] is True
    assert completed["data"]["entryCostGold"] == 0
    assert invoke("tower.registerCompleted", registration)["data"] == completed["data"]
    assert counts(database)[:3] == (1, 0, 0)
