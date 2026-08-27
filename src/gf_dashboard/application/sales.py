from datetime import UTC, datetime
from uuid import uuid4

from gf_dashboard.domain.value_objects import WorkspaceId
from gf_dashboard.infrastructure.persistence import SqliteDatabase


class SaleService:
    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database

    def record_sale(
        self,
        workspace_id: WorkspaceId,
        sale_type: str,
        item_description: str,
        quantity: int,
        original_amount_minor: int,
        currency: str,
        exchange_rate_micros: int,
        real_amount_minor: int,
        sold_at: datetime | None = None,
    ) -> dict[str, str | int]:
        if sold_at is None:
            sold_at = datetime.now(UTC)

        sold_at_str = sold_at.isoformat()
        now_str = datetime.now(UTC).isoformat()
        sale_id = str(uuid4())
        tx_id = str(uuid4())

        gold_qty = quantity if sale_type == "gold" else 0

        connection = self._database.connect()
        try:
            # 1. Insert into sales
            connection.execute(
                """
                INSERT INTO sales (
                    id, workspace_id, sale_type, status, gold_quantity,
                    real_amount_minor, currency, buyer_reference, sold_at,
                    fees_minor, notes, created_at, updated_at,
                    original_amount_minor, exchange_rate_micros, item_quantity
                ) VALUES (?, ?, ?, 'completed', ?, ?, ?, ?, ?, 0, NULL, ?, ?, ?, ?, ?)
                """,
                (
                    sale_id,
                    str(workspace_id),
                    sale_type,
                    gold_qty,
                    real_amount_minor,
                    currency.upper(),
                    item_description,
                    sold_at_str,
                    now_str,
                    now_str,
                    original_amount_minor,
                    exchange_rate_micros,
                    quantity,
                ),
            )

            # 2. Insert into transactions
            connection.execute(
                """
                INSERT INTO transactions (
                    id, workspace_id, type, category, amount_gold, amount_minor,
                    currency, sale_id, occurred_at, description, created_at, updated_at
                ) VALUES (?, ?, 'income', 'sale', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tx_id,
                    str(workspace_id),
                    gold_qty,
                    real_amount_minor,
                    currency.upper(),
                    sale_id,
                    sold_at_str,
                    f"Venda de {item_description} ({quantity})",
                    now_str,
                    now_str,
                ),
            )

            connection.commit()

            return {
                "saleId": sale_id,
                "realAmountMinor": real_amount_minor,
                "originalAmountMinor": original_amount_minor,
                "currency": currency.upper(),
                "exchangeRateMicros": exchange_rate_micros,
                "soldAt": sold_at_str,
            }
        finally:
            connection.close()
