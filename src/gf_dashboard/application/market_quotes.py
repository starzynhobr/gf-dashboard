from __future__ import annotations

from gf_dashboard.application.ports import Clock, FarmUnitOfWork, IdGenerator
from gf_dashboard.domain.entities import Item, MarketPriceQuote
from gf_dashboard.domain.value_objects import Gold, WorkspaceId

PVE_BAG_NAME = "Saco PvE"


class MarketQuoteService:
    def __init__(self, uow: FarmUnitOfWork, ids: IdGenerator, clock: Clock) -> None:
        self._uow = uow
        self._ids = ids
        self._clock = clock

    def ensure_pve_bag_item(self, workspace_id: WorkspaceId) -> Item:
        with self._uow:
            existing = self._uow.items.get_by_name(workspace_id, PVE_BAG_NAME)
            if existing is not None:
                return existing
            item = Item(
                id=self._ids.new(),
                workspace_id=workspace_id,
                name=PVE_BAG_NAME,
                category="material",
                created_at=self._clock.now(),
            )
            self._uow.items.save(item)
            return item

    def record_pve_bag_quote(
        self, workspace_id: WorkspaceId, unit_value_gold: Gold, source: str | None = None
    ) -> MarketPriceQuote:
        item = self.ensure_pve_bag_item(workspace_id)
        quote = MarketPriceQuote(
            id=self._ids.new(),
            workspace_id=workspace_id,
            item_id=item.id,
            unit_value_gold=unit_value_gold,
            observed_at=self._clock.now(),
            source=source,
        )
        with self._uow:
            self._uow.market_quotes.save(quote)
        return quote

    def current_pve_bag_quote(self, workspace_id: WorkspaceId) -> MarketPriceQuote | None:
        with self._uow:
            item = self._uow.items.get_by_name(workspace_id, PVE_BAG_NAME)
            return self._uow.market_quotes.latest_for_item(workspace_id, item.id) if item else None
