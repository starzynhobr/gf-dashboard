import { Coins, Plus, ShieldChevron, Trash, X } from "@phosphor-icons/react";
import { useState } from "react";

import type { TodayCharactersResult, TowerRegistrationInput } from "../gateway/AppGateway";

type Character = Extract<TodayCharactersResult, { state: "ready" }>["characters"][number];
type DropDraft = { id: number; itemName: string; quantity: string; estimatedUnitValue: string };

export function TowerDialog({ characters, saving, error, onClose, onSave }: {
  characters: Character[];
  saving: boolean;
  error: string | null;
  onClose: () => void;
  onSave: (input: TowerRegistrationInput) => Promise<void>;
}) {
  const [guildName, setGuildName] = useState("");
  const [participantIds, setParticipantIds] = useState<string[]>([]);
  const [drops, setDrops] = useState<DropDraft[]>([{ id: 1, itemName: "", quantity: "1", estimatedUnitValue: "" }]);
  const [nextDropId, setNextDropId] = useState(2);

  function toggleParticipant(characterId: string) {
    setParticipantIds((current) => current.includes(characterId) ? current.filter((id) => id !== characterId) : [...current, characterId]);
  }

  function updateDrop(id: number, field: keyof Omit<DropDraft, "id">, value: string) {
    setDrops((current) => current.map((drop) => drop.id === id ? { ...drop, [field]: value } : drop));
  }

  function addDrop() {
    setDrops((current) => [...current, { id: nextDropId, itemName: "", quantity: "1", estimatedUnitValue: "" }]);
    setNextDropId((current) => current + 1);
  }

  async function submit() {
    await onSave({
      guildName: guildName.trim(),
      participantIds,
      drops: drops.filter((drop) => drop.itemName.trim()).map((drop) => ({
        itemName: drop.itemName.trim(),
        quantity: Math.max(1, Number(drop.quantity) || 1),
        estimatedUnitValue: drop.estimatedUnitValue ? Math.max(0, Number(drop.estimatedUnitValue) || 0) : null,
      })),
    });
  }

  return <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !saving) onClose(); }}>
    <section className="day-dialog tower-dialog" role="dialog" aria-modal="true" aria-labelledby="tower-title">
      <header className="day-dialog__header"><div className="day-dialog__identity"><i><ShieldChevron size={25} weight="duotone" /></i><div><h2 id="tower-title">Registrar Torre concluída</h2><span>Sessão independente das dungeons diárias</span></div></div><button className="icon-button" type="button" aria-label="Fechar" disabled={saving} onClick={onClose}><X size={21} /></button></header>
      <div className="day-dialog__body tower-dialog__body">
        <div className="tower-cost"><Coins size={23} weight="duotone" /><div><span>Custo fixo da abertura</span><strong>25.000 gold</strong></div><small>A sessão será salva como concluída.</small></div>
        <label className="field"><span>Guild (opcional)</span><input value={guildName} onChange={(event) => setGuildName(event.target.value)} placeholder="Nome usado nesta abertura" /></label>
        <fieldset className="tower-participants"><legend>Personagens participantes <small>(opcional)</small></legend><div>{characters.map((character) => <label key={character.id} className={participantIds.includes(character.id) ? "participant-chip participant-chip--selected" : "participant-chip"}><input type="checkbox" checked={participantIds.includes(character.id)} onChange={() => toggleParticipant(character.id)} /><span>{character.name}<small>{character.accountName}</small></span></label>)}</div></fieldset>
        <div className="tower-drops"><div className="section-title"><div><strong>Drops relevantes</strong><span>Registre apenas o que vale acompanhar ou vender.</span></div><button className="secondary-button" type="button" onClick={addDrop}><Plus size={16} />Adicionar drop</button></div>
          {drops.map((drop) => <div className="drop-editor" key={drop.id}><label className="field"><span>Item</span><input value={drop.itemName} onChange={(event) => updateDrop(drop.id, "itemName", event.target.value)} placeholder="Ex.: Pedra rara" /></label><label className="field field--small"><span>Qtd.</span><input type="number" min="1" value={drop.quantity} onChange={(event) => updateDrop(drop.id, "quantity", event.target.value)} /></label><label className="field field--value"><span>Valor unitário estimado</span><input type="number" min="0" value={drop.estimatedUnitValue} onChange={(event) => updateDrop(drop.id, "estimatedUnitValue", event.target.value)} placeholder="Opcional" /></label>{drops.length > 1 && <button className="icon-button drop-remove" type="button" aria-label="Remover drop" onClick={() => setDrops((current) => current.filter((item) => item.id !== drop.id))}><Trash size={18} /></button>}</div>)}
        </div>
        {error && <div className="error-banner" role="alert">{error}</div>}
      </div>
      <footer className="day-dialog__footer"><span>{participantIds.length} participante(s) · {drops.filter((drop) => drop.itemName.trim()).length} drop(s)</span><div><button className="secondary-button" type="button" disabled={saving} onClick={onClose}>Cancelar</button><button className="primary-button" type="button" disabled={saving} onClick={() => void submit()}>{saving ? "Salvando..." : "Registrar sessão"}</button></div></footer>
    </section>
  </div>;
}
