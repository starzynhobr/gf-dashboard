import {
  Calculator,
  Coins,
  CurrencyDollar,
  PencilSimple,
  Tote,
  X,
} from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";

import { formatGoldInput } from "./goldInput";

export interface SalePresetData {
  saleType: "gold" | "pve_bag";
  quantity: number;
  amountStr: string;
  currency: "BRL" | "USD" | "EUR";
}

export interface GoldCalculatorDialogProps {
  pveBagUnitValueGold?: number | null;
  onClose: () => void;
  onOpenSale?: (preset: SalePresetData) => void;
}

const currencyFormatBRL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

const currencyFormatEUR = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "EUR",
});

const currencyFormatUSD = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

const numberFormat = new Intl.NumberFormat("pt-BR");

export function GoldCalculatorDialog({
  pveBagUnitValueGold,
  onClose,
  onOpenSale,
}: GoldCalculatorDialogProps) {
  const [calcType, setCalcType] = useState<"gold" | "pve_bag">(() => {
    const saved = localStorage.getItem("gf-dashboard.calc-type");
    return saved === "pve_bag" ? "pve_bag" : "gold";
  });

  const [pveBaseMode, setPveBaseMode] = useState<"gold_quote" | "market_package">(() => {
    const saved = localStorage.getItem("gf-dashboard.calc-pve-base");
    return saved === "gold_quote" ? "gold_quote" : "market_package";
  });

  const [centsPerThousand, setCentsPerThousand] = useState(() => {
    return localStorage.getItem("gf-dashboard.calc-cents") ?? "8";
  });

  const [gold, setGold] = useState("1000000");
  const [pveBags, setPveBags] = useState("250");
  const [packageEur, setPackageEur] = useState("3,50");
  const [packageBags, setPackageBags] = useState("250");

  // Exchange rates
  const [eurRate, setEurRate] = useState<number>(6.0);
  const [usdRate, setUsdRate] = useState<number>(5.4);
  const [eurRateStr, setEurRateStr] = useState<string>("6,00");
  const [usdRateStr, setUsdRateStr] = useState<string>("5,40");
  const [isEditingRates, setIsEditingRates] = useState(false);

  useEffect(() => {
    localStorage.setItem("gf-dashboard.calc-type", calcType);
  }, [calcType]);

  useEffect(() => {
    localStorage.setItem("gf-dashboard.calc-pve-base", pveBaseMode);
  }, [pveBaseMode]);

  useEffect(() => {
    localStorage.setItem("gf-dashboard.calc-cents", centsPerThousand);
  }, [centsPerThousand]);

  const handleEurRateChange = (val: string) => {
    setEurRateStr(val);
    const parsed = parseFloat(val.replace(",", "."));
    if (!isNaN(parsed) && parsed > 0) setEurRate(parsed);
  };

  const handleUsdRateChange = (val: string) => {
    setUsdRateStr(val);
    const parsed = parseFloat(val.replace(",", "."));
    if (!isNaN(parsed) && parsed > 0) setUsdRate(parsed);
  };

  const effectiveBagGoldPrice = pveBagUnitValueGold && pveBagUnitValueGold > 0 ? pveBagUnitValueGold : 1000;

  const calculation = useMemo(() => {
    const cents = Number(centsPerThousand.replace(",", "."));
    const validCents = Number.isFinite(cents) && cents >= 0 ? cents : 0;

    let totalBrl = 0;
    let totalEur = 0;
    let totalUsd = 0;
    let primaryCurrency: "BRL" | "EUR" = "BRL";
    let subtitle: string;
    let equivGold = 0;
    let equivBags = 0;
    let equivCentsPerThousand = validCents;

    if (calcType === "gold") {
      const amount = Number(gold.replace(/\D/g, ""));
      if (Number.isSafeInteger(amount) && amount > 0) {
        totalBrl = (amount / 1000) * (validCents / 100);
        totalEur = eurRate > 0 ? totalBrl / eurRate : 0;
        totalUsd = usdRate > 0 ? totalBrl / usdRate : 0;
        equivBags = Math.floor(amount / effectiveBagGoldPrice);
        equivGold = amount;
      }
      subtitle = `${centsPerThousand || "0"}c por 1.000 gold • Equivale a ${numberFormat.format(equivBags)} sacos PvE`;
    } else {
      const bags = Number(pveBags.replace(/\D/g, ""));
      equivGold = bags * effectiveBagGoldPrice;
      equivBags = bags;

      if (pveBaseMode === "market_package") {
        primaryCurrency = "EUR";
        const pkgEur = Number(packageEur.replace(",", "."));
        const pkgBags = Number(packageBags.replace(/\D/g, ""));
        const validPkgEur = Number.isFinite(pkgEur) && pkgEur > 0 ? pkgEur : 0;
        const validPkgBags = pkgBags > 0 ? pkgBags : 250;

        if (bags > 0 && validPkgBags > 0) {
          totalEur = (bags / validPkgBags) * validPkgEur;
          totalBrl = totalEur * eurRate;
          totalUsd = usdRate > 0 ? totalBrl / usdRate : 0;
          if (equivGold > 0) {
            equivCentsPerThousand = (totalBrl / (equivGold / 1000)) * 100;
          }
        }
        subtitle = `Pacote: ${packageEur} € / ${packageBags} sacos • Equivale a ${equivCentsPerThousand.toFixed(1)}c/1k gold`;
      } else {
        primaryCurrency = "BRL";
        if (bags > 0) {
          totalBrl = (equivGold / 1000) * (validCents / 100);
          totalEur = eurRate > 0 ? totalBrl / eurRate : 0;
          totalUsd = usdRate > 0 ? totalBrl / usdRate : 0;
        }
        subtitle = `Cotação saco: ${numberFormat.format(effectiveBagGoldPrice)} gold • ${centsPerThousand || "0"}c por 1.000 gold`;
      }
    }

    return {
      totalBrl,
      totalEur,
      totalUsd,
      primaryCurrency,
      subtitle,
      equivGold,
      equivBags,
      equivCentsPerThousand,
    };
  }, [
    calcType,
    gold,
    pveBags,
    pveBaseMode,
    packageEur,
    packageBags,
    centsPerThousand,
    effectiveBagGoldPrice,
    eurRate,
    usdRate,
  ]);

  const handleLaunchSale = () => {
    if (!onOpenSale) return;
    if (calcType === "gold") {
      const g = Number(gold.replace(/\D/g, ""));
      onOpenSale({
        saleType: "gold",
        quantity: g > 0 ? g : 1_000_000,
        amountStr: calculation.totalBrl.toFixed(2).replace(".", ","),
        currency: "BRL",
      });
    } else {
      const b = Number(pveBags.replace(/\D/g, ""));
      const validBags = b > 0 ? b : 250;
      if (pveBaseMode === "market_package") {
        onOpenSale({
          saleType: "pve_bag",
          quantity: validBags,
          amountStr: calculation.totalEur.toFixed(2).replace(".", ","),
          currency: "EUR",
        });
      } else {
        onOpenSale({
          saleType: "pve_bag",
          quantity: validBags,
          amountStr: calculation.totalBrl.toFixed(2).replace(".", ","),
          currency: "BRL",
        });
      }
    }
  };

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="day-dialog calculator-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Calculadora de gold"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="day-dialog__header">
          <div className="day-dialog__identity">
            <i>
              <Calculator size={25} weight="duotone" />
            </i>
            <div>
              <h2>Calculadora</h2>
              <span>Estimativa local; câmbios indicativos e ajustáveis.</span>
            </div>
          </div>
          <button className="icon-button" type="button" aria-label="Fechar" onClick={onClose}>
            <X size={21} />
          </button>
        </header>

        <div className="day-dialog__body calculator-dialog__body">
          {/* Seletor Tipo: Gold vs Saco PvE */}
          <div className="sale-form-field">
            <span>Tipo de cálculo</span>
            <div className="sale-type-selector calculator-type-selector">
              <button
                type="button"
                className={`type-pill ${calcType === "gold" ? "type-pill--active" : ""}`}
                onClick={() => setCalcType("gold")}
              >
                <Coins size={16} weight={calcType === "gold" ? "fill" : "regular"} />
                <span>Gold</span>
              </button>
              <button
                type="button"
                className={`type-pill ${calcType === "pve_bag" ? "type-pill--active" : ""}`}
                onClick={() => setCalcType("pve_bag")}
              >
                <Tote size={16} weight={calcType === "pve_bag" ? "fill" : "regular"} />
                <span>Saco PvE</span>
              </button>
            </div>
          </div>

          {/* MODO GOLD */}
          {calcType === "gold" && (
            <>
              <label className="sale-form-field">
                <span>Valor de 1.000 gold em centavos</span>
                <div className="calculator-input">
                  <span>R$</span>
                  <input
                    aria-label="Centavos por mil gold"
                    autoFocus
                    inputMode="decimal"
                    value={centsPerThousand}
                    onChange={(event) => setCentsPerThousand(event.target.value)}
                  />
                  <small>c</small>
                </div>
              </label>

              <label className="sale-form-field">
                <span>Quantidade de gold</span>
                <div className="expense-gold-input calculator-gold-input">
                  <Coins size={19} weight="duotone" />
                  <input
                    aria-label="Gold para calcular"
                    inputMode="numeric"
                    value={formatGoldInput(gold)}
                    onChange={(event) => setGold(event.target.value.replace(/\D/g, ""))}
                    placeholder="Ex.: 1.000.000"
                  />
                  <small>gold</small>
                </div>
                <small className="calculator-gold-hint">Separado automaticamente a cada milhar.</small>
              </label>
            </>
          )}

          {/* MODO SACO PVE */}
          {calcType === "pve_bag" && (
            <>
              <label className="sale-form-field">
                <span>Quantidade de Sacos PvE</span>
                <div className="sale-number-input calculator-number-input">
                  <Tote size={19} weight="duotone" />
                  <input
                    aria-label="Sacos para calcular"
                    autoFocus
                    inputMode="numeric"
                    value={formatGoldInput(pveBags)}
                    onChange={(event) => setPveBags(event.target.value.replace(/\D/g, ""))}
                    placeholder="Ex.: 250"
                  />
                  <small>sacos</small>
                </div>
                <small className="calculator-gold-hint">
                  Equivale a {numberFormat.format(calculation.equivGold)} Gold ({numberFormat.format(effectiveBagGoldPrice)}g/saco).
                </small>
              </label>

              <div className="sale-form-field">
                <span>Base de precificação</span>
                <div className="calculator-pve-base-selector">
                  <button
                    type="button"
                    className={`calculator-base-btn ${pveBaseMode === "market_package" ? "calculator-base-btn--active" : ""}`}
                    onClick={() => setPveBaseMode("market_package")}
                  >
                    <span>Pacote de Mercado (€)</span>
                    <small>Ex.: 3,50 € / 250 sacos</small>
                  </button>
                  <button
                    type="button"
                    className={`calculator-base-btn ${pveBaseMode === "gold_quote" ? "calculator-base-btn--active" : ""}`}
                    onClick={() => setPveBaseMode("gold_quote")}
                  >
                    <span>Cotação de Gold (R$)</span>
                    <small>{centsPerThousand}c por 1.000 gold</small>
                  </button>
                </div>
              </div>

              {pveBaseMode === "market_package" ? (
                <div className="calculator-package-config">
                  <div className="sale-form-row sale-form-row--package">
                    <label className="sale-form-field">
                      <span>Preço do pacote</span>
                      <div className="calculator-input">
                        <span>€</span>
                        <input
                          aria-label="Valor do pacote em Euro"
                          inputMode="decimal"
                          value={packageEur}
                          onChange={(e) => setPackageEur(e.target.value)}
                          placeholder="3,50"
                        />
                      </div>
                    </label>
                    <label className="sale-form-field">
                      <span>Por quantos sacos</span>
                      <div className="calculator-input">
                        <input
                          aria-label="Quantidade de sacos do pacote"
                          inputMode="numeric"
                          value={formatGoldInput(packageBags)}
                          onChange={(e) => setPackageBags(e.target.value.replace(/\D/g, ""))}
                          placeholder="250"
                        />
                        <small>sacos</small>
                      </div>
                    </label>
                  </div>
                  <div className="calculator-preset-chips">
                    <button
                      type="button"
                      className="calculator-chip"
                      onClick={() => {
                        setPackageEur("3,50");
                        setPackageBags("250");
                      }}
                    >
                      Padrão: 3,50 € / 250 sacos
                    </button>
                  </div>
                </div>
              ) : (
                <label className="sale-form-field">
                  <span>Valor de 1.000 gold em centavos</span>
                  <div className="calculator-input">
                    <span>R$</span>
                    <input
                      aria-label="Centavos por mil gold"
                      inputMode="decimal"
                      value={centsPerThousand}
                      onChange={(event) => setCentsPerThousand(event.target.value)}
                    />
                    <small>c</small>
                  </div>
                </label>
              )}
            </>
          )}

          {/* CARD DE RESULTADOS MULTIMOEDA */}
          <div className="calculator-result">
            <div className="calculator-result__header">
              <span>Valor estimado</span>
            </div>

            {calculation.primaryCurrency === "BRL" ? (
              <>
                <strong className="calculator-main-value">
                  {currencyFormatBRL.format(calculation.totalBrl)}
                </strong>
                <div className="calculator-multicurrency-grid">
                  <div className="calculator-currency-pill">
                    <span className="currency-label">EUR</span>
                    <strong className="currency-val">{currencyFormatEUR.format(calculation.totalEur)}</strong>
                  </div>
                  <div className="calculator-currency-pill">
                    <span className="currency-label">USD</span>
                    <strong className="currency-val">{currencyFormatUSD.format(calculation.totalUsd)}</strong>
                  </div>
                </div>
              </>
            ) : (
              <>
                <strong className="calculator-main-value">
                  {currencyFormatEUR.format(calculation.totalEur)}
                </strong>
                <div className="calculator-multicurrency-grid">
                  <div className="calculator-currency-pill">
                    <span className="currency-label">BRL</span>
                    <strong className="currency-val">{currencyFormatBRL.format(calculation.totalBrl)}</strong>
                  </div>
                  <div className="calculator-currency-pill">
                    <span className="currency-label">USD</span>
                    <strong className="currency-val">{currencyFormatUSD.format(calculation.totalUsd)}</strong>
                  </div>
                </div>
              </>
            )}

            <div className="calculator-result__footer">
              <small>{calculation.subtitle}</small>
            </div>

            {/* BARRA DE CÂMBIO */}
            <div className="calculator-exchange-bar">
              {!isEditingRates ? (
                <div className="calculator-exchange-info">
                  <span>
                    Câmbio: 1 EUR = R$ {eurRate.toFixed(2).replace(".", ",")} • 1 USD = R$ {usdRate.toFixed(2).replace(".", ",")}
                  </span>
                  <button
                    type="button"
                    className="calculator-exchange-toggle"
                    onClick={() => setIsEditingRates(true)}
                    title="Ajustar taxa de câmbio"
                  >
                    <PencilSimple size={13} />
                    <span>Ajustar</span>
                  </button>
                </div>
              ) : (
                <div className="calculator-exchange-edit-row">
                  <div className="exchange-mini-field">
                    <span>1 EUR = R$</span>
                    <input
                      aria-label="Cotação EUR para BRL"
                      value={eurRateStr}
                      onChange={(e) => handleEurRateChange(e.target.value)}
                    />
                  </div>
                  <div className="exchange-mini-field">
                    <span>1 USD = R$</span>
                    <input
                      aria-label="Cotação USD para BRL"
                      value={usdRateStr}
                      onChange={(e) => handleUsdRateChange(e.target.value)}
                    />
                  </div>
                  <button
                    type="button"
                    className="calculator-exchange-done"
                    onClick={() => setIsEditingRates(false)}
                  >
                    OK
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        <footer className="day-dialog__footer calculator-dialog__footer">
          {onOpenSale ? (
            <button
              type="button"
              className="primary-button calculator-launch-sale-btn"
              onClick={handleLaunchSale}
              title="Abrir Nova Venda com esses valores"
            >
              <CurrencyDollar size={17} weight="bold" />
              <span>Lançar em Nova Venda</span>
            </button>
          ) : (
            <span>Use como referência de venda.</span>
          )}
          <button className="secondary-button" type="button" onClick={onClose}>
            Fechar
          </button>
        </footer>
      </section>
    </div>
  );
}
