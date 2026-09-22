import { Bell, Calculator, CalendarBlank, ChartBar, CheckCircle, Clock, Coins, Crown, GearSix, House, Moon, Play, Plus, Receipt, ShieldChevron, Sparkle, Stop, Sword, Timer, Trophy, UserPlus, UsersThree } from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import brandMark from "../assets/gf-farmer-mark.png";
import type { AppGateway, CharacterDayResult, DashboardLayoutResult, DashboardModuleKey, ExpenseRegistrationInput, ManagementOverviewResult, TodayActivityResult, TodayCharactersResult, TodayResult, TowerRegistrationInput, WorkRoutineResult } from "../gateway/AppGateway";
import { CharacterDayDialog } from "./CharacterDayDialog";
import { DashboardModuleHost } from "./DashboardModules";
import { EditRegistrationDialog, type RegistrationDraft } from "./EditRegistrationDialog";
import { HistoryPage } from "./HistoryPage";
import { ManagementPage } from "./ManagementPage";
import { PveBagPriceDialog } from "./PveBagPriceDialog";
import { ReportsPage } from "./ReportsPage";
import { SaleDialog, type SaleInitialData } from "./SaleDialog";
import { SettingsPage } from "./SettingsPage";
import { TowerDialog } from "./TowerDialog";
import { VipDialog } from "./VipDialog";
import { ExpenseDialog } from "./ExpenseDialog";
import { GoldCalculatorDialog } from "./GoldCalculatorDialog";
import { RoutineTargetDialog } from "./RoutineTargetDialog";
import { TopbarRoutineTracker } from "./TopbarRoutineTracker";
import { formatTargetDuration } from "./routineFormatting";
import { millisecondsUntilNextLocalMidnight } from "./dailyRefresh";
import { formatVipRemaining } from "./vipTime";

type BridgeState = "connecting" | "ready" | "error";
type Page = "today" | "management" | "reports" | "history" | "settings";
const numberFormat = new Intl.NumberFormat("pt-BR");
const dateFormat = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "long", year: "numeric" });
const defaultLayout: DashboardLayoutResult = { schemaVersion: 1, visibility: { "daily-summary": true, "recent-drops": true, "monthly-performance": true } };

function Panel({ children, className = "", ...props }: React.HTMLAttributes<HTMLElement>) {
  return <section className={`panel ${className}`} {...props}>{children}</section>;
}

function StatCard({
  icon,
  label,
  value,
  detail,
  tone,
  hoverLabel,
  hoverValue,
  hoverDetail,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  detail: string;
  tone: "blue" | "violet" | "teal" | "gold";
  hoverLabel?: string;
  hoverValue?: string;
  hoverDetail?: string;
}) {
  const [hovered, setHovered] = useState(false);
  const isInteractive = Boolean(hoverValue && hoverValue !== value);
  const displayLabel = hovered && hoverLabel ? hoverLabel : label;
  const displayValue = hovered && hoverValue ? hoverValue : value;
  const displayDetail = hovered && hoverDetail ? hoverDetail : detail;

  return (
    <Panel
      className={`stat-card ${isInteractive ? "stat-card--interactive" : ""}`}
      onMouseEnter={isInteractive ? () => setHovered(true) : undefined}
      onMouseLeave={isInteractive ? () => setHovered(false) : undefined}
      onFocus={isInteractive ? () => setHovered(true) : undefined}
      onBlur={isInteractive ? () => setHovered(false) : undefined}
      tabIndex={isInteractive ? 0 : undefined}
    >
      <div className={`stat-icon stat-icon--${tone}`}>{icon}</div>
      <div>
        <p className="eyebrow">{displayLabel}</p>
        <strong className="stat-value">{displayValue}</strong>
        <p className="stat-detail">{displayDetail}</p>
      </div>
    </Panel>
  );
}

export function App({ gateway }: { gateway: AppGateway }) {
  const [bridgeState, setBridgeState] = useState<BridgeState>("connecting");
  const [today, setToday] = useState<TodayResult | null>(null);
  const [todayError, setTodayError] = useState<string | null>(null);
  const [characters, setCharacters] = useState<TodayCharactersResult | null>(null);
  const [vipNow, setVipNow] = useState(() => Date.now());
  const [activity, setActivity] = useState<TodayActivityResult | null>(null);
  const [workspaceName, setWorkspaceName] = useState("Meu farm");
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);
  const [page, setPage] = useState<Page>("today");
  const [management, setManagement] = useState<ManagementOverviewResult | null>(null);
  const [managementLoading, setManagementLoading] = useState(false);
  const [managementBusy, setManagementBusy] = useState(false);
  const [managementError, setManagementError] = useState<string | null>(null);
  const [characterDay, setCharacterDay] = useState<CharacterDayResult | null>(null);
  const [dayLoading, setDayLoading] = useState(false);
  const [daySaving, setDaySaving] = useState(false);
  const [dayError, setDayError] = useState<string | null>(null);
  const [towerOpen, setTowerOpen] = useState(false);
  const [towerSaving, setTowerSaving] = useState(false);
  const [towerError, setTowerError] = useState<string | null>(null);
  const [priceModalOpen, setPriceModalOpen] = useState(false);
  const [priceSaving, setPriceSaving] = useState(false);
  const [priceError, setPriceError] = useState<string | null>(null);
  const [saleModalOpen, setSaleModalOpen] = useState(false);
  const [saleInitialData, setSaleInitialData] = useState<SaleInitialData | null>(null);
  const [layout, setLayout] = useState<DashboardLayoutResult>(defaultLayout);
  const [layoutBusy, setLayoutBusy] = useState(false);
  const [layoutError, setLayoutError] = useState<string | null>(null);
  const [editingRegistration, setEditingRegistration] = useState<RegistrationDraft | null>(null);
  const [vipCharacter, setVipCharacter] = useState<Extract<TodayCharactersResult, { state: "ready" }>['characters'][number] | null>(null);
  const [vipSaving, setVipSaving] = useState(false);
  const [vipError, setVipError] = useState<string | null>(null);
  const [expenseOpen, setExpenseOpen] = useState(false);
  const [expenseSaving, setExpenseSaving] = useState(false);
  const [expenseError, setExpenseError] = useState<string | null>(null);
  const [routine, setRoutine] = useState<WorkRoutineResult | null>(null);
  const [routineBusy, setRoutineBusy] = useState(false);
  const [calculatorOpen, setCalculatorOpen] = useState(false);
  const [autostart, setAutostart] = useState(false);
  const [autostartBusy, setAutostartBusy] = useState(false);
  const [targetRoutineMinutes, setTargetRoutineMinutes] = useState<number>(() => {
    const saved = localStorage.getItem("gf-dashboard.routine-target-minutes");
    return saved ? Math.max(15, parseInt(saved, 10)) || 240 : 240;
  });
  const [targetModalOpen, setTargetModalOpen] = useState(false);
  const [dismissedCompletionBanner, setDismissedCompletionBanner] = useState(false);

  const routineAnchorRef = useRef<{
    id: string;
    status: string;
    baseElapsed: number;
    syncedAt: number;
  } | null>(null);

  const syncRoutine = useCallback((next: WorkRoutineResult | null) => {
    if (!next) {
      routineAnchorRef.current = null;
      setRoutine(null);
      return;
    }
    routineAnchorRef.current = {
      id: next.id,
      status: next.status,
      baseElapsed: next.elapsedSeconds,
      syncedAt: Date.now(),
    };
    setRoutine(next);
  }, []);

  const updateTargetRoutineMinutes = (minutes: number) => {
    const sanitized = Math.max(15, minutes);
    setTargetRoutineMinutes(sanitized);
    localStorage.setItem("gf-dashboard.routine-target-minutes", String(sanitized));
  };

  const loadDashboard = useCallback(async () => {
    const [nextToday, nextCharacters, nextActivity] = await Promise.all([
      gateway.getToday(), gateway.getTodayCharacters(), gateway.getTodayActivity(),
    ]);
    setToday(nextToday);
    setCharacters(nextCharacters);
    setActivity(nextActivity);
    return nextToday;
  }, [gateway]);

  const loadManagement = useCallback(async (options?: { silent?: boolean }) => {
    if (!options?.silent) setManagementLoading(true);
    setManagementError(null);
    try { setManagement(await gateway.getManagementOverview()); }
    catch (error: unknown) { setManagementError(error instanceof Error ? error.message : "Falha ao carregar cadastros"); }
    finally { if (!options?.silent) setManagementLoading(false); }
  }, [gateway]);

  useEffect(() => {
    let active = true;
    gateway.ping().then(async () => {
      if (!active) return;
      setBridgeState("ready");
      try {
        await loadDashboard();
        try { setLayout(await gateway.getDashboardLayout()); } catch { /* workspace may not exist yet */ }
        try { syncRoutine((await gateway.getWorkRoutine()).routine); } catch { /* workspace may not exist yet */ }
        try { setAutostart((await gateway.getAutostart()).enabled); } catch { /* ignore */ }
      } catch (error: unknown) {
        if (active) setTodayError(error instanceof Error ? error.message : "Falha ao carregar hoje");
      }
    }).catch((error: unknown) => {
      if (active) {
        setBridgeState("error");
        setTodayError(error instanceof Error ? error.message : "Falha desconhecida");
      }
    });
    return () => { active = false; };
  }, [gateway, loadDashboard, syncRoutine]);

  useEffect(() => {
    if (bridgeState !== "ready") return;

    let timeoutId: number | undefined;
    let disposed = false;
    const refreshDashboard = async () => {
      if (disposed) return;
      try {
        await loadDashboard();
        setTodayError(null);
      } catch (error: unknown) {
        if (!disposed) {
          setTodayError(error instanceof Error ? error.message : "Falha ao atualizar o dia de farm");
        }
      }
    };
    const refreshRoutine = async () => {
      if (disposed) return;
      try {
        const res = await gateway.getWorkRoutine();
        if (!disposed) syncRoutine(res.routine);
      } catch {
        /* workspace may not exist yet */
      }
    };
    const scheduleNextMidnightRefresh = () => {
      timeoutId = window.setTimeout(async () => {
        await refreshDashboard();
        await refreshRoutine();
        if (!disposed) scheduleNextMidnightRefresh();
      }, millisecondsUntilNextLocalMidnight());
    };
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") {
        void refreshDashboard();
        void refreshRoutine();
      }
    };
    const refreshWhenFocused = () => {
      void refreshDashboard();
      void refreshRoutine();
    };

    scheduleNextMidnightRefresh();
    window.addEventListener("focus", refreshWhenFocused);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      disposed = true;
      if (timeoutId !== undefined) window.clearTimeout(timeoutId);
      window.removeEventListener("focus", refreshWhenFocused);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [bridgeState, gateway, loadDashboard, syncRoutine]);

  useEffect(() => {
    if (routine?.status !== "running") return;

    const updateElapsed = () => {
      const anchor = routineAnchorRef.current;
      if (!anchor || anchor.status !== "running") return;
      const deltaSeconds = Math.max(0, Math.floor((Date.now() - anchor.syncedAt) / 1000));
      const currentElapsed = anchor.baseElapsed + deltaSeconds;
      setRoutine((current) => {
        if (!current || current.status !== "running" || current.elapsedSeconds === currentElapsed) {
          return current;
        }
        return { ...current, elapsedSeconds: currentElapsed };
      });
    };

    updateElapsed();
    const timer = window.setInterval(updateElapsed, 1000);
    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        updateElapsed();
      }
    };

    window.addEventListener("focus", updateElapsed);
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", updateElapsed);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [routine?.status]);

  useEffect(() => {
    const timer = window.setInterval(() => setVipNow(Date.now()), 60_000);
    return () => window.clearInterval(timer);
  }, []);

  async function createWorkspace() {
    setCreatingWorkspace(true);
    setTodayError(null);
    try {
      await gateway.createWorkspace(workspaceName);
      await loadDashboard();
    } catch (error: unknown) {
      setTodayError(error instanceof Error ? error.message : "Não foi possível criar o workspace");
    } finally { setCreatingWorkspace(false); }
  }

  async function createAccount(name: string, serverName: string) {
    setManagementBusy(true); setManagementError(null);
    try { await gateway.createAccount(name, serverName); await loadManagement({ silent: true }); }
    catch (error: unknown) { setManagementError(error instanceof Error ? error.message : "Não foi possível cadastrar a conta"); }
    finally { setManagementBusy(false); }
  }

  function openManagement() {
    setPage("management");
    if (bridgeState === "ready") void loadManagement();
  }

  function openHistory() {
    setPage("history");
    if (bridgeState === "ready" && !management) void loadManagement({ silent: true });
  }

  async function createCharacter(accountId: string, name: string, className: string, level: number) {
    setManagementBusy(true); setManagementError(null);
    try { await gateway.createCharacter(accountId, name, className, level); await Promise.all([loadManagement({ silent: true }), loadDashboard()]); }
    catch (error: unknown) { setManagementError(error instanceof Error ? error.message : "Não foi possível cadastrar o personagem"); }
    finally { setManagementBusy(false); }
  }

  async function toggleDungeon(activityId: string, enabled: boolean) {
    setManagementBusy(true); setManagementError(null);
    try { await gateway.setDungeonActive(activityId, enabled); await Promise.all([loadManagement({ silent: true }), loadDashboard()]); }
    catch (error: unknown) { setManagementError(error instanceof Error ? error.message : "Não foi possível alterar a rotina"); }
    finally { setManagementBusy(false); }
  }

  async function saveRegistrationEdit(draft: RegistrationDraft) {
    setManagementBusy(true); setManagementError(null);
    try {
      if (draft.kind === "account") await gateway.updateAccount(draft.id, draft.name, draft.serverName);
      else await gateway.updateCharacter(draft.id, draft.name, draft.className, draft.level);
      setEditingRegistration(null);
      await Promise.all([loadManagement({ silent: true }), loadDashboard()]);
    } catch (error: unknown) { setManagementError(error instanceof Error ? error.message : "Não foi possível salvar as alterações"); }
    finally { setManagementBusy(false); }
  }

  async function openCharacterDay(characterId: string) {
    setDayLoading(true); setDayError(null);
    try { setCharacterDay(await gateway.getCharacterDay(characterId)); }
    catch (error: unknown) { setTodayError(error instanceof Error ? error.message : "Não foi possível abrir o resumo"); }
    finally { setDayLoading(false); }
  }

  async function saveCharacterDay(completedIds: string[]) {
    if (!characterDay) return;
    setDaySaving(true); setDayError(null);
    try { await gateway.saveCharacterDay(characterDay.characterId, completedIds, characterDay.activityDate); setCharacterDay(null); await loadDashboard(); }
    catch (error: unknown) { setDayError(error instanceof Error ? error.message : "Não foi possível salvar o resumo"); }
    finally { setDaySaving(false); }
  }

  async function setCharacterDailyMission(characterId: string, completed: boolean) {
    setTodayError(null);
    try {
      await gateway.setCharacterDailyMission(characterId, completed);
      await loadDashboard();
    } catch (error: unknown) {
      setTodayError(error instanceof Error ? error.message : "Não foi possível atualizar a diária");
    }
  }
  async function saveVip(paidGold: number, remainingDays: number, remainingHours: number) {
    if (!vipCharacter) return;
    setVipSaving(true); setVipError(null);
    try { await gateway.saveCharacterVip(vipCharacter.id, paidGold, remainingDays, remainingHours); setVipCharacter(null); await loadDashboard(); }
    catch (error: unknown) { setVipError(error instanceof Error ? error.message : "Não foi possível salvar o VIP"); }
    finally { setVipSaving(false); }
  }

  async function recordExpense(input: ExpenseRegistrationInput) {
    setExpenseSaving(true); setExpenseError(null);
    try { await gateway.recordExpense(input); setExpenseOpen(false); }
    catch (error: unknown) { setExpenseError(error instanceof Error ? error.message : "Não foi possível registrar a despesa"); }
    finally { setExpenseSaving(false); }
  }

  async function updateRoutine(action: "start" | "pause" | "resume" | "stop") {
    setRoutineBusy(true); setTodayError(null);
    try {
      const next = action === "start" ? await gateway.startWorkRoutine() : action === "pause" ? await gateway.pauseWorkRoutine() : action === "resume" ? await gateway.resumeWorkRoutine() : await gateway.stopWorkRoutine();
      syncRoutine(next.status === "completed" ? null : next);
      if (action === "start" || action === "stop") {
        setDismissedCompletionBanner(false);
      }
    } catch (error: unknown) { setTodayError(error instanceof Error ? error.message : "Não foi possível atualizar a rotina"); }
    finally { setRoutineBusy(false); }
  }

  async function registerTower(input: TowerRegistrationInput) {
    setTowerSaving(true); setTowerError(null);
    try { await gateway.registerCompletedTower(input); setTowerOpen(false); await loadDashboard(); }
    catch (error: unknown) { setTowerError(error instanceof Error ? error.message : "Não foi possível registrar a Torre"); }
    finally { setTowerSaving(false); }
  }

  async function savePveBagPrice(unitValueGold: number) {
    setPriceSaving(true); setPriceError(null);
    try {
      await gateway.recordPveBagQuote(unitValueGold);
      setPriceModalOpen(false);
      await loadDashboard();
    } catch (error: unknown) {
      setPriceError(error instanceof Error ? error.message : "Não foi possível salvar a cotação");
    } finally {
      setPriceSaving(false);
    }
  }

  async function setModuleVisible(moduleKey: DashboardModuleKey, enabled: boolean) {
    setLayoutBusy(true); setLayoutError(null);
    try { setLayout(await gateway.setDashboardModuleVisible(moduleKey, enabled)); }
    catch (error: unknown) { setLayoutError(error instanceof Error ? error.message : "Não foi possível salvar a visualização"); }
    finally { setLayoutBusy(false); }
  }

  async function resetLayout() {
    setLayoutBusy(true); setLayoutError(null);
    try { setLayout(await gateway.resetDashboardLayout()); }
    catch (error: unknown) { setLayoutError(error instanceof Error ? error.message : "Não foi possível restaurar a visualização"); }
    finally { setLayoutBusy(false); }
  }

  async function toggleAutostart(enabled: boolean) {
    setAutostartBusy(true);
    setLayoutError(null);
    try {
      const res = await gateway.setAutostart(enabled);
      setAutostart(res.enabled);
    } catch (error: unknown) {
      setLayoutError(error instanceof Error ? error.message : "Não foi possível alterar a inicialização com o Windows");
    } finally {
      setAutostartBusy(false);
    }
  }

  const characterRows = useMemo(
    () => (characters?.state === "ready" ? characters.characters : []),
    [characters],
  );
  const totals = useMemo(() => {
    const selected = characterRows.reduce((sum, character) => sum + character.selectedDungeons, 0);
    const completed = characterRows.reduce((sum, character) => sum + character.completedDungeons, 0);
    const completedCharacters = characterRows.filter((character) => character.selectedDungeons > 0 && character.completedDungeons === character.selectedDungeons).length;
    return { selected, completed, completedCharacters };
  }, [characterRows]);
  const operationalDate = today?.activityDate ? new Date(`${today.activityDate}T12:00:00`) : new Date();
  const formattedDate = dateFormat.format(operationalDate);
  const titleDate = formattedDate.charAt(0).toUpperCase() + formattedDate.slice(1);
  const gold = today?.state === "ready" ? today.estimatedGold : 0;
  const bags = today?.state === "ready" ? today.estimatedPveBags : 0;
  const bagsMarketValue = today?.state === "ready"
    ? (today.estimatedPveBagMarketValue ?? (today.pveBagUnitValueGold ? bags * today.pveBagUnitValueGold : 0))
    : 0;
  const goldWithBags = gold + bagsMarketValue;
  const runsCompleted = activity?.runsCompleted ?? 0;
  const towerCompleted = activity?.towerCompleted ?? 0;
  const towerTotal = activity?.towerTotal ?? 0;
  const monthlyData = useMemo(
    () => (activity?.monthlyGold ?? []).map((point) => ({ day: Number(point.activityDate.slice(-2)), gold: point.gold })),
    [activity],
  );
  const routineTime = routine ? `${String(Math.floor(routine.elapsedSeconds / 3600)).padStart(2, "0")}:${String(Math.floor((routine.elapsedSeconds % 3600) / 60)).padStart(2, "0")}:${String(routine.elapsedSeconds % 60).padStart(2, "0")}` : null;
  const isFarmCompleted = (totals.completedCharacters > 0 && totals.completedCharacters === characterRows.length) || (totals.selected > 0 && runsCompleted >= totals.selected * 5);
  const showCompletionPrompt = isFarmCompleted && routine?.status === "running" && !dismissedCompletionBanner;

  return <main className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><img src={brandMark} alt="" /></div><div><strong>GF Farmer</strong><span>Grand Fantasia</span></div></div>
      <div className="sidebar-rule" />
      <nav className="nav-list" aria-label="Principal">
        <button className={page === "today" ? "nav-item nav-item--active" : "nav-item"} type="button" onClick={() => setPage("today")}><House size={22} weight="duotone" />Hoje</button>
        <button className={page === "management" ? "nav-item nav-item--active" : "nav-item"} type="button" onClick={openManagement}><UsersThree size={22} weight="duotone" />Personagens</button>
        <button className={page === "reports" ? "nav-item nav-item--active" : "nav-item"} type="button" onClick={() => setPage("reports")}><ChartBar size={22} weight="duotone" />Relatórios</button>
        <button className={page === "history" ? "nav-item nav-item--active" : "nav-item"} type="button" onClick={openHistory}><CalendarBlank size={22} weight="duotone" />Histórico</button>
        <button className={page === "settings" ? "nav-item nav-item--active" : "nav-item"} type="button" onClick={() => setPage("settings")}><GearSix size={22} weight="duotone" />Configurações</button>
      </nav>
      <Panel className="account-card"><div className="account-avatar">GF</div><div><strong>Workspace local</strong><span>Dados no SQLite</span></div><small data-testid="bridge-status"><i />{bridgeState === "ready" ? "Online" : bridgeState === "error" ? "Offline" : "Conectando"}</small></Panel>
    </aside>

    <div className="workspace">
      <header className="topbar">
        <div className="date-block"><CalendarBlank size={25} weight="duotone" /><div><strong>{titleDate}</strong><span>Farm diário</span></div></div>
        {routine && (
          <TopbarRoutineTracker
            routine={routine}
            routineBusy={routineBusy}
            targetMinutes={targetRoutineMinutes}
            onUpdateRoutine={updateRoutine}
            onOpenTargetModal={() => setTargetModalOpen(true)}
          />
        )}
        <div className="top-actions"><button aria-label="Tema"><Moon size={23} /></button><button aria-label="Relatórios" onClick={() => setPage("reports")}><ChartBar size={23} /></button><button aria-label="Notificações"><Bell size={23} /></button><div className="profile-dot">GF</div></div>
      </header>
      <div className="dashboard" id="today">
        {page === "today" ? <>
        <div className="page-title-row">
          <h1>Farm de Hoje</h1>
          <div className="page-title-actions">
            {routine ? (
              <button
                className="routine-page-badge"
                type="button"
                title="Ajustar meta de tempo da rotina"
                onClick={() => setTargetModalOpen(true)}
              >
                <Timer size={18} weight="duotone" />
                <span>Rotina ativa · Meta {formatTargetDuration(targetRoutineMinutes)}</span>
                <strong>{routineTime}</strong>
              </button>
            ) : (
              <button className="secondary-button routine-action" type="button" disabled={today?.state !== "ready" || routineBusy} onClick={() => void updateRoutine("start")}>
                <Play size={17} weight="fill" />
                Iniciar rotina
              </button>
            )}
            <button className="secondary-button calculator-action" type="button" onClick={() => setCalculatorOpen(true)}><Calculator size={18} weight="duotone" />Calculadora</button>
            <button className="secondary-button expense-action" type="button" disabled={today?.state !== "ready"} onClick={() => { setExpenseError(null); setExpenseOpen(true); }}><Receipt size={18} weight="duotone" />Nova despesa</button>
            <button
              className="primary-button sale-action"
              type="button"
              disabled={today?.state !== "ready"}
              onClick={() => {
                setSaleInitialData(null);
                setSaleModalOpen(true);
              }}
            >
              <Plus size={18} weight="bold" />
              Nova Venda
            </button>
            <button
              className="secondary-button price-action"
              type="button"
              disabled={today?.state !== "ready"}
              onClick={() => {
                setPriceError(null);
                setPriceModalOpen(true);
              }}
            >
              <Coins size={18} weight="duotone" />
              Preço Saco PvE
            </button>
            <button
              className="secondary-button tower-action"
              type="button"
              disabled={today?.state !== "ready"}
              onClick={() => {
                setTowerError(null);
                setTowerOpen(true);
              }}
            >
              <ShieldChevron size={18} weight="duotone" />
              Registrar Torre
            </button>
          </div>
        </div>
        {todayError && <div className="error-banner" role="alert">{todayError}</div>}
        {today?.state === "empty" && <Panel className="onboarding"><div><strong>Configure seu espaço de farm</strong><span>O catálogo das nove dungeons será criado automaticamente.</span></div><input aria-label="Nome do workspace" value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} /><button disabled={creatingWorkspace || !workspaceName.trim()} onClick={() => void createWorkspace()}>{creatingWorkspace ? "Criando..." : "Começar"}</button></Panel>}

        {showCompletionPrompt && (
          <div className="routine-completion-banner" role="status">
            <div className="routine-completion-banner__identity">
              <i><Trophy size={26} weight="duotone" /></i>
              <div>
                <strong>Todas as runs de hoje foram concluídas!</strong>
                <span>Você completou as dungeons planejadas de todos os personagens. Deseja encerrar a rotina agora?</span>
                <div className="routine-completion-banner__meta">
                  <span>Tempo decorrido: <strong>{routineTime}</strong></span>
                  <span>Meta configurada: <strong>{formatTargetDuration(targetRoutineMinutes)}</strong></span>
                </div>
              </div>
            </div>
            <div className="routine-completion-banner__actions">
              <button
                type="button"
                className="primary-button routine-completion-banner__finish-btn"
                disabled={routineBusy}
                onClick={() => void updateRoutine("stop")}
              >
                <Stop size={16} weight="fill" />
                Encerrar rotina agora
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={() => setDismissedCompletionBanner(true)}
              >
                Continuar rodando
              </button>
            </div>
          </div>
        )}

        <div className="stats-grid" data-testid="today-cards">
          <StatCard icon={<UsersThree size={22} weight="duotone" />} label="Personagens concluídos" value={`${totals.completedCharacters} / ${characterRows.length}`} detail={characterRows.length ? `${Math.round((totals.completedCharacters / characterRows.length) * 100)}% do total` : "Nenhum personagem"} tone="blue" />
          <StatCard icon={<Sword size={22} weight="duotone" />} label="Runs totais" value={`${runsCompleted} / ${totals.selected * 5}`} detail="Progresso diário" tone="violet" />
          <StatCard icon={<ShieldChevron size={22} weight="duotone" />} label="Torre concluída" value={`${towerCompleted} / ${towerTotal}`} detail={towerTotal ? "Sessões de hoje" : "Sem sessões hoje"} tone="teal" />
          <StatCard
            icon={<Coins size={22} weight="duotone" />}
            label="Ouro estimado hoje"
            value={numberFormat.format(gold)}
            detail={bags ? `+ ${numberFormat.format(bags)} Sacos PvE` : "Recompensas das dungeons"}
            hoverLabel="Ouro estimado c/ venda de sacos"
            hoverValue={bagsMarketValue > 0 ? numberFormat.format(goldWithBags) : undefined}
            hoverDetail={bagsMarketValue > 0 ? `${numberFormat.format(bags)} sacos (~${numberFormat.format(bagsMarketValue)}g)` : undefined}
            tone="gold"
          />
        </div>

        <div className="content-grid">
          <Panel className="characters-panel"><div className="panel-heading"><h2>Personagens</h2></div><div className="character-table">
            <div className="character-row character-header"><span>#</span><span>Personagem</span><span>Classe</span><span>VIP</span><span>Diárias</span><span>Dungeons</span><span>Status</span><span /></div>
            {characterRows.length ? characterRows.map((character, index) => {
              const percent = character.selectedDungeons ? Math.round((character.completedDungeons / character.selectedDungeons) * 100) : 0;
              const complete = percent === 100;
              const vipRemaining = character.vipExpiresAt ? formatVipRemaining(character.vipExpiresAt, vipNow) : null;
              const vipActive = Boolean(vipRemaining);
              return <div className="character-row character-row--action" key={character.id} onClick={() => void openCharacterDay(character.id)}><span className={index < 3 ? "rank rank--top" : "rank"}>{index + 1}</span><span className="character-name"><i>{character.name.slice(0, 2).toUpperCase()}</i><strong>{character.name}</strong></span><span className="muted">{character.className}</span><span><button className={vipActive ? "vip-status vip-status--active" : "vip-status"} type="button" aria-label={vipActive ? `Ajustar VIP de ${character.name}, ${vipRemaining} restantes` : `Ativar VIP para ${character.name}`} title={vipActive && character.vipExpiresAt ? `Expira em ${new Date(character.vipExpiresAt).toLocaleString("pt-BR")}` : undefined} onClick={(event) => { event.stopPropagation(); setVipError(null); setVipCharacter(character); }}>{<Crown size={16} weight={vipActive ? "fill" : "duotone"} />}<span>{vipActive ? vipRemaining : "VIP?"}</span></button></span><span><button className={character.dailyMissionCompleted ? "daily-mission daily-mission--done" : "daily-mission"} type="button" aria-label={`${character.dailyMissionCompleted ? "Desmarcar" : "Marcar"} diária de ${character.name}`} onClick={(event) => { event.stopPropagation(); void setCharacterDailyMission(character.id, !character.dailyMissionCompleted); }}>{character.dailyMissionCompleted ? <CheckCircle size={17} weight="fill" /> : <Clock size={17} weight="duotone" />}<span>{character.dailyMissionCompleted ? "Feita" : "Pendente"}</span></button></span><span className="progress-cell"><span className="progress-track"><i style={{ width: `${percent}%` }} /></span><b>{character.completedDungeons} / {character.selectedDungeons}</b></span><span><em className={complete ? "status status--done" : percent ? "status status--doing" : "status"}>{complete ? "Concluído" : percent ? "Em andamento" : "Pendente"}</em></span><button className="row-menu" aria-label={`Abrir resumo de ${character.name}`} onClick={(event) => { event.stopPropagation(); void openCharacterDay(character.id); }}>•••</button></div>;
            }) : bridgeState === "connecting" || dayLoading ? <div className="table-empty"><UsersThree size={30} weight="duotone" /><strong>Carregando dados...</strong><span>Conectando ao banco local.</span></div> : <div className="table-empty"><UsersThree size={30} weight="duotone" /><strong>Nenhum personagem cadastrado</strong><span>Cadastre contas e personagens para iniciar o farm.</span><button className="primary-button empty-action" onClick={openManagement}><UserPlus size={18} />Cadastrar personagens</button></div>}
          </div></Panel>

          <DashboardModuleHost visibility={layout.visibility} activity={activity} runsCompleted={runsCompleted} completedCharacters={totals.completedCharacters} characterTotal={characterRows.length} towerCompleted={towerCompleted} towerTotal={towerTotal} gold={gold} monthlyData={monthlyData} />
        </div>
        <footer className="dashboard-footer"><Sparkle size={16} weight="duotone" />Dados atualizados pelo banco local.</footer>
        </> : page === "management" ? <ManagementPage overview={management} loading={managementLoading} busy={managementBusy} error={managementError} onCreateAccount={createAccount} onCreateCharacter={createCharacter} onEdit={setEditingRegistration} onToggleDungeon={toggleDungeon} /> : page === "reports" ? <ReportsPage gateway={gateway} onOpenHistory={openHistory} onOpenManagement={openManagement} /> : page === "history" ? <HistoryPage gateway={gateway} management={management} /> : <SettingsPage layout={layout} busy={layoutBusy} error={layoutError} targetMinutes={targetRoutineMinutes} autostart={autostart} autostartBusy={autostartBusy} onToggle={setModuleVisible} onReset={resetLayout} onSaveTargetMinutes={updateTargetRoutineMinutes} onToggleAutostart={toggleAutostart} />}
      </div>
      {characterDay && <CharacterDayDialog day={characterDay} saving={daySaving} error={dayError} onClose={() => setCharacterDay(null)} onSave={saveCharacterDay} />}
      {towerOpen && <TowerDialog characters={characterRows} saving={towerSaving} error={towerError} onClose={() => setTowerOpen(false)} onSave={registerTower} />}
      {priceModalOpen && <PveBagPriceDialog currentPrice={today?.state === "ready" ? (today.pveBagUnitValueGold ?? null) : null} saving={priceSaving} error={priceError} onClose={() => setPriceModalOpen(false)} onSave={savePveBagPrice} />}
      {saleModalOpen && <SaleDialog gateway={gateway} isOpen={saleModalOpen} initialData={saleInitialData} onClose={() => { setSaleModalOpen(false); setSaleInitialData(null); }} onSuccess={() => { void loadDashboard(); }} />}
      {editingRegistration && <EditRegistrationDialog draft={editingRegistration} saving={managementBusy} error={managementError} onClose={() => setEditingRegistration(null)} onSave={saveRegistrationEdit} />}
      {vipCharacter && <VipDialog characterName={vipCharacter.name} expiresAt={vipCharacter.vipExpiresAt ?? null} saving={vipSaving} error={vipError} onClose={() => setVipCharacter(null)} onSave={saveVip} />}
      {expenseOpen && <ExpenseDialog saving={expenseSaving} error={expenseError} onClose={() => setExpenseOpen(false)} onSave={recordExpense} />}
      {calculatorOpen && <GoldCalculatorDialog pveBagUnitValueGold={today?.state === "ready" ? (today.pveBagUnitValueGold ?? 1000) : 1000} onClose={() => setCalculatorOpen(false)} onOpenSale={(preset) => { setCalculatorOpen(false); setSaleInitialData(preset); setSaleModalOpen(true); }} />}
      {targetModalOpen && <RoutineTargetDialog currentMinutes={targetRoutineMinutes} onClose={() => setTargetModalOpen(false)} onSave={(minutes) => { updateTargetRoutineMinutes(minutes); setTargetModalOpen(false); }} />}
    </div>
  </main>;
}
