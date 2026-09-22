import { ArrowRight, Coins, CurrencyDollar, Package, Tote, X } from "@phosphor-icons/react";
import { useEffect, useMemo, useRef, useState } from "react";

import type { AppGateway } from "../gateway/AppGateway";

export interface SaleInitialData {
  saleType?: "gold" | "pve_bag" | "item";
  quantity?: number;
  amountStr?: string;
  currency?: string;
}

interface SaleDialogProps {
  gateway: AppGateway;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  initialData?: SaleInitialData | null;
}

const currencyFormat = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

function localDateTimeNow() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 16);
}

function parseDecimalToMinor(value: string, scale: number): number | null {
  const normalized = value.trim().replace(/\./g, "").replace(",", ".");
  if (!/^\d+(?:\.\d+)?$/.test(normalized)) return null;
  const [whole, fraction = ""] = normalized.split(".");
  const padded = `${fraction}${"0".repeat(scale)}`.slice(0, scale);
  const result = Number(whole) * 10 ** scale + Number(padded);
  return Number.isSafeInteger(result) ? result : null;
}

function formatNumberInput(value: string): string {
  const digits = value.replace(/\D/g, "");
  return digits ? digits.replace(/\B(?=(\d{3})+(?!\d))/g, ".") : "";
}

export function SaleDialog({ gateway, isOpen, onClose, onSuccess, initialData }: SaleDialogProps) {
  const [saleType, setSaleType] = useState<"gold" | "pve_bag" | "item">(() => {
    if (initialData?.saleType) return initialData.saleType;
    const value = localStorage.getItem("gf-dashboard.sale-type");
    return value === "pve_bag" || value === "item" ? value : "gold";
  });
  const [goldQuantity, setGoldQuantity] = useState<string>(() => {
    if (initialData?.saleType === "gold" && initialData.quantity) return String(initialData.quantity);
    return "1000000";
  });
  const [pveBagQuantity, setPveBagQuantity] = useState<string>(() => {
    if (initialData?.saleType === "pve_bag" && initialData.quantity) return String(initialData.quantity);
    return "10";
  });
  const [itemName, setItemName] = useState<string>("");
  const [itemQuantity, setItemQuantity] = useState<string>("1");
  const [amountStr, setAmountStr] = useState<string>(() => {
    if (initialData?.amountStr) return initialData.amountStr;
    return "25,00";
  });
  const [currency, setCurrency] = useState<string>(() => {
    if (initialData?.currency) return initialData.currency;
    return localStorage.getItem("gf-dashboard.sale-currency") ?? "BRL";
  });
  const [saleDateTime, setSaleDateTime] = useState(localDateTimeNow);

  const [rateMode, setRateMode] = useState<"auto" | "manual">("auto");
  const [autoRateMicros, setAutoRateMicros] = useState<number>(1_000_000);
  const [autoRateFormatted, setAutoRateFormatted] = useState<string>("1,00");
  const [autoRateSource, setAutoRateSource] = useState<string>("identity");
  const [manualRateStr, setManualRateStr] = useState<string>("5,43");
  const [fetchingRate, setFetchingRate] = useState<boolean>(false);

  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const idempotencyKey = useRef(crypto.randomUUID());


  useEffect(() => {
    localStorage.setItem("gf-dashboard.sale-type", saleType);
  }, [saleType]);

  useEffect(() => {
    localStorage.setItem("gf-dashboard.sale-currency", currency);
  }, [currency]);

  // Fetch exchange rate on currency or date change
  useEffect(() => {
    if (!isOpen || currency === "BRL") return;

    let active = true;
    gateway
      .getCurrencyRate(currency, "BRL", saleDateTime.slice(0, 10))
      .then((res) => {
        if (!active) return;
        setAutoRateMicros(res.rateMicros);
        setAutoRateFormatted(res.rateFormatted);
        setAutoRateSource(res.source);
        setManualRateStr(res.rateFormatted);
        setFetchingRate(false);
      })
      .catch(() => {
        if (!active) return;
        setAutoRateSource("unavailable");
        setFetchingRate(false);
      });

    return () => {
      active = false;
    };
  }, [gateway, isOpen, currency, saleDateTime]);

  // Compute effective rate & converted amount
  const originalMinor = useMemo(() => parseDecimalToMinor(amountStr, 2), [amountStr]);

  const effectiveRateMicros = useMemo(() => {
    if (currency === "BRL") return 1_000_000;
    if (rateMode === "auto") return autoRateMicros;
    return parseDecimalToMinor(manualRateStr, 6) ?? 0;
  }, [currency, rateMode, autoRateMicros, manualRateStr]);

  const convertedMinor = useMemo(() => originalMinor === null || effectiveRateMicros <= 0 ? 0 : Math.floor((originalMinor * effectiveRateMicros + 500_000) / 1_000_000), [originalMinor, effectiveRateMicros]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (originalMinor === null || originalMinor <= 0 || effectiveRateMicros <= 0) {
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
      const b = parseInt(pveBagQuantity.replace(/\D/g, ""), 10);
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
      const q = parseInt(itemQuantity.replace(/\D/g, ""), 10);
      qty = isNaN(q) || q <= 0 ? 1 : q;
      desc = itemName.trim();
    }

    try {
      setSubmitting(true);
      setError(null);
      const source = currency === "BRL" ? "identity" : rateMode === "manual" ? "manual" : autoRateSource;
      if (source === "unavailable") {
        setError("Não foi possível obter a cotação. Informe uma cotação manual para continuar.");
        return;
      }

      await gateway.recordSale({
        saleType,
        itemDescription: desc,
        quantity: qty,
        originalAmountMinor: originalMinor,
        currency,
        exchangeRateMicros: effectiveRateMicros,
        exchangeRateSource: source,
        idempotencyKey: idempotencyKey.current,
        soldAt: new Date(saleDateTime).toISOString(),
      });

      onSuccess();
      idempotencyKey.current = crypto.randomUUID();
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
              <div className="expense-gold-input sale-gold-input">
                <Coins size={19} weight="duotone" />
                <input
                  id="gold-quantity-input"
                  aria-label="Quantidade de Gold"
                  inputMode="numeric"
                  value={formatNumberInput(goldQuantity)}
                  onChange={(e) => setGoldQuantity(e.target.value.replace(/\D/g, ""))}
                  placeholder="Ex.: 1.000.000"
                  required
                />
                <small>gold</small>
              </div>
              <small className="sale-gold-hint">Separado automaticamente a cada milhar.</small>
            </label>
          )}

          {saleType === "pve_bag" && (
            <label className="sale-form-field">
              <span>Quantidade de Sacos</span>
              <div className="sale-number-input">
                <Tote size={19} weight="duotone" />
                <input
                  id="pve-bag-quantity-input"
                  aria-label="Quantidade de Sacos"
                  inputMode="numeric"
                  value={formatNumberInput(pveBagQuantity)}
                  onChange={(e) => setPveBagQuantity(e.target.value.replace(/\D/g, ""))}
                  placeholder="Ex.: 10"
                  required
                />
                <small>sacos</small>
              </div>
              <small className="sale-gold-hint">Separado automaticamente a cada milhar.</small>
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
                <div className="sale-number-input sale-number-input--compact">
                  <input
                    id="item-qty-input"
                    aria-label="Qtd."
                    inputMode="numeric"
                    value={formatNumberInput(itemQuantity)}
                    onChange={(e) => setItemQuantity(e.target.value.replace(/\D/g, ""))}
                    required
                  />
                  <small>unid.</small>
                </div>
              </label>
            </div>
          )}

          {/* Valor recebido & Moeda */}
          <div className="sale-form-row sale-form-row--amount">
            <label className="sale-form-field">
              <span>Valor recebido</span>
              <div className="sale-amount-input">
                <span className="sale-currency-symbol">
                  {currency === "USD" ? "$" : currency === "EUR" ? "€" : "R$"}
                </span>
                <input
                  id="amount-input"
                  aria-label="Valor recebido"
                  type="text"
                  inputMode="decimal"
                  value={amountStr}
                  onChange={(e) => setAmountStr(e.target.value)}
                  placeholder="25,00"
                  required
                />
              </div>
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
            <span>Data e hora da venda</span>
            <input
              id="sale-date-input"
              aria-label="Data e hora da venda"
              type="datetime-local"
              value={saleDateTime}
              onChange={(e) => setSaleDateTime(e.target.value)}
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
                    {fetchingRate ? "Buscando..." : autoRateSource === "unavailable" ? "Indisponível — use Manual" : `R$ ${autoRateFormatted}`}
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
                  {currencyFormat.format(convertedMinor / 100)}
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
