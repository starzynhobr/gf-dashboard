from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from gf_dashboard.application.sales import SaleCommand, SaleResult
from gf_dashboard.infrastructure.persistence import SqliteDatabase


class SqliteSaleLedger:
    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database

    def record(self, command: SaleCommand, real_amount_minor: int) -> SaleResult:
        connection = self._database.connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """SELECT id, real_amount_minor, original_amount_minor, currency,
                          exchange_rate_micros, exchange_rate_source, sold_at
                   FROM sales WHERE workspace_id = ? AND idempotency_key = ?
                     AND deleted_at IS NULL""",
                (str(command.workspace_id), str(command.idempotency_key)),
            ).fetchone()
            if existing is not None:
                connection.rollback()
                return SaleResult(
                    str(existing["id"]),
                    int(existing["real_amount_minor"]),
                    int(existing["original_amount_minor"]),
                    str(existing["currency"]),
                    int(existing["exchange_rate_micros"]),
                    str(existing["exchange_rate_source"]),
                    datetime.fromisoformat(str(existing["sold_at"])),
                    True,
                )
            now = datetime.now(UTC).isoformat()
            sale_id, transaction_id = str(uuid4()), str(uuid4())
            gold_quantity = command.quantity if command.sale_type == "gold" else 0
            connection.execute(
                """INSERT INTO sales (
                    id, workspace_id, sale_type, status, gold_quantity, real_amount_minor,
                    currency, buyer_reference, item_description, item_quantity, sold_at,
                    fees_minor, notes, original_amount_minor, exchange_rate_micros,
                    exchange_rate_source, converted_currency, idempotency_key, created_at,
                    updated_at
                ) VALUES (
                    ?, ?, ?, 'completed', ?, ?, ?, NULL, ?, ?, ?, 0, NULL, ?, ?, ?, 'BRL', ?, ?, ?
                )""",
                (
                    sale_id,
                    str(command.workspace_id),
                    command.sale_type,
                    gold_quantity,
                    real_amount_minor,
                    command.currency,
                    command.item_description,
                    command.quantity,
                    command.sold_at.isoformat(),
                    command.original_amount_minor,
                    command.exchange_rate_micros,
                    command.exchange_rate_source,
                    str(command.idempotency_key),
                    now,
                    now,
                ),
            )
            connection.execute(
                """INSERT INTO transactions (
                    id, workspace_id, type, category, amount_gold, amount_minor, currency,
                    sale_id, occurred_at, description, created_at, updated_at
                ) VALUES (?, ?, 'income', 'sale', ?, ?, 'BRL', ?, ?, ?, ?, ?)""",
                (
                    transaction_id,
                    str(command.workspace_id),
                    gold_quantity,
                    real_amount_minor,
                    sale_id,
                    command.sold_at.isoformat(),
                    f"Venda de {command.item_description} ({command.quantity})",
                    now,
                    now,
                ),
            )
            connection.commit()
            return SaleResult(
                sale_id,
                real_amount_minor,
                command.original_amount_minor,
                command.currency,
                command.exchange_rate_micros,
                command.exchange_rate_source,
                command.sold_at,
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
