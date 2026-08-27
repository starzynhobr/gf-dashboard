from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Literal
from uuid import UUID

from gf_dashboard.application.ports import (
    AccountRepository,
    ActivityCompletionRepository,
    ActivityRepository,
    ActivityRuleRepository,
    CharacterActivityRepository,
    CharacterRepository,
    Clock,
    DailyActivityEntryRepository,
    IdGenerator,
    WorkspaceRepository,
)
from gf_dashboard.domain.entities import (
    Activity,
    ActivityCompletion,
    ActivityRuleVersion,
    Character,
    CharacterActivity,
    DailyActivityEntry,
    GameAccount,
    Workspace,
)
from gf_dashboard.domain.value_objects import EntityId, WorkspaceId, new_entity_id, require_utc


@dataclass
class InMemoryState:
    workspaces: dict[WorkspaceId, Workspace] = field(default_factory=dict)
    accounts: dict[EntityId, GameAccount] = field(default_factory=dict)
    characters: dict[EntityId, Character] = field(default_factory=dict)
    activities: dict[EntityId, Activity] = field(default_factory=dict)
    character_activities: dict[EntityId, CharacterActivity] = field(default_factory=dict)
    rules: dict[EntityId, ActivityRuleVersion] = field(default_factory=dict)
    daily_entries: dict[EntityId, DailyActivityEntry] = field(default_factory=dict)
    completions: dict[EntityId, ActivityCompletion] = field(default_factory=dict)


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock(Clock):
    def __init__(self, current: datetime) -> None:
        self._current = require_utc(current)

    def now(self) -> datetime:
        return self._current


class UUIDGenerator(IdGenerator):
    def new(self) -> EntityId:
        return new_entity_id()


class SequenceIdGenerator(IdGenerator):
    def __init__(self) -> None:
        self._next = 1

    def new(self) -> EntityId:
        value = EntityId(UUID(int=self._next))
        self._next += 1
        return value


class InMemoryWorkspaceRepository(WorkspaceRepository):
    def __init__(self, state: InMemoryState) -> None:
        self._state = state

    def get(self, workspace_id: WorkspaceId) -> Workspace | None:
        return self._state.workspaces.get(workspace_id)

    def save(self, workspace: Workspace) -> None:
        self._state.workspaces[workspace.id] = workspace


class InMemoryAccountRepository(AccountRepository):
    def __init__(self, state: InMemoryState) -> None:
        self._state = state

    def get(self, account_id: EntityId, workspace_id: WorkspaceId) -> GameAccount | None:
        account = self._state.accounts.get(account_id)
        return account if account and account.workspace_id == workspace_id else None

    def save(self, account: GameAccount) -> None:
        self._state.accounts[account.id] = account

    def exists_by_name(self, workspace_id: WorkspaceId, name: str) -> bool:
        normalized = name.strip().casefold()
        return any(
            account.workspace_id == workspace_id
            and account.deleted_at is None
            and account.is_active
            and account.name.casefold() == normalized
            for account in self._state.accounts.values()
        )

    def list_active(self, workspace_id: WorkspaceId) -> list[GameAccount]:
        return sorted(
            (
                account
                for account in self._state.accounts.values()
                if account.workspace_id == workspace_id
                and account.deleted_at is None
                and account.is_active
            ),
            key=lambda account: (account.created_at, account.name),
        )


class InMemoryCharacterRepository(CharacterRepository):
    def __init__(self, state: InMemoryState) -> None:
        self._state = state

    def get(self, character_id: EntityId, workspace_id: WorkspaceId) -> Character | None:
        character = self._state.characters.get(character_id)
        return character if character and character.workspace_id == workspace_id else None

    def save(self, character: Character) -> None:
        self._state.characters[character.id] = character

    def exists_by_account_and_name(
        self, workspace_id: WorkspaceId, account_id: EntityId, name: str
    ) -> bool:
        normalized = name.strip().casefold()
        return any(
            character.workspace_id == workspace_id
            and character.account_id == account_id
            and character.deleted_at is None
            and character.is_active
            and character.name.casefold() == normalized
            for character in self._state.characters.values()
        )

    def list_active(
        self, workspace_id: WorkspaceId, account_id: EntityId | None = None
    ) -> list[Character]:
        return sorted(
            (
                character
                for character in self._state.characters.values()
                if character.workspace_id == workspace_id
                and character.deleted_at is None
                and character.is_active
                and (account_id is None or character.account_id == account_id)
            ),
            key=lambda character: (
                str(character.account_id),
                character.sort_order,
                character.name,
            ),
        )

    def next_sort_order(self, workspace_id: WorkspaceId, account_id: EntityId) -> int:
        characters = self.list_active(workspace_id, account_id)
        return max((character.sort_order for character in characters), default=0) + 1


class InMemoryActivityRepository(ActivityRepository):
    def __init__(self, state: InMemoryState) -> None:
        self._state = state

    def get(self, activity_id: EntityId, workspace_id: WorkspaceId) -> Activity | None:
        activity = self._state.activities.get(activity_id)
        return activity if activity and activity.workspace_id == workspace_id else None

    def save(self, activity: Activity) -> None:
        self._state.activities[activity.id] = activity

    def exists_by_name(self, workspace_id: WorkspaceId, name: str) -> bool:
        normalized = name.strip().casefold()
        return any(
            activity.workspace_id == workspace_id
            and activity.name.casefold() == normalized
            and activity.is_active
            for activity in self._state.activities.values()
        )

    def list_active(self, workspace_id: WorkspaceId) -> list[Activity]:
        return sorted(
            (
                activity
                for activity in self._state.activities.values()
                if activity.workspace_id == workspace_id and activity.is_active
            ),
            key=lambda activity: activity.name,
        )

    def list_all(self, workspace_id: WorkspaceId) -> list[Activity]:
        return sorted(
            (
                activity
                for activity in self._state.activities.values()
                if activity.workspace_id == workspace_id
            ),
            key=lambda activity: activity.name,
        )


class InMemoryCharacterActivityRepository(CharacterActivityRepository):
    def __init__(self, state: InMemoryState) -> None:
        self._state = state

    def get(
        self, character_activity_id: EntityId, workspace_id: WorkspaceId
    ) -> CharacterActivity | None:
        character_activity = self._state.character_activities.get(character_activity_id)
        return (
            character_activity
            if character_activity and character_activity.workspace_id == workspace_id
            else None
        )

    def save(self, character_activity: CharacterActivity) -> None:
        self._state.character_activities[character_activity.id] = character_activity

    def list_for_character(
        self, workspace_id: WorkspaceId, character_id: EntityId
    ) -> list[CharacterActivity]:
        return sorted(
            (
                item
                for item in self._state.character_activities.values()
                if item.workspace_id == workspace_id and item.character_id == character_id
            ),
            key=lambda item: item.sort_order,
        )


class InMemoryActivityRuleRepository(ActivityRuleRepository):
    def __init__(self, state: InMemoryState) -> None:
        self._state = state

    def find_effective(
        self, workspace_id: WorkspaceId, activity_id: EntityId, activity_date: date
    ) -> ActivityRuleVersion | None:
        rules = [
            rule
            for rule in self._state.rules.values()
            if rule.workspace_id == workspace_id
            and rule.activity_id == activity_id
            and rule.applies_on(activity_date)
        ]
        if not rules:
            return None
        return max(rules, key=lambda rule: rule.effective_from)

    def save(self, rule: ActivityRuleVersion) -> None:
        self._state.rules[rule.id] = rule


class InMemoryDailyActivityEntryRepository(DailyActivityEntryRepository):
    def __init__(self, state: InMemoryState) -> None:
        self._state = state

    def find_by_activity_and_date(
        self,
        workspace_id: WorkspaceId,
        character_activity_id: EntityId,
        activity_date: date,
    ) -> DailyActivityEntry | None:
        return next(
            (
                entry
                for entry in self._state.daily_entries.values()
                if entry.workspace_id == workspace_id
                and entry.character_activity_id == character_activity_id
                and entry.activity_date == activity_date
            ),
            None,
        )

    def save(self, entry: DailyActivityEntry) -> None:
        self._state.daily_entries[entry.id] = entry


class InMemoryActivityCompletionRepository(ActivityCompletionRepository):
    def __init__(self, state: InMemoryState) -> None:
        self._state = state

    def list_for_entry(
        self, workspace_id: WorkspaceId, daily_activity_entry_id: EntityId
    ) -> list[ActivityCompletion]:
        return sorted(
            (
                completion
                for completion in self._state.completions.values()
                if completion.workspace_id == workspace_id
                and completion.daily_activity_entry_id == daily_activity_entry_id
            ),
            key=lambda completion: completion.sequence_no,
        )

    def save_many(self, completions: list[ActivityCompletion]) -> None:
        for completion in completions:
            self._state.completions[completion.id] = completion

    def delete_for_entry(
        self, workspace_id: WorkspaceId, daily_activity_entry_id: EntityId
    ) -> None:
        to_delete = [
            completion_id
            for completion_id, completion in self._state.completions.items()
            if completion.workspace_id == workspace_id
            and completion.daily_activity_entry_id == daily_activity_entry_id
        ]
        for completion_id in to_delete:
            del self._state.completions[completion_id]


class InMemoryUnitOfWork:
    """Transactional test adapter that restores a deep copy if a use case raises."""

    workspaces: WorkspaceRepository
    accounts: AccountRepository
    characters: CharacterRepository
    activities: ActivityRepository
    character_activities: CharacterActivityRepository
    rules: ActivityRuleRepository
    daily_entries: DailyActivityEntryRepository
    completions: ActivityCompletionRepository

    def __init__(self) -> None:
        self.state = InMemoryState()
        self.workspaces = InMemoryWorkspaceRepository(self.state)
        self.accounts = InMemoryAccountRepository(self.state)
        self.characters = InMemoryCharacterRepository(self.state)
        self.activities = InMemoryActivityRepository(self.state)
        self.character_activities = InMemoryCharacterActivityRepository(self.state)
        self.rules = InMemoryActivityRuleRepository(self.state)
        self.daily_entries = InMemoryDailyActivityEntryRepository(self.state)
        self.completions = InMemoryActivityCompletionRepository(self.state)
        self._snapshot: InMemoryState | None = None

    def __enter__(self) -> InMemoryUnitOfWork:
        self._snapshot = deepcopy(self.state)
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> Literal[False]:
        if exc_type is not None and self._snapshot is not None:
            self.state = self._snapshot
            self.workspaces = InMemoryWorkspaceRepository(self.state)
            self.accounts = InMemoryAccountRepository(self.state)
            self.characters = InMemoryCharacterRepository(self.state)
            self.activities = InMemoryActivityRepository(self.state)
            self.character_activities = InMemoryCharacterActivityRepository(self.state)
            self.rules = InMemoryActivityRuleRepository(self.state)
            self.daily_entries = InMemoryDailyActivityEntryRepository(self.state)
            self.completions = InMemoryActivityCompletionRepository(self.state)
        self._snapshot = None
        return False
