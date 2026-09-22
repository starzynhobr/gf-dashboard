import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AppGateway } from "../gateway/AppGateway";
import { App } from "./App";
import { millisecondsUntilNextLocalMidnight } from "./dailyRefresh";

function createGateway(overrides: Partial<AppGateway> = {}): AppGateway {
  return {
    ping: async () => ({ message: "pong", runtime: "desktop", bridgeVersion: 1 }),
    getToday: async () => ({ state: "empty", activityDate: "2026-08-26" }),
    getTodayCharacters: async () => ({ state: "empty", characters: [] }),
    getTodayActivity: async () => ({ state: "empty", runsCompleted: 0, towerCompleted: 0, towerTotal: 0, recentDrops: [], monthlyGold: [], monthlyGoldTotal: 0 }),
    getCharacterDay: async () => ({ characterId: "character-1", characterName: "Star01", className: "Ranger", accountName: "Conta", activityDate: "2026-08-26", dungeons: [] }),
    saveCharacterDay: async (_characterId, completedActivityIds, activityDate) => {
      void activityDate;
      return { completedDungeons: completedActivityIds.length, gold: 0, pveBags: 0 };
    },
    setCharacterDailyMission: async (_characterId, completed) => ({ completed }),
    saveCharacterVip: async () => ({ expiresAt: "2026-09-27T12:00:00+00:00", paidGold: 100000 }),
    getManagementOverview: async () => ({ state: "ready", workspaceName: "Farm", accounts: [], dungeons: [] }),
    createAccount: async (name) => ({ id: "account-1", name }),
    createCharacter: async (_accountId, name) => ({ id: "character-1", name }),
    updateAccount: async (accountId, name) => ({ id: accountId, name }),
    updateCharacter: async (characterId, name) => ({ id: characterId, name }),
    setDungeonActive: async () => ({ updated: true }),
    registerCompletedTower: async (input) => ({ sessionId: "tower-1", participantCount: input.participantIds.length, dropCount: input.drops.length, entryCostGold: 25_000 }),
    getDashboardLayout: async () => ({ schemaVersion: 1, visibility: { "daily-summary": true, "recent-drops": true, "monthly-performance": true } }),
    setDashboardModuleVisible: async (moduleKey, enabled) => ({ schemaVersion: 1, visibility: { "daily-summary": true, "recent-drops": true, "monthly-performance": true, [moduleKey]: enabled } }),
    resetDashboardLayout: async () => ({ schemaVersion: 1, visibility: { "daily-summary": true, "recent-drops": true, "monthly-performance": true } }),
    createWorkspace: async (name) => ({ name }),
    getHistoryOverview: async () => ({ state: "empty", days: [] }),
    getHistoryDayDetail: async (activityDate) => ({
      state: "ready",
      activityDate,
      runsCompleted: 0,
      goldEarned: 0,
      pveBagsEarned: 0,
      characters: [],
      towerSessions: [],
      drops: [],
    }),
    recordPveBagQuote: async (unitValueGold) => ({ quoteId: "quote-1", unitValueGold, observedAt: "2026-08-26T20:00:00" }),
    getReportsOverview: async () => ({ state: "empty" }),
    setMonthlyTarget: async (targetMonth, targetGold) => ({ targetMonth, targetGold }),
    recordExpense: async () => ({ transactionId: "expense-1" }),
    getExpenseHistory: async () => ({ expenses: [] }),
    updateExpense: async () => ({ transactionId: "expense-2" }),
    voidExpense: async () => ({ voided: true }),
    getWorkRoutine: async () => ({ routine: null }),
    startWorkRoutine: async () => ({ id: "routine-1", status: "running", startedAt: "2026-08-26T12:00:00Z", pausedAt: null, elapsedSeconds: 0 }),
    pauseWorkRoutine: async () => ({ id: "routine-1", status: "paused", startedAt: "2026-08-26T12:00:00Z", pausedAt: "2026-08-26T12:01:00Z", elapsedSeconds: 60 }),
    resumeWorkRoutine: async () => ({ id: "routine-1", status: "running", startedAt: "2026-08-26T12:02:00Z", pausedAt: null, elapsedSeconds: 60 }),
    stopWorkRoutine: async () => ({ id: "routine-1", status: "completed", startedAt: "2026-08-26T12:00:00Z", pausedAt: null, finishedAt: "2026-08-26T13:00:00Z", elapsedSeconds: 3600 }),
    getCurrencyRate: async (baseCurrency) => ({
      baseCurrency,
      quoteCurrency: "BRL",
      rateMicros: baseCurrency === "EUR" ? 6_000_000 : 5_430_000,
      rateFormatted: baseCurrency === "EUR" ? "6,00" : "5,43",
      source: "test",
      date: "2026-08-27",
    }),
    recordSale: async (input) => ({
      saleId: "sale-1",
      realAmountMinor: Math.round((input.originalAmountMinor * input.exchangeRateMicros) / 1_000_000),
      originalAmountMinor: input.originalAmountMinor,
      currency: input.currency,
      exchangeRateMicros: input.exchangeRateMicros,
      exchangeRateSource: input.exchangeRateSource,
      soldAt: input.soldAt,
      alreadyRecorded: false,
    }),
    getAutostart: async () => ({ enabled: false }),
    setAutostart: async (enabled: boolean) => ({ enabled }),
    ...overrides,
  };
}

describe("App", () => {
  afterEach(() => {
    cleanup();
    localStorage.clear();
    vi.useRealTimers();
  });

  it("calculates the next local midnight without using a calendar-day interval", () => {
    expect(millisecondsUntilNextLocalMidnight(new Date(2026, 7, 28, 23, 59, 59, 900))).toBe(125);
  });

  it("shows that the Python bridge is ready after a successful ping", async () => {
    const gateway = createGateway();

    render(<App gateway={gateway} />);

    expect(await screen.findByText("Online")).toBeInTheDocument();
  });

  it("refreshes the Home when the app regains focus", async () => {
    const getToday = vi.fn(async () => ({ state: "empty" as const, activityDate: "2026-08-29" }));
    const gateway = createGateway({ getToday });

    render(<App gateway={gateway} />);
    await screen.findByText("29 de agosto de 2026");
    expect(getToday).toHaveBeenCalledTimes(1);
    await new Promise((resolve) => setTimeout(resolve, 0));

    window.dispatchEvent(new Event("focus"));

    await waitFor(() => expect(getToday).toHaveBeenCalledTimes(2));
  });

  it("refreshes the Home immediately after local midnight", async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 7, 28, 23, 59, 59, 900));
    const getToday = vi
      .fn()
      .mockResolvedValueOnce({ state: "empty" as const, activityDate: "2026-08-28" })
      .mockResolvedValueOnce({ state: "empty" as const, activityDate: "2026-08-29" });

    render(<App gateway={createGateway({ getToday })} />);
    await vi.advanceTimersByTimeAsync(0);
    expect(getToday).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(125);
    expect(getToday).toHaveBeenCalledTimes(2);
  });

  it("shows a recoverable status when the bridge is unavailable", async () => {
    const gateway = createGateway({
      ping: async () => Promise.reject(new Error("Bridge indisponível")),
    });

    render(<App gateway={gateway} />);

    expect(await screen.findByText("Bridge indisponível")).toBeInTheDocument();
  });

  it("shows the separate predicted dungeon gold and toggles on hover to include bag sales", async () => {
    const gateway = createGateway({
      getToday: async () => ({
        state: "ready", activityDate: "2026-08-26", selectedDungeons: 90,
        estimatedGold: 469750, estimatedPveBags: 450, estimatedPveBagMarketValue: 450000,
      }),
    });
    render(<App gateway={gateway} />);
    const cardTitle = await screen.findByText("Ouro estimado hoje");
    expect(cardTitle).toBeInTheDocument();
    expect(screen.getAllByText("469.750")).toHaveLength(2);

    // Hover over the gold card panel to see the combined estimate with bag sales
    const goldCard = cardTitle.closest(".stat-card");
    expect(goldCard).not.toBeNull();
    if (goldCard) {
      fireEvent.mouseEnter(goldCard);
      expect(screen.getByText("Ouro estimado c/ venda de sacos")).toBeInTheDocument();
      expect(screen.getByText("919.750")).toBeInTheDocument();

      fireEvent.mouseLeave(goldCard);
      expect(screen.getByText("Ouro estimado hoje")).toBeInTheDocument();
      expect(screen.getAllByText("469.750")).toHaveLength(2);
    }
  });

  it("renders recent drops and actual monthly gold from the activity read model", async () => {
    const gateway = createGateway({
      getTodayActivity: async () => ({
        state: "ready", runsCompleted: 5, towerCompleted: 1, towerTotal: 1,
        recentDrops: [{ itemName: "Drop raro", quantity: 2, obtainedAt: "2026-08-26T14:32:00" }],
        monthlyGold: [{ activityDate: "2026-08-26", gold: 7000 }], monthlyGoldTotal: 7000,
      }),
    });
    render(<App gateway={gateway} />);
    expect(await screen.findByText("2× Drop raro")).toBeInTheDocument();
    expect(screen.getByText("7.000")).toBeInTheDocument();
    expect(screen.getAllByText("1 / 1")).toHaveLength(2);
  });

  it("opens the management page and creates an account", async () => {
    const createAccount = vi.fn(async (name: string) => ({ id: "account-1", name }));
    const gateway = createGateway({ createAccount });
    render(<App gateway={gateway} />);

    fireEvent.click(await screen.findByRole("button", { name: "Personagens" }));
    expect(await screen.findByText("Contas e personagens")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Nome da conta"), { target: { value: "Conta Principal" } });
    fireEvent.click(screen.getByRole("button", { name: "Cadastrar conta" }));

    await waitFor(() => expect(createAccount).toHaveBeenCalledWith("Conta Principal", "Valhalla"));
  });

  it("opens a character summary with dungeons pre-marked and saves the selected dungeon cycle directly", async () => {
    const saveCharacterDay = vi.fn(async (_characterId: string, completedActivityIds: string[]) => ({ completedDungeons: completedActivityIds.length, gold: 7000, pveBags: 5 }));
    const gateway = createGateway({
      getTodayCharacters: async () => ({ state: "ready", characters: [{ id: "character-1", name: "Star01", className: "Ranger", accountName: "Conta", completedDungeons: 0, selectedDungeons: 1 }] }),
      getCharacterDay: async () => ({ characterId: "character-1", characterName: "Star01", className: "Ranger", accountName: "Conta", activityDate: "2026-08-26", dungeons: [{ characterActivityId: "ca-1", activityId: "dungeon-1", name: "Palácio de Proteção do Selo", completed: false, targetAmount: 5, gold: 7000, pveBags: 5 }] }),
      saveCharacterDay,
    });
    render(<App gateway={gateway} />);

    fireEvent.click(await screen.findByText("Star01"));
    expect(await screen.findByText("1 de 1 dungeons concluídas")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Salvar resumo" }));

    await waitFor(() => expect(saveCharacterDay).toHaveBeenCalledWith("character-1", ["ca-1"], "2026-08-26"));
  });

  it("allows unchecking a pre-marked dungeon or clearing all before saving", async () => {
    const saveCharacterDay = vi.fn(async (_characterId: string, completedActivityIds: string[]) => ({ completedDungeons: completedActivityIds.length, gold: 0, pveBags: 0 }));
    const gateway = createGateway({
      getTodayCharacters: async () => ({ state: "ready", characters: [{ id: "character-1", name: "Star01", className: "Ranger", accountName: "Conta", completedDungeons: 0, selectedDungeons: 1 }] }),
      getCharacterDay: async () => ({ characterId: "character-1", characterName: "Star01", className: "Ranger", accountName: "Conta", activityDate: "2026-08-26", dungeons: [{ characterActivityId: "ca-1", activityId: "dungeon-1", name: "Palácio de Proteção do Selo", completed: false, targetAmount: 5, gold: 7000, pveBags: 5 }] }),
      saveCharacterDay,
    });
    render(<App gateway={gateway} />);

    fireEvent.click(await screen.findByText("Star01"));
    expect(await screen.findByText("1 de 1 dungeons concluídas")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Limpar" }));
    expect(screen.getByText("0 de 1 dungeons concluídas")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Salvar resumo" }));

    await waitFor(() => expect(saveCharacterDay).toHaveBeenCalledWith("character-1", [], "2026-08-26"));
  });

  it("edits a registered account without rebuilding its characters", async () => {
    const updateAccount = vi.fn(async (accountId: string, name: string) => ({ id: accountId, name }));
    const gateway = createGateway({
      getManagementOverview: async () => ({ state: "ready", workspaceName: "Farm", dungeons: [], accounts: [{ id: "account-1", name: "DK", serverName: "Servidor Violet", characters: [{ id: "character-1", accountId: "account-1", name: "Sentry1", className: "Druida", level: 100, sortOrder: 1 }] }] }),
      updateAccount,
    });
    render(<App gateway={gateway} />);

    fireEvent.click(await screen.findByRole("button", { name: "Personagens" }));
    fireEvent.click(await screen.findByRole("button", { name: "Editar conta DK" }));
    fireEvent.change(screen.getByLabelText("Novo nome da conta"), { target: { value: "DK Principal" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));

    await waitFor(() => expect(updateAccount).toHaveBeenCalledWith("account-1", "DK Principal", "Servidor Violet"));
  });

  it("registers a completed Tower session with participants and drops", async () => {
    const registerCompletedTower = vi.fn(async () => ({ sessionId: "tower-1", participantCount: 1, dropCount: 1, entryCostGold: 25_000 }));
    const gateway = createGateway({
      getToday: async () => ({ state: "ready", activityDate: "2026-08-26", selectedDungeons: 9, estimatedGold: 7000, estimatedPveBags: 5, estimatedPveBagMarketValue: 5000 }),
      getTodayCharacters: async () => ({ state: "ready", characters: [{ id: "character-1", name: "Star01", className: "Ranger", accountName: "Conta", completedDungeons: 0, selectedDungeons: 9 }] }),
      registerCompletedTower,
    });
    render(<App gateway={gateway} />);

    fireEvent.click(await screen.findByRole("button", { name: "Registrar Torre" }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Star01/ }));
    fireEvent.change(screen.getByPlaceholderText("Ex.: Pedra rara"), { target: { value: "Drop raro" } });
    fireEvent.click(screen.getByRole("button", { name: "Registrar sessão" }));

    await waitFor(() => expect(registerCompletedTower).toHaveBeenCalledWith(expect.objectContaining({ participantIds: ["character-1"], drops: [expect.objectContaining({ itemName: "Drop raro" })] })));
  });

  it("persists module visibility from Settings", async () => {
    const setDashboardModuleVisible = vi.fn(async () => ({ schemaVersion: 1 as const, visibility: { "daily-summary": true, "recent-drops": true, "monthly-performance": false } }));
    const gateway = createGateway({ setDashboardModuleVisible });
    render(<App gateway={gateway} />);

    fireEvent.click(await screen.findByRole("button", { name: "Configurações" }));
    fireEvent.click(await screen.findByRole("switch", { name: "Ocultar Desempenho mensal" }));

    await waitFor(() => expect(setDashboardModuleVisible).toHaveBeenCalledWith("monthly-performance", false));
  });

  it("toggles global routine dungeon without full page reload", async () => {
    const setDungeonActive = vi.fn(async () => ({ updated: true }));
    const gateway = createGateway({
      getManagementOverview: async () => ({
        state: "ready", workspaceName: "Farm", accounts: [],
        dungeons: [{ id: "dungeon-primata", name: "Primata", category: "dungeon", targetAmount: 5, enabled: false, sortOrder: 1, goldMissionOne: 0, goldMissionTwo: 0, pveBags: 5 }],
      }),
      setDungeonActive,
    });
    render(<App gateway={gateway} />);

    fireEvent.click(await screen.findByRole("button", { name: "Personagens" }));
    const checkbox = await screen.findByRole("checkbox", { name: /Primata/ });
    expect(checkbox).not.toBeChecked();

    fireEvent.click(checkbox);
    await waitFor(() => expect(setDungeonActive).toHaveBeenCalledWith("dungeon-primata", true));
  });

  it("opens the history page and displays past days and detail breakdown", async () => {
    const getHistoryOverview = vi.fn(async () => ({
      state: "ready" as const,
      days: [
        {
          activityDate: "2026-08-26",
          runsCompleted: 25,
          charactersCompleted: 5,
          charactersTotal: 10,
          goldEarned: 35000,
          pveBagsEarned: 25,
          towerCompleted: 1,
          towerTotal: 1,
          dropsCount: 1,
        },
      ],
    }));

    const getHistoryDayDetail = vi.fn(async (activityDate: string) => ({
      state: "ready" as const,
      activityDate,
      runsCompleted: 25,
      goldEarned: 35000,
      pveBagsEarned: 25,
      characters: [
        {
          id: "character-1",
          name: "Star01",
          className: "Ranger",
          accountName: "Conta Principal",
          completedDungeons: 5,
          selectedDungeons: 5,
          dungeons: [
            {
              activityId: "dungeon-1",
              name: "Palácio de Proteção do Selo",
              completed: true,
              targetAmount: 5,
              gold: 7000,
              pveBags: 5,
            },
          ],
        },
      ],
      towerSessions: [],
      drops: [{ itemName: "Cristal Mágico", quantity: 2, obtainedAt: "2026-08-26T21:00:00" }],
    }));

    const gateway = createGateway({ getHistoryOverview, getHistoryDayDetail });
    render(<App gateway={gateway} />);

    fireEvent.click(await screen.findByRole("button", { name: "Histórico" }));
    expect(await screen.findByText("Histórico de farm")).toBeInTheDocument();
    expect(await screen.findByText("25 runs")).toBeInTheDocument();
    expect(await screen.findByText("Cristal Mágico")).toBeInTheDocument();
    expect(await screen.findByText("Todos os 1 personagens concluíram as atividades")).toBeInTheDocument();

    fireEvent.click(await screen.findByRole("button", { name: "Ver detalhes" }));
    expect(await screen.findByText("Star01")).toBeInTheDocument();
    expect(await screen.findByText("Palácio de Proteção do Selo")).toBeInTheDocument();
  });

  it("highlights incomplete character exceptions, period summary, and event filters in history", async () => {
    const getHistoryOverview = vi.fn(async () => ({
      state: "ready" as const,
      days: [
        {
          activityDate: "2026-08-26",
          runsCompleted: 15,
          charactersCompleted: 1,
          charactersTotal: 2,
          goldEarned: 21000,
          pveBagsEarned: 15,
          towerCompleted: 1,
          towerTotal: 1,
          dropsCount: 3,
          routineDurationSeconds: 23940,
        },
        {
          activityDate: "2026-08-25",
          runsCompleted: 25,
          charactersCompleted: 2,
          charactersTotal: 2,
          goldEarned: 35000,
          pveBagsEarned: 25,
          towerCompleted: 0,
          towerTotal: 0,
          dropsCount: 0,
          routineDurationSeconds: 0,
        },
      ],
    }));

    const getHistoryDayDetail = vi.fn(async (activityDate: string) => {
      if (activityDate === "2026-08-26") {
        return {
          state: "ready" as const,
          activityDate,
          runsCompleted: 15,
          goldEarned: 21000,
          pveBagsEarned: 15,
          routineDurationSeconds: 23940,
          characters: [
            {
              id: "char-complete",
              name: "StarDone",
              className: "Ranger",
              accountName: "Conta 1",
              completedDungeons: 5,
              selectedDungeons: 5,
              dungeons: [
                { activityId: "d-1", name: "Dungeon 1", completed: true, targetAmount: 5, gold: 7000, pveBags: 5 },
              ],
            },
            {
              id: "char-incomplete",
              name: "StarzyinhoBR",
              className: "Guerreiro",
              accountName: "Conta 2",
              completedDungeons: 3,
              selectedDungeons: 5,
              dungeons: [
                { activityId: "d-1", name: "Dungeon 1", completed: true, targetAmount: 5, gold: 7000, pveBags: 5 },
                { activityId: "d-2", name: "Igreja Subterrânea de Carso", completed: false, targetAmount: 5, gold: 7000, pveBags: 5 },
                { activityId: "d-3", name: "Palácio de Proteção do Selo", completed: false, targetAmount: 5, gold: 7000, pveBags: 5 },
              ],
            },
          ],
          towerSessions: [
            {
              sessionId: "tower-1",
              completed: true,
              costGold: 25000,
              participantNames: ["StarDone"],
              drops: [{ itemName: "Pedra Alma", quantity: 1, obtainedAt: "2026-08-26T20:00:00" }],
            },
          ],
          drops: [{ itemName: "Pedra Alma", quantity: 1, obtainedAt: "2026-08-26T20:00:00" }],
        };
      }
      return {
        state: "ready" as const,
        activityDate,
        runsCompleted: 25,
        goldEarned: 35000,
        pveBagsEarned: 25,
        routineDurationSeconds: 0,
        characters: [],
        towerSessions: [],
        drops: [],
      };
    });

    const gateway = createGateway({ getHistoryOverview, getHistoryDayDetail });
    render(<App gateway={gateway} />);

    fireEvent.click(await screen.findByRole("button", { name: "Histórico" }));
    expect(await screen.findByText("Histórico de farm")).toBeInTheDocument();

    // Period summary strip is rendered with correct aggregated stats
    expect(await screen.findByText("Dias registrados")).toBeInTheDocument();
    expect(screen.getByText("Dias registrados").nextElementSibling).toHaveTextContent("2 dias");
    expect(screen.getByText("Runs totais").nextElementSibling).toHaveTextContent("40");
    expect(screen.getByText("Gold acumulado").nextElementSibling).toHaveTextContent("56k gold");
    expect(screen.getByText("Tempo em rotina").nextElementSibling).toHaveTextContent("6h 39min");

    // Days list cards and Hero status pill
    expect((await screen.findAllByText("Parcial")).length).toBeGreaterThanOrEqual(1);
    expect(await screen.findByText("6h39 de rotina")).toBeInTheDocument();

    // Exception alert box appears automatically for incomplete characters
    expect(await screen.findByText("Atenção: Atividades incompletas")).toBeInTheDocument();
    expect(await screen.findByText("StarzyinhoBR")).toBeInTheDocument();
    expect(await screen.findByText("• Igreja Subterrânea de Carso")).toBeInTheDocument();
    expect(await screen.findByText("• Palácio de Proteção do Selo")).toBeInTheDocument();

    // Event filter buttons with counts
    expect(await screen.findByRole("button", { name: /^Incompletos/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Torre/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Drops/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Rotinas/ })).toBeInTheDocument();

    // Filter by Incompletos
    fireEvent.click(screen.getByRole("button", { name: /^Incompletos/ }));
    expect(await screen.findByText("Filtro: Incompletos")).toBeInTheDocument();
  });

  it("allows correcting a past day in history by opening character dungeons dialog and saving", async () => {
    const saveCharacterDay = vi.fn(async (_characterId: string, completedActivityIds: string[]) => ({
      completedDungeons: completedActivityIds.length,
      gold: 7000,
      pveBags: 5,
    }));

    const getHistoryOverview = vi.fn(async () => ({
      state: "ready" as const,
      days: [
        {
          activityDate: "2026-08-25",
          runsCompleted: 0,
          charactersCompleted: 0,
          charactersTotal: 1,
          goldEarned: 0,
          pveBagsEarned: 0,
          towerCompleted: 0,
          towerTotal: 0,
          dropsCount: 0,
        },
      ],
    }));

    const getHistoryDayDetail = vi.fn(async (activityDate: string) => ({
      state: "ready" as const,
      activityDate,
      runsCompleted: 0,
      goldEarned: 0,
      pveBagsEarned: 0,
      characters: [
        {
          id: "character-1",
          name: "Sentry2",
          className: "Druida",
          accountName: "mightmetroid",
          completedDungeons: 0,
          selectedDungeons: 1,
          dungeons: [
            {
              activityId: "dungeon-1",
              name: "Câmara Secreta do Ritual das Trevas",
              completed: false,
              targetAmount: 5,
              gold: 7000,
              pveBags: 5,
            },
          ],
        },
      ],
      towerSessions: [],
      drops: [],
    }));

    const getCharacterDay = vi.fn(async (_characterId: string, activityDate?: string) => ({
      characterId: "character-1",
      characterName: "Sentry2",
      className: "Druida",
      accountName: "mightmetroid",
      activityDate: activityDate ?? "2026-08-25",
      dungeons: [
        {
          characterActivityId: "ca-1",
          activityId: "dungeon-1",
          name: "Câmara Secreta do Ritual das Trevas",
          completed: false,
          targetAmount: 5,
          gold: 7000,
          pveBags: 5,
        },
      ],
    }));

    const gateway = createGateway({
      getHistoryOverview,
      getHistoryDayDetail,
      getCharacterDay,
      saveCharacterDay,
    });
    render(<App gateway={gateway} />);

    fireEvent.click(await screen.findByRole("button", { name: "Histórico" }));
    expect(await screen.findByText("Atenção: Atividades incompletas")).toBeInTheDocument();
    expect(await screen.findByText("Sentry2")).toBeInTheDocument();

    // Click on "Marcar" button in the exception card
    fireEvent.click(screen.getByRole("button", { name: "Marcar" }));

    // CharacterDayDialog opens with the character's details and date
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("1 de 1 dungeons concluídas")).toBeInTheDocument();

    // Save
    fireEvent.click(screen.getByRole("button", { name: "Salvar resumo" }));

    await waitFor(() =>
      expect(saveCharacterDay).toHaveBeenCalledWith("character-1", ["ca-1"], "2026-08-25"),
    );
  });

  it("allows completing all incomplete characters in history via bulk complete button", async () => {
    const saveCharacterDay = vi.fn(async (_characterId: string, completedActivityIds: string[]) => ({
      completedDungeons: completedActivityIds.length,
      gold: 7000,
      pveBags: 5,
    }));

    const getHistoryOverview = vi.fn(async () => ({
      state: "ready" as const,
      days: [
        {
          activityDate: "2026-08-25",
          runsCompleted: 0,
          charactersCompleted: 0,
          charactersTotal: 1,
          goldEarned: 0,
          pveBagsEarned: 0,
          towerCompleted: 0,
          towerTotal: 0,
          dropsCount: 0,
        },
      ],
    }));

    const getHistoryDayDetail = vi.fn(async (activityDate: string) => ({
      state: "ready" as const,
      activityDate,
      runsCompleted: 0,
      goldEarned: 0,
      pveBagsEarned: 0,
      characters: [
        {
          id: "character-1",
          name: "Sentry2",
          className: "Druida",
          accountName: "mightmetroid",
          completedDungeons: 0,
          selectedDungeons: 1,
          dungeons: [
            {
              activityId: "dungeon-1",
              name: "Câmara Secreta do Ritual das Trevas",
              completed: false,
              targetAmount: 5,
              gold: 7000,
              pveBags: 5,
            },
          ],
        },
      ],
      towerSessions: [],
      drops: [],
    }));

    const getCharacterDay = vi.fn(async (_characterId: string, activityDate?: string) => ({
      characterId: "character-1",
      characterName: "Sentry2",
      className: "Druida",
      accountName: "mightmetroid",
      activityDate: activityDate ?? "2026-08-25",
      dungeons: [
        {
          characterActivityId: "ca-1",
          activityId: "dungeon-1",
          name: "Câmara Secreta do Ritual das Trevas",
          completed: false,
          targetAmount: 5,
          gold: 7000,
          pveBags: 5,
        },
      ],
    }));

    vi.spyOn(window, "confirm").mockReturnValue(true);

    const gateway = createGateway({
      getHistoryOverview,
      getHistoryDayDetail,
      getCharacterDay,
      saveCharacterDay,
    });
    render(<App gateway={gateway} />);

    fireEvent.click(await screen.findByRole("button", { name: "Histórico" }));
    expect(await screen.findByText("Atenção: Atividades incompletas")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Concluir todos pendentes" }));

    await waitFor(() =>
      expect(saveCharacterDay).toHaveBeenCalledWith("character-1", ["ca-1"], "2026-08-25"),
    );
  });

  it("opens the pve bag price dialog and records a new quote", async () => {
    const recordPveBagQuote = vi.fn(async (unitValueGold: number) => ({
      quoteId: "quote-1",
      unitValueGold,
      observedAt: "2026-08-26T20:00:00",
    }));
    const gateway = createGateway({
      getToday: async () => ({
        state: "ready",
        activityDate: "2026-08-26",
        selectedDungeons: 9,
        estimatedGold: 7000,
        estimatedPveBags: 5,
        estimatedPveBagMarketValue: 5000,
        pveBagUnitValueGold: 1000,
      }),
      recordPveBagQuote,
    });
    render(<App gateway={gateway} />);

    fireEvent.click(await screen.findByRole("button", { name: "Preço Saco PvE" }));
    expect(await screen.findByText("Preço do Saco PvE")).toBeInTheDocument();
    expect(screen.getByText(/1\.000 Gold/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Novo preço unitário em Gold"), { target: { value: "1350" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar cotação" }));

    await waitFor(() => expect(recordPveBagQuote).toHaveBeenCalledWith(1350));
  });

  it("opens the reports page and displays KPIs, charts, financial summary and ranking", async () => {
    const getReportsOverview = vi.fn(async () => ({
      state: "ready" as const,
      kpis: {
        monthlySalesMinor: 84200,
        previousSalesMinor: 71350,
        salesChangePercent: 18,
        salesChangeStatus: "valid" as const,
        monthlyFarmGold: 18420000,
        previousFarmGold: 16460000,
        farmGoldChangePercent: 12,
        farmGoldChangeStatus: "valid" as const,
        allTimeFarmGold: 126850000,
        dailyAverageGold: 614000,
        monthlyPveBagsEarned: 250,
        previousPveBagsEarned: 200,
        pveBagsEarnedChangePercent: 25,
        pveBagsEarnedChangeStatus: "valid" as const,
        isPartialMonth: true,
        comparisonPeriodDays: 27,
      },
      dailyEvolution: [
        { day: 26, activityDate: "2026-08-26", gold: 7000, runs: 5 },
      ],
      monthlyComparison: {
        previousMonthName: "Mês passado",
        previousMonthGold: 16460000,
        currentMonthName: "Mês atual",
        currentMonthGold: 18420000,
        growthPercent: 12,
        growthStatus: "valid" as const,
        isPartial: true,
        previousPeriodLabel: "1 - 27 jul",
        currentPeriodLabel: "1 - 27 ago",
      },
      monthlySalesHistory: [
        {
          monthKey: "2026-07",
          monthLabel: "jul/26",
          salesAmountMinor: 65000,
          salesCount: 8,
          isPartial: false,
        },
        {
          monthKey: "2026-08",
          monthLabel: "ago/26",
          salesAmountMinor: 84200,
          salesCount: 12,
          isPartial: true,
        },
      ],
      cumulativeHistory: [
        { monthLabel: "ago/26", monthKey: "2026-08", cumulativeGold: 126850000 },
      ],
      financialSummary: {
        salesAmountMinor: 84200,
        itemsSoldCount: 94,
        goldConvertedTotal: 18420000,
        averageTicketMinor: 896,
        expensesGold: 0,
        vipExpensesGold: 0,
        towerExpensesGold: 0,
        manualExpensesGold: 0,
      },
      recentSales: [
        { id: "sale-1", itemName: "Saco de Cristal (PvE)", quantity: 10, amountMinor: 3500, currency: "BRL", soldAt: "2026-08-27T14:32:00" },
      ],
      recentMovements: [
        { id: "movement-1", kind: "dungeon", title: "Dimensão Distorcida", detail: "Sentry1", occurredAt: "2026-08-27T14:32:00", goldAmount: 7000, pveBags: 5, amountMinor: null },
      ],
      workRoutineHistory: {
        monthSeconds: 14_400,
        weekSeconds: 10_800,
        previousWeekSeconds: 7_200,
        monthSessionCount: 3,
        activeDaysInMonth: 2,
        recentSessions: [
          { id: "routine-1", startedAt: "2026-08-27T18:00:00Z", finishedAt: "2026-08-27T20:00:00Z", elapsedSeconds: 7_200 },
        ],
      },
      monthlyTarget: {
        targetMonth: "2026-08",
        targetGold: 25000000,
        currentGold: 18420000,
        currentPveBags: 250,
        pveBagUnitValueGold: 1000,
        currentTotalValueGold: 18670000,
        percentage: 74,
        remainingGold: 6580000,
        daysRemaining: 5,
      },
      topCharacters: [
        { rank: 1, characterId: "char-1", characterName: "Sentry1", className: "Druida", goldEarned: 4920000 },
      ],
    }));

    const gateway = createGateway({ getReportsOverview });
    render(<App gateway={gateway} />);

    const reportButtons = await screen.findAllByRole("button", { name: "Relatórios" });
    fireEvent.click(reportButtons[0]);
    expect(await screen.findByTestId("reports-page")).toBeInTheDocument();
    expect(screen.getByText("Vendido no mês")).toBeInTheDocument();
    expect(screen.getByText("Farm do mês")).toBeInTheDocument();
    expect(screen.getByText("Sacos PvE ganhos")).toBeInTheDocument();
    expect(screen.getAllByText("18.420.000").length).toBeGreaterThan(0);
    expect(screen.getByText("+18% vs mesmo período")).toBeInTheDocument();
    expect(screen.getByText("Comparativo de farm")).toBeInTheDocument();
    expect(screen.getByText("1 - 27 ago vs 1 - 27 jul")).toBeInTheDocument();
    expect(screen.getByText("Últimas movimentações")).toBeInTheDocument();
    expect(screen.getByText("Dimensão Distorcida")).toBeInTheDocument();
    expect(screen.getByText("Resumo financeiro")).toBeInTheDocument();
    expect(screen.getAllByText("Sentry1").length).toBeGreaterThan(0);

    // Default sales view is "Por mês"
    expect(screen.getAllByText("Vendas em R$").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Faturamento e histórico mensal")).toBeInTheDocument();
    expect(screen.getByText("parcial")).toBeInTheDocument();

    // Toggle to "Recentes" view to inspect recent individual sales
    const recentSalesBtn = screen.getByRole("button", { name: "Recentes" });
    fireEvent.click(recentSalesBtn);
    expect(screen.getByText("Saco de Cristal (PvE)")).toBeInTheDocument();
  });

  it("displays transparent 'Sem base comparável' when previous period had no movement", async () => {
    const getReportsOverview = vi.fn(async () => ({
      state: "ready" as const,
      kpis: {
        monthlySalesMinor: 5000,
        previousSalesMinor: 0,
        salesChangePercent: null,
        salesChangeStatus: "no_baseline" as const,
        monthlyFarmGold: 1000000,
        previousFarmGold: 0,
        farmGoldChangePercent: null,
        farmGoldChangeStatus: "no_baseline" as const,
        allTimeFarmGold: 1000000,
        dailyAverageGold: 100000,
        monthlyPveBagsEarned: 15,
        previousPveBagsEarned: 0,
        pveBagsEarnedChangePercent: null,
        pveBagsEarnedChangeStatus: "no_baseline" as const,
        isPartialMonth: true,
        comparisonPeriodDays: 5,
      },
      dailyEvolution: [],
      monthlyComparison: {
        previousMonthName: "Mês passado",
        previousMonthGold: 0,
        currentMonthName: "Mês atual",
        currentMonthGold: 1000000,
        growthPercent: null,
        growthStatus: "no_baseline" as const,
        isPartial: true,
        previousPeriodLabel: "1 - 5 jul",
        currentPeriodLabel: "1 - 5 ago",
      },
      monthlySalesHistory: [],
      cumulativeHistory: [],
      financialSummary: {
        salesAmountMinor: 5000,
        itemsSoldCount: 1,
        goldConvertedTotal: 1000000,
        averageTicketMinor: 5000,
        expensesGold: 0,
        vipExpensesGold: 0,
        towerExpensesGold: 0,
        manualExpensesGold: 0,
      },
      recentSales: [],
      recentMovements: [],
      workRoutineHistory: {
        monthSeconds: 0,
        weekSeconds: 0,
        previousWeekSeconds: 0,
        monthSessionCount: 0,
        activeDaysInMonth: 0,
        recentSessions: [],
      },
      monthlyTarget: {
        targetMonth: "2026-08",
        targetGold: 10000000,
        currentGold: 1000000,
        currentPveBags: 15,
        pveBagUnitValueGold: 1000,
        currentTotalValueGold: 1015000,
        percentage: 10,
        remainingGold: 8985000,
        daysRemaining: 26,
      },
      topCharacters: [],
    }));

    const gateway = createGateway({ getReportsOverview });
    render(<App gateway={gateway} />);

    const reportButtons = await screen.findAllByRole("button", { name: "Relatórios" });
    fireEvent.click(reportButtons[0]);
    expect(await screen.findByTestId("reports-page")).toBeInTheDocument();

    const noBaselines = screen.getAllByText("Sem base comparável");
    // Should appear in KPIs and in monthly farm comparison
    expect(noBaselines.length).toBeGreaterThanOrEqual(2);
  });

  it("opens Nova Venda modal, converts USD to BRL and records a sale", async () => {
    const recordSale = vi.fn().mockResolvedValue({
      saleId: "sale-123",
      realAmountMinor: 13575,
      originalAmountMinor: 2500,
      currency: "USD",
      exchangeRateMicros: 5_430_000,
      soldAt: "2026-08-27T12:00:00",
    });

    const gateway = createGateway({
      getToday: async () => ({
        state: "ready",
        activityDate: "2026-08-27",
        selectedDungeons: 10,
        estimatedGold: 310000,
        estimatedPveBags: 250,
        estimatedPveBagMarketValue: 250000,
      }),
      getTodayActivity: async () => ({
        state: "ready",
        runsCompleted: 10,
        towerCompleted: 0,
        towerTotal: 0,
        recentDrops: [],
        monthlyGold: [],
        monthlyGoldTotal: 1000000,
        earnedGoldToday: 310000,
        pveBagsEarnedToday: 50,
        todaySalesMinor: 13575,
      }),
      recordSale,
    });

    render(<App gateway={gateway} />);

    expect(await screen.findByText("Ouro ganho")).toBeInTheDocument();
    expect(screen.getByText("Sacos PvE ganhos")).toBeInTheDocument();
    expect(screen.getByText("50")).toBeInTheDocument();
    expect(screen.getByText("Vendido hoje")).toBeInTheDocument();
    expect(screen.getByText("R$ 135,75")).toBeInTheDocument();

    const saleButton = await screen.findByRole("button", { name: /Nova Venda/i });
    fireEvent.click(saleButton);

    expect(await screen.findByRole("dialog", { name: "Nova venda" })).toBeInTheDocument();

    // Select USD
    const currencySelect = screen.getByLabelText("Moeda");
    fireEvent.change(currencySelect, { target: { value: "USD" } });

    // Fill amount 25,00
    const amountInput = screen.getByLabelText("Valor recebido");
    fireEvent.change(amountInput, { target: { value: "25,00" } });

    expect(await screen.findByText("R$ 5,43")).toBeInTheDocument();
    expect(await screen.findByText("R$ 135,75", { selector: ".converted-total-value" })).toBeInTheDocument();

    // Submit sale
    const submitButton = screen.getByRole("button", { name: "Registrar venda" });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(recordSale).toHaveBeenCalledTimes(1);
    });

    expect(recordSale).toHaveBeenCalledWith(
      expect.objectContaining({
        saleType: "gold",
        currency: "USD",
        originalAmountMinor: 2500,
        exchangeRateSource: "test",
      }),
    );
  });

  it("records a manual gold expense and controls a work routine from Home", async () => {
    const recordExpense = vi.fn(async () => ({ transactionId: "expense-1" }));
    const startWorkRoutine = vi.fn(async () => ({ id: "routine-1", status: "running" as const, startedAt: "2026-08-27T12:00:00Z", pausedAt: null, elapsedSeconds: 0 }));
    const gateway = createGateway({
      getToday: async () => ({ state: "ready", activityDate: "2026-08-27", selectedDungeons: 1, estimatedGold: 7_000, estimatedPveBags: 5, estimatedPveBagMarketValue: 5_000 }),
      recordExpense,
      startWorkRoutine,
    });
    render(<App gateway={gateway} />);

    fireEvent.click(await screen.findByRole("button", { name: "Nova despesa" }));
    fireEvent.change(screen.getByLabelText("Gold gasto"), { target: { value: "42000" } });
    fireEvent.change(screen.getByLabelText("Descrição da despesa"), { target: { value: "Pedra de arma" } });
    fireEvent.click(screen.getByRole("button", { name: "Registrar despesa" }));
    await waitFor(() => expect(recordExpense).toHaveBeenCalledWith(expect.objectContaining({ category: "upgrade", amountGold: 42_000, description: "Pedra de arma" })));

    fireEvent.click(screen.getByRole("button", { name: "Iniciar rotina" }));
    await waitFor(() => expect(startWorkRoutine).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("button", { name: "Pausar rotina" })).toBeInTheDocument();
  });

  it("opens the calculator, converts multimoeda and calculates Gold and Saco PvE", async () => {
    const getCurrencyRate = vi.fn(async () => ({
      baseCurrency: "EUR",
      quoteCurrency: "BRL",
      rateMicros: 6_000_000,
      rateFormatted: "6,00",
      source: "test",
      date: "2026-08-27",
    }));
    render(<App gateway={createGateway({ getToday: async () => ({ state: "ready", activityDate: "2026-08-27", selectedDungeons: 1, estimatedGold: 7_000, estimatedPveBags: 5, estimatedPveBagMarketValue: 5_000, pveBagUnitValueGold: 1000 }), getCurrencyRate })} />);
    fireEvent.click(await screen.findByRole("button", { name: "Calculadora" }));
    expect(screen.getByRole("dialog", { name: "Calculadora de gold" })).toBeInTheDocument();
    expect(getCurrencyRate).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Centavos por mil gold")).toHaveValue("8");

    // Gold Mode
    fireEvent.change(screen.getByLabelText("Gold para calcular"), { target: { value: "1000000" } });
    expect(screen.getByLabelText("Gold para calcular")).toHaveValue("1.000.000");
    expect(screen.getByText(/80,00/)).toBeInTheDocument();
    expect(screen.getByText(/Equivale a 1\.000 sacos PvE/i)).toBeInTheDocument();

    // Switch to Saco PvE Mode
    fireEvent.click(screen.getByRole("button", { name: "Saco PvE" }));
    const bagInput = screen.getByLabelText("Sacos para calcular");
    expect(bagInput).toHaveValue("250");

    // By default Saco PvE uses market package (3,50 EUR for 250 bags)
    expect(screen.getAllByText(/3,50/).length).toBeGreaterThanOrEqual(1);

    // Switch to Gold quote base (1 saco = 1000g, 8c / 1k = R$ 20,00 for 250 bags)
    fireEvent.click(screen.getByText(/Cotação de Gold/i));
    expect(screen.getAllByText(/20,00/).length).toBeGreaterThanOrEqual(1);

    // Click "Lançar em Nova Venda"
    fireEvent.click(screen.getByRole("button", { name: /Lançar em Nova Venda/i }));

    // Calculator closes, Nova Venda opens prefilled with Saco PvE
    expect(screen.queryByRole("dialog", { name: "Calculadora de gold" })).not.toBeInTheDocument();
    expect(await screen.findByRole("dialog", { name: "Nova venda" })).toBeInTheDocument();
    expect(screen.getByLabelText("Quantidade de Sacos")).toHaveValue("250");
  });

  it("formats numbers with thousand separators in Nova Venda dialog", async () => {
    render(<App gateway={createGateway({ getToday: async () => ({ state: "ready", activityDate: "2026-08-27", selectedDungeons: 1, estimatedGold: 7_000, estimatedPveBags: 5, estimatedPveBagMarketValue: 5_000 }) })} />);
    const saleButton = await screen.findByRole("button", { name: /Nova Venda/i });
    fireEvent.click(saleButton);

    const goldInput = screen.getByLabelText("Quantidade de Gold");
    expect(goldInput).toHaveValue("1.000.000");

    fireEvent.change(goldInput, { target: { value: "100000000" } });
    expect(goldInput).toHaveValue("100.000.000");

    // Change to Saco PvE
    fireEvent.click(screen.getByRole("button", { name: "Saco PvE" }));
    const bagInput = screen.getByLabelText("Quantidade de Sacos");
    expect(bagInput).toHaveValue("10");
    fireEvent.change(bagInput, { target: { value: "2500" } });
    expect(bagInput).toHaveValue("2.500");
  });

  it("displays TopbarRoutineTracker, allows adjusting target duration, and triggers completion prompt when runs complete", async () => {
    const stopWorkRoutine = vi.fn().mockResolvedValue({
      id: "routine-1",
      status: "completed",
      startedAt: "2026-08-26T12:00:00Z",
      pausedAt: null,
      finishedAt: "2026-08-26T14:00:00Z",
      elapsedSeconds: 7200,
    });

    const gateway = createGateway({
      getToday: async () => ({
        state: "ready",
        activityDate: "2026-08-27",
        selectedDungeons: 1,
        estimatedGold: 7_000,
        estimatedPveBags: 5,
        estimatedPveBagMarketValue: 5_000,
      }),
      getTodayCharacters: async () => ({
        state: "ready",
        characters: [
          {
            id: "char-1",
            name: "Striker",
            className: "Guerreiro",
            level: 70,
            accountName: "Conta 1",
            selectedDungeons: 1,
            completedDungeons: 1,
            dailyMissionCompleted: true,
            vipExpiresAt: null,
          },
        ],
      }),
      getTodayActivity: async () => ({
        state: "ready",
        activityDate: "2026-08-27",
        runsCompleted: 5,
        towerCompleted: 0,
        towerTotal: 0,
        recentDrops: [],
        monthlyGold: [],
        monthlyGoldTotal: 0,
      }),
      getWorkRoutine: async () => ({
        routine: {
          id: "routine-1",
          status: "running",
          startedAt: "2026-08-27T10:00:00Z",
          pausedAt: null,
          elapsedSeconds: 7200, // 2h
        },
      }),
      stopWorkRoutine,
    });

    render(<App gateway={gateway} />);

    // Tracker rendered in topbar
    const tracker = await screen.findByTestId("topbar-routine-tracker");
    expect(tracker).toBeInTheDocument();
    expect(screen.getByTestId("topbar-routine-time")).toHaveTextContent("02:00:00");
    expect(screen.getByRole("button", { name: "Pausar rotina" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Encerrar rotina" })).toBeInTheDocument();

    // Open target dialog
    fireEvent.click(screen.getByTitle("Ajustar meta de tempo"));
    expect(screen.getByRole("dialog", { name: "Configurar meta de tempo da rotina" })).toBeInTheDocument();

    // Pick 3h preset and save
    fireEvent.click(screen.getByRole("button", { name: "3h" }));
    fireEvent.click(screen.getByRole("button", { name: "Salvar meta" }));

    // Target modal closes and tracker reflects new meta
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Configurar meta de tempo da rotina" })).not.toBeInTheDocument();
    });
    expect(screen.getByText(/Meta: 3h/)).toBeInTheDocument();

    // Since 1/1 character is completed and routine is running, completion prompt banner is shown
    expect(screen.getByText("Todas as runs de hoje foram concluídas!")).toBeInTheDocument();

    // Click "Encerrar rotina agora" on the banner
    fireEvent.click(screen.getByRole("button", { name: "Encerrar rotina agora" }));
    await waitFor(() => expect(stopWorkRoutine).toHaveBeenCalledTimes(1));
  });

  it("keeps routine timer accurate across background throttling and window focus", async () => {
    let mockNow = 1_000_000_000;
    const dateSpy = vi.spyOn(Date, "now").mockImplementation(() => mockNow);
    try {
      const gateway = createGateway({
        getToday: async () => ({
          state: "ready",
          activityDate: "2026-08-27",
          selectedDungeons: 1,
          estimatedGold: 7_000,
          estimatedPveBags: 5,
          estimatedPveBagMarketValue: 5_000,
        }),
        getWorkRoutine: async () => ({
          routine: {
            id: "routine-1",
            status: "running",
            startedAt: new Date(mockNow).toISOString(),
            pausedAt: null,
            elapsedSeconds: 0,
          },
        }),
      });

      render(<App gateway={gateway} />);

      // Initially 00:00:00
      expect(await screen.findByTestId("topbar-routine-time")).toHaveTextContent("00:00:00");

      // Advance mock wall-clock time by 2 hours (7200 seconds)
      mockNow += 7200 * 1000;

      // Trigger focus event (user alt-tabbed back into the app after background throttling)
      act(() => {
        window.dispatchEvent(new Event("focus"));
      });

      expect(screen.getByTestId("topbar-routine-time")).toHaveTextContent("02:00:00");
    } finally {
      dateSpy.mockRestore();
    }
  });

  it("allows configuring routine target duration from the settings page", async () => {
    render(
      <App
        gateway={createGateway({
          getToday: async () => ({
            state: "ready",
            activityDate: "2026-08-27",
            selectedDungeons: 1,
            estimatedGold: 7_000,
            estimatedPveBags: 5,
            estimatedPveBagMarketValue: 5_000,
          }),
        })}
      />,
    );

    // Navigate to Settings
    fireEvent.click(screen.getByRole("button", { name: "Configurações" }));
    expect(screen.getByText("Meta de tempo da rotina de farm")).toBeInTheDocument();

    // Select 5h preset
    fireEvent.click(screen.getByRole("button", { name: "5h" }));

    // Expect target text to update
    expect(screen.getByText("5h (300 minutos)")).toBeInTheDocument();
  });

  it("allows toggling autostart with Windows from the settings page", async () => {
    let autostartEnabled = false;
    const setAutostart = vi.fn(async (enabled: boolean) => {
      autostartEnabled = enabled;
      return { enabled };
    });

    render(
      <App
        gateway={createGateway({
          getAutostart: async () => ({ enabled: autostartEnabled }),
          setAutostart,
          getToday: async () => ({
            state: "ready",
            activityDate: "2026-08-27",
            selectedDungeons: 1,
            estimatedGold: 7_000,
            estimatedPveBags: 5,
            estimatedPveBagMarketValue: 5_000,
          }),
        })}
      />,
    );

    // Navigate to Settings
    fireEvent.click(screen.getByRole("button", { name: "Configurações" }));
    expect(screen.getByText("Inicialização do sistema")).toBeInTheDocument();
    expect(screen.getByText("Iniciar com o Windows")).toBeInTheDocument();

    const switchBtn = screen.getByRole("switch", { name: /iniciar com o Windows/i });
    expect(switchBtn).toHaveAttribute("aria-checked", "false");

    // Click switch to enable
    fireEvent.click(switchBtn);
    await waitFor(() => expect(setAutostart).toHaveBeenCalledWith(true));
    expect(switchBtn).toHaveAttribute("aria-checked", "true");

    // Click switch to disable
    fireEvent.click(switchBtn);
    await waitFor(() => expect(setAutostart).toHaveBeenCalledWith(false));
    expect(switchBtn).toHaveAttribute("aria-checked", "false");
  });
});
