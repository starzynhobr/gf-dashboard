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

  getCharacterDay(characterId: string): Promise<CharacterDayResult> {
    return this.invoke<CharacterDayResult>("dashboard.characterDay", { characterId });
  }

  saveCharacterDay(characterId: string, completedActivityIds: string[]): Promise<{ completedDungeons: number; gold: number; pveBags: number }> {
    return this.invoke("dashboard.saveCharacterDay", { characterId, completedActivityIds });
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
