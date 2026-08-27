import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AppGateway } from "../gateway/AppGateway";
import { App } from "./App";

function createGateway(overrides: Partial<AppGateway> = {}): AppGateway {
  return {
    ping: async () => ({ message: "pong", runtime: "desktop", bridgeVersion: 1 }),
    getToday: async () => ({ state: "empty", activityDate: "2026-08-26" }),
    getTodayCharacters: async () => ({ state: "empty", characters: [] }),
    getTodayActivity: async () => ({ state: "empty", runsCompleted: 0, towerCompleted: 0, towerTotal: 0, recentDrops: [], monthlyGold: [], monthlyGoldTotal: 0 }),
    getCharacterDay: async () => ({ characterId: "character-1", characterName: "Star01", className: "Ranger", accountName: "Conta", activityDate: "2026-08-26", dungeons: [] }),
    saveCharacterDay: async (_characterId, completedActivityIds) => ({ completedDungeons: completedActivityIds.length, gold: 0, pveBags: 0 }),
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
    ...overrides,
  };
}

describe("App", () => {
  afterEach(cleanup);

  it("shows that the Python bridge is ready after a successful ping", async () => {
    const gateway = createGateway();

    render(<App gateway={gateway} />);

    expect(await screen.findByText("Online")).toBeInTheDocument();
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

  it("opens a character summary and saves the selected dungeon cycle", async () => {
    const saveCharacterDay = vi.fn(async (_characterId: string, completedActivityIds: string[]) => ({ completedDungeons: completedActivityIds.length, gold: 7000, pveBags: 5 }));
    const gateway = createGateway({
      getTodayCharacters: async () => ({ state: "ready", characters: [{ id: "character-1", name: "Star01", className: "Ranger", accountName: "Conta", completedDungeons: 0, selectedDungeons: 1 }] }),
      getCharacterDay: async () => ({ characterId: "character-1", characterName: "Star01", className: "Ranger", accountName: "Conta", activityDate: "2026-08-26", dungeons: [{ characterActivityId: "ca-1", activityId: "dungeon-1", name: "Palácio de Proteção do Selo", completed: false, targetAmount: 5, gold: 7000, pveBags: 5 }] }),
      saveCharacterDay,
    });
    render(<App gateway={gateway} />);

    fireEvent.click(await screen.findByText("Star01"));
    fireEvent.click(await screen.findByText("Palácio de Proteção do Selo"));
    fireEvent.click(screen.getByRole("button", { name: "Salvar resumo" }));

    await waitFor(() => expect(saveCharacterDay).toHaveBeenCalledWith("character-1", ["ca-1"]));
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
    expect(await screen.findByText("Star01")).toBeInTheDocument();
    expect(await screen.findByText("Palácio de Proteção do Selo")).toBeInTheDocument();
    expect(await screen.findByText("Cristal Mágico")).toBeInTheDocument();
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
});



