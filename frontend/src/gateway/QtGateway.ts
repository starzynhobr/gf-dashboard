import { type AppGateway, type CharacterDayResult, type DashboardLayoutResult, type DashboardModuleKey, GatewayError, type ManagementOverviewResult, type PingResult, type TodayActivityResult, type TodayCharactersResult, type TodayResult, type TowerRegistrationInput } from "./AppGateway";

interface BridgeResponse<T> {
  version: number;
  requestId: string | null;
  ok: boolean;
  data?: T;
  error?: { code: string; message: string };
}

export class QtGateway implements AppGateway {
  private bridgePromise?: Promise<QtBridgeObject>;

  ping(): Promise<PingResult> {
    return this.invoke<PingResult>("system.ping", {});
  }

  getToday(): Promise<TodayResult> {
    return this.invoke<TodayResult>("dashboard.today", {});
  }

  getTodayCharacters(): Promise<TodayCharactersResult> {
    return this.invoke<TodayCharactersResult>("dashboard.todayCharacters", {});
  }

  getTodayActivity(): Promise<TodayActivityResult> {
    return this.invoke<TodayActivityResult>("dashboard.todayActivity", {});
  }

  getCharacterDay(characterId: string, activityDate?: string): Promise<CharacterDayResult> {
    return this.invoke<CharacterDayResult>("dashboard.characterDay", {
      characterId,
      ...(activityDate ? { activityDate } : {}),
    });
  }

  saveCharacterDay(characterId: string, completedActivityIds: string[], activityDate: string): Promise<{ completedDungeons: number; gold: number; pveBags: number }> {
    return this.invoke("dashboard.saveCharacterDay", { characterId, completedActivityIds, activityDate });
  }

  setCharacterDailyMission(characterId: string, completed: boolean): Promise<{ completed: boolean }> {
    return this.invoke("dashboard.setDailyMission", { characterId, completed });
  }

  saveCharacterVip(characterId: string, paidGold: number, remainingDays: number, remainingHours: number): Promise<{ expiresAt: string; paidGold: number }> {
    return this.invoke("vip.save", { characterId, paidGold, remainingDays, remainingHours });
  }

  getManagementOverview(): Promise<ManagementOverviewResult> {
    return this.invoke<ManagementOverviewResult>("management.overview", {});
  }

  createAccount(name: string, serverName: string): Promise<{ id: string; name: string }> {
    return this.invoke("management.createAccount", { name, serverName });
  }

  createCharacter(accountId: string, name: string, className: string, level: number): Promise<{ id: string; name: string }> {
    return this.invoke("management.createCharacter", { accountId, name, className, level });
  }

  updateAccount(accountId: string, name: string, serverName: string): Promise<{ id: string; name: string }> {
    return this.invoke("management.updateAccount", { accountId, name, serverName });
  }

  updateCharacter(characterId: string, name: string, className: string, level: number): Promise<{ id: string; name: string }> {
    return this.invoke("management.updateCharacter", { characterId, name, className, level });
  }

  setDungeonActive(activityId: string, enabled: boolean): Promise<{ updated: boolean }> {
    return this.invoke("management.setDungeonActive", { activityId, enabled });
  }

  registerCompletedTower(input: TowerRegistrationInput): Promise<{ sessionId: string; participantCount: number; dropCount: number; entryCostGold: number }> {
    return this.invoke("tower.registerCompleted", { ...input });
  }

  getDashboardLayout(): Promise<DashboardLayoutResult> {
    return this.invoke("dashboard.layout", {});
  }

  setDashboardModuleVisible(moduleKey: DashboardModuleKey, enabled: boolean): Promise<DashboardLayoutResult> {
    return this.invoke("dashboard.setModuleVisible", { moduleKey, enabled });
  }

  resetDashboardLayout(): Promise<DashboardLayoutResult> {
    return this.invoke("dashboard.resetLayout", {});
  }

  createWorkspace(name: string): Promise<{ name: string }> {
    return this.invoke<{ name: string }>("workspace.create", { name });
  }

  getHistoryOverview(filter?: import("./AppGateway").HistoryFilterInput): Promise<import("./AppGateway").HistoryOverviewResult> {
    return this.invoke("history.overview", { ...filter });
  }

  getHistoryDayDetail(activityDate: string, filter?: import("./AppGateway").HistoryFilterInput): Promise<import("./AppGateway").HistoryDayDetailResult> {
    return this.invoke("history.dayDetail", { activityDate, ...filter });
  }

  recordPveBagQuote(unitValueGold: number, source?: string): Promise<{ quoteId: string; unitValueGold: number; observedAt: string }> {
    return this.invoke("market.recordPveBagQuote", { unitValueGold, source });
  }

  getReportsOverview(referenceDate?: string): Promise<import("./AppGateway").ReportsOverviewResult> {
    return this.invoke("reports.overview", { referenceDate });
  }

  setMonthlyTarget(targetMonth: string, targetGold: number): Promise<{ targetMonth: string; targetGold: number }> {
    return this.invoke("reports.setMonthlyTarget", { targetMonth, targetGold });
  }

  recordExpense(input: import("./AppGateway").ExpenseRegistrationInput): Promise<{ transactionId: string }> {
    return this.invoke("expenses.record", { ...input });
  }

  getExpenseHistory(): Promise<{ expenses: import("./AppGateway").ExpenseHistoryRow[] }> {
    return this.invoke("expenses.history", {});
  }

  updateExpense(transactionId: string, input: import("./AppGateway").ExpenseRegistrationInput): Promise<{ transactionId: string }> {
    return this.invoke("expenses.update", { transactionId, ...input });
  }

  voidExpense(transactionId: string): Promise<{ voided: boolean }> {
    return this.invoke("expenses.void", { transactionId });
  }

  getWorkRoutine(): Promise<{ routine: import("./AppGateway").WorkRoutineResult | null }> {
    return this.invoke("routine.current", {});
  }

  startWorkRoutine(): Promise<import("./AppGateway").WorkRoutineResult> { return this.invoke("routine.start", {}); }
  pauseWorkRoutine(): Promise<import("./AppGateway").WorkRoutineResult> { return this.invoke("routine.pause", {}); }
  resumeWorkRoutine(): Promise<import("./AppGateway").WorkRoutineResult> { return this.invoke("routine.resume", {}); }
  stopWorkRoutine(): Promise<import("./AppGateway").WorkRoutineResult> { return this.invoke("routine.stop", {}); }

  getCurrencyRate(baseCurrency: string, quoteCurrency?: string, date?: string): Promise<import("./AppGateway").CurrencyRateResult> {
    return this.invoke("currency.getRate", { baseCurrency, quoteCurrency, date });
  }

  recordSale(input: import("./AppGateway").SaleRegistrationInput): Promise<import("./AppGateway").SaleRegistrationResult> {
    return this.invoke("sales.record", { ...input });
  }

  getAutostart(): Promise<{ enabled: boolean }> {
    return this.invoke("system.getAutostart", {});
  }

  setAutostart(enabled: boolean): Promise<{ enabled: boolean }> {
    return this.invoke("system.setAutostart", { enabled });
  }

  private async invoke<T>(method: string, payload: Record<string, unknown>): Promise<T> {
    const bridge = await this.getBridge();
    const requestId = crypto.randomUUID();
    const request = JSON.stringify({ version: 1, requestId, method, payload });

    return new Promise<T>((resolve, reject) => {
      bridge.invoke(request, (rawResponse) => {
        try {
          const response = JSON.parse(rawResponse) as BridgeResponse<T>;
          if (response.requestId !== requestId) {
            reject(new GatewayError("mismatched_response", "Resposta não corresponde à chamada"));
          } else if (!response.ok || response.data === undefined) {
            reject(
              new GatewayError(
                response.error?.code ?? "bridge_error",
                response.error?.message ?? "Falha na comunicação com o aplicativo",
              ),
            );
          } else {
            resolve(response.data);
          }
        } catch {
          reject(new GatewayError("invalid_response", "Resposta inválida da bridge"));
        }
      });
    });
  }

  private getBridge(): Promise<QtBridgeObject> {
    this.bridgePromise ??= new Promise((resolve, reject) => {
      if (!window.qt?.webChannelTransport || !window.QWebChannel) {
        reject(new GatewayError("bridge_unavailable", "Qt WebChannel não está disponível"));
        return;
      }

      new window.QWebChannel(window.qt.webChannelTransport, (channel) => {
        const bridge = channel.objects.appBridge;
        if (!bridge) {
          reject(new GatewayError("bridge_missing", "Bridge do aplicativo não foi registrada"));
          return;
        }
        resolve(bridge);
      });
    });
    return this.bridgePromise;
  }
}
