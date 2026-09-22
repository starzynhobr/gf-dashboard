import { useCallback, useEffect, useMemo, useState } from "react";
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
  Timer,
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
import { ExpenseHistoryDialog } from "./ExpenseHistoryDialog";

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

function formatDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  return hours ? `${hours}h ${String(minutes).padStart(2, "0")}min` : `${minutes} min`;
}

function formatReportPeriod(points: Array<{ activityDate: string }>): string {
  const reference = points.at(-1)?.activityDate;
  if (!reference) return "Mês atual";
  const date = new Date(`${reference}T12:00:00`);
  const month = new Intl.DateTimeFormat("pt-BR", { month: "long", year: "numeric" }).format(date);
  return `1 – ${date.getDate()} de ${month}`;
}

export function ReportsPage({ gateway, onOpenHistory, onOpenManagement }: { gateway: AppGateway; onOpenHistory: () => void; onOpenManagement: () => void }) {
  const [reports, setReports] = useState<ReportsOverviewResult>({ state: "empty" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [targetDialogOpen, setTargetDialogOpen] = useState(false);
  const [targetValue, setTargetValue] = useState("");
  const [targetSaving, setTargetSaving] = useState(false);
  const [targetError, setTargetError] = useState<string | null>(null);
  const [expenseHistoryOpen, setExpenseHistoryOpen] = useState(false);
  const [salesView, setSalesView] = useState<"monthly" | "recent">("monthly");

  const loadReports = useCallback(async () => {
    const res = await gateway.getReportsOverview();
    setReports(res);
    setError(null);
  }, [gateway]);

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

  const monthlySalesData = useMemo(() => {
    if (reports.state !== "ready") return [];
    return (reports.monthlySalesHistory ?? []).map((pt) => ({
      name: pt.monthLabel,
      amountBrl: pt.salesAmountMinor / 100,
      count: pt.salesCount,
      isPartial: pt.isPartial,
      monthKey: pt.monthKey,
    }));
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

  const { kpis, dailyEvolution, monthlyComparison, financialSummary, recentSales, recentMovements, workRoutineHistory, monthlyTarget, topCharacters } = reports;
  const reportPeriod = formatReportPeriod(dailyEvolution);
  const routineWeekChange = workRoutineHistory.previousWeekSeconds > 0
    ? Math.round(((workRoutineHistory.weekSeconds - workRoutineHistory.previousWeekSeconds) / workRoutineHistory.previousWeekSeconds) * 100)
    : workRoutineHistory.weekSeconds > 0 ? 100 : 0;
  const routineDailyAverage = workRoutineHistory.activeDaysInMonth > 0
    ? Math.round(workRoutineHistory.monthSeconds / workRoutineHistory.activeDaysInMonth)
    : 0;
  const openTargetDialog = () => {
    setTargetValue(String(monthlyTarget.targetGold));
    setTargetError(null);
    setTargetDialogOpen(true);
  };
  const saveTarget = async () => {
    const value = Number(targetValue.replace(/\D/g, ""));
    if (!Number.isSafeInteger(value) || value <= 0) { setTargetError("Informe uma meta em gold maior que zero."); return; }
    setTargetSaving(true); setTargetError(null);
    try { await gateway.setMonthlyTarget(monthlyTarget.targetMonth ?? new Date().toISOString().slice(0, 7), value); await loadReports(); setTargetDialogOpen(false); }
    catch (err: unknown) { setTargetError(err instanceof Error ? err.message : "Não foi possível salvar a meta."); }
    finally { setTargetSaving(false); }
  };

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
            <span>{reportPeriod}</span>
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
            <span className="kpi-subtext">
              Mês passado (completo): {currencyFormat.format((kpis.previousSalesMinor ?? 0) / 100)}
            </span>
            {kpis.salesChangeStatus === "no_baseline" ? (
              <span className="kpi-badge kpi-badge--neutral">Sem base comparável</span>
            ) : kpis.salesChangePercent !== null ? (
              <span className={`kpi-badge ${kpis.salesChangePercent >= 0 ? "kpi-badge--positive" : "kpi-badge--negative"}`}>
                {kpis.salesChangePercent >= 0 ? "+" : ""}{kpis.salesChangePercent}% vs mês passado
              </span>
            ) : (
              <span className="kpi-badge kpi-badge--neutral">Sem movimentação</span>
            )}
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
            <span className="kpi-subtext">
              Mês passado (completo): {numberFormat.format(kpis.previousFarmGold ?? 0)} gold
            </span>
            {kpis.farmGoldChangeStatus === "no_baseline" ? (
              <span className="kpi-badge kpi-badge--neutral">Sem base comparável</span>
            ) : kpis.farmGoldChangePercent !== null ? (
              <span className={`kpi-badge ${kpis.farmGoldChangePercent >= 0 ? "kpi-badge--positive" : "kpi-badge--negative"}`}>
                {kpis.farmGoldChangePercent >= 0 ? "+" : ""}{kpis.farmGoldChangePercent}% vs mês passado
              </span>
            ) : (
              <span className="kpi-badge kpi-badge--neutral">Sem movimentação</span>
            )}
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
            <span className="kpi-subtext">gold/dia farmado</span>
          </div>
        </div>

        {/* Card 5: Sacos PvE ganhos */}
        <div className="kpi-card kpi-card--teal">
          <div className="kpi-icon kpi-icon--teal">
            <Tote size={24} weight="duotone" />
          </div>
          <div className="kpi-body">
            <span className="kpi-label">Sacos PvE ganhos</span>
            <strong className="kpi-value">{numberFormat.format(kpis.monthlyPveBagsEarned)}</strong>
            <span className="kpi-subtext">
              Mês passado (completo): {numberFormat.format(kpis.previousPveBagsEarned ?? 0)} sacos
            </span>
            {kpis.pveBagsEarnedChangeStatus === "no_baseline" ? (
              <span className="kpi-badge kpi-badge--neutral">Sem base comparável</span>
            ) : kpis.pveBagsEarnedChangePercent !== null ? (
              <span className={`kpi-badge ${kpis.pveBagsEarnedChangePercent >= 0 ? "kpi-badge--positive" : "kpi-badge--negative"}`}>
                {kpis.pveBagsEarnedChangePercent >= 0 ? "+" : ""}{kpis.pveBagsEarnedChangePercent}% vs mês passado
              </span>
            ) : (
              <span className="kpi-badge kpi-badge--neutral">Sem movimentação</span>
            )}
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
                  contentStyle={{ background: "#0c2232", border: "1px solid #294054", borderRadius: 8, fontSize: 12, color: "#edf3fb" }} itemStyle={{ color: "#edf3fb" }} labelStyle={{ color: "#c7d8e8" }}
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

        {/* Comparativo de farm */}
        <div className="panel chart-panel chart-panel--side">
          <div className="chart-heading">
            <div>
              <h2>Comparativo de farm</h2>
              <span className="chart-sub">Mês atual até o dia indicado vs mês passado completo</span>
            </div>
          </div>
          <div className="comparative-body">
            <div className="comparative-highlight">
              {monthlyComparison.growthStatus === "no_baseline" ? (
                <span className="text-slate-300 font-bold text-lg">Sem base comparável</span>
              ) : (
                <span className={`${(monthlyComparison.growthPercent ?? 0) >= 0 ? "text-emerald-400" : "text-rose-400"} font-bold text-xl`}>
                  {(monthlyComparison.growthPercent ?? 0) >= 0 ? "+" : ""}{monthlyComparison.growthPercent}%
                </span>
              )}
              <span className="text-xs text-slate-400 block">
                {monthlyComparison.currentPeriodLabel || monthlyComparison.currentMonthName} vs {monthlyComparison.previousPeriodLabel || monthlyComparison.previousMonthName}
              </span>
              <span className="text-xs text-slate-300 font-medium block mt-0.5">
                {formatCompactGold(monthlyComparison.currentMonthGold)} vs {formatCompactGold(monthlyComparison.previousMonthGold)}
              </span>
            </div>
            <div className="chart-container" style={{ width: "100%", height: 155 }}>
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
                    contentStyle={{ background: "#0c2232", border: "1px solid #294054", borderRadius: 8, fontSize: 12, color: "#edf3fb" }} itemStyle={{ color: "#edf3fb" }} labelStyle={{ color: "#c7d8e8" }}
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

      {/* Row 2: Últimas movimentações + Resumo Financeiro */}
      <section className="reports-grid-row reports-grid-row--charts">
        <div className="panel chart-panel chart-panel--main recent-movements-panel">
          <div className="chart-heading">
            <div>
              <h2>Últimas movimentações</h2>
              <span className="chart-sub">Conferência rápida do que entrou e saiu no farm</span>
            </div>
          </div>
          {recentMovements.length ? <div className="recent-movements-list">{recentMovements.map((movement) => <article className={`recent-movement recent-movement--${movement.kind.split("_")[0]}`} key={movement.id}>
            <span className="recent-movement__icon"><Receipt size={17} /></span>
            <div className="recent-movement__main"><strong>{movement.title}</strong><span>{movement.detail || "Sem detalhe adicional"}</span></div>
            <div className="recent-movement__values">{movement.goldAmount !== null && <span className={movement.kind === "expense" || movement.kind === "tower" ? "text-rose-300" : "text-amber-300"}>{movement.kind === "expense" || movement.kind === "tower" ? "−" : "+"}{numberFormat.format(movement.goldAmount)} gold</span>}{movement.pveBags !== null && <span className="text-teal-300">+{numberFormat.format(movement.pveBags)} sacos</span>}{movement.amountMinor !== null && <span className="text-emerald-400">{currencyFormat.format(movement.amountMinor / 100)}</span>}<time>{formatShortDate(movement.occurredAt)}</time></div>
          </article>)}</div> : <div className="recent-movements-empty">Nenhuma movimentação registrada ainda.</div>}
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
                Itens e sacos vendidos
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
            <div className="fin-row">
              <span className="fin-row-left"><span className="fin-row-icon fin-row-icon--purple"><Coins size={16} /></span>Despesas em gold</span>
              <strong className="fin-row-value text-rose-300">{numberFormat.format(financialSummary.expensesGold)}</strong>
            </div>
            <div className="fin-row fin-row--detail"><span>VIP</span><strong>{numberFormat.format(financialSummary.vipExpensesGold)}</strong><span>Torre</span><strong>{numberFormat.format(financialSummary.towerExpensesGold)}</strong></div>
            <div className="fin-row fin-row--detail"><span>Outras despesas</span><strong>{numberFormat.format(financialSummary.manualExpensesGold)}</strong></div>
            <div className="panel-footer-link"><button type="button" onClick={() => setExpenseHistoryOpen(true)}>Ver e corrigir despesas <ArrowRight size={13} className="inline ml-1" /></button></div>
          </div>
        </div>
      </section>

      {/* Row 3: Últimas vendas + Meta do mês + Top personagens */}
      <section className="reports-grid-row reports-grid-row--bottom">
        {/* Vendas e faturamento */}
        <div className="panel bottom-panel bottom-panel--sales">
          <div className="panel-heading sales-panel-heading">
            <div>
              <h2>Vendas em R$</h2>
              <span className="chart-sub">Faturamento e histórico mensal</span>
            </div>
            <div className="sales-view-toggle">
              <button
                type="button"
                className={`sales-toggle-btn ${salesView === "monthly" ? "sales-toggle-btn--active" : ""}`}
                onClick={() => setSalesView("monthly")}
              >
                Por mês
              </button>
              <button
                type="button"
                className={`sales-toggle-btn ${salesView === "recent" ? "sales-toggle-btn--active" : ""}`}
                onClick={() => setSalesView("recent")}
              >
                Recentes
              </button>
            </div>
          </div>

          {salesView === "monthly" ? (
            <div className="monthly-sales-view">
              {monthlySalesData.length ? (
                <>
                  <div className="chart-container" style={{ width: "100%", height: 145 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={monthlySalesData} margin={{ top: 12, right: 10, bottom: 0, left: -5 }}>
                        <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.06)" />
                        <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: "#8293a5", fontSize: 10 }} />
                        <YAxis
                          axisLine={false}
                          tickLine={false}
                          tick={{ fill: "#8293a5", fontSize: 10 }}
                          tickFormatter={(v) => `R$${v}`}
                        />
                        <Tooltip
                          formatter={(value, _name, item) => {
                            const pt = (item as { payload?: { count: number; isPartial: boolean } }).payload;
                            const count = pt?.count ?? 0;
                            const isPart = pt?.isPartial ?? false;
                            return [
                              `${currencyFormat.format(Number(value))} (${count} ${count === 1 ? "venda" : "vendas"}${isPart ? " · parcial" : ""})`,
                              "Faturamento",
                            ];
                          }}
                          contentStyle={{ background: "#0c2232", border: "1px solid #294054", borderRadius: 8, fontSize: 12, color: "#edf3fb" }}
                          itemStyle={{ color: "#edf3fb" }}
                          labelStyle={{ color: "#c7d8e8" }}
                        />
                        <Bar dataKey="amountBrl" radius={[4, 4, 0, 0]} maxBarSize={40}>
                          {monthlySalesData.map((entry, index) => (
                            <Cell
                              key={`sales-bar-${index}`}
                              fill={entry.isPartial ? "#38bdf8" : "#10b981"}
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="monthly-sales-summary-strip">
                    {monthlySalesData.map((m) => (
                      <div
                        key={m.monthKey}
                        className={`monthly-sales-pill ${m.isPartial ? "monthly-sales-pill--partial" : ""}`}
                        title={m.isPartial ? "Mês atual em andamento" : undefined}
                      >
                        <span className="monthly-sales-pill__label">
                          {m.name}
                          {m.isPartial && <span className="monthly-partial-tag">parcial</span>}
                        </span>
                        <strong className="monthly-sales-pill__val">
                          {currencyFormat.format(m.amountBrl)}
                        </strong>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="text-center py-6 text-slate-500 text-sm">
                  Nenhum faturamento registrado nos últimos meses
                </div>
              )}
            </div>
          ) : (
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
          )}
          <div className="panel-footer-link">
            <button type="button" onClick={onOpenHistory}>Ver todas as vendas <ArrowRight size={13} className="inline ml-1" /></button>
          </div>
        </div>

        {/* Meta do mês */}
        <div className="panel bottom-panel bottom-panel--target target-panel-action" role="button" tabIndex={0} onClick={openTargetDialog} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") openTargetDialog(); }} aria-label="Definir meta mensal de gold">
          <div className="panel-heading">
            <h2>Meta do mês</h2>
            <Target size={20} className="text-indigo-400" />
          </div>
          <div className="target-body">
            <div className="target-header-line">
              <span className="text-slate-300 font-medium">Meta: {numberFormat.format(monthlyTarget.targetGold)} gold equivalente</span>
              <span className="text-slate-200 font-bold">{numberFormat.format(monthlyTarget.currentTotalValueGold)} ({monthlyTarget.percentage}%)</span>
            </div>
            {/* Progress bar */}
            <div className="target-progress-track">
              <div
                className="target-progress-fill"
                style={{ width: `${Math.min(100, monthlyTarget.percentage)}%` }}
              />
            </div>
            <p className="target-hint">
              Faltam <strong className="text-amber-300">{numberFormat.format(monthlyTarget.remainingGold)} gold equivalente</strong> para atingir a meta
            </p>
            <p className="target-hint target-hint--detail">{numberFormat.format(monthlyTarget.currentGold)} gold + {numberFormat.format(monthlyTarget.currentPveBags)} Sacos PvE{monthlyTarget.pveBagUnitValueGold ? ` (${numberFormat.format(monthlyTarget.pveBagUnitValueGold)}g cada)` : " (sem cotação)"}</p>
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
            <button type="button" onClick={onOpenManagement}>Ver todos os personagens <ArrowRight size={13} className="inline ml-1" /></button>
          </div>
        </div>
      </section>
      <section className="panel routine-history-panel" aria-labelledby="routine-history-title">
        <div className="panel-heading">
          <div><h2 id="routine-history-title">Tempo de rotina</h2><span className="chart-sub">Sessões com 5 min ativos ou mais; pausas não contam</span></div>
          <Timer size={20} className="text-indigo-300" weight="duotone" />
        </div>
        <div className="routine-history-summary">
          <div><span>No mês</span><strong>{formatDuration(workRoutineHistory.monthSeconds)}</strong><small>{workRoutineHistory.monthSessionCount} sessões encerradas</small></div>
          <div><span>Esta semana</span><strong>{formatDuration(workRoutineHistory.weekSeconds)}</strong><small className={routineWeekChange >= 0 ? "text-emerald-400" : "text-rose-300"}>{routineWeekChange >= 0 ? "+" : ""}{routineWeekChange}% vs semana passada</small></div>
          <div><span>Média por dia ativo</span><strong>{formatDuration(routineDailyAverage)}</strong><small>{workRoutineHistory.activeDaysInMonth} dias com rotina</small></div>
        </div>
        {workRoutineHistory.recentSessions.length ? <div className="routine-history-table-wrap"><table className="routine-history-table"><thead><tr><th>Data</th><th>Início</th><th>Fim</th><th>Duração</th></tr></thead><tbody>{workRoutineHistory.recentSessions.map((session) => <tr key={session.id}><td>{formatShortDate(session.finishedAt).slice(0, 10)}</td><td>{formatShortDate(session.startedAt).slice(-5)}</td><td>{formatShortDate(session.finishedAt).slice(-5)}</td><td><strong>{formatDuration(session.elapsedSeconds)}</strong></td></tr>)}</tbody></table></div> : <div className="routine-history-empty">Encerre uma rotina com pelo menos 5 min ativos para ela aparecer aqui.</div>}
      </section>
      {targetDialogOpen && <div className="dialog-backdrop" role="presentation" onMouseDown={() => !targetSaving && setTargetDialogOpen(false)}>
        <section className="edit-dialog target-dialog" role="dialog" aria-modal="true" aria-labelledby="monthly-target-title" onMouseDown={(event) => event.stopPropagation()}>
          <header><div className="edit-dialog__identity"><i><Target size={22} weight="duotone" /></i><div><h2 id="monthly-target-title">Meta de {monthlyTarget.targetMonth ?? "este mês"}</h2><span>Gold realizado e Sacos PvE valorados pela cotação atual contam para ela.</span></div></div></header>
          <div className="edit-dialog__body"><label>Meta em gold equivalente<input autoFocus inputMode="numeric" value={targetValue} onChange={(event) => setTargetValue(event.target.value.replace(/\D/g, ""))} onKeyDown={(event) => { if (event.key === "Enter") void saveTarget(); }} /></label>{targetError && <div className="error-banner" role="alert">{targetError}</div>}</div>
          <footer><button className="secondary-button" type="button" disabled={targetSaving} onClick={() => setTargetDialogOpen(false)}>Cancelar</button><button className="primary-button" type="button" disabled={targetSaving} onClick={() => void saveTarget()}>{targetSaving ? "Salvando..." : "Salvar meta"}</button></footer>
        </section>
      </div>}
      {expenseHistoryOpen && <ExpenseHistoryDialog gateway={gateway} onClose={() => setExpenseHistoryOpen(false)} onChanged={loadReports} />}
    </div>
  );
}
