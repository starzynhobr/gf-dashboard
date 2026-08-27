from __future__ import annotations

from datetime import UTC, datetime

import pytest

from gf_dashboard.domain.errors import ValidationError
from gf_dashboard.domain.value_objects import Gold, Money, operational_date


def test_gold_uses_integers_and_can_be_multiplied() -> None:
    assert Gold(910).times(5) == Gold(4550)
    assert Gold(910) + Gold(490) == Gold(1400)


@pytest.mark.parametrize("invalid", [-1, 1.5, True])
def test_gold_rejects_negative_float_or_boolean(invalid: object) -> None:
    with pytest.raises(ValidationError):
        Gold(invalid)  # type: ignore[arg-type]


def test_money_normalizes_iso_currency_without_float() -> None:
    assert Money(7, "brl") == Money(7, "BRL")


def test_operational_date_respects_midnight_in_configured_timezone() -> None:
    timestamp = datetime(2026, 8, 27, 2, 30, tzinfo=UTC)

    assert operational_date(timestamp, "America/Sao_Paulo").isoformat() == "2026-08-26"


def test_operational_date_rejects_naive_timestamp() -> None:
    with pytest.raises(ValidationError, match="Timestamp"):
        operational_date(datetime(2026, 8, 26, 23, 0), "America/Sao_Paulo")
