import { ArrowRight, Coins, CurrencyDollar, Package, Tote, X } from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";

import type { AppGateway } from "../gateway/AppGateway";

interface SaleDialogProps {
  gateway: AppGateway;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const currencyFormat = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

export function SaleDialog({ gateway, isOpen, onClose, onSuccess }: SaleDialogProps) {
  const [saleType, setSaleType] = useState<"gold" | "pve_bag" | "item">("gold");
  const [goldQuantity, setGoldQuantity] = useState<string>("1000000");
  const [pveBagQuantity, setPveBagQuantity] = useState<string>("10");
  const [itemName, setItemName] = useState<string>("");
  const [itemQuantity, setItemQuantity] = useState<string>("1");
  const [amountStr, setAmountStr] = useState<string>("25,00");
  const [currency, setCurrency] = useState<string>("BRL");
  const [saleDate, setSaleDate] = useState<string>(() => new Date().toISOString().slice(0, 10));

  const [rateMode, setRateMode] = useState<"auto" | "manual">("auto");
  const [autoRateMicros, setAutoRateMicros] = useState<number>(1_000_000);
  const [autoRateFormatted, setAutoRateFormatted] = useState<string>("1,00");
  const [manualRateStr, setManualRateStr] = useState<string>("5,43");
  const [fetchingRate, setFetchingRate] = useState<boolean>(false);

  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch exchange rate on currency or date change
  useEffect(() => {
    if (!isOpen || currency === "BRL") return;

    let active = true;
    gateway
      .getCurrencyRate(currency, "BRL", saleDate)
      .then((res) => {
        if (!active) return;
        setAutoRateMicros(res.rateMicros);
        setAutoRateFormatted(res.rateFormatted);
        setManualRateStr(res.rateFormatted);
        setFetchingRate(false);
      })
      .catch(() => {
        if (!active) return;
        // Fallback default
        const def = currency === "EUR" ? "6,42" : "5,43";
        const defMicros = currency === "EUR" ? 6_420_000 : 5_430_000;
        setAutoRateMicros(defMicros);
        setAutoRateFormatted(def);
        setManualRateStr(def);
        setFetchingRate(false);
      });

    return () => {
      active = false;
    };
  }, [gateway, isOpen, currency, saleDate]);

  // Compute effective rate & converted amount
  const parsedAmount = useMemo(() => {
    const clean = amountStr.replace(/\./g, "").replace(",", ".");
    const num = parseFloat(clean);
    return isNaN(num) || num < 0 ? 0 : num;
  }, [amountStr]);

  const effectiveRateMicros = useMemo(() => {
    if (currency === "BRL") return 1_000_000;
    if (rateMode === "auto") return autoRateMicros;
    const clean = manualRateStr.replace(/\./g, "").replace(",", ".");
    const num = parseFloat(clean);
    return isNaN(num) || num <= 0 ? 1_000_000 : Math.round(num * 1_000_000);
  }, [currency, rateMode, autoRateMicros, manualRateStr]);

  const convertedBrlAmount = useMemo(() => {
    if (currency === "BRL") return parsedAmount;
    return parsedAmount * (effectiveRateMicros / 1_000_000);
  }, [currency, parsedAmount, effectiveRateMicros]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (parsedAmount <= 0) {
      setError("Informe um valor recebido válido maior que zero.");
      return;
    }

    let desc: string;
    let qty: number;

    if (saleType === "gold") {
      const g = parseInt(goldQuantity.replace(/\D/g, ""), 10);
      if (isNaN(g) || g <= 0) {
        setError("Informe uma quantidade de gold válida.");
        return;
      }
      qty = g;
      desc = "Gold";
    } else if (saleType === "pve_bag") {
      const b = parseInt(pveBagQuantity, 10);
      if (isNaN(b) || b <= 0) {
        setError("Informe a quantidade de sacos PvE.");
        return;
      }
      qty = b;
      desc = "Saco de Cristal (PvE)";
    } else {
      if (!itemName.trim()) {
        setError("Informe a descrição ou nome do item.");
        return;
      }
      const q = parseInt(itemQuantity, 10);
      qty = isNaN(q) || q <= 0 ? 1 : q;
      desc = itemName.trim();
    }

    try {
      setSubmitting(true);
      setError(null);
      const originalMinor = Math.round(parsedAmount * 100);
      const realMinor = Math.round(convertedBrlAmount * 100);

      await gateway.recordSale({
        saleType,
        itemDescription: desc,
        quantity: qty,
        originalAmountMinor: originalMinor,
        currency,
        exchangeRateMicros: effectiveRateMicros,
        realAmountMinor: realMinor,
        soldAt: `${saleDate}T12:00:00`,
      });

      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao registrar venda");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="dialog-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !submitting) onClose();
      }}
    >
      <form
        className="edit-dialog sale-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="sale-dialog-title"
        onSubmit={(e) => void handleSubmit(e)}
      >
        <header className="sale-dialog__header">
          <div className="edit-dialog__identity">
            <i className="sale-icon-badge">
              <CurrencyDollar size={24} weight="bold" />
            </i>
            <div>
              <h2 id="sale-dialog-title">Nova venda</h2>
              <span>Registre a venda de gold, sacos PvE ou itens comercializados.</span>
            </div>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label="Fechar"
            disabled={submitting}
          >
            <X size={20} />
          </button>
        </header>

        <div className="edit-dialog__body sale-dialog__body">
          {error && <div className="error-banner" role="alert">{error}</div>}

          {/* Tipo de Venda */}
          <div className="sale-form-field">
            <span>Tipo</span>
            <div className="sale-type-selector">
              <button
                type="button"
                className={`type-pill ${saleType === "gold" ? "type-pill--active" : ""}`}
                onClick={() => setSaleType("gold")}
              >
                <Coins size={16} weight={saleType === "gold" ? "fill" : "regular"} />
                <span>Gold</span>
              </button>
              <button
                type="button"
                className={`type-pill ${saleType === "pve_bag" ? "type-pill--active" : ""}`}
                onClick={() => setSaleType("pve_bag")}
              >
                <Tote size={16} weight={saleType === "pve_bag" ? "fill" : "regular"} />
                <span>Saco PvE</span>
              </button>
              <button
                type="button"
                className={`type-pill ${saleType === "item" ? "type-pill--active" : ""}`}
                onClick={() => setSaleType("item")}
              >
                <Package size={16} weight={saleType === "item" ? "fill" : "regular"} />
                <span>Item</span>
              </button>
            </div>
          </div>

          {/* Campos específicos por tipo */}
          {saleType === "gold" && (
            <label className="sale-form-field">
              <span>Quantidade de Gold</span>
              <input
                id="gold-quantity-input"
                aria-label="Quantidade de Gold"
                type="text"
                value={goldQuantity}
                onChange={(e) => setGoldQuantity(e.target.value)}
                placeholder="Ex.: 1.000.000"
                required
              />
            </label>
          )}

          {saleType === "pve_bag" && (
            <label className="sale-form-field">
              <span>Quantidade de Sacos</span>
              <input
                id="pve-bag-quantity-input"
                aria-label="Quantidade de Sacos"
                type="number"
                min="1"
                value={pveBagQuantity}
                onChange={(e) => setPveBagQuantity(e.target.value)}
                placeholder="Ex.: 10"
                required
              />
            </label>
          )}

          {saleType === "item" && (
            <div className="sale-form-row sale-form-row--item">
              <label className="sale-form-field">
                <span>Nome / Descrição do Item</span>
                <input
                  id="item-name-input"
                  aria-label="Nome / Descrição do Item"
                  type="text"
                  value={itemName}
                  onChange={(e) => setItemName(e.target.value)}
                  placeholder="Ex.: Pedra da Alma"
                  required
                />
              </label>
              <label className="sale-form-field">
                <span>Qtd.</span>
                <input
                  id="item-qty-input"
                  aria-label="Qtd."
                  type="number"
                  min="1"
                  value={itemQuantity}
                  onChange={(e) => setItemQuantity(e.target.value)}
                  required
                />
              </label>
            </div>
          )}

          {/* Valor recebido & Moeda */}
          <div className="sale-form-row sale-form-row--amount">
            <label className="sale-form-field">
              <span>Valor recebido</span>
              <input
                id="amount-input"
                aria-label="Valor recebido"
                type="text"
                value={amountStr}
                onChange={(e) => setAmountStr(e.target.value)}
                placeholder="25,00"
                required
              />
            </label>
            <label className="sale-form-field">
              <span>Moeda</span>
              <select
                id="currency-select"
                aria-label="Moeda"
                className="sale-currency-select"
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
              >
                <option value="BRL">BRL (R$)</option>
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
              </select>
            </label>
          </div>

          {/* Data da venda */}
          <label className="sale-form-field">
            <span>Data da venda</span>
            <input
              id="sale-date-input"
              aria-label="Data da venda"
              type="date"
              value={saleDate}
              onChange={(e) => setSaleDate(e.target.value)}
              required
            />
          </label>

          {/* Conversão Multimoeda */}
          {currency !== "BRL" && (
            <div className="currency-conversion-card">
              <div className="conversion-rate-header">
                <span className="conversion-label">Cotação</span>
                <div className="rate-mode-toggle">
                  <button
                    type="button"
                    className={`rate-mode-btn ${rateMode === "auto" ? "rate-mode-btn--active" : ""}`}
                    onClick={() => setRateMode("auto")}
                  >
                    Automática (API)
                  </button>
                  <button
                    type="button"
                    className={`rate-mode-btn ${rateMode === "manual" ? "rate-mode-btn--active" : ""}`}
                    onClick={() => setRateMode("manual")}
                  >
                    Manual
                  </button>
                </div>
              </div>

              <div className="conversion-rate-row">
                <span className="rate-pair-text">
                  {currency} <ArrowRight size={13} className="inline" /> BRL:
                </span>
                {rateMode === "auto" ? (
                  <span className="rate-value-badge">
                    {fetchingRate ? "Buscando..." : `R$ ${autoRateFormatted}`}
                  </span>
                ) : (
                  <div className="rate-input-wrap">
                    <span>R$</span>
                    <input
                      type="text"
                      className="rate-input"
                      value={manualRateStr}
                      onChange={(e) => setManualRateStr(e.target.value)}
                      placeholder="5,21"
                    />
                  </div>
                )}
              </div>

              <div className="converted-total-row">
                <span>Valor convertido</span>
                <strong className="converted-total-value">
                  {currencyFormat.format(convertedBrlAmount)}
                </strong>
              </div>
            </div>
          )}
        </div>

        <footer>
          <button
            type="button"
            className="secondary-button"
            onClick={onClose}
            disabled={submitting}
          >
            Cancelar
          </button>
          <button
            type="submit"
            className="primary-button sale-action-submit"
            disabled={submitting}
          >
            <CurrencyDollar size={17} weight="bold" />
            {submitting ? "Registrando..." : "Registrar venda"}
          </button>
        </footer>
      </form>
    </div>
  );
}
