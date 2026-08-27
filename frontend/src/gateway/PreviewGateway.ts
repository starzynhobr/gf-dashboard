import type { AppGateway, CharacterDayResult, DashboardLayoutResult, DashboardModuleKey, ManagementOverviewResult, PingResult, TodayActivityResult, TodayCharactersResult, TodayResult, TowerRegistrationInput } from "./AppGateway";

const dungeonNames = [
  "Palácio de Proteção do Selo", "Câmara Secreta do Ritual das Trevas", "Destruidor do Vazio",
  "Igreja Subterrânea de Carso", "Santuário Maldito", "Dimensão Distorcida", "Primata",
  "Kaslow Ardente", "Ilha Condenada",
];

const previewCharacters: TodayCharactersResult = {
  state: "ready",
  characters: [
    ["Star01", "Ranger", 9], ["Star02", "Mago", 9], ["Star03", "Sacerdote", 6],
    ["Star04", "Guerreiro", 0], ["Star05", "Assassino", 9], ["Star06", "Bárbaro", 8],
    ["Star07", "Batedor", 5], ["Star08", "Místico", 9], ["Star09", "Alquimista", 0],
    ["Star10", "Atirador", 0],
  ].map(([name, className, completedDungeons], index) => ({
    id: `preview-character-${index + 1}`,
    name: String(name),
    className: String(className),
    accountName: index < 5 ? "Conta 1" : "Conta 2",
    completedDungeons: Number(completedDungeons),
    selectedDungeons: 9,
  })),
};

export class PreviewGateway implements AppGateway {
  private visibility: DashboardLayoutResult["visibility"] = { "daily-summary": true, "recent-drops": true, "monthly-performance": true };
  ping(): Promise<PingResult> {
    return Promise.resolve({ message: "pong", runtime: "desktop", bridgeVersion: 1 });
  }

  getToday(): Promise<TodayResult> {
    return Promise.resolve({
      state: "ready",
      activityDate: "2026-08-26",
      selectedDungeons: 90,
      estimatedGold: 469750,
      estimatedPveBags: 450,
      estimatedPveBagMarketValue: 450000,
      pveBagUnitValueGold: 1000,
    });
  }

  getTodayCharacters(): Promise<TodayCharactersResult> {
    return Promise.resolve(previewCharacters);
  }

  getTodayActivity(): Promise<TodayActivityResult> {
    return Promise.resolve({
      state: "ready",
      runsCompleted: 275,
      towerCompleted: 0,
      towerTotal: 0,
      recentDrops: [
        { itemName: "Pedra da Alma Brilhante", quantity: 1, obtainedAt: "2026-08-26T14:32:00" },
        { itemName: "Pergaminho da Experiência", quantity: 1, obtainedAt: "2026-08-26T13:10:00" },
        { itemName: "Cristal de Geleia", quantity: 2, obtainedAt: "2026-08-26T11:45:00" },
        { itemName: "Emblema de Honra", quantity: 1, obtainedAt: "2026-08-26T10:22:00" },
        { itemName: "Pedra Rúnica (Nível 2)", quantity: 1, obtainedAt: "2026-08-26T09:15:00" },
      ],
      monthlyGold: [
        42000, 81000, 126000, 94000, 153000, 111000, 174000, 132000,
        191000, 148000, 238000, 184000, 226000,
      ].map((gold, index) => ({
        activityDate: `2026-08-${String(index * 2 + 1).padStart(2, "0")}`,
        gold,
      })),
      monthlyGoldTotal: 1900000,
    });
  }

  getCharacterDay(characterId: string): Promise<CharacterDayResult> {
    const character = previewCharacters.characters.find((item) => item.id === characterId) ?? previewCharacters.characters[0];
    return Promise.resolve({
      characterId: character.id,
      characterName: character.name,
      className: character.className,
      accountName: character.accountName,
      activityDate: "2026-08-26",
      dungeons: dungeonNames.map((name, index) => ({
        characterActivityId: `preview-ca-${index + 1}`,
        activityId: `preview-dungeon-${index + 1}`,
        name,
        completed: index < character.completedDungeons,
        targetAmount: 5,
        gold: 7000 - index * 350,
        pveBags: 5,
      })),
    });
  }

  saveCharacterDay(_characterId: string, completedActivityIds: string[]): Promise<{ completedDungeons: number; gold: number; pveBags: number }> {
    return Promise.resolve({ completedDungeons: completedActivityIds.length, gold: 0, pveBags: completedActivityIds.length * 5 });
  }

  getManagementOverview(): Promise<ManagementOverviewResult> {
    const characters = previewCharacters.characters;
    return Promise.resolve({
      state: "ready",
      workspaceName: "Fixture visual",
      accounts: [0, 1].map((accountIndex) => ({
        id: `preview-account-${accountIndex + 1}`,
        name: `Conta ${accountIndex + 1}`,
        serverName: "Valhalla",
        characters: characters.slice(accountIndex * 5, accountIndex * 5 + 5).map((character, index) => ({
          id: character.id, accountId: `preview-account-${accountIndex + 1}`, name: character.name,
          className: character.className, level: 91, sortOrder: index + 1,
        })),
      })),
      dungeons: dungeonNames.map((name, index) => ({ id: `preview-dungeon-${index + 1}`, name, enabled: true, targetAmount: 5 })),
    });
  }

  createAccount(name: string): Promise<{ id: string; name: string }> {
    return Promise.resolve({ id: "preview-new-account", name });
  }

  createCharacter(_accountId: string, name: string): Promise<{ id: string; name: string }> {
    return Promise.resolve({ id: "preview-new-character", name });
  }

  updateAccount(accountId: string, name: string): Promise<{ id: string; name: string }> {
    return Promise.resolve({ id: accountId, name });
  }

  updateCharacter(characterId: string, name: string): Promise<{ id: string; name: string }> {
    return Promise.resolve({ id: characterId, name });
  }

  setDungeonActive(): Promise<{ updated: boolean }> {
    return Promise.resolve({ updated: true });
  }

  registerCompletedTower(input: TowerRegistrationInput): Promise<{ sessionId: string; participantCount: number; dropCount: number; entryCostGold: number }> {
    return Promise.resolve({ sessionId: "preview-tower", participantCount: input.participantIds.length, dropCount: input.drops.length, entryCostGold: 25_000 });
  }

  getDashboardLayout(): Promise<DashboardLayoutResult> {
    return Promise.resolve({ schemaVersion: 1, visibility: { ...this.visibility } });
  }

  setDashboardModuleVisible(moduleKey: DashboardModuleKey, enabled: boolean): Promise<DashboardLayoutResult> {
    this.visibility[moduleKey] = enabled;
    return this.getDashboardLayout();
  }

  resetDashboardLayout(): Promise<DashboardLayoutResult> {
    this.visibility = { "daily-summary": true, "recent-drops": true, "monthly-performance": true };
    return this.getDashboardLayout();
  }

  createWorkspace(name: string): Promise<{ name: string }> {
    return Promise.resolve({ name });
  }

  getHistoryOverview(): Promise<import("./AppGateway").HistoryOverviewResult> {
    return Promise.resolve({
      state: "ready",
      days: [
        {
          activityDate: "2026-08-26",
          runsCompleted: 275,
          charactersCompleted: 6,
          charactersTotal: 10,
          goldEarned: 310000,
          pveBagsEarned: 250,
          towerCompleted: 1,
          towerTotal: 1,
          dropsCount: 5,
        },
        {
          activityDate: "2026-08-25",
          runsCompleted: 250,
          charactersCompleted: 5,
          charactersTotal: 10,
          goldEarned: 290000,
          pveBagsEarned: 230,
          towerCompleted: 0,
          towerTotal: 0,
          dropsCount: 2,
        },
      ],
    });
  }

  getHistoryDayDetail(activityDate: string): Promise<import("./AppGateway").HistoryDayDetailResult> {
    return Promise.resolve({
      state: "ready",
      activityDate,
      runsCompleted: 275,
      goldEarned: 310000,
      pveBagsEarned: 250,
      characters: previewCharacters.characters.map((character) => ({
        id: character.id,
        name: character.name,
        className: character.className,
        accountName: character.accountName,
        completedDungeons: character.completedDungeons,
        selectedDungeons: character.selectedDungeons,
        dungeons: dungeonNames.map((name, index) => ({
          activityId: `preview-dungeon-${index + 1}`,
          name,
          completed: index < character.completedDungeons,
          targetAmount: 5,
          gold: 7000 - index * 350,
          pveBags: 5,
        })),
      })),
      towerSessions: [
        {
          sessionId: "preview-tower-1",
          completed: true,
          costGold: 25000,
          participantNames: ["Star01", "Star02"],
          drops: [
            { itemName: "Pedra da Alma Brilhante", quantity: 1, obtainedAt: `${activityDate}T20:45:00` },
          ],
        },
      ],
      drops: [
        { itemName: "Pedra da Alma Brilhante", quantity: 1, obtainedAt: `${activityDate}T20:45:00` },
        { itemName: "Pergaminho da Experiência", quantity: 1, obtainedAt: `${activityDate}T13:10:00` },
      ],
    });
  }

  recordPveBagQuote(unitValueGold: number): Promise<{ quoteId: string; unitValueGold: number; observedAt: string }> {
    return Promise.resolve({
      quoteId: "preview-quote-1",
      unitValueGold,
      observedAt: new Date().toISOString(),
    });
  }
}
