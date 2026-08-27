from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from gf_dashboard.domain.value_objects import Gold


@dataclass(frozen=True, slots=True)
class TodayEstimate:
    activity_date: date
    selected_dungeons: int
    estimated_gold: Gold
    estimated_pve_bags: int
    estimated_pve_bag_market_value: Gold | None
    pve_bag_unit_value: Gold | None = None


@dataclass(frozen=True, slots=True)
class TodayCharacter:
    id: str
    name: str
    class_name: str
    account_name: str
    completed_dungeons: int
    selected_dungeons: int


@dataclass(frozen=True, slots=True)
class ManagementCharacter:
    id: str
    account_id: str
    name: str
    class_name: str
    level: int
    sort_order: int


@dataclass(frozen=True, slots=True)
class ManagementAccount:
    id: str
    name: str
    server_name: str
    characters: tuple[ManagementCharacter, ...]


@dataclass(frozen=True, slots=True)
class RoutineDungeon:
    id: str
    name: str
    enabled: bool
    target_amount: int


@dataclass(frozen=True, slots=True)
class ManagementOverview:
    workspace_name: str
    accounts: tuple[ManagementAccount, ...]
    dungeons: tuple[RoutineDungeon, ...]


@dataclass(frozen=True, slots=True)
class CharacterDayDungeon:
    character_activity_id: str
    activity_id: str
    name: str
    completed: bool
    target_amount: int
    gold: Gold
    pve_bags: int


@dataclass(frozen=True, slots=True)
class CharacterDay:
    character_id: str
    character_name: str
    class_name: str
    account_name: str
    activity_date: date
    dungeons: tuple[CharacterDayDungeon, ...]


@dataclass(frozen=True, slots=True)
class RecentDrop:
    item_name: str
    quantity: int
    obtained_at: datetime


@dataclass(frozen=True, slots=True)
class MonthlyGoldPoint:
    activity_date: date
    gold: Gold


@dataclass(frozen=True, slots=True)
class TodayActivityOverview:
    runs_completed: int
    tower_completed: int
    tower_total: int
    recent_drops: tuple[RecentDrop, ...]
    monthly_gold: tuple[MonthlyGoldPoint, ...]
    monthly_gold_total: Gold


@dataclass(frozen=True, slots=True)
class HistoryDaySummary:
    activity_date: date
    runs_completed: int
    characters_completed: int
    characters_total: int
    gold_earned: Gold
    pve_bags_earned: int
    tower_completed: int
    tower_total: int
    drops_count: int


@dataclass(frozen=True, slots=True)
class HistoryDungeonEntry:
    activity_id: str
    name: str
    completed: bool
    target_amount: int
    gold: Gold
    pve_bags: int


@dataclass(frozen=True, slots=True)
class HistoryCharacterDetail:
    character_id: str
    name: str
    class_name: str
    account_name: str
    completed_dungeons: int
    selected_dungeons: int
    dungeons: tuple[HistoryDungeonEntry, ...]


@dataclass(frozen=True, slots=True)
class HistoryTowerSession:
    session_id: str
    completed: bool
    cost_gold: Gold
    participant_names: tuple[str, ...]
    drops: tuple[RecentDrop, ...]


@dataclass(frozen=True, slots=True)
class HistoryDayDetail:
    activity_date: date
    runs_completed: int
    gold_earned: Gold
    pve_bags_earned: int
    characters: tuple[HistoryCharacterDetail, ...]
    tower_sessions: tuple[HistoryTowerSession, ...]
    drops: tuple[RecentDrop, ...]
