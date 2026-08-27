from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from gf_dashboard.infrastructure.migrations.runner import load_migrations
from gf_dashboard.infrastructure.persistence import (
    Migration,
    MigrationChecksumError,
    MigrationFailedError,
    MigrationRunner,
    SchemaTooNewError,
    SqliteDatabase,
    UnsafeDatabasePathError,
    resolve_personal_database_path,
)


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "data" / "farm.sqlite3"


@pytest.fixture
def runner(database_path: Path, tmp_path: Path) -> MigrationRunner:
    database = SqliteDatabase(database_path, test_temporary_root=tmp_path)
    return MigrationRunner(database, load_migrations(), app_version="0.1.0-test")


@pytest.mark.integration
def test_migrate_clean_database_creates_v1_schema_and_indexes(
    runner: MigrationRunner, database_path: Path, tmp_path: Path
) -> None:
    assert runner.migrate() == 3
    assert runner.current_version() == 3

    connection = SqliteDatabase(database_path, test_temporary_root=tmp_path).connect()
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        indexes = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }
        assert {
            "workspaces",
            "activity_completions",
            "tower_session_details",
            "schema_migrations",
        } <= tables
        assert "daily_activity_entries_date_idx" in indexes
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO accounts "
                "(id, workspace_id, name, server_name, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "account-1",
                    "missing-workspace",
                    "Conta",
                    "Valhalla",
                    "2026-08-26T00:00:00+00:00",
                    "2026-08-26T00:00:00+00:00",
                ),
            )
    finally:
        connection.close()


@pytest.mark.integration
def test_migrate_again_is_idempotent_and_does_not_create_backup_when_nothing_is_pending(
    runner: MigrationRunner, database_path: Path
) -> None:
    runner.migrate()

    assert runner.migrate() == 3
    assert not (database_path.parent / "backups").exists()


@pytest.mark.integration
def test_checksum_divergence_is_rejected_before_new_writes(
    runner: MigrationRunner, database_path: Path, tmp_path: Path
) -> None:
    runner.migrate()
    migrations = load_migrations()
    altered_first = Migration(version=1, name="initial", sql=migrations[0].sql + "\n-- altered\n")
    altered_runner = MigrationRunner(
        SqliteDatabase(database_path, test_temporary_root=tmp_path),
        (altered_first, *migrations[1:]),
        app_version="0.1.0-test",
    )

    with pytest.raises(MigrationChecksumError, match="001"):
        altered_runner.migrate()


@pytest.mark.integration
def test_newer_schema_is_rejected_without_downgrade(
    runner: MigrationRunner, database_path: Path
) -> None:
    runner.migrate()
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            "INSERT INTO schema_migrations (version, name, checksum, applied_at, app_version) "
            "VALUES (99, 'future', 'future', '2026-08-26T00:00:00+00:00', 'future')"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(SchemaTooNewError):
        runner.migrate()


@pytest.mark.integration
def test_failed_migration_rolls_back_and_keeps_verified_backup(
    runner: MigrationRunner, database_path: Path, tmp_path: Path
) -> None:
    runner.migrate()
    failed_runner = MigrationRunner(
        SqliteDatabase(database_path, test_temporary_root=tmp_path),
        (*load_migrations(), Migration(version=4, name="broken", sql="CREATE TABLE broken (id;")),
        app_version="0.1.0-test",
    )

    with pytest.raises(MigrationFailedError) as error:
        failed_runner.migrate()

    assert error.value.backup_path is not None
    assert error.value.backup_path.is_file()
    assert failed_runner.current_version() == 3
    connection = sqlite3.connect(database_path)
    try:
        assert (
            connection.execute("SELECT name FROM sqlite_master WHERE name = 'broken'").fetchone()
            is None
        )
    finally:
        connection.close()


@pytest.mark.integration
def test_restore_preserves_current_database_as_recovery_copy(
    runner: MigrationRunner, database_path: Path
) -> None:
    runner.migrate()
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            "INSERT INTO workspaces (id, name, created_at, updated_at) "
            "VALUES ('workspace-a', 'A', '2026-08-26T00:00:00+00:00', '2026-08-26T00:00:00+00:00')"
        )
        connection.commit()
    finally:
        connection.close()
    backup = runner.create_verified_backup()
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            "INSERT INTO workspaces (id, name, created_at, updated_at) "
            "VALUES ('workspace-b', 'B', '2026-08-26T00:00:00+00:00', '2026-08-26T00:00:00+00:00')"
        )
        connection.commit()
    finally:
        connection.close()

    recovery_path = runner.restore_verified_backup(backup.backup_path)

    assert recovery_path.is_file()
    restored = sqlite3.connect(database_path)
    recovery = sqlite3.connect(recovery_path)
    try:
        assert restored.execute("SELECT COUNT(*) FROM workspaces").fetchone()[0] == 1
        assert recovery.execute("SELECT COUNT(*) FROM workspaces").fetchone()[0] == 2
    finally:
        restored.close()
        recovery.close()


def test_test_database_guard_rejects_personal_location(tmp_path: Path) -> None:
    personal_database = resolve_personal_database_path(tmp_path.parent / "personal")

    with pytest.raises(UnsafeDatabasePathError):
        SqliteDatabase(personal_database, test_temporary_root=tmp_path)
