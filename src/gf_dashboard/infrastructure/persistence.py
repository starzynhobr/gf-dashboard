from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from PySide6.QtCore import QStandardPaths

DATABASE_FILENAME: Final = "gf-dashboard.sqlite3"
SQLITE_BUSY_TIMEOUT_MS: Final = 5_000


class PersistenceError(Exception):
    """Base error for local persistence failures safe to show as a typed application error."""


class UnsafeDatabasePathError(PersistenceError):
    pass


class DatabaseIntegrityError(PersistenceError):
    pass


class MigrationChecksumError(PersistenceError):
    pass


class SchemaTooNewError(PersistenceError):
    pass


class MigrationFailedError(PersistenceError):
    def __init__(self, message: str, backup_path: Path | None) -> None:
        super().__init__(message)
        self.backup_path = backup_path


class BackupVerificationError(PersistenceError):
    pass


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    sql: str

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.sql.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class BackupInfo:
    database_path: Path
    backup_path: Path
    metadata_path: Path
    schema_version: int
    checksum: str
    created_at: datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def resolve_app_data_directory() -> Path:
    location = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    if not location:
        raise PersistenceError("Não foi possível localizar o diretório de dados do aplicativo")
    return Path(location)


def resolve_personal_database_path(app_data_directory: Path | None = None) -> Path:
    root = app_data_directory if app_data_directory is not None else resolve_app_data_directory()
    return root.expanduser().resolve() / "data" / DATABASE_FILENAME


def migrate_personal_database(*, app_version: str) -> Path:
    """Open the stable local database and bring it to the supported schema version."""
    from gf_dashboard.infrastructure.migrations.runner import load_migrations

    database = SqliteDatabase(resolve_personal_database_path())
    MigrationRunner(database, load_migrations(), app_version=app_version).migrate()
    return database.path


def require_temporary_database_path(database_path: Path, temporary_root: Path) -> Path:
    resolved_path = database_path.expanduser().resolve()
    resolved_root = temporary_root.expanduser().resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise UnsafeDatabasePathError(
            "Testes SQLite só podem usar bancos dentro do diretório temporário do teste"
        ) from exc
    return resolved_path


class SqliteDatabase:
    def __init__(self, database_path: Path, *, test_temporary_root: Path | None = None) -> None:
        self.path = (
            require_temporary_database_path(database_path, test_temporary_root)
            if test_temporary_root is not None
            else database_path.expanduser().resolve()
        )

    def connect(self, *, read_only: bool = False) -> sqlite3.Connection:
        if read_only:
            if not self.path.is_file():
                raise PersistenceError(
                    "Banco de dados não encontrado para abertura somente leitura"
                )
            connection = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
        if not read_only:
            connection.execute("PRAGMA journal_mode = WAL")
        return connection


class MigrationRunner:
    def __init__(
        self,
        database: SqliteDatabase,
        migrations: tuple[Migration, ...],
        *,
        app_version: str,
    ) -> None:
        self._database = database
        self._migrations = tuple(sorted(migrations, key=lambda migration: migration.version))
        self._app_version = app_version
        self._validate_migration_catalog()

    @property
    def latest_version(self) -> int:
        return self._migrations[-1].version if self._migrations else 0

    def migrate(self) -> int:
        existed_before_open = self._database.path.exists()
        connection = self._database.connect()
        backup: BackupInfo | None = None
        try:
            self._ensure_migration_table(connection)
            self._assert_database_integrity(connection)
            applied = self._load_applied_migrations(connection)
            self._assert_compatible_schema(applied)
            pending = tuple(
                migration for migration in self._migrations if migration.version not in applied
            )
            if not pending:
                return self.latest_version
            if existed_before_open and self._database.path.stat().st_size > 0:
                backup = self.create_verified_backup(connection)
            for migration in pending:
                self._apply_migration(connection, migration)
            self._assert_database_integrity(connection)
            return self.latest_version
        except PersistenceError:
            raise
        except sqlite3.Error as exc:
            backup_path = backup.backup_path if backup is not None else None
            raise MigrationFailedError(
                "Falha ao aplicar migration; banco original foi preservado",
                backup_path,
            ) from exc
        finally:
            connection.close()

    def current_version(self) -> int:
        connection = self._database.connect(read_only=True)
        try:
            row = connection.execute(
                "SELECT MAX(version) AS version FROM schema_migrations"
            ).fetchone()
            return int(row["version"] or 0)
        except sqlite3.Error as exc:
            raise PersistenceError("Não foi possível ler a versão do schema") from exc
        finally:
            connection.close()

    def create_verified_backup(
        self, source_connection: sqlite3.Connection | None = None
    ) -> BackupInfo:
        owns_connection = source_connection is None
        connection = source_connection or self._database.connect()
        try:
            self._assert_database_integrity(connection)
            timestamp = utc_now()
            version = self._schema_version(connection)
            backup_directory = self._database.path.parent / "backups"
            backup_directory.mkdir(parents=True, exist_ok=True)
            suffix = timestamp.strftime("%Y%m%dT%H%M%S%fZ")
            backup_path = (
                backup_directory / f"{self._database.path.stem}.v{version}.{suffix}.sqlite3"
            )
            destination = sqlite3.connect(backup_path)
            try:
                connection.backup(destination)
            finally:
                destination.close()
            checksum = _file_checksum(backup_path)
            self._verify_backup_file(backup_path)
            metadata_path = backup_path.with_suffix(".json")
            metadata_path.write_text(
                json.dumps(
                    {
                        "app_version": self._app_version,
                        "backup_file": backup_path.name,
                        "checksum_sha256": checksum,
                        "created_at": timestamp.isoformat(),
                        "schema_version": version,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            return BackupInfo(
                database_path=self._database.path,
                backup_path=backup_path,
                metadata_path=metadata_path,
                schema_version=version,
                checksum=checksum,
                created_at=timestamp,
            )
        finally:
            if owns_connection:
                connection.close()

    def restore_verified_backup(self, backup_path: Path) -> Path:
        backup_path = backup_path.expanduser().resolve()
        self._verify_backup_file(backup_path)
        database_path = self._database.path
        if database_path.exists():
            recovery_path = database_path.with_name(
                f"{database_path.stem}.before-restore.{utc_now().strftime('%Y%m%dT%H%M%S%fZ')}.sqlite3"
            )
            shutil.copy2(database_path, recovery_path)
            self._verify_backup_file(recovery_path)
        else:
            recovery_path = database_path.with_name(
                f"{database_path.stem}.before-restore.empty.sqlite3"
            )
        restore_temp_path = database_path.with_suffix(".restore.tmp")
        shutil.copy2(backup_path, restore_temp_path)
        self._verify_backup_file(restore_temp_path)
        restore_temp_path.replace(database_path)
        return recovery_path

    def _validate_migration_catalog(self) -> None:
        versions = [migration.version for migration in self._migrations]
        if any(version <= 0 for version in versions) or len(versions) != len(set(versions)):
            raise PersistenceError("Catálogo de migrations contém versões inválidas ou duplicadas")

    @staticmethod
    def _ensure_migration_table(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL,
                app_version TEXT NOT NULL
            )
            """
        )
        connection.commit()

    def _load_applied_migrations(self, connection: sqlite3.Connection) -> dict[int, str]:
        rows = connection.execute(
            "SELECT version, checksum FROM schema_migrations ORDER BY version"
        ).fetchall()
        applied = {int(row["version"]): str(row["checksum"]) for row in rows}
        catalog_by_version = {migration.version: migration for migration in self._migrations}
        for version, checksum in applied.items():
            migration = catalog_by_version.get(version)
            if migration is not None and migration.checksum != checksum:
                raise MigrationChecksumError(f"Checksum divergente na migration {version:03d}")
        return applied

    def _assert_compatible_schema(self, applied: dict[int, str]) -> None:
        if applied and max(applied) > self.latest_version:
            raise SchemaTooNewError("O banco foi criado por uma versão mais nova do aplicativo")

    def _apply_migration(self, connection: sqlite3.Connection, migration: Migration) -> None:
        try:
            connection.execute("BEGIN IMMEDIATE")
            _execute_sql_script(connection, migration.sql)
            connection.execute(
                "INSERT INTO schema_migrations "
                "(version, name, checksum, applied_at, app_version) VALUES (?, ?, ?, ?, ?)",
                (
                    migration.version,
                    migration.name,
                    migration.checksum,
                    utc_now().isoformat(),
                    self._app_version,
                ),
            )
            connection.commit()
        except sqlite3.Error:
            connection.rollback()
            raise

    @staticmethod
    def _assert_database_integrity(connection: sqlite3.Connection) -> None:
        quick_check = connection.execute("PRAGMA quick_check").fetchone()
        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if quick_check is None or quick_check[0] != "ok" or foreign_key_errors:
            raise DatabaseIntegrityError("A verificação de integridade do banco falhou")

    @staticmethod
    def _schema_version(connection: sqlite3.Connection) -> int:
        row = connection.execute("SELECT MAX(version) AS version FROM schema_migrations").fetchone()
        return int(row["version"] or 0)

    @staticmethod
    def _verify_backup_file(backup_path: Path) -> None:
        if not backup_path.is_file() or backup_path.stat().st_size == 0:
            raise BackupVerificationError("Backup não foi criado")
        connection = sqlite3.connect(backup_path.as_uri() + "?mode=ro", uri=True)
        try:
            result = connection.execute("PRAGMA quick_check").fetchone()
            if result is None or result[0] != "ok":
                raise BackupVerificationError("Backup falhou na verificação de integridade")
        finally:
            connection.close()


def _execute_sql_script(connection: sqlite3.Connection, sql: str) -> None:
    statement = ""
    for line in sql.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            completed_statement = statement.strip()
            if completed_statement:
                connection.execute(completed_statement)
            statement = ""
    if statement.strip():
        connection.execute(statement)


def _file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
