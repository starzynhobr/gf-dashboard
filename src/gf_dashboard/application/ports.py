from __future__ import annotations

from contextlib import AbstractContextManager
from datetime import date, datetime
from typing import Protocol

from gf_dashboard.domain.entities import (
    Activity,
    ActivityCompletion,
    ActivityRuleVersion,
    Character,
    CharacterActivity,
    DailyActivityEntry,
    FarmSession,
    FarmSessionItem,
    FarmSessionParticipant,
    GameAccount,
    Item,
    MarketPriceQuote,
    TowerSessionDetails,
    Workspace,
)
from gf_dashboard.domain.value_objects import EntityId, WorkspaceId


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new(self) -> EntityId: ...


class WorkspaceRepository(Protocol):
    def get(self, workspace_id: WorkspaceId) -> Workspace | None: ...

    def save(self, workspace: Workspace) -> None: ...


class AccountRepository(Protocol):
    def get(self, account_id: EntityId, workspace_id: WorkspaceId) -> GameAccount | None: ...

    def save(self, account: GameAccount) -> None: ...

    def exists_by_name(self, workspace_id: WorkspaceId, name: str) -> bool: ...

    def list_active(self, workspace_id: WorkspaceId) -> list[GameAccount]: ...


class CharacterRepository(Protocol):
    def get(self, character_id: EntityId, workspace_id: WorkspaceId) -> Character | None: ...

    def save(self, character: Character) -> None: ...

    def exists_by_account_and_name(
        self, workspace_id: WorkspaceId, account_id: EntityId, name: str
    ) -> bool: ...

    def list_active(
        self, workspace_id: WorkspaceId, account_id: EntityId | None = None
    ) -> list[Character]: ...

    def next_sort_order(self, workspace_id: WorkspaceId, account_id: EntityId) -> int: ...


class ActivityRepository(Protocol):
    def get(self, activity_id: EntityId, workspace_id: WorkspaceId) -> Activity | None: ...

    def save(self, activity: Activity) -> None: ...

    def exists_by_name(self, workspace_id: WorkspaceId, name: str) -> bool: ...

    def list_active(self, workspace_id: WorkspaceId) -> list[Activity]: ...

    def list_all(self, workspace_id: WorkspaceId) -> list[Activity]: ...


class CharacterActivityRepository(Protocol):
    def get(
        self, character_activity_id: EntityId, workspace_id: WorkspaceId
    ) -> CharacterActivity | None: ...

    def save(self, character_activity: CharacterActivity) -> None: ...

    def list_for_character(
        self, workspace_id: WorkspaceId, character_id: EntityId
    ) -> list[CharacterActivity]: ...


class ActivityRuleRepository(Protocol):
    def find_effective(
        self, workspace_id: WorkspaceId, activity_id: EntityId, activity_date: date
    ) -> ActivityRuleVersion | None: ...

    def save(self, rule: ActivityRuleVersion) -> None: ...


class DailyActivityEntryRepository(Protocol):
    def find_by_activity_and_date(
        self,
        workspace_id: WorkspaceId,
        character_activity_id: EntityId,
        activity_date: date,
    ) -> DailyActivityEntry | None: ...

    def save(self, entry: DailyActivityEntry) -> None: ...


class ActivityCompletionRepository(Protocol):
    def list_for_entry(
        self, workspace_id: WorkspaceId, daily_activity_entry_id: EntityId
    ) -> list[ActivityCompletion]: ...

    def save_many(self, completions: list[ActivityCompletion]) -> None: ...

    def delete_for_entry(
        self, workspace_id: WorkspaceId, daily_activity_entry_id: EntityId
    ) -> None: ...


class TowerSessionRepository(Protocol):
    def save(
        self,
        session: FarmSession,
        details: TowerSessionDetails,
        participants: tuple[FarmSessionParticipant, ...],
    ) -> None: ...

    def get(
        self, workspace_id: WorkspaceId, session_id: EntityId
    ) -> tuple[FarmSession, TowerSessionDetails, tuple[FarmSessionParticipant, ...]] | None: ...

    def add_drop(self, drop: FarmSessionItem) -> None: ...


class ItemRepository(Protocol):
    def get(self, item_id: EntityId, workspace_id: WorkspaceId) -> Item | None: ...

    def get_by_name(self, workspace_id: WorkspaceId, name: str) -> Item | None: ...

    def save(self, item: Item) -> None: ...


class MarketPriceQuoteRepository(Protocol):
    def save(self, quote: MarketPriceQuote) -> None: ...

    def latest_for_item(
        self, workspace_id: WorkspaceId, item_id: EntityId
    ) -> MarketPriceQuote | None: ...


class DashboardLayoutRepository(Protocol):
    def get_enabled(self, workspace_id: WorkspaceId) -> dict[str, bool]: ...

    def save_enabled(
        self,
        workspace_id: WorkspaceId,
        module_key: str,
        enabled: bool,
        layout_id: EntityId,
        item_id: EntityId,
        changed_at: datetime,
    ) -> None: ...

    def reset(self, workspace_id: WorkspaceId) -> None: ...


class FarmUnitOfWork(AbstractContextManager["FarmUnitOfWork"], Protocol):
    workspaces: WorkspaceRepository
    accounts: AccountRepository
    characters: CharacterRepository
    activities: ActivityRepository
    character_activities: CharacterActivityRepository
    rules: ActivityRuleRepository
    daily_entries: DailyActivityEntryRepository
    completions: ActivityCompletionRepository
    items: ItemRepository
    market_quotes: MarketPriceQuoteRepository
    dashboard_layouts: DashboardLayoutRepository

    def __enter__(self) -> FarmUnitOfWork: ...

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool | None: ...


class TowerUnitOfWork(AbstractContextManager["TowerUnitOfWork"], Protocol):
    characters: CharacterRepository
    tower_sessions: TowerSessionRepository
    items: ItemRepository

    def __enter__(self) -> TowerUnitOfWork: ...

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool | None: ...
