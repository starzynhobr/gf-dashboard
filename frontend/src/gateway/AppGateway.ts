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

export interface AppGateway {
  ping(): Promise<PingResult>;
  getToday(): Promise<TodayResult>;
  getTodayCharacters(): Promise<TodayCharactersResult>;
  getTodayActivity(): Promise<TodayActivityResult>;
  getCharacterDay(characterId: string): Promise<CharacterDayResult>;
  saveCharacterDay(characterId: string, completedActivityIds: string[]): Promise<{ completedDungeons: number; gold: number; pveBags: number }>;
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
