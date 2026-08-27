import { useEffect, useMemo, useState } from "react";
import {
  Coins,
  CurrencyDollar,
  Package,
  TrendUp,
  Tote,
  Target,
  ArrowRight,
  Receipt,
  Tag,
  ArrowsClockwise,
} from "@phosphor-icons/react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AppGateway, ReportsOverviewResult } from "../gateway/AppGateway";

const numberFormat = new Intl.NumberFormat("pt-BR");
const currencyFormat = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

function formatCompactGold(val: number): string {
  if (val >= 1_000_000) {
    const m = val / 1_000_000;
    return Number.isInteger(m) ? `${m}M` : `${m.toFixed(1)}M`;
  }
  if (val >= 1_000) {
    const k = val / 1_000;
    return Number.isInteger(k) ? `${k}k` : `${k.toFixed(0)}k`;
  }
  return String(val);
}

function formatShortDate(iso: string): string {
  try {
    const d = new Date(iso);
    return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  } catch {
    return iso;
  }
}

export function ReportsPage({ gateway }: { gateway: AppGateway }) {
  const [reports, setReports] = useState<ReportsOverviewResult>({ state: "empty" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    gateway
      .getReportsOverview()
      .then((res) => {
        if (!active) return;
        setReports(res);
        setLoading(false);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Erro ao carregar relatórios");
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [gateway]);

  const barData = useMemo(() => {
    if (reports.state !== "ready") return [];
    return [
      {
        name: reports.monthlyComparison.previousMonthName,
        gold: reports.monthlyComparison.previousMonthGold,
        isCurrent: false,
      },
      {
        name: reports.monthlyComparison.currentMonthName,
        gold: reports.monthlyComparison.currentMonthGold,
        isCurrent: true,
      },
    ];
  }, [reports]);

  if (loading) {
    return (
      <div className="reports-page" data-testid="reports-loading">
        <div className="reports-header">
          <div>
            <span className="eyebrow uppercase tracking-wider text-xs">Visão Geral</span>
            <h1 className="text-2xl font-bold text-slate-100">Relatórios</h1>
            <p className="text-sm text-slate-400">Carregando métricas e histórico financeiro...</p>
          </div>
        </div>
        <div className="empty-state p-12 text-center text-slate-400">
          <ArrowsClockwise size={32} className="animate-spin mx-auto mb-2 text-indigo-400" />
          <p>Carregando dados consolidados...</p>
        </div>
      </div>
    );
  }

  if (error || reports.state === "empty") {
    return (
      <div className="reports-page" data-testid="reports-empty">
        <div className="reports-header">
          <div>
            <span className="eyebrow uppercase tracking-wider text-xs">Visão Geral</span>
            <h1 className="text-2xl font-bold text-slate-100">Relatórios</h1>
            <p className="text-sm text-slate-400">Resumo do desempenho do farm, vendas e evolução acumulada.</p>
          </div>
        </div>
        <div className="empty-state p-12 text-center text-slate-400">
          <p>{error || "Nenhum dado consolidado disponível no momento."}</p>
        </div>
      </div>
    );
  }

  const { kpis, dailyEvolution, monthlyComparison, cumulativeHistory, financialSummary, recentSales, monthlyTarget, topCharacters } = reports;

  return (
    <div className="reports-page" data-testid="reports-page">
      {/* Header Area */}
      <header className="reports-header">
        <div>
          <span className="eyebrow text-xs uppercase tracking-wider text-slate-400">Visão Geral</span>
          <h1 className="text-2xl font-bold text-slate-100">Relatórios</h1>
          <p className="text-sm text-slate-400">Resumo do desempenho do farm, vendas e evolução acumulada.</p>
        </div>
        <div className="reports-controls">
          <div className="filter-pill">
            <span>1 – 27 de agosto de 2026</span>
          </div>
        </div>
      </header>

      {/* Top 5 KPI Stat Cards */}
      <section className="reports-kpi-grid">
        {/* Card 1: Vendido no mês */}
        <div className="kpi-card kpi-card--green">
          <div className="kpi-icon kpi-icon--green">
            <CurrencyDollar size={24} weight="duotone" />
          </div>
          <div className="kpi-body">
            <span className="kpi-label">Vendido no mês</span>
            <strong className="kpi-value">{currencyFormat.format(kpis.monthlySalesMinor / 100)}</strong>
            <span className="kpi-badge kpi-badge--positive">
              +{kpis.salesChangePercent}% vs mês passado
            </span>
          </div>
        </div>

        {/* Card 2: Farm do mês */}
        <div className="kpi-card kpi-card--gold">
          <div className="kpi-icon kpi-icon--gold">
            <Coins size={24} weight="duotone" />
          </div>
          <div className="kpi-body">
            <span className="kpi-label">Farm do mês</span>
            <strong className="kpi-value">{numberFormat.format(kpis.monthlyFarmGold)}</strong>
            <span className="kpi-badge kpi-badge--positive">
              +{kpis.farmGoldChangePercent}% vs mês passado
            </span>
          </div>
        </div>

        {/* Card 3: Farm total */}
        <div className="kpi-card kpi-card--purple">
          <div className="kpi-icon kpi-icon--purple">
            <Package size={24} weight="duotone" />
          </div>
          <div className="kpi-body">
            <span className="kpi-label">Farm total</span>
            <strong className="kpi-value">{numberFormat.format(kpis.allTimeFarmGold)}</strong>
            <span className="kpi-subtext">Desde o início</span>
          </div>
        </div>

        {/* Card 4: Média diária */}
        <div className="kpi-card kpi-card--blue">
          <div className="kpi-icon kpi-icon--blue">
            <TrendUp size={24} weight="duotone" />
          </div>
          <div className="kpi-body">
            <span className="kpi-label">Média diária</span>
            <strong className="kpi-value">{numberFormat.format(kpis.dailyAverageGold)}</strong>
            <span className="kpi-subtext">gold/dia</span>
          </div>
        </div>

        {/* Card 5: Sacos PvE vendidos */}
        <div className="kpi-card kpi-card--teal">
          <div className="kpi-icon kpi-icon--teal">
            <Tote size={24} weight="duotone" />
          </div>
          <div className="kpi-body">
            <span className="kpi-label">Sacos PvE vendidos</span>
            <strong className="kpi-value">{numberFormat.format(kpis.monthlyPveBagsSold)}</strong>
            <span className="kpi-badge kpi-badge--positive">
              +{kpis.pveBagsChangePercent}% vs mês passado
            </span>
          </div>
        </div>
      </section>

      {/* Row 1: Evolução do Mês + Comparativo Mensal */}
      <section className="reports-grid-row reports-grid-row--charts">
        {/* Evolução do mês */}
        <div className="panel chart-panel chart-panel--main">
          <div className="chart-heading">
            <div>
              <h2>Evolução do mês</h2>
              <span className="chart-sub">Gold farmado por dia</span>
            </div>
            <div className="chart-selector">
              <span>Gold por dia</span>
            </div>
          </div>
          <div className="chart-container" style={{ width: "100%", height: 230 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={dailyEvolution} margin={{ top: 12, right: 20, bottom: 0, left: -5 }}>
                <defs>
                  <linearGradient id="blueEvolGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#4f80ff" stopOpacity={0.45} />
                    <stop offset="100%" stopColor="#4f80ff" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: "#8293a5", fontSize: 10 }} />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "#8293a5", fontSize: 10 }}
                  tickFormatter={formatCompactGold}
                />
                <Tooltip
                  formatter={(value) => [`${numberFormat.format(Number(value))} gold`, "Farm"]}
                  labelFormatter={(d) => `Dia ${d}`}
                  contentStyle={{ background: "#0c2232", border: "1px solid #294054", borderRadius: 8, fontSize: 12 }}
                />
                <Area
                  type="monotone"
                  dataKey="gold"
                  stroke="#5d93ff"
                  strokeWidth={2.5}
                  fill="url(#blueEvolGrad)"
                  dot={{ r: 3.5, fill: "#5d93ff", stroke: "#0b1523", strokeWidth: 1.5 }}
                  activeDot={{ r: 5.5, fill: "#8ab4f8" }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Comparativo mensal */}
        <div className="panel chart-panel chart-panel--side">
          <div className="chart-heading">
            <div>
              <h2>Comparativo mensal</h2>
              <span className="chart-sub">Gold farmado</span>
            </div>
          </div>
          <div className="comparative-body">
            <div className="comparative-highlight">
              <span className="text-emerald-400 font-bold text-xl">+{monthlyComparison.growthPercent}%</span>
              <span className="text-xs text-slate-400 block">vs mês passado</span>
            </div>
            <div className="chart-container" style={{ width: "100%", height: 165 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData} margin={{ top: 15, right: 10, bottom: 0, left: -10 }}>
                  <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.06)" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: "#8293a5", fontSize: 10 }} />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: "#8293a5", fontSize: 10 }}
                    tickFormatter={formatCompactGold}
                  />
                  <Tooltip
                    formatter={(value) => [`${numberFormat.format(Number(value))} gold`, "Total"]}
                    contentStyle={{ background: "#0c2232", border: "1px solid #294054", borderRadius: 8, fontSize: 12 }}
                  />
                  <Bar dataKey="gold" radius={[4, 4, 0, 0]} maxBarSize={48}>
                    {barData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.isCurrent ? "#4f80ff" : "#4a5568"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      {/* Row 2: Acumulado desde o início + Resumo Financeiro */}
      <section className="reports-grid-row reports-grid-row--charts">
        {/* Acumulado desde o início */}
        <div className="panel chart-panel chart-panel--main">
          <div className="chart-heading">
            <div>
              <h2>Acumulado desde o início</h2>
              <span className="chart-sub">Evolução total do farm (gold)</span>
            </div>
            <div className="chart-selector">
              <span>Todos os personagens</span>
            </div>
          </div>
          <div className="chart-container" style={{ width: "100%", height: 210 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={cumulativeHistory} margin={{ top: 12, right: 20, bottom: 0, left: -5 }}>
                <defs>
                  <linearGradient id="amberCumGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="#f59e0b" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="monthLabel" axisLine={false} tickLine={false} tick={{ fill: "#8293a5", fontSize: 10 }} />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "#8293a5", fontSize: 10 }}
                  tickFormatter={formatCompactGold}
                />
                <Tooltip
                  formatter={(value) => [`${numberFormat.format(Number(value))} gold`, "Acumulado"]}
                  labelFormatter={(label) => `Mês: ${label}`}
                  contentStyle={{ background: "#0c2232", border: "1px solid #294054", borderRadius: 8, fontSize: 12 }}
                />
                <Area
                  type="monotone"
                  dataKey="cumulativeGold"
                  stroke="#fbbf24"
                  strokeWidth={2.5}
                  fill="url(#amberCumGrad)"
                  dot={{ r: 3, fill: "#fbbf24", stroke: "#0b1523", strokeWidth: 1 }}
                  activeDot={{ r: 5, fill: "#fde68a" }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Resumo financeiro */}
        <div className="panel summary-panel">
          <div className="panel-heading">
            <h2>Resumo financeiro</h2>
          </div>
          <div className="financial-rows">
            <div className="fin-row">
              <span className="fin-row-left">
                <span className="fin-row-icon fin-row-icon--green"><CurrencyDollar size={16} /></span>
                Vendas em R$
              </span>
              <strong className="fin-row-value text-emerald-400">{currencyFormat.format(financialSummary.salesAmountMinor / 100)}</strong>
            </div>

            <div className="fin-row">
              <span className="fin-row-left">
                <span className="fin-row-icon fin-row-icon--blue"><Tag size={16} /></span>
                Itens vendidos
              </span>
              <strong className="fin-row-value text-slate-200">{financialSummary.itemsSoldCount}</strong>
            </div>

            <div className="fin-row">
              <span className="fin-row-left">
                <span className="fin-row-icon fin-row-icon--gold"><Coins size={16} /></span>
                Gold convertido
              </span>
              <strong className="fin-row-value text-amber-300">{numberFormat.format(financialSummary.goldConvertedTotal)}</strong>
            </div>

            <div className="fin-row">
              <span className="fin-row-left">
                <span className="fin-row-icon fin-row-icon--purple"><Receipt size={16} /></span>
                Ticket médio
              </span>
              <strong className="fin-row-value text-slate-200">{currencyFormat.format(financialSummary.averageTicketMinor / 100)}</strong>
            </div>
          </div>
        </div>
      </section>

      {/* Row 3: Últimas vendas + Meta do mês + Top personagens */}
      <section className="reports-grid-row reports-grid-row--bottom">
        {/* Últimas vendas */}
        <div className="panel bottom-panel bottom-panel--sales">
          <div className="panel-heading">
            <h2>Últimas vendas</h2>
          </div>
          <div className="sales-table-wrap">
            <table className="sales-table">
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Quantidade</th>
                  <th>Valor (R$)</th>
                  <th>Data</th>
                </tr>
              </thead>
              <tbody>
                {recentSales.length ? (
                  recentSales.map((sale) => (
                    <tr key={sale.id}>
                      <td className="sale-item-cell">
                        <span className="item-badge-icon">
                          <Coins size={14} className="text-amber-400" />
                        </span>
                        <span>{sale.itemName}</span>
                      </td>
                      <td>{sale.quantity}</td>
                      <td className="font-semibold text-emerald-400">{currencyFormat.format(sale.amountMinor / 100)}</td>
                      <td className="text-slate-400 text-xs">{formatShortDate(sale.soldAt)}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="text-center py-6 text-slate-500 text-sm">
                      Nenhuma venda registrada
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="panel-footer-link">
            <span>Ver todas as vendas <ArrowRight size={13} className="inline ml-1" /></span>
          </div>
        </div>

        {/* Meta do mês */}
        <div className="panel bottom-panel bottom-panel--target">
          <div className="panel-heading">
            <h2>Meta do mês</h2>
            <Target size={20} className="text-indigo-400" />
          </div>
          <div className="target-body">
            <div className="target-header-line">
              <span className="text-slate-300 font-medium">Meta: {numberFormat.format(monthlyTarget.targetGold)} gold</span>
              <span className="text-slate-200 font-bold">{numberFormat.format(monthlyTarget.currentGold)} ({monthlyTarget.percentage}%)</span>
            </div>
            {/* Progress bar */}
            <div className="target-progress-track">
              <div
                className="target-progress-fill"
                style={{ width: `${Math.min(100, monthlyTarget.percentage)}%` }}
              />
            </div>
            <p className="target-hint">
              Faltam <strong className="text-amber-300">{numberFormat.format(monthlyTarget.remainingGold)} gold</strong> para atingir a meta
            </p>
            <span className="target-days-left">{monthlyTarget.daysRemaining} dias restantes</span>
          </div>
        </div>

        {/* Top personagens do mês */}
        <div className="panel bottom-panel bottom-panel--ranking">
          <div className="panel-heading">
            <h2>Top personagens do mês</h2>
          </div>
          <div className="ranking-list">
            <div className="ranking-header">
              <span>#</span>
              <span>Personagem</span>
              <span className="text-right">Gold farmado</span>
            </div>
            {topCharacters.length ? (
              topCharacters.map((char) => (
                <div key={char.characterId} className="ranking-row">
                  <span className="ranking-pos">{char.rank}</span>
                  <div className="ranking-char">
                    <span className="ranking-avatar">{char.characterName.slice(0, 2).toUpperCase()}</span>
                    <div>
                      <strong className="block text-slate-200 text-sm leading-none">{char.characterName}</strong>
                      <span className="text-xs text-slate-400">{char.className}</span>
                    </div>
                  </div>
                  <span className="ranking-gold">{numberFormat.format(char.goldEarned)}</span>
                </div>
              ))
            ) : (
              <div className="text-center py-6 text-slate-500 text-sm">
                Nenhum personagem registrado no mês
              </div>
            )}
          </div>
          <div className="panel-footer-link">
            <span>Ver todos os personagens <ArrowRight size={13} className="inline ml-1" /></span>
          </div>
        </div>
      </section>
    </div>
  );
}
