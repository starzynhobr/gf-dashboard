import type { DashboardModuleKey } from "../gateway/AppGateway";

export const dashboardModuleRegistry: ReadonlyArray<{ moduleKey: DashboardModuleKey; title: string; description: string; defaultEnabled: boolean }> = [
  { moduleKey: "daily-summary", title: "Resumo do dia", description: "Runs, personagens, Torre e ouro estimado.", defaultEnabled: true },
  { moduleKey: "recent-drops", title: "Últimos drops", description: "Itens relevantes registrados nas sessões recentes.", defaultEnabled: true },
  { moduleKey: "monthly-performance", title: "Desempenho mensal", description: "Gráfico e total de ouro obtido no mês.", defaultEnabled: true },
];
