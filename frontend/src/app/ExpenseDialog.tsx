import { Coins, Receipt, X } from "@phosphor-icons/react";
import { useState } from "react";
import type { ExpenseCategory, ExpenseRegistrationInput } from "../gateway/AppGateway";

const categories: Array<{ value: ExpenseCategory; label: string }> = [
  { value: "upgrade", label: "Melhoria" },
  { value: "consumable", label: "Consumível" },
  { value: "service", label: "Serviço" },
  { value: "other", label: "Outro" },
];

export function ExpenseDialog({ saving, error, onClose, onSave }: {
  saving: boolean;
  error: string | null;
  onClose: () => void;
  onSave: (input: ExpenseRegistrationInput) => Promise<void>;
}) {
  const [category, setCategory] = useState<ExpenseCategory>("upgrade");
  const [amountGold, setAmountGold] = useState("");
  const [description, setDescription] = useState("");
  const [occurredOn, setOccurredOn] = useState(() => new Date().toISOString().slice(0, 10));
  const submit = () => {
    const parsed = Number(amountGold.replace(/\D/g, ""));
    if (!Number.isSafeInteger(parsed) || parsed <= 0) return;
    void onSave({ category, amountGold: parsed, occurredOn, description: description.trim() || undefined });
  };
  return <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
    <section className="day-dialog expense-dialog" role="dialog" aria-modal="true" aria-label="Nova despesa" onMouseDown={(event) => event.stopPropagation()}>
      <header className="day-dialog__header"><div className="day-dialog__identity"><i><Receipt size={25} weight="duotone" /></i><div><h2>Nova despesa</h2><span>Registre gold gasto sem alterar o farm obtido.</span></div></div><button className="icon-button" type="button" aria-label="Fechar" disabled={saving} onClick={onClose}><X size={21} /></button></header>
      <div className="day-dialog__body expense-dialog__body">
        <label className="sale-form-field"><span>Categoria</span><select aria-label="Categoria da despesa" className="sale-currency-select" value={category} disabled={saving} onChange={(event) => setCategory(event.target.value as ExpenseCategory)}>{categories.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
        <label className="sale-form-field"><span>Gold gasto</span><div className="expense-gold-input"><Coins size={18} weight="duotone" /><input aria-label="Gold gasto" inputMode="numeric" autoFocus value={amountGold} disabled={saving} onChange={(event) => setAmountGold(event.target.value)} placeholder="Ex.: 100000" onKeyDown={(event) => { if (event.key === "Enter") submit(); }} /></div></label>
        <label className="sale-form-field"><span>Descrição <small>(opcional)</small></span><input aria-label="Descrição da despesa" value={description} disabled={saving} maxLength={140} onChange={(event) => setDescription(event.target.value)} placeholder="Ex.: pedra para melhorar arma" /></label>
        <label className="sale-form-field"><span>Data da despesa</span><input aria-label="Data da despesa" type="date" value={occurredOn} disabled={saving} onChange={(event) => setOccurredOn(event.target.value)} /></label>
        {error && <p className="form-error" role="alert">{error}</p>}
      </div>
      <footer className="day-dialog__footer"><button className="secondary-button" type="button" disabled={saving} onClick={onClose}>Cancelar</button><button className="primary-button expense-submit" type="button" disabled={saving || !amountGold.trim()} onClick={submit}>{saving ? "Salvando..." : "Registrar despesa"}</button></footer>
    </section>
  </div>;
}
