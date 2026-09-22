from __future__ import annotations

import json
import sqlite3
from datetime import UTC, date, datetime, timedelta
from typing import cast
from uuid import uuid4

from gf_dashboard.application.work_routines import MIN_RECORDED_ROUTINE_SECONDS
from gf_dashboard.infrastructure.persistence import SqliteDatabase


class SqliteDailyOperations:
    """Persistence adapter for small operational facts outside dungeon rewards."""

    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database

    def set_character_daily_mission(
        self, workspace_id: str, character_id: str, activity_date: date, completed: bool
    ) -> bool:
        now = datetime.now(UTC).isoformat()
        connection = self._database.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            character = connection.execute(
                "SELECT 1 FROM characters WHERE id = ? AND workspace_id = ? AND deleted_at IS NULL",
                (character_id, workspace_id),
            ).fetchone()
            if character is None:
                raise ValueError("Personagem não encontrado no workspace local")
            connection.execute(
                """
                INSERT INTO character_daily_missions
                    (id, workspace_id, character_id, activity_date, completed_at,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(workspace_id, character_id, activity_date) DO UPDATE SET
                    completed_at = excluded.completed_at,
                    updated_at = excluded.updated_at,
                    deleted_at = NULL
                """,
                (
                    str(uuid4()),
                    workspace_id,
                    character_id,
                    activity_date.isoformat(),
                    now if completed else None,
                    now,
                    now,
                ),
            )
            connection.commit()
            return completed
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def set_monthly_target(self, workspace_id: str, target_month: str, target_gold: int) -> int:
        if len(target_month) != 7 or target_gold <= 0:
            raise ValueError("Meta mensal inválida")
        now = datetime.now(UTC).isoformat()
        connection = self._database.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO monthly_gold_targets
                    (id, workspace_id, target_month, target_gold, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(workspace_id, target_month) DO UPDATE SET
                    target_gold = excluded.target_gold,
                    updated_at = excluded.updated_at,
                    deleted_at = NULL
                """,
                (str(uuid4()), workspace_id, target_month, target_gold, now, now),
            )
            connection.commit()
            return target_gold
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def save_character_vip(
        self,
        workspace_id: str,
        character_id: str,
        paid_gold: int,
        remaining_days: int,
        remaining_hours: int,
        *,
        current_time: datetime | None = None,
    ) -> datetime:
        if paid_gold <= 0:
            raise ValueError("O valor do VIP deve ser maior que zero")
        if remaining_days < 0 or remaining_hours < 0 or remaining_hours > 23:
            raise ValueError("O tempo restante do VIP é inválido")
        remaining = timedelta(days=remaining_days, hours=remaining_hours)
        if remaining <= timedelta(0) or remaining > timedelta(days=30):
            raise ValueError("O VIP deve ter entre 1 hora e 30 dias restantes")
        instant = current_time or datetime.now(UTC)
        if instant.tzinfo is None:
            raise ValueError("O horário atual deve incluir fuso horário")
        instant = instant.astimezone(UTC)
        now = instant.isoformat()
        expires_at = instant + remaining
        activated_at = expires_at - timedelta(days=30)
        activated_on = activated_at.date().isoformat()
        expires_on = expires_at.date().isoformat()
        connection = self._database.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            active = connection.execute(
                """SELECT id FROM character_vip_subscriptions
                WHERE workspace_id = ? AND character_id = ?
                  AND COALESCE(expires_at, expires_on || 'T00:00:00+00:00') > ?
                  AND deleted_at IS NULL
                ORDER BY COALESCE(expires_at, expires_on) DESC LIMIT 1""",
                (workspace_id, character_id, now),
            ).fetchone()
            if active is not None:
                connection.execute(
                    """UPDATE character_vip_subscriptions
                    SET activated_on = ?, expires_on = ?, activated_at = ?, expires_at = ?,
                        updated_at = ? WHERE id = ?""",
                    (
                        activated_on,
                        expires_on,
                        activated_at.isoformat(),
                        expires_at.isoformat(),
                        now,
                        active["id"],
                    ),
                )
            else:
                connection.execute(
                    """INSERT INTO character_vip_subscriptions
                    (id, workspace_id, character_id, activated_on, expires_on, paid_gold,
                     created_at, updated_at, activated_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(uuid4()),
                        workspace_id,
                        character_id,
                        activated_on,
                        expires_on,
                        paid_gold,
                        now,
                        now,
                        activated_at.isoformat(),
                        expires_at.isoformat(),
                    ),
                )
                connection.execute(
                    """INSERT INTO transactions
                    (id, workspace_id, type, category, amount_gold, amount_minor, currency,
                     character_id, occurred_at, description, created_at, updated_at)
                    VALUES (?, ?, 'expense', 'vip', ?, 0, NULL, ?, ?, 'VIP de 30 dias', ?, ?)""",
                    (
                        str(uuid4()),
                        workspace_id,
                        paid_gold,
                        character_id,
                        activated_at.isoformat(),
                        now,
                        now,
                    ),
                )
            connection.commit()
            return expires_at
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def record_expense(
        self,
        workspace_id: str,
        category: str,
        amount_gold: int,
        occurred_at: datetime,
        description: str | None = None,
    ) -> str:
        allowed_categories = {"upgrade", "consumable", "service", "other"}
        if category not in allowed_categories:
            raise ValueError("Categoria de despesa inválida")
        if amount_gold <= 0:
            raise ValueError("O valor da despesa deve ser maior que zero")
        if occurred_at.tzinfo is None:
            raise ValueError("A data da despesa deve incluir fuso horário")
        normalized_description = (description or "").strip() or None
        now = datetime.now(UTC).isoformat()
        transaction_id = str(uuid4())
        connection = self._database.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """INSERT INTO transactions
                (id, workspace_id, type, category, amount_gold, amount_minor, currency,
                 occurred_at, description, created_at, updated_at)
                VALUES (?, ?, 'expense', ?, ?, 0, NULL, ?, ?, ?, ?)""",
                (
                    transaction_id,
                    workspace_id,
                    category,
                    amount_gold,
                    occurred_at.astimezone(UTC).isoformat(),
                    normalized_description,
                    now,
                    now,
                ),
            )
            connection.commit()
            return transaction_id
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def list_manual_expenses(self, workspace_id: str, limit: int = 100) -> list[dict[str, object]]:
        connection = self._database.connect()
        try:
            rows = connection.execute(
                """SELECT id, category, amount_gold, occurred_at, description, created_at
                FROM transactions
                WHERE workspace_id = ? AND type = 'expense'
                  AND category IN ('upgrade', 'consumable', 'service', 'other')
                  AND deleted_at IS NULL
                ORDER BY occurred_at DESC, created_at DESC
                LIMIT ?""",
                (workspace_id, limit),
            ).fetchall()
            return [
                {
                    "id": str(row["id"]),
                    "category": str(row["category"]),
                    "amount_gold": int(row["amount_gold"]),
                    "occurred_at": str(row["occurred_at"]),
                    "description": row["description"],
                    "created_at": str(row["created_at"]),
                }
                for row in rows
            ]
        finally:
            connection.close()

    def update_manual_expense(
        self,
        workspace_id: str,
        transaction_id: str,
        category: str,
        amount_gold: int,
        occurred_at: datetime,
        description: str | None = None,
    ) -> str:
        self._validate_manual_expense(category, amount_gold, occurred_at)
        normalized_description = (description or "").strip() or None
        now = datetime.now(UTC).isoformat()
        replacement_id = str(uuid4())
        connection = self._database.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            original = self._manual_expense_row(connection, workspace_id, transaction_id)
            before = self._expense_audit_payload(original)
            connection.execute(
                "UPDATE transactions SET deleted_at = ?, updated_at = ? WHERE id = ?",
                (now, now, transaction_id),
            )
            connection.execute(
                """INSERT INTO transactions
                (id, workspace_id, type, category, amount_gold, amount_minor, currency,
                 occurred_at, description, created_at, updated_at)
                VALUES (?, ?, 'expense', ?, ?, 0, NULL, ?, ?, ?, ?)""",
                (
                    replacement_id,
                    workspace_id,
                    category,
                    amount_gold,
                    occurred_at.astimezone(UTC).isoformat(),
                    normalized_description,
                    now,
                    now,
                ),
            )
            self._write_expense_audit(
                connection,
                workspace_id,
                transaction_id,
                "corrected",
                before,
                {
                    "replacementTransactionId": replacement_id,
                    "category": category,
                    "amountGold": amount_gold,
                    "occurredAt": occurred_at.astimezone(UTC).isoformat(),
                    "description": normalized_description,
                },
                now,
            )
            connection.commit()
            return replacement_id
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def void_manual_expense(self, workspace_id: str, transaction_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        connection = self._database.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            original = self._manual_expense_row(connection, workspace_id, transaction_id)
            connection.execute(
                "UPDATE transactions SET deleted_at = ?, updated_at = ? WHERE id = ?",
                (now, now, transaction_id),
            )
            self._write_expense_audit(
                connection,
                workspace_id,
                transaction_id,
                "voided",
                self._expense_audit_payload(original),
                {"voided": True},
                now,
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _validate_manual_expense(category: str, amount_gold: int, occurred_at: datetime) -> None:
        if category not in {"upgrade", "consumable", "service", "other"}:
            raise ValueError("Categoria de despesa inválida")
        if amount_gold <= 0:
            raise ValueError("O valor da despesa deve ser maior que zero")
        if occurred_at.tzinfo is None:
            raise ValueError("A data da despesa deve incluir fuso horário")

    @staticmethod
    def _expense_audit_payload(row: sqlite3.Row) -> dict[str, object]:
        return {
            "id": str(row["id"]),
            "category": str(row["category"]),
            "amountGold": int(row["amount_gold"]),
            "occurredAt": str(row["occurred_at"]),
            "description": row["description"],
        }

    @staticmethod
    def _manual_expense_row(
        connection: sqlite3.Connection, workspace_id: str, transaction_id: str
    ) -> sqlite3.Row:
        row = connection.execute(
            """SELECT id, category, amount_gold, occurred_at, description FROM transactions
            WHERE id = ? AND workspace_id = ? AND type = 'expense'
              AND category IN ('upgrade', 'consumable', 'service', 'other')
              AND deleted_at IS NULL""",
            (transaction_id, workspace_id),
        ).fetchone()
        if row is None:
            raise ValueError("Despesa manual não encontrada ou já estornada")
        return cast(sqlite3.Row, row)

    @staticmethod
    def _write_expense_audit(
        connection: sqlite3.Connection,
        workspace_id: str,
        transaction_id: str,
        action: str,
        before: dict[str, object],
        after: dict[str, object],
        now: str,
    ) -> None:
        connection.execute(
            """INSERT INTO audit_log
            (id, workspace_id, entity_type, entity_id, action, before_json, after_json,
             occurred_at, created_at)
            VALUES (?, ?, 'transaction', ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid4()),
                workspace_id,
                transaction_id,
                action,
                json.dumps(before, ensure_ascii=False, sort_keys=True),
                json.dumps(after, ensure_ascii=False, sort_keys=True),
                now,
                now,
            ),
        )

    def get_work_routine(self, workspace_id: str) -> dict[str, object] | None:
        connection = self._database.connect()
        try:
            row = connection.execute(
                """SELECT id, status, started_at, paused_at, accumulated_seconds
                FROM work_routine_sessions
                WHERE workspace_id = ? AND status IN ('running', 'paused') AND deleted_at IS NULL
                ORDER BY created_at DESC LIMIT 1""",
                (workspace_id,),
            ).fetchone()
            return self._routine_payload(row) if row is not None else None
        finally:
            connection.close()

    def start_work_routine(self, workspace_id: str) -> dict[str, object]:
        now = datetime.now(UTC)
        connection = self._database.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            current = connection.execute(
                """SELECT id, status, started_at, paused_at, accumulated_seconds
                FROM work_routine_sessions WHERE workspace_id = ?
                AND status IN ('running', 'paused') AND deleted_at IS NULL LIMIT 1""",
                (workspace_id,),
            ).fetchone()
            if current is not None:
                connection.commit()
                return self._routine_payload(current, now)
            routine_id = str(uuid4())
            timestamp = now.isoformat()
            connection.execute(
                """INSERT INTO work_routine_sessions
                (id, workspace_id, status, started_at, accumulated_seconds, created_at, updated_at)
                VALUES (?, ?, 'running', ?, 0, ?, ?)""",
                (routine_id, workspace_id, timestamp, timestamp, timestamp),
            )
            created = {
                "id": routine_id,
                "status": "running",
                "started_at": timestamp,
                "paused_at": None,
                "accumulated_seconds": 0,
            }
            connection.commit()
            return self._routine_payload(created, now)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def pause_work_routine(self, workspace_id: str) -> dict[str, object]:
        return self._change_work_routine(workspace_id, "pause")

    def resume_work_routine(self, workspace_id: str) -> dict[str, object]:
        return self._change_work_routine(workspace_id, "resume")

    def stop_work_routine(self, workspace_id: str) -> dict[str, object]:
        return self._change_work_routine(workspace_id, "stop")

    def _change_work_routine(self, workspace_id: str, action: str) -> dict[str, object]:
        now = datetime.now(UTC)
        connection = self._database.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT id, status, started_at, paused_at, accumulated_seconds
                FROM work_routine_sessions WHERE workspace_id = ?
                AND status IN ('running', 'paused') AND deleted_at IS NULL LIMIT 1""",
                (workspace_id,),
            ).fetchone()
            if row is None:
                raise ValueError("Nenhuma rotina ativa para atualizar")
            current = self._routine_payload(row, now)
            timestamp = now.isoformat()
            if action == "pause":
                if current["status"] == "running":
                    connection.execute(
                        "UPDATE work_routine_sessions SET status = 'paused', paused_at = ?, "
                        "accumulated_seconds = ?, updated_at = ? WHERE id = ?",
                        (
                            timestamp,
                            int(cast(int, current["elapsedSeconds"])),
                            timestamp,
                            current["id"],
                        ),
                    )
                    current["status"] = "paused"
                    current["pausedAt"] = timestamp
            elif action == "resume":
                if current["status"] == "paused":
                    connection.execute(
                        "UPDATE work_routine_sessions SET status = 'running', started_at = ?, "
                        "paused_at = NULL, updated_at = ? WHERE id = ?",
                        (timestamp, timestamp, current["id"]),
                    )
                    current["status"] = "running"
                    current["pausedAt"] = None
                    current["startedAt"] = timestamp
            else:
                elapsed = int(cast(int, current["elapsedSeconds"]))
                deleted_at = None if elapsed >= MIN_RECORDED_ROUTINE_SECONDS else timestamp
                connection.execute(
                    "UPDATE work_routine_sessions SET status = 'completed', paused_at = NULL, "
                    "finished_at = ?, accumulated_seconds = ?, deleted_at = ?, updated_at = ? "
                    "WHERE id = ?",
                    (timestamp, elapsed, deleted_at, timestamp, current["id"]),
                )
                current["status"] = "completed"
                current["finishedAt"] = timestamp
            connection.commit()
            return current
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _routine_payload(row: object, now: datetime | None = None) -> dict[str, object]:
        if isinstance(row, dict):
            values = row
        else:
            values = {
                "id": row["id"],  # type: ignore[index]
                "status": row["status"],  # type: ignore[index]
                "started_at": row["started_at"],  # type: ignore[index]
                "paused_at": row["paused_at"],  # type: ignore[index]
                "accumulated_seconds": row["accumulated_seconds"],  # type: ignore[index]
            }
        current_time = now or datetime.now(UTC)
        started_at = datetime.fromisoformat(str(values["started_at"]))
        paused_at_raw = values["paused_at"]
        status = str(values["status"])
        elapsed = int(cast(int, values["accumulated_seconds"]))
        if status == "running":
            elapsed += max(0, int((current_time - started_at).total_seconds()))
        return {
            "id": str(values["id"]),
            "status": status,
            "startedAt": started_at.isoformat(),
            "pausedAt": str(paused_at_raw) if paused_at_raw else None,
            "elapsedSeconds": elapsed,
        }
