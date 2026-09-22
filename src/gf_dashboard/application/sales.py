from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from gf_dashboard.domain.errors import ValidationError
from gf_dashboard.domain.value_objects import WorkspaceId

SUPPORTED_SALE_TYPES = frozenset({"gold", "pve_bag", "item"})


@dataclass(frozen=True, slots=True)
class SaleCommand:
    workspace_id: WorkspaceId
    idempotency_key: UUID
    sale_type: str
    item_description: str
    quantity: int
    original_amount_minor: int
    currency: str
    exchange_rate_micros: int
    exchange_rate_source: str
    sold_at: datetime


@dataclass(frozen=True, slots=True)
class SaleResult:
    sale_id: str
    real_amount_minor: int
    original_amount_minor: int
    currency: str
    exchange_rate_micros: int
    exchange_rate_source: str
    sold_at: datetime
    already_recorded: bool = False


class SaleLedger(Protocol):
    def record(self, command: SaleCommand, real_amount_minor: int) -> SaleResult: ...


class SaleService:
    """Validates a commercial fact and delegates its atomic persistence to a ledger."""

    def __init__(self, ledger: SaleLedger) -> None:
        self._ledger = ledger

    def record_sale(self, command: SaleCommand) -> SaleResult:
        sale_type = command.sale_type.strip().lower()
        if sale_type not in SUPPORTED_SALE_TYPES:
            raise ValidationError("Tipo de venda inválido")
        if not command.item_description.strip():
            raise ValidationError("Descrição da venda é obrigatória")
        if isinstance(command.quantity, bool) or command.quantity <= 0:
            raise ValidationError("Quantidade da venda deve ser inteira e positiva")
        if isinstance(command.original_amount_minor, bool) or command.original_amount_minor <= 0:
            raise ValidationError("Valor recebido deve ser positivo em unidade mínima")
        currency = command.currency.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValidationError("Moeda deve usar código ISO de três letras")
        if isinstance(command.exchange_rate_micros, bool) or command.exchange_rate_micros <= 0:
            raise ValidationError("Cotação deve ser positiva")
        if not command.exchange_rate_source.strip():
            raise ValidationError("Origem da cotação é obrigatória")
        if command.sold_at.tzinfo is None or command.sold_at.utcoffset() is None:
            raise ValidationError("Data da venda deve incluir timezone")
        normalized = SaleCommand(
            command.workspace_id,
            command.idempotency_key,
            sale_type,
            command.item_description.strip(),
            command.quantity,
            command.original_amount_minor,
            currency,
            command.exchange_rate_micros,
            command.exchange_rate_source.strip(),
            command.sold_at.astimezone(UTC),
        )
        real_amount_minor = (
            normalized.original_amount_minor * normalized.exchange_rate_micros + 500_000
        ) // 1_000_000
        return self._ledger.record(normalized, real_amount_minor)
