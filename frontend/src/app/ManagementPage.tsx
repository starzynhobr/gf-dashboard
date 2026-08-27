import { Buildings, Check, PencilSimple, Plus, Sword, UserPlus, UsersThree } from "@phosphor-icons/react";
import { type FormEvent, useMemo, useState } from "react";

import type { ManagementOverviewResult } from "../gateway/AppGateway";
import type { RegistrationDraft } from "./EditRegistrationDialog";

interface ManagementPageProps {
  overview: ManagementOverviewResult | null;
  loading: boolean;
  busy: boolean;
  error: string | null;
  onCreateAccount: (name: string, serverName: string) => Promise<void>;
  onCreateCharacter: (accountId: string, name: string, className: string, level: number) => Promise<void>;
  onEdit: (draft: RegistrationDraft) => void;
  onToggleDungeon: (activityId: string, enabled: boolean) => Promise<void>;
}

export function ManagementPage({ overview, loading, busy, error, onCreateAccount, onCreateCharacter, onEdit, onToggleDungeon }: ManagementPageProps) {
  const [accountName, setAccountName] = useState("");
  const [serverName, setServerName] = useState("Valhalla");
  const [accountId, setAccountId] = useState("");
  const [characterName, setCharacterName] = useState("");
  const [className, setClassName] = useState("");
  const [level, setLevel] = useState(91);
  const accounts = useMemo(() => overview?.state === "ready" ? overview.accounts : [], [overview]);
  const selectedAccountId = accountId || accounts[0]?.id || "";
  const characterCount = useMemo(() => accounts.reduce((sum, account) => sum + account.characters.length, 0), [accounts]);

  async function submitAccount(event: FormEvent) {
    event.preventDefault();
    await onCreateAccount(accountName, serverName);
    setAccountName("");
  }

  async function submitCharacter(event: FormEvent) {
    event.preventDefault();
    await onCreateCharacter(selectedAccountId, characterName, className, level);
    setCharacterName("");
    setClassName("");
  }

  if (loading && !overview) return <div className="page-state"><UsersThree size={32} weight="duotone" /><strong>Carregando cadastros...</strong></div>;
  if (!overview || overview.state === "empty") return <div className="page-state"><Buildings size={32} weight="duotone" /><strong>Crie o workspace local antes de cadastrar contas.</strong></div>;

  return <div className="management-page">
    <div className="page-title"><div><p className="page-kicker">Cadastros locais</p><h1>Contas e personagens</h1><span>{accounts.length} contas · {characterCount} personagens · rotina global aplicada automaticamente</span></div></div>
    {error && <div className="error-banner" role="alert">{error}</div>}

    <div className="management-grid">
      <section className="panel management-main">
        <div className="panel-heading"><h2>Estrutura do farm</h2><span>Meta inicial: 2 contas × 5 personagens</span></div>
        <div className="account-list">
          {accounts.length ? accounts.map((account) => <article className="account-group" key={account.id}>
            <header><div className="account-glyph"><Buildings size={21} weight="duotone" /></div><div><strong>{account.name}</strong><span>Servidor {account.serverName}</span></div><div className="account-meta"><b>{account.characters.length} / 5</b><button className="edit-icon" type="button" aria-label={`Editar conta ${account.name}`} disabled={busy} onClick={() => onEdit({ kind: "account", id: account.id, name: account.name, serverName: account.serverName })}><PencilSimple size={16} /></button></div></header>
            <div className="managed-characters">
              {account.characters.length ? account.characters.map((character) => <div className="managed-character" key={character.id}><i>{character.sortOrder}</i><span className="managed-avatar">{character.name.slice(0, 2).toUpperCase()}</span><div><strong>{character.name}</strong><small>{character.className} · nível {character.level}</small></div><Check size={18} /><button className="edit-icon" type="button" aria-label={`Editar personagem ${character.name}`} disabled={busy} onClick={() => onEdit({ kind: "character", id: character.id, name: character.name, className: character.className, level: character.level })}><PencilSimple size={15} /></button></div>) : <p className="inline-empty">Nenhum personagem nesta conta.</p>}
            </div>
          </article>) : <div className="inline-empty large"><Buildings size={27} /><strong>Cadastre a primeira conta</strong><span>Depois você poderá adicionar os cinco personagens.</span></div>}
        </div>
      </section>

      <aside className="management-side">
        <form className="panel compact-form" onSubmit={(event) => void submitAccount(event)}>
          <div className="panel-heading"><h2><Plus size={18} /> Nova conta</h2></div>
          <label>Nome da conta<input value={accountName} onChange={(event) => setAccountName(event.target.value)} placeholder="Ex.: Conta Principal" required /></label>
          <label>Servidor<input value={serverName} onChange={(event) => setServerName(event.target.value)} required /></label>
          <button className="primary-button" disabled={busy || !accountName.trim() || !serverName.trim()}><Buildings size={18} />Cadastrar conta</button>
        </form>

        <form className="panel compact-form" onSubmit={(event) => void submitCharacter(event)}>
          <div className="panel-heading"><h2><UserPlus size={18} /> Novo personagem</h2></div>
          <label>Conta<select value={selectedAccountId} onChange={(event) => setAccountId(event.target.value)} required>{accounts.map((account) => <option value={account.id} key={account.id}>{account.name}</option>)}</select></label>
          <div className="form-row"><label>Nome<input value={characterName} onChange={(event) => setCharacterName(event.target.value)} placeholder="Star01" required /></label><label>Classe<input value={className} onChange={(event) => setClassName(event.target.value)} placeholder="Ranger" required /></label></div>
          <label>Nível<input type="number" min="1" max="999" value={level} onChange={(event) => setLevel(Number(event.target.value))} required /></label>
          <button className="primary-button" disabled={busy || !selectedAccountId || !characterName.trim() || !className.trim()}><UserPlus size={18} />Cadastrar personagem</button>
        </form>
      </aside>
    </div>

    <section className="panel routine-panel">
      <div className="panel-heading"><h2><Sword size={18} /> Rotina global de dungeons</h2><span>Personagens novos herdam as dungeons ativas</span></div>
      <div className="routine-grid">{overview.dungeons.map((dungeon) => <label className={dungeon.enabled ? "routine-item routine-item--enabled" : "routine-item"} key={dungeon.id}><input type="checkbox" checked={dungeon.enabled} disabled={busy} onChange={(event) => void onToggleDungeon(dungeon.id, event.target.checked)} /><span><strong>{dungeon.name}</strong><small>{dungeon.targetAmount} rodadas · {dungeon.enabled ? "incluída no farm" : "dormente"}</small></span></label>)}</div>
    </section>
  </div>;
}
