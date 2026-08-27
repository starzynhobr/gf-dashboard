import { Bell, CalendarBlank, ChartBar, Coins, GearSix, House, Moon, ShieldChevron, Sparkle, Sword, UserPlus, UsersThree } from "@phosphor-icons/react";
import { useCallback, useEffect, useMemo, useState } from "react";

import brandMark from "../assets/gf-farmer-mark.png";
import type { AppGateway, CharacterDayResult, DashboardLayoutResult, DashboardModuleKey, ManagementOverviewResult, TodayActivityResult, TodayCharactersResult, TodayResult, TowerRegistrationInput } from "../gateway/AppGateway";
import { CharacterDayDialog } from "./CharacterDayDialog";
import { DashboardModuleHost } from "./DashboardModules";
import { EditRegistrationDialog, type RegistrationDraft } from "./EditRegistrationDialog";
import { ManagementPage } from "./ManagementPage";
import { SettingsPage } from "./SettingsPage";
import { TowerDialog } from "./TowerDialog";

type BridgeState = "connecting" | "ready" | "error";
type Page = "today" | "management" | "settings";
const numberFormat = new Intl.NumberFormat("pt-BR");
const dateFormat = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "long", year: "numeric" });
const defaultLayout: DashboardLayoutResult = { schemaVersion: 1, visibility: { "daily-summary": true, "recent-drops": true, "monthly-performance": true } };

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{children}</section>;
}

function StatCard({ icon, label, value, detail, tone }: { icon: React.ReactNode; label: string; value: string; detail: string; tone: "blue" | "violet" | "teal" | "gold" }) {
  return <Panel className="stat-card"><div className={`stat-icon stat-icon--${tone}`}>{icon}</div><div><p className="eyebrow">{label}</p><strong className="stat-value">{value}</strong><p className="stat-detail">{detail}</p></div></Panel>;
}

export function App({ gateway }: { gateway: AppGateway }) {
  const [bridgeState, setBridgeState] = useState<BridgeState>("connecting");
  const [today, setToday] = useState<TodayResult | null>(null);
  const [todayError, setTodayError] = useState<string | null>(null);
  const [characters, setCharacters] = useState<TodayCharactersResult | null>(null);
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
  const [layout, setLayout] = useState<DashboardLayoutResult>(defaultLayout);
  const [layoutBusy, setLayoutBusy] = useState(false);
  const [layoutError, setLayoutError] = useState<string | null>(null);
  const [editingRegistration, setEditingRegistration] = useState<RegistrationDraft | null>(null);

  const loadDashboard = useCallback(async () => {
    const [nextToday, nextCharacters, nextActivity] = await Promise.all([
      gateway.getToday(), gateway.getTodayCharacters(), gateway.getTodayActivity(),
    ]);
    setToday(nextToday);
    setCharacters(nextCharacters);
    setActivity(nextActivity);
  }, [gateway]);

  const loadManagement = useCallback(async () => {
    setManagementLoading(true);
    setManagementError(null);
    try { setManagement(await gateway.getManagementOverview()); }
    catch (error: unknown) { setManagementError(error instanceof Error ? error.message : "Falha ao carregar cadastros"); }
    finally { setManagementLoading(false); }
  }, [gateway]);

  useEffect(() => {
    let active = true;
    gateway.ping().then(async () => {
      if (!active) return;
      setBridgeState("ready");
      try {
        await loadDashboard();
        try { setLayout(await gateway.getDashboardLayout()); } catch { /* workspace may not exist yet */ }
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
  }, [gateway, loadDashboard]);

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
    try { await gateway.createAccount(name, serverName); await loadManagement(); }
    catch (error: unknown) { setManagementError(error instanceof Error ? error.message : "Não foi possível cadastrar a conta"); }
    finally { setManagementBusy(false); }
  }

  function openManagement() {
    setPage("management");
    if (bridgeState === "ready") void loadManagement();
  }

  async function createCharacter(accountId: string, name: string, className: string, level: number) {
    setManagementBusy(true); setManagementError(null);
    try { await gateway.createCharacter(accountId, name, className, level); await Promise.all([loadManagement(), loadDashboard()]); }
    catch (error: unknown) { setManagementError(error instanceof Error ? error.message : "Não foi possível cadastrar o personagem"); }
    finally { setManagementBusy(false); }
  }

  async function toggleDungeon(activityId: string, enabled: boolean) {
    setManagementBusy(true); setManagementError(null);
    try { await gateway.setDungeonActive(activityId, enabled); await Promise.all([loadManagement(), loadDashboard()]); }
    catch (error: unknown) { setManagementError(error instanceof Error ? error.message : "Não foi possível alterar a rotina"); }
    finally { setManagementBusy(false); }
  }

  async function saveRegistrationEdit(draft: RegistrationDraft) {
    setManagementBusy(true); setManagementError(null);
    try {
      if (draft.kind === "account") await gateway.updateAccount(draft.id, draft.name, draft.serverName);
      else await gateway.updateCharacter(draft.id, draft.name, draft.className, draft.level);
      setEditingRegistration(null);
      await Promise.all([loadManagement(), loadDashboard()]);
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
    try { await gateway.saveCharacterDay(characterDay.characterId, completedIds); setCharacterDay(null); await loadDashboard(); }
    catch (error: unknown) { setDayError(error instanceof Error ? error.message : "Não foi possível salvar o resumo"); }
    finally { setDaySaving(false); }
  }

  async function registerTower(input: TowerRegistrationInput) {
    setTowerSaving(true); setTowerError(null);
    try { await gateway.registerCompletedTower(input); setTowerOpen(false); await loadDashboard(); }
    catch (error: unknown) { setTowerError(error instanceof Error ? error.message : "Não foi possível registrar a Torre"); }
    finally { setTowerSaving(false); }
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
  const runsCompleted = activity?.runsCompleted ?? 0;
  const towerCompleted = activity?.towerCompleted ?? 0;
  const towerTotal = activity?.towerTotal ?? 0;
  const monthlyData = useMemo(
    () => (activity?.monthlyGold ?? []).map((point) => ({ day: Number(point.activityDate.slice(-2)), gold: point.gold })),
    [activity],
  );

  return <main className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><img src={brandMark} alt="" /></div><div><strong>GF Farmer</strong><span>Grand Fantasia</span></div></div>
      <div className="sidebar-rule" />
      <nav className="nav-list" aria-label="Principal">
        <button className={page === "today" ? "nav-item nav-item--active" : "nav-item"} type="button" onClick={() => setPage("today")}><House size={22} weight="duotone" />Hoje</button>
        <button className={page === "management" ? "nav-item nav-item--active" : "nav-item"} type="button" onClick={openManagement}><UsersThree size={22} weight="duotone" />Personagens</button>
        <button className="nav-item" type="button" disabled><ChartBar size={22} weight="duotone" />Relatórios</button>
        <button className="nav-item" type="button" disabled><CalendarBlank size={22} weight="duotone" />Histórico</button>
        <button className={page === "settings" ? "nav-item nav-item--active" : "nav-item"} type="button" onClick={() => setPage("settings")}><GearSix size={22} weight="duotone" />Configurações</button>
      </nav>
      <Panel className="account-card"><div className="account-avatar">GF</div><div><strong>Workspace local</strong><span>Dados no SQLite</span></div><small data-testid="bridge-status"><i />{bridgeState === "ready" ? "Online" : bridgeState === "error" ? "Offline" : "Conectando"}</small></Panel>
    </aside>

    <div className="workspace">
      <header className="topbar"><div className="date-block"><CalendarBlank size={25} weight="duotone" /><div><strong>{titleDate}</strong><span>Farm diário</span></div></div><div className="top-actions"><button aria-label="Tema"><Moon size={23} /></button><button aria-label="Relatórios"><ChartBar size={23} /></button><button aria-label="Notificações"><Bell size={23} /></button><div className="profile-dot">GF</div></div></header>
      <div className="dashboard" id="today">
        {page === "today" ? <>
        <div className="page-title-row"><h1>Farm de Hoje</h1><button className="secondary-button tower-action" type="button" disabled={today?.state !== "ready"} onClick={() => { setTowerError(null); setTowerOpen(true); }}><ShieldChevron size={18} weight="duotone" />Registrar Torre</button></div>
        {todayError && <div className="error-banner" role="alert">{todayError}</div>}
        {today?.state === "empty" && <Panel className="onboarding"><div><strong>Configure seu espaço de farm</strong><span>O catálogo das nove dungeons será criado automaticamente.</span></div><input aria-label="Nome do workspace" value={workspaceName} onChange={(event) => setWorkspaceName(event.target.value)} /><button disabled={creatingWorkspace || !workspaceName.trim()} onClick={() => void createWorkspace()}>{creatingWorkspace ? "Criando..." : "Começar"}</button></Panel>}

        <div className="stats-grid" data-testid="today-cards">
          <StatCard icon={<UsersThree size={29} weight="duotone" />} label="Personagens concluídos" value={`${totals.completedCharacters} / ${characterRows.length}`} detail={characterRows.length ? `${Math.round((totals.completedCharacters / characterRows.length) * 100)}% do total` : "Nenhum personagem"} tone="blue" />
          <StatCard icon={<Sword size={29} weight="duotone" />} label="Runs totais" value={`${runsCompleted} / ${totals.selected * 5}`} detail="Progresso diário" tone="violet" />
          <StatCard icon={<ShieldChevron size={29} weight="duotone" />} label="Torre concluída" value={`${towerCompleted} / ${towerTotal}`} detail={towerTotal ? "Sessões de hoje" : "Sem sessões hoje"} tone="teal" />
          <StatCard icon={<Coins size={29} weight="duotone" />} label="Ouro estimado hoje" value={numberFormat.format(gold)} detail={bags ? `+ ${numberFormat.format(bags)} Sacos PvE` : "Recompensas das dungeons"} tone="gold" />
        </div>

        <div className="content-grid">
          <Panel className="characters-panel"><div className="panel-heading"><h2>Personagens</h2></div><div className="character-table">
            <div className="character-row character-header"><span>#</span><span>Personagem</span><span>Classe</span><span>Dungeons</span><span>Status</span><span /></div>
            {characterRows.length ? characterRows.map((character, index) => {
              const percent = character.selectedDungeons ? Math.round((character.completedDungeons / character.selectedDungeons) * 100) : 0;
              const complete = percent === 100;
              return <div className="character-row character-row--action" key={character.id} onClick={() => void openCharacterDay(character.id)}><span className={index < 3 ? "rank rank--top" : "rank"}>{index + 1}</span><span className="character-name"><i>{character.name.slice(0, 2).toUpperCase()}</i><strong>{character.name}</strong></span><span className="muted">{character.className}</span><span className="progress-cell"><span className="progress-track"><i style={{ width: `${percent}%` }} /></span><b>{character.completedDungeons} / {character.selectedDungeons}</b></span><span><em className={complete ? "status status--done" : percent ? "status status--doing" : "status"}>{complete ? "Concluído" : percent ? "Em andamento" : "Pendente"}</em></span><button className="row-menu" aria-label={`Abrir resumo de ${character.name}`} onClick={(event) => { event.stopPropagation(); void openCharacterDay(character.id); }}>•••</button></div>;
            }) : bridgeState === "connecting" || dayLoading ? <div className="table-empty"><UsersThree size={30} weight="duotone" /><strong>Carregando dados...</strong><span>Conectando ao banco local.</span></div> : <div className="table-empty"><UsersThree size={30} weight="duotone" /><strong>Nenhum personagem cadastrado</strong><span>Cadastre contas e personagens para iniciar o farm.</span><button className="primary-button empty-action" onClick={openManagement}><UserPlus size={18} />Cadastrar personagens</button></div>}
          </div></Panel>

          <DashboardModuleHost visibility={layout.visibility} activity={activity} runsCompleted={runsCompleted} completedCharacters={totals.completedCharacters} characterTotal={characterRows.length} towerCompleted={towerCompleted} towerTotal={towerTotal} gold={gold} monthlyData={monthlyData} />
        </div>
        <footer className="dashboard-footer"><Sparkle size={16} weight="duotone" />Dados atualizados pelo banco local.</footer>
        </> : page === "management" ? <ManagementPage overview={management} loading={managementLoading} busy={managementBusy} error={managementError} onCreateAccount={createAccount} onCreateCharacter={createCharacter} onEdit={setEditingRegistration} onToggleDungeon={toggleDungeon} /> : <SettingsPage layout={layout} busy={layoutBusy} error={layoutError} onToggle={setModuleVisible} onReset={resetLayout} />}
      </div>
      {characterDay && <CharacterDayDialog day={characterDay} saving={daySaving} error={dayError} onClose={() => setCharacterDay(null)} onSave={saveCharacterDay} />}
      {towerOpen && <TowerDialog characters={characterRows} saving={towerSaving} error={towerError} onClose={() => setTowerOpen(false)} onSave={registerTower} />}
      {editingRegistration && <EditRegistrationDialog draft={editingRegistration} saving={managementBusy} error={managementError} onClose={() => setEditingRegistration(null)} onSave={saveRegistrationEdit} />}
    </div>
  </main>;
}
