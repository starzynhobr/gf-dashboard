import { Coins, Sparkle } from "@phosphor-icons/react";
import { type FormEvent, useState } from "react";

const numberFormat = new Intl.NumberFormat("pt-BR");

export function PveBagPriceDialog({
  currentPrice,
  saving,
  error,
  onClose,
  onSave,
}: {
  currentPrice: number | null;
  saving: boolean;
  error: string | null;
  onClose: () => void;
  onSave: (unitValueGold: number) => Promise<void>;
}) {
  const [price, setPrice] = useState(currentPrice !== null ? String(currentPrice) : "1000");

  async function submit(event: FormEvent) {
    event.preventDefault();
    const parsed = parseInt(price, 10);
    if (isNaN(parsed) || parsed < 0) return;
    await onSave(parsed);
  }

  return (
    <div
      className="dialog-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !saving) onClose();
      }}
    >
      <form
        className="edit-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="pve-bag-price-title"
        onSubmit={(event) => void submit(event)}
      >
        <header>
          <div className="edit-dialog__identity">
            <i>
              <Coins size={23} weight="duotone" />
            </i>
            <div>
              <h2 id="pve-bag-price-title">Preço do Saco PvE</h2>
              <span>Atualize a cotação média de mercado por unidade de Saco PvE.</span>
            </div>
          </div>
        </header>
        <div className="edit-dialog__body">
          {currentPrice !== null && (
            <div className="price-quote-current">
              <Sparkle size={15} weight="duotone" />
              <span>
                Cotação atual: <strong>{numberFormat.format(currentPrice)} Gold</strong> / unid.
              </span>
            </div>
          )}
          <label>
            Novo valor por unidade (Gold)
            <input
              aria-label="Novo preço unitário em Gold"
              type="number"
              min="0"
              step="1"
              value={price}
              onChange={(event) => setPrice(event.target.value)}
              placeholder="Ex.: 1000"
              required
              autoFocus
            />
          </label>
          {error && (
            <div className="error-banner" role="alert">
              {error}
            </div>
          )}
        </div>
        <footer>
          <button className="secondary-button" type="button" disabled={saving} onClick={onClose}>
            Cancelar
          </button>
          <button
            className="primary-button"
            type="submit"
            disabled={saving || !price.trim() || isNaN(Number(price)) || Number(price) < 0}
          >
            <Coins size={17} />
            {saving ? "Salvando..." : "Salvar cotação"}
          </button>
        </footer>
      </form>
    </div>
  );
}
