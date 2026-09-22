import { PencilSimple, Receipt, Trash, X } from "@phosphor-icons/react";
import { useCallback, useEffect, useState } from "react";
import type { AppGateway, ExpenseCategory, ExpenseHistoryRow, ExpenseRegistrationInput } from "../gateway/AppGateway";

const categoryLabels: Record<ExpenseCategory, string> = {
  upgrade: "Melhoria",
  consumable: "Consumível",
  service: "Serviço",
  other: "Outro",
};
const numberFormat = new Intl.NumberFormat("pt-BR");

function dateValue(iso: string): string {
  return iso.slice(0, 10);
}

export function ExpenseHistoryDialog({ gateway, onClose, onChanged }: {
  gateway: AppGateway;
  onClose: () => void;
  onChanged: () => Promise<void>;
}) {
  const [expenses, setExpenses] = useState<ExpenseHistoryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<ExpenseHistoryRow | null>(null);
  const [draft, setDraft] = useState<ExpenseRegistrationInput | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmVoidId, setConfirmVoidId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await gateway.getExpenseHistory();
      setExpenses(result.expenses);
      setError(null);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Não foi possível carregar as despesas.");
    } finally {
      setLoading(false);
    }
  }, [gateway]);
  useEffect(() => {
    const timer = window.setTimeout(() => { void load(); }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  const beginEdit = (expense: ExpenseHistoryRow) => {
    setEditing(expense);
    setDraft({
      category: expense.category,
      amountGold: expense.amountGold,
      occurredOn: dateValue(expense.occurredAt),
      description: expense.description ?? "",
    });
    setConfirmVoidId(null);
    setError(null);
  };
  const saveEdit = async () => {
    if (!editing || !draft) return;
    setBusy(true);
    try {
      await gateway.updateExpense(editing.id, draft);
      setEditing(null);
      setDraft(null);
      await Promise.all([load(), onChanged()]);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Não foi possível corrigir a despesa.");
    } finally {
      setBusy(false);
    }
  };
  const voidExpense = async (expenseId: string) => {
    setBusy(true);
    try {
      await gateway.voidExpense(expenseId);
      setConfirmVoidId(null);
      await Promise.all([load(), onChanged()]);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Não foi possível estornar a despesa.");
    } finally {
      setBusy(false);
    }
  };

  return <div className="dialog-backdrop" role="presentation" onMouseDown={() => !busy && onClose()}>
    <section className="day-dialog expense-history-dialog" role="dialog" aria-modal="true" aria-labelledby="expense-history-title" onMouseDown={(event) => event.stopPropagation()}>
      <header className="day-dialog__header"><div className="day-dialog__identity"><i><Receipt size={25} weight="duotone" /></i><div><h2 id="expense-history-title">Despesas cadastradas</h2><span>Corrija ou estorne lançamentos sem apagar o histórico de auditoria.</span></div></div><button className="icon-button" type="button" aria-label="Fechar" disabled={busy} onClick={onClose}><X size={21} /></button></header>
      <div className="day-dialog__body expense-history-dialog__body">
        {error && <p className="form-error" role="alert">{error}</p>}
        {loading ? <p className="text-slate-400">Carregando despesas...</p> : expenses.length === 0 ? <p className="text-slate-400">Nenhuma despesa manual cadastrada.</p> : <div className="expense-history-list">{expenses.map((expense) => <article className="expense-history-row" key={expense.id}>
          {editing?.id === expense.id && draft ? <div className="expense-history-edit">
            <label>Categoria<select value={draft.category} disabled={busy} onChange={(event) => setDraft({ ...draft, category: event.target.value as ExpenseCategory })}>{Object.entries(categoryLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
            <label>Gold gasto<input inputMode="numeric" value={draft.amountGold} disabled={busy} onChange={(event) => setDraft({ ...draft, amountGold: Number(event.target.value.replace(/\D/g, "")) || 0 })} /></label>
            <label>Data<input type="date" value={draft.occurredOn} disabled={busy} onChange={(event) => setDraft({ ...draft, occurredOn: event.target.value })} /></label>
            <label className="expense-history-edit__description">Descrição<input value={draft.description ?? ""} disabled={busy} maxLength={140} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></label>
            <div className="expense-history-actions"><button className="secondary-button" type="button" disabled={busy} onClick={() => { setEditing(null); setDraft(null); }}>Cancelar</button><button className="primary-button" type="button" disabled={busy || draft.amountGold <= 0 || !draft.occurredOn} onClick={() => void saveEdit()}>{busy ? "Salvando..." : "Salvar correção"}</button></div>
          </div> : <>
            <div><strong>{categoryLabels[expense.category]}</strong><span>{expense.description || "Sem descrição"}</span></div>
            <time dateTime={expense.occurredAt}>{dateValue(expense.occurredAt).split("-").reverse().join("/")}</time>
            <strong className="expense-history-row__amount">{numberFormat.format(expense.amountGold)} gold</strong>
            <div className="expense-history-actions">{confirmVoidId === expense.id ? <><button className="secondary-button" type="button" disabled={busy} onClick={() => setConfirmVoidId(null)}>Cancelar</button><button className="danger-button" type="button" disabled={busy} onClick={() => void voidExpense(expense.id)}>{busy ? "Estornando..." : "Confirmar estorno"}</button></> : <><button className="icon-button" type="button" aria-label={`Editar despesa ${expense.description || categoryLabels[expense.category]}`} disabled={busy} onClick={() => beginEdit(expense)}><PencilSimple size={18} /></button><button className="icon-button icon-button--danger" type="button" aria-label={`Estornar despesa ${expense.description || categoryLabels[expense.category]}`} disabled={busy} onClick={() => setConfirmVoidId(expense.id)}><Trash size={18} /></button></>}</div>
          </>}
        </article>)}</div>}
      </div>
      <footer className="day-dialog__footer"><button className="secondary-button" type="button" disabled={busy} onClick={onClose}>Fechar</button></footer>
    </section>
  </div>;
}
