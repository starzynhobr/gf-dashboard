import { Coins, ShieldChevron, X } from "@phosphor-icons/react";
import { useRef, useState } from "react";

import type { TodayCharactersResult, TowerConfiguration, TowerRegistrationInput } from "../gateway/AppGateway";
import { towerInteger } from "./towerValidation";
import { towerDialogKeyboard } from "./towerDialogKeyboard";

type Character = Extract<TodayCharactersResult, { state: "ready" }>["characters"][number];
const numberFormat = new Intl.NumberFormat("pt-BR");

export function TowerDialog({ configuration, characters, activityDate, saving, error, onClose, onSave }: {
  configuration: TowerConfiguration;
  characters: Character[];
  activityDate?: string;
  saving: boolean;
  error: string | null;
  onClose: () => void;
  onSave: (input: TowerRegistrationInput) => Promise<void>;
}) {
  const [sessionDate] = useState(() => {
    if (activityDate) return activityDate;
    const date = new Date();
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  });
  const [guildName, setGuildName] = useState(configuration.guildName);
  const [participantIds, setParticipantIds] = useState<string[]>([...configuration.participantIds]);
  const [quantities, setQuantities] = useState<Record<string, string>>({});
  const [validationError, setValidationError] = useState<string | null>(null);
  const busy = useRef(false);
  const submission = useRef<{ fingerprint: string; key: string } | null>(null);

  async function submit() {
    if (busy.current || saving) return;
    setValidationError(null);
    try {
      if (guildName.trim().length > 120) throw new Error("O nome da guilda deve ter até 120 caracteres.");
      if (participantIds.length > 100) throw new Error("Selecione até 100 participantes.");
      const drops = configuration.items.flatMap((item) => {
        const quantity = towerInteger(quantities[item.itemId] ?? "0", `Quantidade de ${item.itemName}`);
        return quantity === 0 ? [] : [{ itemName: item.itemName, quantity, estimatedUnitValue: item.estimatedUnitValue }];
      });
      const payload = { activityDate: sessionDate, guildName: guildName.trim(), participantIds, drops };
      const fingerprint = JSON.stringify(payload);
      if (submission.current?.fingerprint !== fingerprint) submission.current = { fingerprint, key: crypto.randomUUID() };
      busy.current = true;
      await onSave({ ...payload, idempotencyKey: submission.current.key });
    } catch (reason: unknown) {
      setValidationError(reason instanceof Error ? reason.message : "Não foi possível registrar a sessão.");
    } finally { busy.current = false; }
  }

  return <div className="dialog-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget && !saving) onClose(); }}>
    <section className="day-dialog tower-dialog" role="dialog" aria-modal="true" aria-labelledby="tower-title" onKeyDown={(event) => towerDialogKeyboard(event, onClose, saving)}>
      <header className="day-dialog__header"><div className="day-dialog__identity"><i><ShieldChevron size={25} weight="duotone" /></i><div><h2 id="tower-title">Registrar Torre concluída</h2><span>Esta ação cria uma sessão e registra somente os drops obtidos</span></div></div><button className="icon-button" type="button" aria-label="Voltar à configuração" disabled={saving} onClick={onClose}><X size={21} /></button></header>
      <form className="tower-configuration-form" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
        <fieldset className="tower-dialog__body" disabled={saving}>
          <div className="tower-cost"><Coins size={23} weight="duotone" /><div><span>Custo configurado da abertura</span><strong>{numberFormat.format(configuration.entryCostGold)} gold</strong></div><small>Uma cobrança por sessão.</small></div>
          <label className="field"><span>Guilda da sessão</span><input autoFocus maxLength={120} value={guildName} onChange={(event) => setGuildName(event.target.value)} placeholder="Opcional" /></label>
          <fieldset className="tower-participants"><legend>Personagens participantes <small>(opcional)</small></legend><div>{characters.map((character) => <label key={character.id} className={participantIds.includes(character.id) ? "participant-chip participant-chip--selected" : "participant-chip"}><input type="checkbox" checked={participantIds.includes(character.id)} onChange={() => setParticipantIds((current) => current.includes(character.id) ? current.filter((id) => id !== character.id) : [...current, character.id])} /><span>{character.name}<small>{character.accountName}</small></span></label>)}</div></fieldset>
          <div className="tower-drops"><div className="section-title"><div><strong>Drops obtidos nesta sessão</strong><span>Deixe zero para os itens que não caíram.</span></div></div>
            {configuration.items.map((item) => <div className="drop-editor tower-session-item" key={item.itemId}><span>{item.itemName}<small>{item.estimatedUnitValue === null ? "Sem valor estimado" : `${numberFormat.format(item.estimatedUnitValue)} gold / unidade`}</small></span><label className="field"><span>Quantidade de {item.itemName}</span><input inputMode="numeric" value={quantities[item.itemId] ?? "0"} onChange={(event) => setQuantities((current) => ({ ...current, [item.itemId]: event.target.value }))} /></label></div>)}
            {!configuration.items.length && <p className="tower-catalog-empty">Nenhum item no catálogo. A sessão pode ser registrada sem drops.</p>}
          </div>
          {(validationError || error) && <div className="error-banner" role="alert">{validationError || error}</div>}
        </fieldset>
        <footer className="day-dialog__footer"><span>{participantIds.length} participante(s) · Sessão independente das dungeons</span><div><button className="secondary-button" type="button" disabled={saving} onClick={onClose}>Voltar</button><button className="primary-button" type="submit" disabled={saving}>{saving ? "Registrando..." : "Confirmar sessão"}</button></div></footer>
      </form>
    </section>
  </div>;
}
