import { Plus, ShieldChevron, Trash, X } from "@phosphor-icons/react";
import { useRef, useState } from "react";

import type { TodayCharactersResult, TowerConfiguration, TowerConfigurationInput } from "../gateway/AppGateway";
import { towerInteger } from "./towerValidation";
import { towerDialogKeyboard } from "./towerDialogKeyboard";

type Character = Extract<TodayCharactersResult, { state: "ready" }>["characters"][number];
type Props = {
  configuration: TowerConfiguration | null;
  characters: Character[];
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  onClose: () => void;
  onSave: (input: TowerConfigurationInput) => Promise<TowerConfiguration>;
  onRegister: () => void;
};

export function TowerConfigurationDialog(props: Props) {
  if (props.loading || props.error || !props.configuration) {
    return <div className="dialog-backdrop"><section className="day-dialog tower-dialog" role="dialog" aria-modal="true" aria-labelledby="tower-configuration-title" onKeyDown={(event) => towerDialogKeyboard(event, props.onClose)}>
      <header className="day-dialog__header"><h2 id="tower-configuration-title">Configurar Torre</h2><button autoFocus className="icon-button" type="button" aria-label="Fechar" onClick={props.onClose}><X size={21} /></button></header>
      <div className="tower-dialog__body" aria-busy={props.loading}>{props.error ? <><div className="error-banner" role="alert">{props.error}</div><button className="secondary-button" type="button" onClick={props.onRetry}>Tentar novamente</button></> : <p role="status">Carregando configuração da Torre...</p>}</div>
    </section></div>;
  }
  return <TowerConfigurationForm {...props} configuration={props.configuration} />;
}

function TowerConfigurationForm({ configuration, characters, onClose, onSave, onRegister }: Props & { configuration: TowerConfiguration }) {
  const [guildName, setGuildName] = useState(configuration.guildName);
  const [entryCost, setEntryCost] = useState(String(configuration.entryCostGold));
  const [participantIds, setParticipantIds] = useState([...configuration.participantIds]);
  const [items, setItems] = useState(() => configuration.items.map((item, index) => ({ id: index, itemName: item.itemName, estimatedUnitValue: item.estimatedUnitValue === null ? "" : String(item.estimatedUnitValue) })));
  const nextItemId = useRef(items.length);
  const [saving, setSaving] = useState(false);
  const busy = useRef(false);
  const submission = useRef<{ fingerprint: string; key: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const draftFingerprint = JSON.stringify({ guildName, entryCost, participantIds, items: items.map(({ itemName, estimatedUnitValue }) => ({ itemName, estimatedUnitValue })) });
  const [savedFingerprint, setSavedFingerprint] = useState(draftFingerprint);
  const dirty = draftFingerprint !== savedFingerprint;

  function changed() { setSuccess(false); setError(null); }

  async function submit() {
    if (busy.current) return;
    setError(null); setSuccess(false);
    try {
      const cost = towerInteger(entryCost, "Custo da abertura");
      if (guildName.trim().length > 120) throw new Error("O nome da guilda deve ter até 120 caracteres.");
      if (participantIds.length > 100) throw new Error("Selecione até 100 personagens padrão.");
      if (items.length > 100) throw new Error("Configure até 100 itens da Torre.");
      const names = new Set<string>();
      const catalog = items.map((item) => {
        const itemName = item.itemName.trim();
        if (!itemName) throw new Error("Preencha o nome de todos os itens ou remova a linha vazia.");
        if (itemName.length > 120) throw new Error("O nome de cada item deve ter até 120 caracteres.");
        const key = itemName.toLocaleLowerCase("pt-BR");
        if (names.has(key)) throw new Error("Os itens da Torre não podem se repetir.");
        names.add(key);
        return { itemName, estimatedUnitValue: item.estimatedUnitValue.trim() === "" ? null : towerInteger(item.estimatedUnitValue, `Valor de ${itemName}`) };
      });
      const payload = { guildName: guildName.trim(), entryCostGold: cost, participantIds, items: catalog };
      const fingerprint = JSON.stringify(payload);
      if (submission.current?.fingerprint !== fingerprint) submission.current = { fingerprint, key: crypto.randomUUID() };
      busy.current = true; setSaving(true);
      await onSave({ ...payload, idempotencyKey: submission.current.key });
      setSavedFingerprint(draftFingerprint); setSuccess(true);
      submission.current = null;
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Não foi possível salvar a configuração.");
    } finally { busy.current = false; setSaving(false); }
  }

  return <div className="dialog-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget && !saving) onClose(); }}>
    <section className="day-dialog tower-dialog" role="dialog" aria-modal="true" aria-labelledby="tower-configuration-title" onKeyDown={(event) => towerDialogKeyboard(event, onClose, saving)}>
      <header className="day-dialog__header"><div className="day-dialog__identity"><i><ShieldChevron size={25} weight="duotone" /></i><div><h2 id="tower-configuration-title">Configurar Torre</h2><span>Preferências e itens usados nas próximas sessões</span></div></div><button className="icon-button" type="button" aria-label="Fechar" disabled={saving} onClick={onClose}><X size={21} /></button></header>
      <form className="tower-configuration-form" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
        <fieldset className="tower-dialog__body" disabled={saving}>
          <div className="tower-configuration-fields">
            <label className="field"><span>Guilda</span><input autoFocus maxLength={120} value={guildName} onChange={(event) => { setGuildName(event.target.value); changed(); }} placeholder="Opcional" /></label>
            <label className="field"><span>Custo da abertura (gold)</span><input inputMode="numeric" value={entryCost} onChange={(event) => { setEntryCost(event.target.value); changed(); }} /></label>
          </div>
          <fieldset className="tower-participants"><legend>Personagens padrão <small>(opcional)</small></legend><div>{characters.map((character) => <label key={character.id} className={participantIds.includes(character.id) ? "participant-chip participant-chip--selected" : "participant-chip"}><input type="checkbox" checked={participantIds.includes(character.id)} onChange={() => { setParticipantIds((current) => current.includes(character.id) ? current.filter((id) => id !== character.id) : [...current, character.id]); changed(); }} /><span>{character.name}<small>{character.accountName}</small></span></label>)}</div>{!characters.length && <p className="muted">Nenhum personagem disponível.</p>}</fieldset>
          <div className="tower-drops"><div className="section-title"><div><strong>Itens relevantes</strong><span>O catálogo não registra drops nem movimenta o inventário.</span></div><button className="secondary-button" type="button" disabled={items.length >= 100} onClick={() => { setItems((current) => [...current, { id: nextItemId.current++, itemName: "", estimatedUnitValue: "" }]); changed(); }}><Plus size={16} />Adicionar item</button></div>
            {!items.length && <p className="tower-catalog-empty">Nenhum item configurado. Adicione os itens que deseja acompanhar.</p>}
            {items.map((item, index) => <div className="drop-editor tower-catalog-editor" key={item.id}>
              <label className="field"><span>Nome do item {index + 1}</span><input maxLength={120} value={item.itemName} onChange={(event) => { setItems((current) => current.map((row) => row.id === item.id ? { ...row, itemName: event.target.value } : row)); changed(); }} placeholder="Ex.: Pedra rara" /></label>
              <label className="field"><span>Valor estimado do item {index + 1} (gold)</span><input inputMode="numeric" value={item.estimatedUnitValue} onChange={(event) => { setItems((current) => current.map((row) => row.id === item.id ? { ...row, estimatedUnitValue: event.target.value } : row)); changed(); }} placeholder="Opcional" /></label>
              <button className="icon-button drop-remove" type="button" aria-label={`Remover item ${index + 1}`} onClick={() => { setItems((current) => current.filter((row) => row.id !== item.id)); changed(); }}><Trash size={18} /></button>
            </div>)}
          </div>
          {error && <div className="error-banner" role="alert">{error}</div>}
          {success && <p className="tower-success" role="status">Configuração salva.</p>}
        </fieldset>
        <footer className="day-dialog__footer"><div className="tower-session-action"><button className="secondary-button" type="button" disabled={saving || dirty} onClick={onRegister}><ShieldChevron size={16} />Registrar sessão</button><span>{dirty ? "Salve as alterações antes de registrar uma sessão." : "Registre uma abertura somente após realizá-la."}</span></div><div><button className="secondary-button" type="button" disabled={saving} onClick={onClose}>Fechar</button><button className="primary-button" type="submit" disabled={saving}>{saving ? "Salvando..." : "Salvar configuração"}</button></div></footer>
      </form>
    </section>
  </div>;
}
