import { Coins, Crown, X } from "@phosphor-icons/react";
import { useState } from "react";

import { formatGoldInput } from "./goldInput";

export function VipDialog({
  characterName, expiresAt, saving, error, onClose, onSave,
}: {
  characterName: string; expiresAt: string | null; saving: boolean; error: string | null;
  onClose: () => void; onSave: (paidGold: number, remainingDays: number, remainingHours: number) => void;
}) {
  const [paidGold, setPaidGold] = useState("100000");
  const [remaining, setRemaining] = useState(() => {
    const totalHours = expiresAt ? Math.max(1, Math.ceil((new Date(expiresAt).getTime() - Date.now()) / 3_600_000)) : 30 * 24;
    return { days: String(Math.floor(totalHours / 24)), hours: String(totalHours % 24) };
  });
  const isEditing = Boolean(expiresAt);
  const durationIsValid = Number(remaining.days) * 24 + Number(remaining.hours) > 0 && Number(remaining.days) * 24 + Number(remaining.hours) <= 30 * 24 && Number(remaining.hours) <= 23;
  const submit = () => onSave(Number(paidGold), Number(remaining.days), Number(remaining.hours));
  return <div className="dialog-backdrop" role="presentation" onMouseDown={() => !saving && onClose()}>
    <section className="edit-dialog" role="dialog" aria-modal="true" aria-label={`${isEditing ? "Ajustar" : "Ativar"} VIP para ${characterName}`} onMouseDown={(event) => event.stopPropagation()}>
      <header><div className="edit-dialog__identity"><i><Crown size={22} weight="duotone" /></i><div><h2>{isEditing ? "Ajustar VIP" : "Ativar VIP"}</h2><span>{characterName} · informe o tempo restante no cartão</span></div></div><button className="icon-button" type="button" aria-label="Fechar" onClick={onClose}><X size={18} /></button></header>
      <div className="edit-dialog__body vip-dialog__body">
        {!isEditing && <label>Valor pago em gold<div className="expense-gold-input calculator-gold-input"><Coins size={19} weight="duotone" /><input aria-label="Valor pago em gold" autoFocus inputMode="numeric" value={formatGoldInput(paidGold)} onChange={(event) => setPaidGold(event.target.value.replace(/\D/g, ""))} /><small>gold</small></div><small className="calculator-gold-hint">Separado automaticamente a cada milhar.</small></label>}
        <fieldset className="vip-duration"><legend>Tempo restante do VIP</legend><label><span>Dias</span><input aria-label="Dias restantes" autoFocus={isEditing} inputMode="numeric" min="0" max="30" value={remaining.days} onChange={(event) => setRemaining({ ...remaining, days: event.target.value.replace(/\D/g, "") })} /></label><label><span>Horas</span><input aria-label="Horas restantes" inputMode="numeric" min="0" max="23" value={remaining.hours} onChange={(event) => setRemaining({ ...remaining, hours: event.target.value.replace(/\D/g, "") })} onKeyDown={(event) => { if (event.key === "Enter" && durationIsValid) submit(); }} /></label></fieldset>
        <small className="muted">{isEditing ? "O ajuste altera somente a validade; a despesa original é preservada." : "O máximo é 30 dias. Se o VIP começou antes, copie o tempo restante mostrado no jogo."}</small>{error && <div className="error-banner" role="alert">{error}</div>}
      </div>
      <footer><button className="secondary-button" type="button" disabled={saving} onClick={onClose}>Cancelar</button><button className="primary-button" type="button" disabled={saving || Number(paidGold) <= 0 || !durationIsValid} onClick={submit}>{saving ? "Salvando..." : isEditing ? "Salvar ajuste" : "Ativar VIP"}</button></footer>
    </section>
  </div>;
}
