from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from gf_dashboard.application.ports import Clock, FarmUnitOfWork, IdGenerator
from gf_dashboard.domain.entities import (
    ActivityCompletion,
    Character,
    CharacterActivity,
    DailyActivityEntry,
    GameAccount,
    Workspace,
    reward_total,
)
from gf_dashboard.domain.enums import ActivityCategory, ActivityStatus
from gf_dashboard.domain.errors import ConflictError, NotFoundError, ValidationError
from gf_dashboard.domain.value_objects import EntityId, RewardSnapshot, WorkspaceId


@dataclass(frozen=True, slots=True)
class CompletionResult:
    entry: DailyActivityEntry
    completions: tuple[ActivityCompletion, ...]
    total_reward: RewardSnapshot
    already_completed: bool


@dataclass(frozen=True, slots=True)
class CharacterDaySaveResult:
    completed_dungeons: int
    gold: int
    pve_bags: int


class WorkspaceService:
    def __init__(self, uow: FarmUnitOfWork, ids: IdGenerator, clock: Clock) -> None:
        self._uow = uow
        self._ids = ids
        self._clock = clock

    def create_workspace(self, name: str) -> Workspace:
        workspace = Workspace(
            id=WorkspaceId(self._ids.new()), name=name, created_at=self._clock.now()
        )
        with self._uow:
            self._uow.workspaces.save(workspace)
        return workspace

    def create_account(self, workspace_id: WorkspaceId, name: str, server_name: str) -> GameAccount:
        with self._uow:
            self._require_workspace(workspace_id)
            if self._uow.accounts.exists_by_name(workspace_id, name):
                raise ConflictError("Já existe uma conta ativa com esse nome no workspace")
            account = GameAccount(
                id=self._ids.new(),
                workspace_id=workspace_id,
                name=name,
                server_name=server_name,
                created_at=self._clock.now(),
            )
            self._uow.accounts.save(account)
            return account

    def create_character(
        self,
        workspace_id: WorkspaceId,
        account_id: EntityId,
        name: str,
        class_name: str,
        level: int,
        sort_order: int,
    ) -> Character:
        with self._uow:
            self._require_workspace(workspace_id)
            if self._uow.accounts.get(account_id, workspace_id) is None:
                raise NotFoundError("Conta não encontrada no workspace")
            if self._uow.characters.exists_by_account_and_name(workspace_id, account_id, name):
                raise ConflictError("Já existe personagem ativo com esse nome nesta conta")
            character = Character(
                id=self._ids.new(),
                workspace_id=workspace_id,
                account_id=account_id,
                name=name,
                class_name=class_name,
                level=level,
                sort_order=sort_order,
                created_at=self._clock.now(),
            )
            self._uow.characters.save(character)
            return character

    def configure_character_activity(
        self,
        workspace_id: WorkspaceId,
        character_id: EntityId,
        activity_id: EntityId,
        target_amount: int,
        sort_order: int,
    ) -> CharacterActivity:
        with self._uow:
            self._require_workspace(workspace_id)
            if self._uow.characters.get(character_id, workspace_id) is None:
                raise NotFoundError("Personagem não encontrado no workspace")
            if self._uow.activities.get(activity_id, workspace_id) is None:
                raise NotFoundError("Atividade não encontrada no workspace")
            character_activity = CharacterActivity(
                id=self._ids.new(),
                workspace_id=workspace_id,
                character_id=character_id,
                activity_id=activity_id,
                target_amount=target_amount,
                sort_order=sort_order,
            )
            self._uow.character_activities.save(character_activity)
            return character_activity

    def _require_workspace(self, workspace_id: WorkspaceId) -> Workspace:
        workspace = self._uow.workspaces.get(workspace_id)
        if workspace is None:
            raise NotFoundError("Workspace não encontrado")
        return workspace


class ManagementService:
    def __init__(self, uow: FarmUnitOfWork, ids: IdGenerator, clock: Clock) -> None:
        self._uow = uow
        self._ids = ids
        self._clock = clock

    def create_account(self, workspace_id: WorkspaceId, name: str, server_name: str) -> GameAccount:
        with self._uow:
            if self._uow.workspaces.get(workspace_id) is None:
                raise NotFoundError("Workspace não encontrado")
            if self._uow.accounts.exists_by_name(workspace_id, name):
                raise ConflictError("Já existe uma conta ativa com esse nome")
            account = GameAccount(
                self._ids.new(), workspace_id, name, server_name, self._clock.now()
            )
            self._uow.accounts.save(account)
            return account

    def create_character_with_default_activities(
        self,
        workspace_id: WorkspaceId,
        account_id: EntityId,
        name: str,
        class_name: str,
        level: int,
    ) -> Character:
        with self._uow:
            if self._uow.workspaces.get(workspace_id) is None:
                raise NotFoundError("Workspace não encontrado")
            if self._uow.accounts.get(account_id, workspace_id) is None:
                raise NotFoundError("Conta não encontrada no workspace")
            if self._uow.characters.exists_by_account_and_name(workspace_id, account_id, name):
                raise ConflictError("Já existe personagem ativo com esse nome nesta conta")
            character = Character(
                id=self._ids.new(),
                workspace_id=workspace_id,
                account_id=account_id,
                name=name,
                class_name=class_name,
                level=level,
                sort_order=self._uow.characters.next_sort_order(workspace_id, account_id),
                created_at=self._clock.now(),
            )
            self._uow.characters.save(character)
            activities = [
                activity
                for activity in self._uow.activities.list_active(workspace_id)
                if activity.category is ActivityCategory.DUNGEON
            ]
            for sort_order, activity in enumerate(activities, start=1):
                self._uow.character_activities.save(
                    CharacterActivity(
                        self._ids.new(),
                        workspace_id,
                        character.id,
                        activity.id,
                        activity.default_target_amount,
                        sort_order,
                    )
                )
            return character

    def update_account(
        self, workspace_id: WorkspaceId, account_id: EntityId, name: str, server_name: str
    ) -> GameAccount:
        with self._uow:
            account = self._uow.accounts.get(account_id, workspace_id)
            if account is None:
                raise NotFoundError("Conta não encontrada no workspace")
            if (
                account.name.casefold() != name.strip().casefold()
                and self._uow.accounts.exists_by_name(workspace_id, name)
            ):
                raise ConflictError("Já existe uma conta ativa com esse nome")
            updated = replace(account, name=name, server_name=server_name)
            self._uow.accounts.save(updated)
            return updated

    def update_character(
        self,
        workspace_id: WorkspaceId,
        character_id: EntityId,
        name: str,
        class_name: str,
        level: int,
    ) -> Character:
        with self._uow:
            character = self._uow.characters.get(character_id, workspace_id)
            if character is None:
                raise NotFoundError("Personagem não encontrado no workspace")
            if (
                character.name.casefold() != name.strip().casefold()
                and self._uow.characters.exists_by_account_and_name(
                    workspace_id, character.account_id, name
                )
            ):
                raise ConflictError("Já existe personagem ativo com esse nome nesta conta")
            updated = replace(character, name=name, class_name=class_name, level=level)
            self._uow.characters.save(updated)
            return updated

    def set_dungeon_active(
        self, workspace_id: WorkspaceId, activity_id: EntityId, enabled: bool
    ) -> None:
        with self._uow:
            activity = self._uow.activities.get(activity_id, workspace_id)
            if activity is None or activity.category is not ActivityCategory.DUNGEON:
                raise NotFoundError("Dungeon não encontrada")
            if activity.is_active == enabled:
                return
            self._uow.activities.save(replace(activity, is_active=enabled))
            if not enabled:
                return
            for character in self._uow.characters.list_active(workspace_id):
                configured = self._uow.character_activities.list_for_character(
                    workspace_id, character.id
                )
                if any(item.activity_id == activity.id for item in configured):
                    continue
                self._uow.character_activities.save(
                    CharacterActivity(
                        self._ids.new(),
                        workspace_id,
                        character.id,
                        activity.id,
                        activity.default_target_amount,
                        len(configured) + 1,
                    )
                )


class ActivityCompletionService:
    def __init__(self, uow: FarmUnitOfWork, ids: IdGenerator, clock: Clock) -> None:
        self._uow = uow
        self._ids = ids
        self._clock = clock

    def complete_activity(
        self,
        workspace_id: WorkspaceId,
        character_activity_id: EntityId,
        activity_date: date,
    ) -> CompletionResult:
        with self._uow:
            return self._complete_activity(workspace_id, character_activity_id, activity_date)

    def reopen_activity(
        self,
        workspace_id: WorkspaceId,
        character_activity_id: EntityId,
        activity_date: date,
    ) -> DailyActivityEntry:
        with self._uow:
            return self._reopen_activity(workspace_id, character_activity_id, activity_date)

    def save_character_day(
        self,
        workspace_id: WorkspaceId,
        character_id: EntityId,
        activity_date: date,
        completed_activity_ids: tuple[EntityId, ...],
    ) -> CharacterDaySaveResult:
        with self._uow:
            if self._uow.characters.get(character_id, workspace_id) is None:
                raise NotFoundError("Personagem não encontrado")
            configurations = self._uow.character_activities.list_for_character(
                workspace_id, character_id
            )
            active_configurations = []
            for configuration in configurations:
                activity = self._uow.activities.get(configuration.activity_id, workspace_id)
                if configuration.is_active and activity is not None and activity.is_active:
                    active_configurations.append(configuration)
            allowed_ids = {configuration.id for configuration in active_configurations}
            requested_ids = set(completed_activity_ids)
            if not requested_ids.issubset(allowed_ids):
                raise ValidationError("A seleção contém dungeon que não pertence ao personagem")

            total_gold = 0
            total_bags = 0
            for configuration in active_configurations:
                entry = self._uow.daily_entries.find_by_activity_and_date(
                    workspace_id, configuration.id, activity_date
                )
                if configuration.id in requested_ids:
                    result = self._complete_activity(workspace_id, configuration.id, activity_date)
                    total_gold += result.total_reward.gold.amount
                    total_bags += result.total_reward.pve_bags
                elif entry is not None and entry.status is ActivityStatus.COMPLETED:
                    self._reopen_activity(workspace_id, configuration.id, activity_date)
            return CharacterDaySaveResult(len(requested_ids), total_gold, total_bags)

    def _complete_activity(
        self,
        workspace_id: WorkspaceId,
        character_activity_id: EntityId,
        activity_date: date,
    ) -> CompletionResult:
        character_activity = self._uow.character_activities.get(character_activity_id, workspace_id)
        if character_activity is None or not character_activity.is_active:
            raise NotFoundError("Atividade do personagem não encontrada ou inativa")
        activity = self._uow.activities.get(character_activity.activity_id, workspace_id)
        if activity is None or not activity.is_active:
            raise NotFoundError("Atividade não encontrada ou inativa")
        rule = self._uow.rules.find_effective(workspace_id, activity.id, activity_date)
        if rule is None:
            raise NotFoundError("Não existe regra vigente para esta atividade")
        if character_activity.target_amount > rule.max_completions:
            raise ValidationError("Meta do personagem excede o máximo permitido pela regra")

        entry = self._uow.daily_entries.find_by_activity_and_date(
            workspace_id, character_activity_id, activity_date
        )
        if entry is not None and entry.status is ActivityStatus.COMPLETED:
            existing = tuple(self._uow.completions.list_for_entry(workspace_id, entry.id))
            return CompletionResult(entry, existing, reward_total(existing), True)

        now = self._clock.now()
        pending_entry = entry or DailyActivityEntry(
            id=self._ids.new(),
            workspace_id=workspace_id,
            character_activity_id=character_activity_id,
            activity_date=activity_date,
            status=ActivityStatus.PENDING,
            progress_amount=0,
            created_at=now,
        )
        completed_entry = pending_entry.complete(now, character_activity.target_amount)
        per_run = rule.per_completion_reward()
        completions = tuple(
            ActivityCompletion(
                id=self._ids.new(),
                workspace_id=workspace_id,
                daily_activity_entry_id=completed_entry.id,
                rule_version_id=rule.id,
                sequence_no=sequence,
                completed_at=now,
                reward_snapshot=per_run,
            )
            for sequence in range(1, character_activity.target_amount + 1)
        )
        self._uow.daily_entries.save(completed_entry)
        self._uow.completions.save_many(list(completions))
        return CompletionResult(completed_entry, completions, reward_total(completions), False)

    def _reopen_activity(
        self,
        workspace_id: WorkspaceId,
        character_activity_id: EntityId,
        activity_date: date,
    ) -> DailyActivityEntry:
        entry = self._uow.daily_entries.find_by_activity_and_date(
            workspace_id, character_activity_id, activity_date
        )
        if entry is None:
            raise NotFoundError("Registro diário não encontrado")
        reopened = entry.reopen()
        self._uow.daily_entries.save(reopened)
        self._uow.completions.delete_for_entry(workspace_id, entry.id)
        return reopened


DASHBOARD_MODULE_DEFAULTS: dict[str, bool] = {
    "daily-summary": True,
    "recent-drops": True,
    "monthly-performance": True,
}


class DashboardLayoutService:
    def __init__(self, uow: FarmUnitOfWork, ids: IdGenerator, clock: Clock) -> None:
        self._uow = uow
        self._ids = ids
        self._clock = clock

    def get_visibility(self, workspace_id: WorkspaceId) -> dict[str, bool]:
        with self._uow:
            saved = self._uow.dashboard_layouts.get_enabled(workspace_id)
        return {**DASHBOARD_MODULE_DEFAULTS, **saved}

    def set_visibility(
        self, workspace_id: WorkspaceId, module_key: str, enabled: bool
    ) -> dict[str, bool]:
        if module_key not in DASHBOARD_MODULE_DEFAULTS:
            raise ValidationError("Módulo do dashboard não reconhecido")
        with self._uow:
            self._uow.dashboard_layouts.save_enabled(
                workspace_id,
                module_key,
                enabled,
                self._ids.new(),
                self._ids.new(),
                self._clock.now(),
            )
        return self.get_visibility(workspace_id)

    def reset(self, workspace_id: WorkspaceId) -> dict[str, bool]:
        with self._uow:
            self._uow.dashboard_layouts.reset(workspace_id)
        return dict(DASHBOARD_MODULE_DEFAULTS)
