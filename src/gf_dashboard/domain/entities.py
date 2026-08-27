from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date, datetime, time

from gf_dashboard.domain.enums import (
    ActivityCategory,
    ActivityFrequency,
    ActivityStatus,
    MissionLimitType,
    MovementType,
    RuleStatus,
    SaleStatus,
    SessionStatus,
    SessionType,
    TransactionType,
)
from gf_dashboard.domain.errors import RuleNotConfirmedError, ValidationError
from gf_dashboard.domain.value_objects import (
    EntityId,
    Gold,
    Money,
    RewardSnapshot,
    WorkspaceId,
    require_utc,
)


def _required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} é obrigatório")
    return normalized


def _non_negative_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(f"{field_name} deve ser inteiro não negativo")
    return value


@dataclass(frozen=True, slots=True)
class Workspace:
    id: WorkspaceId
    name: str
    created_at: datetime
    mode: str = "local"

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "Nome do workspace"))
        object.__setattr__(self, "created_at", require_utc(self.created_at))
        object.__setattr__(self, "mode", _required_text(self.mode, "Modo do workspace"))


@dataclass(frozen=True, slots=True)
class LocalProfile:
    id: EntityId
    workspace_id: WorkspaceId
    display_name: str
    timezone: str
    locale: str
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "display_name", _required_text(self.display_name, "Nome de exibição")
        )
        object.__setattr__(self, "timezone", _required_text(self.timezone, "Timezone"))
        object.__setattr__(self, "locale", _required_text(self.locale, "Locale"))
        object.__setattr__(self, "created_at", require_utc(self.created_at))


@dataclass(frozen=True, slots=True)
class GameAccount:
    id: EntityId
    workspace_id: WorkspaceId
    name: str
    server_name: str
    created_at: datetime
    notes: str | None = None
    is_active: bool = True
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "Nome da conta"))
        object.__setattr__(self, "server_name", _required_text(self.server_name, "Servidor"))
        object.__setattr__(self, "created_at", require_utc(self.created_at))
        if self.deleted_at is not None:
            object.__setattr__(self, "deleted_at", require_utc(self.deleted_at))


@dataclass(frozen=True, slots=True)
class Character:
    id: EntityId
    workspace_id: WorkspaceId
    account_id: EntityId
    name: str
    class_name: str
    level: int
    sort_order: int
    created_at: datetime
    notes: str | None = None
    is_active: bool = True
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "Nome do personagem"))
        object.__setattr__(self, "class_name", _required_text(self.class_name, "Classe"))
        object.__setattr__(self, "level", _non_negative_int(self.level, "Nível"))
        object.__setattr__(self, "sort_order", _non_negative_int(self.sort_order, "Ordem"))
        object.__setattr__(self, "created_at", require_utc(self.created_at))
        if self.deleted_at is not None:
            object.__setattr__(self, "deleted_at", require_utc(self.deleted_at))


@dataclass(frozen=True, slots=True)
class Activity:
    id: EntityId
    workspace_id: WorkspaceId
    name: str
    category: ActivityCategory
    frequency: ActivityFrequency
    default_target_amount: int
    created_at: datetime
    is_active: bool = True
    is_special: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "Nome da atividade"))
        target = _non_negative_int(self.default_target_amount, "Meta padrão")
        if target == 0:
            raise ValidationError("Meta padrão deve ser maior que zero")
        object.__setattr__(self, "default_target_amount", target)
        object.__setattr__(self, "created_at", require_utc(self.created_at))


@dataclass(frozen=True, slots=True)
class CharacterActivity:
    id: EntityId
    workspace_id: WorkspaceId
    character_id: EntityId
    activity_id: EntityId
    target_amount: int
    sort_order: int
    is_active: bool = True

    def __post_init__(self) -> None:
        target = _non_negative_int(self.target_amount, "Meta da atividade")
        if target == 0:
            raise ValidationError("Meta da atividade deve ser maior que zero")
        object.__setattr__(self, "target_amount", target)
        object.__setattr__(self, "sort_order", _non_negative_int(self.sort_order, "Ordem"))


@dataclass(frozen=True, slots=True)
class MissionRewardRule:
    mission_key: str
    limit_type: MissionLimitType
    gold_per_completion: Gold
    pve_bags_per_completion: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "mission_key", _required_text(self.mission_key, "Chave da missão"))
        object.__setattr__(
            self,
            "pve_bags_per_completion",
            _non_negative_int(self.pve_bags_per_completion, "Sacos PvE por conclusão"),
        )

    @property
    def reward_per_completion(self) -> RewardSnapshot:
        return RewardSnapshot(self.gold_per_completion, self.pve_bags_per_completion)


@dataclass(frozen=True, slots=True)
class ActivityRuleVersion:
    id: EntityId
    workspace_id: WorkspaceId
    activity_id: EntityId
    effective_from: date
    effective_to: date | None
    max_completions: int
    target_amount: int
    status: RuleStatus
    rewards: tuple[MissionRewardRule, ...]
    created_at: datetime
    source: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValidationError("Fim da vigência não pode anteceder o início")
        max_completions = _non_negative_int(self.max_completions, "Máximo de conclusões")
        target_amount = _non_negative_int(self.target_amount, "Meta da regra")
        if max_completions == 0 or target_amount == 0:
            raise ValidationError("Regra deve permitir ao menos uma conclusão")
        if target_amount > max_completions:
            raise ValidationError("Meta não pode exceder o máximo de conclusões")
        if not self.rewards:
            raise ValidationError("Regra precisa ter ao menos uma recompensa")
        mission_keys = [reward.mission_key for reward in self.rewards]
        if len(mission_keys) != len(set(mission_keys)):
            raise ValidationError("Chaves de missão não podem se repetir na mesma regra")
        object.__setattr__(self, "max_completions", max_completions)
        object.__setattr__(self, "target_amount", target_amount)
        object.__setattr__(self, "created_at", require_utc(self.created_at))

    def applies_on(self, activity_date: date) -> bool:
        return activity_date >= self.effective_from and (
            self.effective_to is None or activity_date <= self.effective_to
        )

    def reward_for_runs(self, runs: int) -> RewardSnapshot:
        if self.status is not RuleStatus.CONFIRMED:
            raise RuleNotConfirmedError("Regra não confirmada não pode calcular recompensas")
        valid_runs = _non_negative_int(runs, "Quantidade de rodadas")
        if valid_runs == 0 or valid_runs > self.max_completions:
            raise ValidationError("Quantidade de rodadas fora do limite da regra")
        per_completion = RewardSnapshot(Gold(0), 0)
        for reward in self.rewards:
            per_completion = RewardSnapshot(
                per_completion.gold + reward.gold_per_completion,
                per_completion.pve_bags + reward.pve_bags_per_completion,
            )
        return per_completion.times(valid_runs)

    def per_completion_reward(self) -> RewardSnapshot:
        return self.reward_for_runs(1)


@dataclass(frozen=True, slots=True)
class ActivityCostRule:
    id: EntityId
    workspace_id: WorkspaceId
    rule_version_id: EntityId
    cost_type: str
    amount: Gold
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "cost_type", _required_text(self.cost_type, "Tipo de custo"))
        object.__setattr__(self, "created_at", require_utc(self.created_at))


@dataclass(frozen=True, slots=True)
class ActivityWindow:
    id: EntityId
    workspace_id: WorkspaceId
    rule_version_id: EntityId
    weekday: int
    opens_at_local: time
    duration_seconds: int
    timezone: str

    def __post_init__(self) -> None:
        weekday = _non_negative_int(self.weekday, "Dia da semana")
        if weekday > 6:
            raise ValidationError("Dia da semana deve estar entre 0 e 6")
        duration = _non_negative_int(self.duration_seconds, "Duração")
        if duration == 0:
            raise ValidationError("Duração deve ser maior que zero")
        object.__setattr__(self, "weekday", weekday)
        object.__setattr__(self, "duration_seconds", duration)
        object.__setattr__(self, "timezone", _required_text(self.timezone, "Timezone"))


@dataclass(frozen=True, slots=True)
class DailyActivityEntry:
    id: EntityId
    workspace_id: WorkspaceId
    character_activity_id: EntityId
    activity_date: date
    status: ActivityStatus
    progress_amount: int
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    skipped_at: datetime | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "progress_amount", _non_negative_int(self.progress_amount, "Progresso")
        )
        object.__setattr__(self, "created_at", require_utc(self.created_at))
        for field_name in ("started_at", "completed_at", "skipped_at"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, require_utc(value))
        if self.status is ActivityStatus.COMPLETED and self.completed_at is None:
            raise ValidationError("Atividade concluída exige horário de conclusão")
        if self.status is ActivityStatus.SKIPPED and self.skipped_at is None:
            raise ValidationError("Atividade ignorada exige horário de registro")

    def complete(self, completed_at: datetime, progress_amount: int) -> DailyActivityEntry:
        return replace(
            self,
            status=ActivityStatus.COMPLETED,
            progress_amount=_non_negative_int(progress_amount, "Progresso"),
            started_at=self.started_at or require_utc(completed_at),
            completed_at=require_utc(completed_at),
            skipped_at=None,
        )

    def reopen(self) -> DailyActivityEntry:
        return replace(
            self,
            status=ActivityStatus.PENDING,
            progress_amount=0,
            completed_at=None,
            skipped_at=None,
        )


@dataclass(frozen=True, slots=True)
class ActivityCompletion:
    id: EntityId
    workspace_id: WorkspaceId
    daily_activity_entry_id: EntityId
    rule_version_id: EntityId
    sequence_no: int
    completed_at: datetime
    reward_snapshot: RewardSnapshot

    def __post_init__(self) -> None:
        sequence = _non_negative_int(self.sequence_no, "Sequência")
        if sequence == 0:
            raise ValidationError("Sequência deve começar em 1")
        object.__setattr__(self, "sequence_no", sequence)
        object.__setattr__(self, "completed_at", require_utc(self.completed_at))


@dataclass(frozen=True, slots=True)
class Item:
    id: EntityId
    workspace_id: WorkspaceId
    name: str
    category: str
    created_at: datetime
    rarity: str | None = None
    is_active: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "Nome do item"))
        object.__setattr__(self, "category", _required_text(self.category, "Categoria do item"))
        object.__setattr__(self, "created_at", require_utc(self.created_at))


@dataclass(frozen=True, slots=True)
class FarmSession:
    id: EntityId
    workspace_id: WorkspaceId
    session_type: SessionType
    activity_date: date
    status: SessionStatus
    created_at: datetime
    primary_character_id: EntityId | None = None
    activity_id: EntityId | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at", require_utc(self.created_at))
        if self.started_at is not None:
            object.__setattr__(self, "started_at", require_utc(self.started_at))
        if self.finished_at is not None:
            object.__setattr__(self, "finished_at", require_utc(self.finished_at))
        if self.started_at and self.finished_at and self.finished_at < self.started_at:
            raise ValidationError("Fim da sessão não pode anteceder o início")


@dataclass(frozen=True, slots=True)
class TowerSessionDetails:
    farm_session_id: EntityId
    entry_cost: Gold
    completed: bool
    opened_at: datetime
    completed_at: datetime | None = None
    guild_name_snapshot: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "opened_at", require_utc(self.opened_at))
        if self.completed and self.completed_at is None:
            raise ValidationError("Torre concluída exige horário de conclusão")
        if self.completed_at is not None:
            object.__setattr__(self, "completed_at", require_utc(self.completed_at))


@dataclass(frozen=True, slots=True)
class FarmSessionParticipant:
    farm_session_id: EntityId
    character_id: EntityId
    role: str | None = None
    joined_at: datetime | None = None
    left_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.joined_at is not None:
            object.__setattr__(self, "joined_at", require_utc(self.joined_at))
        if self.left_at is not None:
            object.__setattr__(self, "left_at", require_utc(self.left_at))
        if self.joined_at and self.left_at and self.left_at < self.joined_at:
            raise ValidationError("Saída do participante não pode anteceder sua entrada")


@dataclass(frozen=True, slots=True)
class FarmSessionItem:
    id: EntityId
    workspace_id: WorkspaceId
    farm_session_id: EntityId
    item_id: EntityId
    quantity: int
    obtained_at: datetime
    estimated_unit_value: Gold | None = None

    def __post_init__(self) -> None:
        quantity = _non_negative_int(self.quantity, "Quantidade de item")
        if quantity == 0:
            raise ValidationError("Quantidade de item deve ser maior que zero")
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "obtained_at", require_utc(self.obtained_at))


@dataclass(frozen=True, slots=True)
class MarketPriceQuote:
    id: EntityId
    workspace_id: WorkspaceId
    item_id: EntityId
    unit_value_gold: Gold
    observed_at: datetime
    source: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "observed_at", require_utc(self.observed_at))


@dataclass(frozen=True, slots=True)
class GoldExchangeQuote:
    id: EntityId
    workspace_id: WorkspaceId
    gold_amount: Gold
    money: Money
    observed_at: datetime

    def __post_init__(self) -> None:
        if self.gold_amount.amount == 0:
            raise ValidationError("Cotação precisa cobrir ao menos 1 gold")
        object.__setattr__(self, "observed_at", require_utc(self.observed_at))


@dataclass(frozen=True, slots=True)
class InventoryMovement:
    id: EntityId
    workspace_id: WorkspaceId
    item_id: EntityId
    movement_type: MovementType
    quantity_delta: int
    occurred_at: datetime
    character_id: EntityId | None = None
    farm_session_id: EntityId | None = None
    unit_value_snapshot: Gold | None = None

    def __post_init__(self) -> None:
        if isinstance(self.quantity_delta, bool) or not isinstance(self.quantity_delta, int):
            raise ValidationError("Movimento de inventário deve usar quantidade inteira")
        if self.quantity_delta == 0:
            raise ValidationError("Movimento de inventário não pode ser zero")
        object.__setattr__(self, "occurred_at", require_utc(self.occurred_at))


@dataclass(frozen=True, slots=True)
class Sale:
    id: EntityId
    workspace_id: WorkspaceId
    status: SaleStatus
    gold_quantity: Gold
    money: Money
    created_at: datetime
    sold_at: datetime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at", require_utc(self.created_at))
        if self.status is SaleStatus.COMPLETED and self.sold_at is None:
            raise ValidationError("Venda concluída exige data de venda")
        if self.sold_at is not None:
            object.__setattr__(self, "sold_at", require_utc(self.sold_at))


@dataclass(frozen=True, slots=True)
class Transaction:
    id: EntityId
    workspace_id: WorkspaceId
    transaction_type: TransactionType
    occurred_at: datetime
    gold_amount: Gold | None = None
    money: Money | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        if self.gold_amount is None and self.money is None:
            raise ValidationError("Transação deve ter valor em gold ou dinheiro")
        object.__setattr__(self, "occurred_at", require_utc(self.occurred_at))


def reward_total(completions: Iterable[ActivityCompletion]) -> RewardSnapshot:
    total = RewardSnapshot(Gold(0), 0)
    for completion in completions:
        total = RewardSnapshot(
            total.gold + completion.reward_snapshot.gold,
            total.pve_bags + completion.reward_snapshot.pve_bags,
        )
    return total
