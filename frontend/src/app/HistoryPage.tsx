import {
  CalendarBlank,
  CaretDown,
  CaretUp,
  Check,
  CheckCircle,
  Clock,
  Funnel,
  ShieldChevron,
  Sparkle,
  TrendUp,
  UsersThree,
  Warning,
  X,
} from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";

import type { AppGateway, CharacterDayResult, HistoryDayDetailResult, HistoryDaySummary, ManagementOverviewResult } from "../gateway/AppGateway";
import { CharacterDayDialog } from "./CharacterDayDialog";

const numberFormat = new Intl.NumberFormat("pt-BR");
const fullDateFormat = new Intl.DateTimeFormat("pt-BR", {
  weekday: "long",
  day: "2-digit",
  month: "long",
  year: "numeric",
});
const shortDateFormat = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});
const timeFormat = new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit" });

function formatCompactNumber(num: number): string {
  if (num >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  }
  if (num >= 1_000) {
    return `${(num / 1_000).toFixed(num % 1_000 === 0 ? 0 : 1).replace(/\.0$/, "")}k`;
  }
  return String(num);
}

function formatDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}h${minutes > 0 ? String(minutes).padStart(2, "0") : "00"}`;
  }
  return `${minutes}min`;
}

function formatDetailedDuration(totalSeconds: number): string {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  if (hours > 0) {
    return `${hours}h ${String(minutes).padStart(2, "0")}min`;
  }
  return `${minutes} min`;
}

type DayStatus = "complete" | "partial" | "empty";

function getDayStatus(day: HistoryDaySummary): DayStatus {
  if (day.runsCompleted === 0 && day.towerTotal === 0 && day.dropsCount === 0 && (day.routineDurationSeconds ?? 0) === 0) {
    return "empty";
  }
  if (day.charactersTotal > 0 && day.charactersCompleted >= day.charactersTotal) {
    return "complete";
  }
  if (day.charactersTotal === 0 && day.runsCompleted > 0) {
    return "complete";
  }
  return "partial";
}

type EventFilter = "all" | "incomplete" | "tower" | "drops" | "routine";

const eventFilterLabels: Record<EventFilter, string> = {
  all: "Todos",
  incomplete: "Incompletos",
  tower: "Torre",
  drops: "Drops",
  routine: "Rotinas",
};

interface HistoryPageProps {
  gateway: AppGateway;
  management: ManagementOverviewResult | null;
}

export function HistoryPage({ gateway, management }: HistoryPageProps) {
  const [days, setDays] = useState<HistoryDaySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [dayDetail, setDayDetail] = useState<HistoryDayDetailResult | null>(null);
  const [charactersExpanded, setCharactersExpanded] = useState(false);

  // Filters
  const [datePreset, setDatePreset] = useState<"7" | "30" | "all">("30");
  const [eventFilter, setEventFilter] = useState<EventFilter>("all");
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");
  const [selectedCharacterId, setSelectedCharacterId] = useState<string>("");

  const accounts = useMemo(() => (management?.state === "ready" ? management.accounts : []), [management]);
  const availableCharacters = useMemo(() => {
    if (!selectedAccountId) {
      return accounts.flatMap((acc) => acc.characters);
    }
    return accounts.find((acc) => acc.id === selectedAccountId)?.characters ?? [];
  }, [accounts, selectedAccountId]);

  // Compute startDate based on preset
  const filterParams = useMemo(() => {
    let startDate: string | undefined;
    if (datePreset !== "all") {
      const d = new Date();
      d.setDate(d.getDate() - Number(datePreset));
      startDate = d.toISOString().slice(0, 10);
    }
    return {
      startDate,
      accountId: selectedAccountId || undefined,
      characterId: selectedCharacterId || undefined,
    };
  }, [datePreset, selectedAccountId, selectedCharacterId]);

  useEffect(() => {
    let active = true;
    gateway
      .getHistoryOverview(filterParams)
      .then((res) => {
        if (!active) return;
        setDays(res.days);
        setLoading(false);
        setError(null);
        if (res.days.length > 0) {
          setSelectedDate((curr) =>
            curr && res.days.some((d) => d.activityDate === curr) ? curr : res.days[0].activityDate,
          );
        } else {
          setSelectedDate(null);
          setDayDetail(null);
        }
      })
      .catch((err: unknown) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : "Falha ao carregar histórico");
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [gateway, filterParams]);

  // Event counts for filter badges
  const eventCounts = useMemo(() => {
    return {
      all: days.length,
      incomplete: days.filter((d) => d.charactersTotal > 0 && d.charactersCompleted < d.charactersTotal).length,
      tower: days.filter((d) => d.towerTotal > 0).length,
      drops: days.filter((d) => d.dropsCount > 0).length,
      routine: days.filter((d) => (d.routineDurationSeconds ?? 0) > 0).length,
    };
  }, [days]);

  // Days filtered by event type
  const filteredDays = useMemo(() => {
    if (eventFilter === "all") return days;
    if (eventFilter === "incomplete") {
      return days.filter((d) => d.charactersTotal > 0 && d.charactersCompleted < d.charactersTotal);
    }
    if (eventFilter === "tower") {
      return days.filter((d) => d.towerTotal > 0);
    }
    if (eventFilter === "drops") {
      return days.filter((d) => d.dropsCount > 0);
    }
    if (eventFilter === "routine") {
      return days.filter((d) => (d.routineDurationSeconds ?? 0) > 0);
    }
    return days;
  }, [days, eventFilter]);

  // Effective selected date respecting active filters
  const activeSelectedDate = useMemo(() => {
    if (filteredDays.length === 0) return null;
    if (selectedDate && filteredDays.some((d) => d.activityDate === selectedDate)) {
      return selectedDate;
    }
    return filteredDays[0].activityDate;
  }, [filteredDays, selectedDate]);

  useEffect(() => {
    if (!activeSelectedDate) {
      return;
    }
    let active = true;
    gateway
      .getHistoryDayDetail(activeSelectedDate, {
        accountId: selectedAccountId || undefined,
        characterId: selectedCharacterId || undefined,
      })
      .then((res) => {
        if (!active) return;
        setDayDetail(res);
        setCharactersExpanded(false);
      })
      .catch(() => {
        if (!active) return;
        setDayDetail(null);
      });
    return () => {
      active = false;
    };
  }, [gateway, activeSelectedDate, selectedAccountId, selectedCharacterId]);

  const detailLoading = Boolean(activeSelectedDate && (!dayDetail || dayDetail.activityDate !== activeSelectedDate));

  // Period Aggregated Summary
  const periodStats = useMemo(() => {
    if (!days.length) return null;
    const totalRuns = days.reduce((sum, d) => sum + d.runsCompleted, 0);
    const totalGold = days.reduce((sum, d) => sum + d.goldEarned, 0);
    const totalBags = days.reduce((sum, d) => sum + d.pveBagsEarned, 0);
    const totalRoutineSeconds = days.reduce((sum, d) => sum + (d.routineDurationSeconds ?? 0), 0);
    const totalCharsPossible = days.reduce((sum, d) => sum + d.charactersTotal, 0);
    const totalCharsCompleted = days.reduce((sum, d) => sum + d.charactersCompleted, 0);
    const avgCompletionRate = totalCharsPossible > 0 ? Math.round((totalCharsCompleted / totalCharsPossible) * 100) : 100;
    const avgDailyGold = Math.round(totalGold / days.length);

    return {
      activeDays: days.length,
      totalRuns,
      totalGold,
      totalBags,
      totalRoutineSeconds,
      avgCompletionRate,
      avgDailyGold,
    };
  }, [days]);

  // Day breakdown
  const incompleteCharacters = useMemo(() => {
    if (!dayDetail) return [];
    return dayDetail.characters.filter((char) => char.completedDungeons < char.selectedDungeons);
  }, [dayDetail]);

  const completeCharacters = useMemo(() => {
    if (!dayDetail) return [];
    return dayDetail.characters.filter((char) => char.completedDungeons >= char.selectedDungeons);
  }, [dayDetail]);

  const allCharactersCompleted = incompleteCharacters.length === 0 && (dayDetail?.characters.length ?? 0) > 0;

  const selectedDaySummary = useMemo(() => {
    return days.find((d) => d.activityDate === activeSelectedDate) ?? null;
  }, [days, activeSelectedDate]);

  const selectedDayStatus = selectedDaySummary ? getDayStatus(selectedDaySummary) : "empty";

  const [editingCharacterDay, setEditingCharacterDay] = useState<CharacterDayResult | null>(null);
  const [characterSaving, setCharacterSaving] = useState(false);
  const [characterError, setCharacterError] = useState<string | null>(null);
  const [bulkSaving, setBulkSaving] = useState(false);

  async function openCharacterDay(characterId: string) {
    if (!activeSelectedDate) return;
    setCharacterError(null);
    try {
      const charDay = await gateway.getCharacterDay(characterId, activeSelectedDate);
      setEditingCharacterDay(charDay);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Não foi possível carregar os dados do personagem");
    }
  }

  async function saveCharacterDay(completedIds: string[]) {
    if (!editingCharacterDay || !activeSelectedDate) return;
    setCharacterSaving(true);
    setCharacterError(null);
    try {
      await gateway.saveCharacterDay(
        editingCharacterDay.characterId,
        completedIds,
        editingCharacterDay.activityDate,
      );
      setEditingCharacterDay(null);
      const [updatedDetail, updatedOverview] = await Promise.all([
        gateway.getHistoryDayDetail(activeSelectedDate, {
          accountId: selectedAccountId || undefined,
          characterId: selectedCharacterId || undefined,
        }),
        gateway.getHistoryOverview(filterParams),
      ]);
      setDayDetail(updatedDetail);
      setDays(updatedOverview.days);
    } catch (err: unknown) {
      setCharacterError(err instanceof Error ? err.message : "Não foi possível salvar o resumo");
    } finally {
      setCharacterSaving(false);
    }
  }

  async function markAllIncomplete() {
    if (!activeSelectedDate || !dayDetail || incompleteCharacters.length === 0) return;
    const dateFormatted = fullDateFormat.format(new Date(activeSelectedDate + "T12:00:00"));
    const confirmed = window.confirm(
      `Deseja marcar todas as dungeons de todos os ${incompleteCharacters.length} personagens incompletos como concluídas para ${dateFormatted}?`,
    );
    if (!confirmed) return;
    setBulkSaving(true);
    setError(null);
    try {
      for (const char of incompleteCharacters) {
        const charDay = await gateway.getCharacterDay(char.id, activeSelectedDate);
        const allIds = charDay.dungeons.map((d) => d.characterActivityId);
        await gateway.saveCharacterDay(char.id, allIds, activeSelectedDate);
      }
      const [updatedDetail, updatedOverview] = await Promise.all([
        gateway.getHistoryDayDetail(activeSelectedDate, {
          accountId: selectedAccountId || undefined,
          characterId: selectedCharacterId || undefined,
        }),
        gateway.getHistoryOverview(filterParams),
      ]);
      setDayDetail(updatedDetail);
      setDays(updatedOverview.days);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erro ao concluir personagens pendentes");
    } finally {
      setBulkSaving(false);
    }
  }

  return (
    <div className="management-page history-page">
      <div className="page-title">
        <div>
          <p className="page-kicker">Registro contínuo</p>
          <h1>Histórico de farm</h1>
          <span>Consulte o passado destacando exceções, progresso diário, sessões de torre e drops obtidos.</span>
        </div>
      </div>

      {error && <div className="error-banner" role="alert">{error}</div>}

      {/* Filter Bar */}
      <section className="panel history-filter-bar">
        <div className="history-filter-group">
          <Funnel size={16} weight="duotone" />
          <span className="filter-label">Período:</span>
          <div className="filter-chips">
            <button
              type="button"
              className={datePreset === "7" ? "filter-chip filter-chip--active" : "filter-chip"}
              onClick={() => setDatePreset("7")}
            >
              Últimos 7 dias
            </button>
            <button
              type="button"
              className={datePreset === "30" ? "filter-chip filter-chip--active" : "filter-chip"}
              onClick={() => setDatePreset("30")}
            >
              Últimos 30 dias
            </button>
            <button
              type="button"
              className={datePreset === "all" ? "filter-chip filter-chip--active" : "filter-chip"}
              onClick={() => setDatePreset("all")}
            >
              Todo o período
            </button>
          </div>
        </div>

        <div className="history-filter-selects">
          <label>
            <span>Conta:</span>
            <select
              value={selectedAccountId}
              onChange={(e) => {
                setSelectedAccountId(e.target.value);
                setSelectedCharacterId("");
              }}
            >
              <option value="">Todas as contas</option>
              {accounts.map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.name} ({acc.serverName})
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Personagem:</span>
            <select
              value={selectedCharacterId}
              onChange={(e) => setSelectedCharacterId(e.target.value)}
            >
              <option value="">Todos os personagens</option>
              {availableCharacters.map((char) => (
                <option key={char.id} value={char.id}>
                  {char.name} ({char.className})
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      {/* Event Type Filter Chips */}
      {days.length > 0 && (
        <section className="panel history-event-filters-bar">
          <div className="history-filter-group">
            <span className="filter-label">Filtrar dias por:</span>
            <div className="filter-chips">
              <button
                type="button"
                className={eventFilter === "all" ? "filter-chip filter-chip--active" : "filter-chip"}
                onClick={() => setEventFilter("all")}
              >
                Todos <span className="chip-count">({eventCounts.all})</span>
              </button>
              <button
                type="button"
                className={eventFilter === "incomplete" ? "filter-chip filter-chip--active" : "filter-chip"}
                onClick={() => setEventFilter("incomplete")}
              >
                Incompletos <span className="chip-count">({eventCounts.incomplete})</span>
              </button>
              <button
                type="button"
                className={eventFilter === "tower" ? "filter-chip filter-chip--active" : "filter-chip"}
                onClick={() => setEventFilter("tower")}
              >
                Torre <span className="chip-count">({eventCounts.tower})</span>
              </button>
              <button
                type="button"
                className={eventFilter === "drops" ? "filter-chip filter-chip--active" : "filter-chip"}
                onClick={() => setEventFilter("drops")}
              >
                Drops <span className="chip-count">({eventCounts.drops})</span>
              </button>
              <button
                type="button"
                className={eventFilter === "routine" ? "filter-chip filter-chip--active" : "filter-chip"}
                onClick={() => setEventFilter("routine")}
              >
                Rotinas <span className="chip-count">({eventCounts.routine})</span>
              </button>
            </div>
          </div>
        </section>
      )}

      {/* Period Aggregated Summary Strip */}
      {periodStats && (
        <section className="panel history-period-summary">
          <div className="period-stat-item">
            <small>Dias registrados</small>
            <strong>{periodStats.activeDays} dias</strong>
          </div>
          <div className="period-stat-divider" />
          <div className="period-stat-item">
            <small>Runs totais</small>
            <strong>{numberFormat.format(periodStats.totalRuns)}</strong>
          </div>
          <div className="period-stat-divider" />
          <div className="period-stat-item">
            <small>Gold acumulado</small>
            <strong className="gold-text">{formatCompactNumber(periodStats.totalGold)} gold</strong>
          </div>
          <div className="period-stat-divider" />
          <div className="period-stat-item">
            <small>Sacos PvE</small>
            <strong>{numberFormat.format(periodStats.totalBags)}</strong>
          </div>
          {periodStats.totalRoutineSeconds > 0 && (
            <>
              <div className="period-stat-divider" />
              <div className="period-stat-item">
                <small>Tempo em rotina</small>
                <strong>{formatDetailedDuration(periodStats.totalRoutineSeconds)}</strong>
              </div>
            </>
          )}
          <div className="period-stat-divider" />
          <div className="period-stat-item">
            <small>Conclusão média</small>
            <strong className={periodStats.avgCompletionRate >= 90 ? "text-emerald-400" : "text-amber-300"}>
              {periodStats.avgCompletionRate}%
            </strong>
          </div>
        </section>
      )}

      {/* Main Grid: Days List on left, Detail on right */}
      {loading ? (
        <div className="page-state">
          <CalendarBlank size={32} weight="duotone" />
          <strong>Carregando histórico...</strong>
        </div>
      ) : days.length === 0 ? (
        <div className="inline-empty large">
          <CalendarBlank size={32} weight="duotone" />
          <strong>Nenhum registro encontrado</strong>
          <span>Não há atividades registradas para o período ou filtros selecionados.</span>
        </div>
      ) : (
        <div className="history-layout">
          {/* Days Master List */}
          <aside className="history-days-list">
            <div className="history-days-header">
              <h3>Dias ({filteredDays.length})</h3>
              {eventFilter !== "all" && (
                <span className="active-filter-indicator">
                  Filtro: {eventFilterLabels[eventFilter]}
                </span>
              )}
            </div>

            {filteredDays.length === 0 ? (
              <div className="history-days-empty">
                <span>Nenhum dia corresponde ao filtro selecionado.</span>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setEventFilter("all")}
                >
                  Ver todos os dias
                </button>
              </div>
            ) : (
              <div className="history-day-cards">
                {filteredDays.map((day) => {
                  const isSelected = day.activityDate === activeSelectedDate;
                  const formattedDate = shortDateFormat.format(new Date(day.activityDate + "T12:00:00"));
                  const status = getDayStatus(day);

                  return (
                    <button
                      key={day.activityDate}
                      type="button"
                      className={isSelected ? "history-day-card history-day-card--selected" : "history-day-card"}
                      onClick={() => setSelectedDate(day.activityDate)}
                    >
                      <div className="day-card-header">
                        <strong>{formattedDate}</strong>
                        <span className={`day-status-pill day-status-pill--${status}`}>
                          {status === "complete" && "✓ Completo"}
                          {status === "partial" && "Parcial"}
                          {status === "empty" && "Sem atividade"}
                        </span>
                      </div>

                      <div className="day-card-metrics">
                        <span>{formatCompactNumber(day.goldEarned)} gold</span>
                        <span className="dot-sep">·</span>
                        <span>{day.pveBagsEarned} sacos</span>
                        <span className="dot-sep">·</span>
                        <span>{day.runsCompleted} runs</span>
                      </div>

                      <div className="day-card-tags">
                        {day.routineDurationSeconds ? (
                          <span className="day-card-tag day-card-tag--routine" title="Duração da rotina">
                            <Clock size={12} weight="bold" /> {formatDuration(day.routineDurationSeconds)} de rotina
                          </span>
                        ) : null}
                        {day.towerTotal > 0 && (
                          <span className="day-card-tag day-card-tag--tower" title="Sessão de Torre">
                            <ShieldChevron size={12} weight="bold" /> {day.towerCompleted ? "Torre concluída" : "Torre parcial"}
                          </span>
                        )}
                        {day.dropsCount > 0 && (
                          <span className="day-card-tag day-card-tag--drops" title="Drops raros">
                            <Sparkle size={12} weight="bold" /> {day.dropsCount} {day.dropsCount === 1 ? "drop" : "drops"}
                          </span>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </aside>

          {/* Selected Day Detail */}
          <main className="history-day-main">
            {detailLoading || !dayDetail ? (
              <div className="panel history-detail-loading">
                <CalendarBlank size={28} weight="duotone" />
                <span>Carregando detalhes do dia...</span>
              </div>
            ) : (
              <div className="history-detail-container">
                {/* 1. Day Summary Hero */}
                <section className="panel history-day-hero">
                  <div className="history-hero-title-area">
                    <div className="flex items-center gap-2">
                      <span className="eyebrow">Resumo do dia</span>
                      <span className={`day-status-pill day-status-pill--${selectedDayStatus}`}>
                        {selectedDayStatus === "complete" && "✓ Completo"}
                        {selectedDayStatus === "partial" && "Parcial"}
                        {selectedDayStatus === "empty" && "Sem atividade"}
                      </span>
                    </div>
                    <h2>{fullDateFormat.format(new Date(dayDetail.activityDate + "T12:00:00"))}</h2>
                  </div>

                  <div className="history-hero-kpis">
                    <div className="kpi-box">
                      <small>Runs feitas</small>
                      <strong>{dayDetail.runsCompleted}</strong>
                    </div>
                    <div className="kpi-box">
                      <small>Ouro obtido</small>
                      <strong className="gold-text">{numberFormat.format(dayDetail.goldEarned)} gold</strong>
                    </div>
                    <div className="kpi-box">
                      <small>Sacos PvE</small>
                      <strong>{dayDetail.pveBagsEarned}</strong>
                    </div>
                    <div className="kpi-box">
                      <small>Personagens</small>
                      <strong>{completeCharacters.length}/{dayDetail.characters.length}</strong>
                    </div>
                    {dayDetail.routineDurationSeconds ? (
                      <div className="kpi-box">
                        <small>Duração da rotina</small>
                        <strong>{formatDetailedDuration(dayDetail.routineDurationSeconds)}</strong>
                      </div>
                    ) : null}
                    {dayDetail.towerSessions.length > 0 && (
                      <div className="kpi-box">
                        <small>Torre</small>
                        <strong className={dayDetail.towerSessions.some((t) => t.completed) ? "text-amber-300" : "text-rose-300"}>
                          {dayDetail.towerSessions.some((t) => t.completed) ? "Concluída" : "Incompleta"}
                        </strong>
                      </div>
                    )}
                    {dayDetail.drops.length > 0 && (
                      <div className="kpi-box">
                        <small>Drops raros</small>
                        <strong className="text-teal-300">{dayDetail.drops.length}</strong>
                      </div>
                    )}
                  </div>
                </section>

                {/* 2. Exceptions and Problems Section (Prioritized Visual Attention) */}
                {incompleteCharacters.length > 0 && (
                  <section className="panel history-exceptions-panel" aria-label="Atividades incompletas">
                    <div className="panel-heading">
                      <div className="flex items-center gap-2 text-amber-300">
                        <Warning size={18} weight="fill" className="text-amber-400" />
                        <h2>Atenção: Atividades incompletas</h2>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="badge-warning">
                          {incompleteCharacters.length} {incompleteCharacters.length === 1 ? "personagem incompleto" : "personagens incompletos"}
                        </span>
                        <button
                          type="button"
                          className="history-bulk-complete-btn"
                          disabled={bulkSaving}
                          onClick={() => void markAllIncomplete()}
                          title="Concluir todas as dungeons de todos os personagens incompletos neste dia"
                        >
                          <CheckCircle size={15} weight="bold" />
                          <span>{bulkSaving ? "Concluindo..." : "Concluir todos pendentes"}</span>
                        </button>
                      </div>
                    </div>

                    <div className="history-exceptions-list">
                      {incompleteCharacters.map((char) => {
                        const missedDungeons = char.dungeons.filter((d) => !d.completed);
                        return (
                          <div
                            key={char.id}
                            className="history-exception-card history-exception-card--action"
                            onClick={() => void openCharacterDay(char.id)}
                            role="button"
                            tabIndex={0}
                            title={`Clique para marcar dungeons de ${char.name} neste dia`}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" || e.key === " ") {
                                e.preventDefault();
                                void openCharacterDay(char.id);
                              }
                            }}
                          >
                            <div className="history-exception-header">
                              <div>
                                <strong className="char-exception-name">{char.name}</strong>
                                <span className="exception-char-meta">{char.className} · {char.accountName}</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="exception-ratio">
                                  {char.completedDungeons} / {char.selectedDungeons} dungeons
                                </span>
                                <button
                                  type="button"
                                  className="history-card-edit-btn"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    void openCharacterDay(char.id);
                                  }}
                                  title={`Marcar dungeons de ${char.name}`}
                                >
                                  <Check size={13} weight="bold" />
                                  <span>Marcar</span>
                                </button>
                              </div>
                            </div>

                            {missedDungeons.length > 0 && (
                              <div className="history-missed-list">
                                <span className="missed-label">Faltaram:</span>
                                <ul>
                                  {missedDungeons.map((d) => (
                                    <li key={d.activityId}>• {d.name}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </section>
                )}

                {/* 3. Highlights & Relevant Events */}
                <section className="panel history-highlights-panel">
                  <div className="panel-heading">
                    <h2><Sparkle size={18} weight="duotone" /> Destaques e Eventos</h2>
                  </div>
                  <div className="history-highlights-grid">
                    {allCharactersCompleted && (
                      <div className="history-highlight-item highlight-success">
                        <CheckCircle size={18} weight="fill" />
                        <span>Todos os {dayDetail.characters.length} personagens concluíram as atividades</span>
                      </div>
                    )}
                    {dayDetail.towerSessions.some((t) => t.completed) && (
                      <div className="history-highlight-item highlight-info">
                        <ShieldChevron size={18} weight="duotone" />
                        <span>Torre concluída ({dayDetail.towerSessions.filter((t) => t.completed).length} sessão/sessões)</span>
                      </div>
                    )}
                    {dayDetail.towerSessions.some((t) => !t.completed) && (
                      <div className="history-highlight-item highlight-warning">
                        <Warning size={18} weight="fill" />
                        <span>Sessão da Torre iniciada mas não concluída</span>
                      </div>
                    )}
                    {periodStats && periodStats.avgDailyGold > 0 && dayDetail.goldEarned > periodStats.avgDailyGold * 1.15 && (
                      <div className="history-highlight-item highlight-accent">
                        <TrendUp size={18} weight="bold" />
                        <span>
                          Gold acima da média recente (+{formatCompactNumber(dayDetail.goldEarned - periodStats.avgDailyGold)} vs média de {formatCompactNumber(periodStats.avgDailyGold)})
                        </span>
                      </div>
                    )}
                    {(dayDetail.routineDurationSeconds ?? 0) > 0 && (
                      <div className="history-highlight-item highlight-neutral">
                        <Clock size={18} weight="duotone" />
                        <span>Rotina de trabalho encerrada ({formatDetailedDuration(dayDetail.routineDurationSeconds!)})</span>
                      </div>
                    )}
                    {dayDetail.drops.length > 0 && (
                      <div className="history-highlight-item highlight-drops">
                        <Sparkle size={18} weight="fill" />
                        <span>{dayDetail.drops.length} {dayDetail.drops.length === 1 ? "drop raro registrado" : "drops raros registrados"}</span>
                      </div>
                    )}
                    {!allCharactersCompleted && incompleteCharacters.length === 0 && dayDetail.characters.length === 0 && (
                      <div className="history-highlight-item highlight-muted">
                        <CalendarBlank size={18} weight="duotone" />
                        <span>Sem atividades de personagens registradas neste dia</span>
                      </div>
                    )}
                  </div>
                </section>

                {/* 4. Characters Section as Expandable Detail */}
                <section className="panel history-characters-panel">
                  <div className="panel-heading">
                    <div>
                      <h2><UsersThree size={18} /> Personagens</h2>
                      <span className="panel-sub">
                        {allCharactersCompleted
                          ? `${dayDetail.characters.length}/${dayDetail.characters.length} concluídos · Todos concluíram suas atividades.`
                          : `${completeCharacters.length}/${dayDetail.characters.length} concluídos · ${incompleteCharacters.length} com pendências.`}
                      </span>
                    </div>
                    <button
                      type="button"
                      className="secondary-button history-toggle-button"
                      onClick={() => setCharactersExpanded((prev) => !prev)}
                      aria-expanded={charactersExpanded}
                    >
                      {charactersExpanded ? (
                        <>
                          <CaretUp size={14} weight="bold" />
                          <span>Ocultar detalhes</span>
                        </>
                      ) : (
                        <>
                          <CaretDown size={14} weight="bold" />
                          <span>Ver detalhes</span>
                        </>
                      )}
                    </button>
                  </div>

                  {charactersExpanded && (
                    <div className="history-character-grid">
                      {dayDetail.characters.map((char) => {
                        const isComplete = char.completedDungeons >= char.selectedDungeons;
                        return (
                          <div
                            key={char.id}
                            className={`history-char-box history-char-box--action ${isComplete ? "" : "history-char-box--incomplete"}`}
                            onClick={() => void openCharacterDay(char.id)}
                            role="button"
                            tabIndex={0}
                            title={`Clique para editar dungeons de ${char.name} neste dia`}
                            onKeyDown={(e) => {
                              if (e.key === "Enter" || e.key === " ") {
                                e.preventDefault();
                                void openCharacterDay(char.id);
                              }
                            }}
                          >
                            <div className="history-char-header">
                              <div className="char-badge">{char.name.slice(0, 2).toUpperCase()}</div>
                              <div>
                                <strong>{char.name}</strong>
                                <small>{char.className} · {char.accountName}</small>
                              </div>
                              <span
                                className={`char-dungeon-count ${
                                  isComplete ? "char-dungeon-count--done" : "char-dungeon-count--pending"
                                }`}
                              >
                                {char.completedDungeons} / {char.selectedDungeons}
                              </span>
                            </div>
                            <div className="history-char-dungeons">
                              {char.dungeons.map((dung) => (
                                <div
                                  key={dung.activityId}
                                  className={dung.completed ? "history-dungeon-item history-dungeon-item--done" : "history-dungeon-item"}
                                >
                                  <span className="dungeon-check-icon">
                                    {dung.completed ? <Check size={12} weight="bold" /> : <X size={12} />}
                                  </span>
                                  <span className="dungeon-name">{dung.name}</span>
                                  <span className="dungeon-reward">
                                    {dung.completed ? `+${numberFormat.format(dung.gold)} G` : "0 G"}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </section>

                {/* 5. Tower Sessions */}
                {dayDetail.towerSessions.length > 0 && (
                  <section className="panel history-tower-panel">
                    <div className="panel-heading">
                      <h2><ShieldChevron size={18} /> Sessões da Torre ({dayDetail.towerSessions.length})</h2>
                    </div>
                    <div className="history-tower-list">
                      {dayDetail.towerSessions.map((session) => (
                        <div key={session.sessionId} className="history-tower-row">
                          <div>
                            <strong>{session.completed ? "Torre Concluída" : "Torre Não Concluída"}</strong>
                            <small>
                              Participantes: {session.participantNames.length ? session.participantNames.join(", ") : "Nenhum participante registrado"}
                            </small>
                          </div>
                          <div className="tower-meta">
                            <span className="cost-tag">Custo: {numberFormat.format(session.costGold)} G</span>
                            {session.drops.length > 0 && (
                              <span className="drops-tag">
                                {session.drops.map((d) => `${d.quantity}× ${d.itemName}`).join(", ")}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {/* 6. Drops of the day */}
                {dayDetail.drops.length > 0 && (
                  <section className="panel history-drops-panel">
                    <div className="panel-heading">
                      <h2><Sparkle size={18} /> Drops Registrados ({dayDetail.drops.length})</h2>
                    </div>
                    <div className="history-drops-list">
                      {dayDetail.drops.map((drop, idx) => (
                        <div key={idx} className="history-drop-row">
                          <span className="drop-icon">✦</span>
                          <strong className="drop-name">{drop.itemName}</strong>
                          <span className="drop-qty">{drop.quantity}×</span>
                          <time className="drop-time">
                            {timeFormat.format(new Date(drop.obtainedAt))}
                          </time>
                        </div>
                      ))}
                    </div>
                  </section>
                )}
              </div>
            )}
          </main>
        </div>
      )}
      {editingCharacterDay && (
        <CharacterDayDialog
          day={editingCharacterDay}
          saving={characterSaving}
          error={characterError}
          onClose={() => setEditingCharacterDay(null)}
          onSave={saveCharacterDay}
        />
      )}
    </div>
  );
}
