import { ChartBar, Coins, CurrencyDollar, Package, ShieldChevron, Sword, Tote, UsersThree } from "@phosphor-icons/react";
import { lazy, Suspense } from "react";

import type { DashboardModuleKey, TodayActivityResult, TowerConfiguration } from "../gateway/AppGateway";

const MonthlyGoldChart = lazy(() => import("./MonthlyGoldChart"));
const numberFormat = new Intl.NumberFormat("pt-BR");
const currencyFormat = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{children}</section>;
}

export function DashboardModuleHost({
  visibility,
  activity,
  runsCompleted,
  completedCharacters,
  characterTotal,
  towerCompleted,
  towerTotal,
  gold,
  monthlyData,
  towerConfiguration,
  towerLoading,
  towerError,
  onRetryTower,
}: {
  visibility: Record<DashboardModuleKey, boolean>;
  activity: TodayActivityResult | null;
  runsCompleted: number;
  completedCharacters: number;
  characterTotal: number;
  towerCompleted: number;
  towerTotal: number;
  gold: number;
  monthlyData: Array<{ day: number; gold: number; pveBags: number; bagValueGold: number; goldEquivalent: number }>;
  towerConfiguration: TowerConfiguration | null;
  towerLoading: boolean;
  towerError: string | null;
  onRetryTower: () => void;
}) {
  const earnedGold = activity?.earnedGoldToday ?? gold;
  const pveBagsEarned = activity?.pveBagsEarnedToday ?? 0;
  const todaySalesMinor = activity?.todaySalesMinor ?? 0;

  return (
    <aside className="right-column">
      {visibility["daily-summary"] && (
        <Panel>
          <div className="panel-heading">
            <h2>Resumo do dia</h2>
          </div>
          <div className="summary-list">
            <p>
              <Sword size={17} />
              <span>Runs concluídas</span>
              <strong>{runsCompleted}</strong>
            </p>
            <p>
              <UsersThree size={17} />
              <span>Personagens concluídos</span>
              <strong>{completedCharacters} / {characterTotal}</strong>
            </p>
            <p>
              <ShieldChevron size={17} />
              <span>Torre concluída</span>
              <strong>{towerCompleted} / {towerTotal}</strong>
            </p>
            <p className="summary-gold">
              <Coins size={17} />
              <span>Ouro ganho</span>
              <strong>{numberFormat.format(earnedGold)}</strong>
            </p>
            <p className="summary-bags">
              <Tote size={17} />
              <span>Sacos PvE ganhos</span>
              <strong>{numberFormat.format(pveBagsEarned)}</strong>
            </p>
            <p className="summary-sales">
              <CurrencyDollar size={17} className="text-emerald-400" />
              <span>Vendido hoje</span>
              <strong className="text-emerald-400">
                {currencyFormat.format(todaySalesMinor / 100)}
              </strong>
            </p>
          </div>
        </Panel>
      )}
      {visibility["recent-drops"] && (
        <Panel>
          <div className="panel-heading">
            <h2>Itens da Torre</h2>
          </div>
          {towerLoading ? <div className="module-empty" role="status">Carregando itens da Torre...</div> : towerError ? <div className="module-empty tower-catalog-error"><span role="alert">{towerError}</span><button className="secondary-button" type="button" onClick={onRetryTower}>Tentar novamente</button></div> : towerConfiguration?.items.length ? (
            <div className="drops-list tower-catalog-list">
              {towerConfiguration.items.map((item) => (
                <p key={item.itemId}>
                  <Package size={17} weight="duotone" />
                  <span>
                    {item.itemName}
                  </span>
                  <strong>{item.estimatedUnitValue === null ? "Sem valor" : `${numberFormat.format(item.estimatedUnitValue)} gold`}</strong>
                </p>
              ))}
            </div>
          ) : (
            <div className="module-empty">
              <Package size={25} weight="duotone" />
              <span>Nenhum item da Torre configurado</span>
            </div>
          )}
        </Panel>
      )}
      {visibility["monthly-performance"] && (
        <Panel className="monthly-panel">
          <div className="panel-heading">
            <h2>Desempenho mensal</h2>
            <span title="Sacos PvE valorados pela cotação atual">Gold + Sacos PvE</span>
          </div>
          {monthlyData.length ? (
            <Suspense fallback={<div className="module-empty chart-empty">Carregando gráfico...</div>}>
              <MonthlyGoldChart data={monthlyData} />
            </Suspense>
          ) : (
            <div className="module-empty chart-empty">
              <ChartBar size={28} weight="duotone" />
              <span>O gráfico aparecerá com o histórico</span>
            </div>
          )}
          <div className="month-total">
            <span>Total equivalente do mês</span>
            <strong>
              <Coins size={17} weight="fill" /> {numberFormat.format(activity?.monthlyGoldTotal ?? 0)}
            </strong>
          </div>
        </Panel>
      )}
    </aside>
  );
}
