import { CalendarBlank, Check, Coins, Funnel, MagnifyingGlass, ShieldChevron, Sparkle, UsersThree, X } from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";

import type { AppGateway, HistoryDayDetailResult, HistoryDaySummary, ManagementOverviewResult } from "../gateway/AppGateway";

const numberFormat = new Intl.NumberFormat("pt-BR");
const dateFormat = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short", year: "numeric" });
const timeFormat = new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit" });

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
  const [detailLoading, setDetailLoading] = useState(false);

  // Filters
  const [datePreset, setDatePreset] = useState<"7" | "30" | "all">("30");
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

  useEffect(() => {
    if (!selectedDate) {
      return;
    }
    let active = true;
    gateway
      .getHistoryDayDetail(selectedDate, {
        accountId: selectedAccountId || undefined,
        characterId: selectedCharacterId || undefined,
      })
      .then((res) => {
        if (!active) return;
        setDayDetail(res);
        setDetailLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setDayDetail(null);
        setDetailLoading(false);
      });
    return () => {
      active = false;
    };
  }, [gateway, selectedDate, selectedAccountId, selectedCharacterId]);

  return (
    <div className="management-page history-page">
      <div className="page-title">
        <div>
          <p className="page-kicker">Registro contínuo</p>
          <h1>Histórico de farm</h1>
          <span>Consulte o histórico de atividades, progresso diário, sessões de torre e drops obtidos.</span>
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
            <h3>Dias registrados ({days.length})</h3>
            <div className="history-day-cards">
              {days.map((day) => {
                const isSelected = day.activityDate === selectedDate;
                const formattedDate = dateFormat.format(new Date(day.activityDate + "T12:00:00"));
                return (
                  <button
                    key={day.activityDate}
                    type="button"
                    className={isSelected ? "history-day-card history-day-card--selected" : "history-day-card"}
                    onClick={() => setSelectedDate(day.activityDate)}
                  >
                    <div className="day-card-header">
                      <strong>{formattedDate}</strong>
                      <span className="day-card-badge">{day.runsCompleted} runs</span>
                    </div>
                    <div className="day-card-stats">
                      <span title="Ouro ganho">
                        <Coins size={14} /> {numberFormat.format(day.goldEarned)}
                      </span>
                      <span title="Sacos PvE">
                        <Sparkle size={14} /> {day.pveBagsEarned} sacos
                      </span>
                      {day.towerTotal > 0 && (
                        <span title="Sessões de Torre">
                          <ShieldChevron size={14} /> {day.towerCompleted}/{day.towerTotal} torre
                        </span>
                      )}
                      {day.dropsCount > 0 && (
                        <span title="Drops obtidos">
                          <MagnifyingGlass size={14} /> {day.dropsCount} drops
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
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
                {/* Day Summary Topbar */}
                <section className="panel history-day-hero">
                  <div>
                    <span className="eyebrow">Resumo do dia</span>
                    <h2>{dateFormat.format(new Date(dayDetail.activityDate + "T12:00:00"))}</h2>
                  </div>
                  <div className="history-hero-kpis">
                    <div>
                      <small>Runs feitas</small>
                      <strong>{dayDetail.runsCompleted}</strong>
                    </div>
                    <div>
                      <small>Ouro obtido</small>
                      <strong className="gold-text">{numberFormat.format(dayDetail.goldEarned)}</strong>
                    </div>
                    <div>
                      <small>Sacos PvE</small>
                      <strong>{dayDetail.pveBagsEarned}</strong>
                    </div>
                    <div>
                      <small>Drops raros</small>
                      <strong>{dayDetail.drops.length}</strong>
                    </div>
                  </div>
                </section>

                {/* Characters and Dungeons */}
                <section className="panel history-characters-panel">
                  <div className="panel-heading">
                    <h2><UsersThree size={18} /> Desempenho dos Personagens</h2>
                    <span>{dayDetail.characters.length} personagens analisados</span>
                  </div>
                  <div className="history-character-grid">
                    {dayDetail.characters.map((char) => (
                      <div className="history-char-box" key={char.id}>
                        <div className="history-char-header">
                          <div className="char-badge">{char.name.slice(0, 2).toUpperCase()}</div>
                          <div>
                            <strong>{char.name}</strong>
                            <small>{char.className} · {char.accountName}</small>
                          </div>
                          <span className="char-dungeon-count">
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
                    ))}
                  </div>
                </section>

                {/* Tower Sessions */}
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

                {/* Drops of the day */}
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
    </div>
  );
}
