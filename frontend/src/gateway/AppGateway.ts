export interface PingResult {
  message: string;
  runtime: "desktop";
  bridgeVersion: number;
}

export type TodayResult =
  | { state: "empty"; activityDate: string }
  | {
      state: "ready";
      activityDate: string;
      selectedDungeons: number;
      estimatedGold: number;
      estimatedPveBags: number;
      estimatedPveBagMarketValue: number | null;
      pveBagUnitValueGold?: number | null;
    };

export type TodayCharactersResult =
  | { state: "empty"; characters: [] }
  | {
      state: "ready";
      characters: Array<{
        id: string;
        name: string;
        className: string;
        accountName: string;
        completedDungeons: number;
        selectedDungeons: number;
        dailyMissionCompleted?: boolean;
        vipExpiresAt?: string | null;
      }>;
    };

export type TodayActivityResult = {
  state: "empty" | "ready";
  runsCompleted: number;
  towerCompleted: number;
  towerTotal: number;
  recentDrops: Array<{
    itemName: string;
    quantity: number;
    obtainedAt: string;
  }>;
  monthlyGold: Array<{
    activityDate: string;
    gold: number;
  }>;
  monthlyGoldTotal: number;
  earnedGoldToday?: number;
  pveBagsEarnedToday?: number;
  todaySalesMinor?: number;
};

export type ManagementOverviewResult =
  | { state: "empty" }
  | {
      state: "ready";
      workspaceName: string;
      accounts: Array<{
        id: string;
        name: string;
        serverName: string;
        characters: Array<{
          id: string;
          accountId: string;
          name: string;
          className: string;
          level: number;
          sortOrder: number;
        }>;
      }>;
      dungeons: Array<{
        id: string;
        name: string;
        enabled: boolean;
        targetAmount: number;
      }>;
    };

export interface CharacterDayResult {
  characterId: string;
  characterName: string;
  className: string;
  accountName: string;
  activityDate: string;
  dungeons: Array<{
    characterActivityId: string;
    activityId: string;
    name: string;
    completed: boolean;
    targetAmount: number;
    gold: number;
    pveBags: number;
  }>;
}

export interface TowerRegistrationInput {
  guildName: string;
  participantIds: string[];
  drops: Array<{ itemName: string; quantity: number; estimatedUnitValue: number | null }>;
}

export type DashboardModuleKey = "daily-summary" | "recent-drops" | "monthly-performance";
export interface DashboardLayoutResult {
  schemaVersion: 1;
  visibility: Record<DashboardModuleKey, boolean>;
}

export interface HistoryFilterInput {
  startDate?: string;
  endDate?: string;
  accountId?: string;
  characterId?: string;
}

export interface HistoryDaySummary {
  activityDate: string;
  runsCompleted: number;
  charactersCompleted: number;
  charactersTotal: number;
  goldEarned: number;
  pveBagsEarned: number;
  towerCompleted: number;
  towerTotal: number;
  dropsCount: number;
  routineDurationSeconds?: number;
}

export type HistoryOverviewResult =
  | { state: "empty"; days: [] }
  | { state: "ready"; days: HistoryDaySummary[] };

export interface HistoryDayDetailResult {
  state: "ready";
  activityDate: string;
  runsCompleted: number;
  goldEarned: number;
  pveBagsEarned: number;
  routineDurationSeconds?: number;
  characters: Array<{
    id: string;
    name: string;
    className: string;
    accountName: string;
    completedDungeons: number;
    selectedDungeons: number;
    dungeons: Array<{
      activityId: string;
      name: string;
      completed: boolean;
      targetAmount: number;
      gold: number;
      pveBags: number;
    }>;
  }>;
  towerSessions: Array<{
    sessionId: string;
    completed: boolean;
    costGold: number;
    participantNames: string[];
    drops: Array<{
      itemName: string;
      quantity: number;
      obtainedAt: string;
    }>;
  }>;
  drops: Array<{
    itemName: string;
    quantity: number;
    obtainedAt: string;
  }>;
}

export interface MonthlySalesHistoryPoint {
  monthKey: string;
  monthLabel: string;
  salesAmountMinor: number;
  salesCount: number;
  isPartial: boolean;
}

export interface ReportKpis {
  monthlySalesMinor: number;
  salesChangePercent: number | null;
  previousSalesMinor?: number;
  salesChangeStatus?: "valid" | "no_baseline" | "no_activity";
  monthlyFarmGold: number;
  farmGoldChangePercent: number | null;
  previousFarmGold?: number;
  farmGoldChangeStatus?: "valid" | "no_baseline" | "no_activity";
  allTimeFarmGold: number;
  dailyAverageGold: number;
  monthlyPveBagsEarned: number;
  pveBagsEarnedChangePercent: number | null;
  previousPveBagsEarned?: number;
  pveBagsEarnedChangeStatus?: "valid" | "no_baseline" | "no_activity";
  isPartialMonth?: boolean;
  comparisonPeriodDays?: number;
}

export interface DailyEvolutionPoint {
  day: number;
  activityDate: string;
  gold: number;
  runs: number;
}

export interface MonthlyComparison {
  previousMonthName: string;
  previousMonthGold: number;
  currentMonthName: string;
  currentMonthGold: number;
  growthPercent: number | null;
  growthStatus?: "valid" | "no_baseline" | "no_activity";
  isPartial?: boolean;
  previousPeriodLabel?: string;
  currentPeriodLabel?: string;
}

export interface CumulativeMonthPoint {
  monthLabel: string;
  monthKey: string;
  cumulativeGold: number;
}

export interface FinancialSummary {
  salesAmountMinor: number;
  itemsSoldCount: number;
  goldConvertedTotal: number;
  averageTicketMinor: number;
  expensesGold: number;
  vipExpensesGold: number;
  towerExpensesGold: number;
  manualExpensesGold: number;
}

export type ExpenseCategory = "upgrade" | "consumable" | "service" | "other";
export interface ExpenseRegistrationInput {
  category: ExpenseCategory;
  amountGold: number;
  occurredOn: string;
  description?: string;
}

export interface ExpenseHistoryRow {
  id: string;
  category: ExpenseCategory;
  amountGold: number;
  occurredAt: string;
  description: string | null;
  createdAt: string;
}

export interface WorkRoutineResult {
  id: string;
  status: "running" | "paused" | "completed";
  startedAt: string;
  pausedAt: string | null;
  finishedAt?: string;
  elapsedSeconds: number;
}

export interface RecentSaleRow {
  id: string;
  itemName: string;
  quantity: number;
  amountMinor: number;
  currency: string;
  soldAt: string;
}

export interface RecentMovement {
  id: string;
  kind: string;
  title: string;
  detail: string | null;
  occurredAt: string;
  goldAmount: number | null;
  pveBags: number | null;
  amountMinor: number | null;
}

export interface WorkRoutineHistory {
  monthSeconds: number;
  weekSeconds: number;
  previousWeekSeconds: number;
  monthSessionCount: number;
  activeDaysInMonth: number;
  recentSessions: Array<{
    id: string;
    startedAt: string;
    finishedAt: string;
    elapsedSeconds: number;
  }>;
}

export interface MonthlyTarget {
  targetMonth?: string;
  targetGold: number;
  currentGold: number;
  currentPveBags: number;
  pveBagUnitValueGold: number | null;
  currentTotalValueGold: number;
  percentage: number;
  remainingGold: number;
  daysRemaining: number;
}

export interface TopCharacterRow {
  rank: number;
  characterId: string;
  characterName: string;
  className: string;
  goldEarned: number;
}

export type ReportsOverviewResult =
  | { state: "empty" }
  | {
      state: "ready";
      kpis: ReportKpis;
      dailyEvolution: DailyEvolutionPoint[];
      monthlyComparison: MonthlyComparison;
      cumulativeHistory: CumulativeMonthPoint[];
      financialSummary: FinancialSummary;
      recentSales: RecentSaleRow[];
      recentMovements: RecentMovement[];
      workRoutineHistory: WorkRoutineHistory;
      monthlyTarget: MonthlyTarget;
      topCharacters: TopCharacterRow[];
      monthlySalesHistory?: MonthlySalesHistoryPoint[];
    };

export interface CurrencyRateResult {
  baseCurrency: string;
  quoteCurrency: string;
  rateMicros: number;
  rateFormatted: string;
  source: string;
  date: string;
}

export interface SaleRegistrationInput {
  saleType: "gold" | "pve_bag" | "item";
  itemDescription: string;
  quantity: number;
  originalAmountMinor: number;
  currency: string;
  exchangeRateMicros: number;
  exchangeRateSource: string;
  idempotencyKey: string;
  soldAt: string;
}

export interface SaleRegistrationResult {
  saleId: string;
  realAmountMinor: number;
  originalAmountMinor: number;
  currency: string;
  exchangeRateMicros: number;
  exchangeRateSource: string;
  soldAt: string;
  alreadyRecorded: boolean;
}

export interface AppGateway {
  ping(): Promise<PingResult>;
  getToday(): Promise<TodayResult>;
  getTodayCharacters(): Promise<TodayCharactersResult>;
  getTodayActivity(): Promise<TodayActivityResult>;
  getCharacterDay(characterId: string, activityDate?: string): Promise<CharacterDayResult>;
  saveCharacterDay(characterId: string, completedActivityIds: string[], activityDate: string): Promise<{ completedDungeons: number; gold: number; pveBags: number }>;
  setCharacterDailyMission(characterId: string, completed: boolean): Promise<{ completed: boolean }>;
  saveCharacterVip(characterId: string, paidGold: number, remainingDays: number, remainingHours: number): Promise<{ expiresAt: string; paidGold: number }>;
  getManagementOverview(): Promise<ManagementOverviewResult>;
  createAccount(name: string, serverName: string): Promise<{ id: string; name: string }>;
  createCharacter(accountId: string, name: string, className: string, level: number): Promise<{ id: string; name: string }>;
  updateAccount(accountId: string, name: string, serverName: string): Promise<{ id: string; name: string }>;
  updateCharacter(characterId: string, name: string, className: string, level: number): Promise<{ id: string; name: string }>;
  setDungeonActive(activityId: string, enabled: boolean): Promise<{ updated: boolean }>;
  registerCompletedTower(input: TowerRegistrationInput): Promise<{ sessionId: string; participantCount: number; dropCount: number; entryCostGold: number }>;
  getDashboardLayout(): Promise<DashboardLayoutResult>;
  setDashboardModuleVisible(moduleKey: DashboardModuleKey, enabled: boolean): Promise<DashboardLayoutResult>;
  resetDashboardLayout(): Promise<DashboardLayoutResult>;
  createWorkspace(name: string): Promise<{ name: string }>;
  getHistoryOverview(filter?: HistoryFilterInput): Promise<HistoryOverviewResult>;
  getHistoryDayDetail(activityDate: string, filter?: HistoryFilterInput): Promise<HistoryDayDetailResult>;
  recordPveBagQuote(unitValueGold: number, source?: string): Promise<{ quoteId: string; unitValueGold: number; observedAt: string }>;
  getReportsOverview(referenceDate?: string): Promise<ReportsOverviewResult>;
  setMonthlyTarget(targetMonth: string, targetGold: number): Promise<{ targetMonth: string; targetGold: number }>;
  recordExpense(input: ExpenseRegistrationInput): Promise<{ transactionId: string }>;
  getExpenseHistory(): Promise<{ expenses: ExpenseHistoryRow[] }>;
  updateExpense(transactionId: string, input: ExpenseRegistrationInput): Promise<{ transactionId: string }>;
  voidExpense(transactionId: string): Promise<{ voided: boolean }>;
  getWorkRoutine(): Promise<{ routine: WorkRoutineResult | null }>;
  startWorkRoutine(): Promise<WorkRoutineResult>;
  pauseWorkRoutine(): Promise<WorkRoutineResult>;
  resumeWorkRoutine(): Promise<WorkRoutineResult>;
  stopWorkRoutine(): Promise<WorkRoutineResult>;
  getCurrencyRate(baseCurrency: string, quoteCurrency?: string, date?: string): Promise<CurrencyRateResult>;
  recordSale(input: SaleRegistrationInput): Promise<SaleRegistrationResult>;
  getAutostart(): Promise<{ enabled: boolean }>;
  setAutostart(enabled: boolean): Promise<{ enabled: boolean }>;
}

export class GatewayError extends Error {
  constructor(
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "GatewayError";
  }
}
