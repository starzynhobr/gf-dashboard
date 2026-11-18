import type { DashboardModuleKey } from "../gateway/AppGateway";

export const dashboardModuleRegistry: ReadonlyArray<{ moduleKey: DashboardModuleKey; title: string; description: string; defaultEnabled: boolean }> = [
  { moduleKey: "daily-summary", title: "Resumo do dia", description: "Runs, personagens, Torre, ouro e Sacos PvE ganhos.", defaultEnabled: true },
  { moduleKey: "recent-drops", title: "Itens da Torre", description: "Catálogo de itens relevantes e seus valores estimados em gold.", defaultEnabled: true },
  { moduleKey: "monthly-performance", title: "Desempenho mensal", description: "Gráfico e total de ouro obtido no mês.", defaultEnabled: true },
];
