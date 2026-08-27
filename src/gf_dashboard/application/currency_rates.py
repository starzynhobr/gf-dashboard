import json
import urllib.request
from datetime import UTC, date, datetime
from uuid import uuid4

from gf_dashboard.infrastructure.persistence import SqliteDatabase


class CurrencyRateService:
    def __init__(self, database: SqliteDatabase) -> None:
        self._database = database

    def get_rate(
        self,
        base_currency: str,
        quote_currency: str = "BRL",
        rate_date: date | None = None,
    ) -> tuple[int, str]:
        base = base_currency.upper().strip()
        quote = quote_currency.upper().strip()

        if base == quote:
            return (1_000_000, "identity")

        if rate_date is None:
            rate_date = date.today()

        rate_date_str = rate_date.isoformat()

        # 1. Check local database cache
        connection = self._database.connect()
        try:
            cached = connection.execute(
                """
                SELECT rate_micros, source
                FROM currency_rates
                WHERE base_currency = ? AND quote_currency = ? AND rate_date = ?
                  AND deleted_at IS NULL
                """,
                (base, quote, rate_date_str),
            ).fetchone()
            if cached is not None:
                return (int(cached["rate_micros"]), str(cached["source"]))
        finally:
            connection.close()

        # 2. Try fetching from public Frankfurter API
        try:
            url = f"https://api.frankfurter.dev/v1/{rate_date_str}?base={base}&symbols={quote}"
            req = urllib.request.Request(url, headers={"User-Agent": "GF-Dashboard/1.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    rate_float = float(payload["rates"][quote])
                    rate_micros = round(rate_float * 1_000_000)
                    self._save_rate(base, quote, rate_date, rate_micros, "frankfurter")
                    return (rate_micros, "frankfurter")
        except Exception:
            pass

        # 3. Fallback: check latest cached rate from any date
        connection = self._database.connect()
        try:
            latest = connection.execute(
                """
                SELECT rate_micros, source
                FROM currency_rates
                WHERE base_currency = ? AND quote_currency = ? AND deleted_at IS NULL
                ORDER BY rate_date DESC
                LIMIT 1
                """,
                (base, quote),
            ).fetchone()
            if latest is not None:
                return (int(latest["rate_micros"]), "cached")
        finally:
            connection.close()

        # 4. Deterministic offline defaults
        defaults: dict[tuple[str, str], int] = {
            ("USD", "BRL"): 5_430_000,
            ("EUR", "BRL"): 6_420_000,
            ("BRL", "USD"): 184_162,
            ("BRL", "EUR"): 155_763,
        }
        fallback = defaults.get((base, quote), 1_000_000)
        return (fallback, "offline_fallback")

    def _save_rate(
        self,
        base_currency: str,
        quote_currency: str,
        rate_date: date,
        rate_micros: int,
        source: str,
    ) -> None:
        connection = self._database.connect()
        try:
            now_iso = datetime.now(UTC).isoformat()
            connection.execute(
                """
                INSERT INTO currency_rates (
                    id, base_currency, quote_currency, rate_micros,
                    rate_date, source, fetched_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (base_currency, quote_currency, rate_date) DO UPDATE SET
                    rate_micros = excluded.rate_micros,
                    source = excluded.source,
                    fetched_at = excluded.fetched_at,
                    updated_at = excluded.updated_at
                """,
                (
                    str(uuid4()),
                    base_currency,
                    quote_currency,
                    rate_micros,
                    rate_date.isoformat(),
                    source,
                    now_iso,
                    now_iso,
                    now_iso,
                ),
            )
            connection.commit()
        finally:
            connection.close()
