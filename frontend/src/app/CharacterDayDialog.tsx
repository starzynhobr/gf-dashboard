import { Check, Coins, FloppyDisk, X } from "@phosphor-icons/react";
import { useMemo, useState } from "react";

import type { CharacterDayResult } from "../gateway/AppGateway";

interface CharacterDayDialogProps {
  day: CharacterDayResult;
  saving: boolean;
  error: string | null;
  onClose: () => void;
  onSave: (completedIds: string[]) => Promise<void>;
}

const numberFormat = new Intl.NumberFormat("pt-BR");
const dateFormat = new Intl.DateTimeFormat("pt-BR", {
  day: "2-digit",
  month: "short",
  year: "numeric",
});

export function CharacterDayDialog({ day, saving, error, onClose, onSave }: CharacterDayDialogProps) {
  const [completed, setCompleted] = useState<Set<string>>(() => new Set(day.dungeons.map((dungeon) => dungeon.characterActivityId)));
  const totals = useMemo(() => day.dungeons.reduce((result, dungeon) => completed.has(dungeon.characterActivityId) ? { gold: result.gold + dungeon.gold, bags: result.bags + dungeon.pveBags } : result, { gold: 0, bags: 0 }), [completed, day.dungeons]);

  function toggle(id: string) {
    setCompleted((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  const formattedDate = day.activityDate ? dateFormat.format(new Date(day.activityDate + "T12:00:00")) : null;

  return <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
    <section className="character-dialog panel" role="dialog" aria-modal="true" aria-labelledby="character-day-title" onMouseDown={(event) => event.stopPropagation()}>
      <header className="dialog-header"><div><p>{day.accountName} · {day.className}{formattedDate ? ` · ${formattedDate}` : ""}</p><h2 id="character-day-title">{day.characterName}</h2><span>{completed.size} de {day.dungeons.length} dungeons concluídas</span></div><button className="icon-button" onClick={onClose} aria-label="Fechar"><X size={22} /></button></header>
      {error && <div className="error-banner" role="alert">{error}</div>}
      <div className="dialog-actions"><button onClick={() => setCompleted(new Set(day.dungeons.map((dungeon) => dungeon.characterActivityId)))}>Marcar todas</button><button onClick={() => setCompleted(new Set())}>Limpar</button></div>
      <div className="dungeon-checklist">{day.dungeons.map((dungeon) => {
        const checked = completed.has(dungeon.characterActivityId);
        return <label className={checked ? "dungeon-check dungeon-check--done" : "dungeon-check"} key={dungeon.characterActivityId}><input type="checkbox" checked={checked} onChange={() => toggle(dungeon.characterActivityId)} /><span className="check-visual"><Check size={16} weight="bold" /></span><span className="dungeon-copy"><strong>{dungeon.name}</strong><small>{dungeon.targetAmount} rodadas · {numberFormat.format(dungeon.gold)} gold · {dungeon.pveBags} Sacos PvE</small></span><b>{checked ? "Feita" : "Pendente"}</b></label>;
      })}</div>
      <footer className="dialog-footer"><div><span>Resultado confirmado</span><strong><Coins size={18} weight="fill" /> {numberFormat.format(totals.gold)} gold</strong><small>{totals.bags} Sacos PvE</small></div><button className="primary-button save-day" disabled={saving} onClick={() => void onSave([...completed])}><FloppyDisk size={19} />{saving ? "Salvando..." : "Salvar resumo"}</button></footer>
    </section>
  </div>;
}
