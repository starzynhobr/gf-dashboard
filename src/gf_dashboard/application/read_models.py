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
    earned_gold_today: Gold
    today_sales_minor: int


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


@dataclass(frozen=True, slots=True)
class ReportKpis:
    monthly_sales_minor: int
    sales_change_percent: int
    monthly_farm_gold: Gold
    farm_gold_change_percent: int
    all_time_farm_gold: Gold
    daily_average_gold: Gold
    monthly_pve_bags_sold: int
    pve_bags_change_percent: int


@dataclass(frozen=True, slots=True)
class DailyEvolutionPoint:
    day: int
    activity_date: date
    gold: Gold
    runs: int


@dataclass(frozen=True, slots=True)
class MonthlyComparison:
    previous_month_name: str
    previous_month_gold: Gold
    current_month_name: str
    current_month_gold: Gold
    growth_percent: int


@dataclass(frozen=True, slots=True)
class CumulativeMonthPoint:
    month_label: str
    month_key: str
    cumulative_gold: Gold


@dataclass(frozen=True, slots=True)
class FinancialSummary:
    sales_amount_minor: int
    items_sold_count: int
    gold_converted_total: Gold
    average_ticket_minor: int


@dataclass(frozen=True, slots=True)
class RecentSaleRow:
    id: str
    item_name: str
    quantity: int
    amount_minor: int
    currency: str
    sold_at: datetime


@dataclass(frozen=True, slots=True)
class MonthlyTarget:
    target_gold: Gold
    current_gold: Gold
    percentage: int
    remaining_gold: Gold
    days_remaining: int


@dataclass(frozen=True, slots=True)
class TopCharacterRow:
    rank: int
    character_id: str
    character_name: str
    class_name: str
    gold_earned: Gold


@dataclass(frozen=True, slots=True)
class ReportsOverview:
    kpis: ReportKpis
    daily_evolution: tuple[DailyEvolutionPoint, ...]
    monthly_comparison: MonthlyComparison
    cumulative_history: tuple[CumulativeMonthPoint, ...]
    financial_summary: FinancialSummary
    recent_sales: tuple[RecentSaleRow, ...]
    monthly_target: MonthlyTarget
    top_characters: tuple[TopCharacterRow, ...]
