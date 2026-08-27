import { Buildings, PencilSimple, User } from "@phosphor-icons/react";
import { type FormEvent, useState } from "react";

type AccountDraft = { kind: "account"; id: string; name: string; serverName: string };
type CharacterDraft = { kind: "character"; id: string; name: string; className: string; level: number };
export type RegistrationDraft = AccountDraft | CharacterDraft;

export function EditRegistrationDialog({ draft, saving, error, onClose, onSave }: {
  draft: RegistrationDraft;
  saving: boolean;
  error: string | null;
  onClose: () => void;
  onSave: (draft: RegistrationDraft) => Promise<void>;
}) {
  const [name, setName] = useState(draft.name);
  const [serverName, setServerName] = useState(draft.kind === "account" ? draft.serverName : "");
  const [className, setClassName] = useState(draft.kind === "character" ? draft.className : "");
  const [level, setLevel] = useState(draft.kind === "character" ? draft.level : 1);
  const account = draft.kind === "account";

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (account) await onSave({ kind: "account", id: draft.id, name, serverName });
    else await onSave({ kind: "character", id: draft.id, name, className, level });
  }

  return <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !saving) onClose(); }}>
    <form className="edit-dialog" role="dialog" aria-modal="true" aria-labelledby="edit-registration-title" onSubmit={(event) => void submit(event)}>
      <header><div className="edit-dialog__identity"><i>{account ? <Buildings size={23} weight="duotone" /> : <User size={23} weight="duotone" />}</i><div><h2 id="edit-registration-title">Editar {account ? "conta" : "personagem"}</h2><span>Os dados de farm e histórico já registrados serão preservados.</span></div></div></header>
      <div className="edit-dialog__body">
        <label>Nome<input aria-label={account ? "Novo nome da conta" : "Novo nome do personagem"} value={name} onChange={(event) => setName(event.target.value)} required autoFocus /></label>
        {account ? <label>Servidor<input aria-label="Novo servidor" value={serverName} onChange={(event) => setServerName(event.target.value)} required /></label> : <><label>Classe<input aria-label="Nova classe" value={className} onChange={(event) => setClassName(event.target.value)} required /></label><label>Nível<input aria-label="Novo nível" type="number" min="1" max="999" value={level} onChange={(event) => setLevel(Number(event.target.value))} required /></label></>}
        {error && <div className="error-banner" role="alert">{error}</div>}
      </div>
      <footer><button className="secondary-button" type="button" disabled={saving} onClick={onClose}>Cancelar</button><button className="primary-button" disabled={saving || !name.trim() || (account ? !serverName.trim() : !className.trim())}><PencilSimple size={17} />{saving ? "Salvando..." : "Salvar alterações"}</button></footer>
    </form>
  </div>;
}
