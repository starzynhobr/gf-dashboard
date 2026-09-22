import { ArrowCounterClockwise, Eye, EyeSlash, SlidersHorizontal, Target, Timer, WindowsLogo } from "@phosphor-icons/react";

import type { DashboardLayoutResult, DashboardModuleKey } from "../gateway/AppGateway";
import { dashboardModuleRegistry } from "./dashboardModuleRegistry";
import { formatTargetDuration } from "./routineFormatting";

const PRESET_MINUTES = [
  { label: "2h", minutes: 120 },
  { label: "3h", minutes: 180 },
  { label: "3h30", minutes: 210 },
  { label: "4h", minutes: 240 },
  { label: "4h30", minutes: 270 },
  { label: "5h", minutes: 300 },
  { label: "6h", minutes: 360 },
];

export function SettingsPage({
  layout,
  busy,
  error,
  targetMinutes = 240,
  autostart = false,
  autostartBusy = false,
  onToggle,
  onReset,
  onSaveTargetMinutes,
  onToggleAutostart,
}: {
  layout: DashboardLayoutResult | null;
  busy: boolean;
  error: string | null;
  targetMinutes?: number;
  autostart?: boolean;
  autostartBusy?: boolean;
  onToggle: (moduleKey: DashboardModuleKey, enabled: boolean) => Promise<void>;
  onReset: () => Promise<void>;
  onSaveTargetMinutes?: (minutes: number) => void;
  onToggleAutostart?: (enabled: boolean) => Promise<void>;
}) {
  return (
    <section className="management-page settings-page">
      <div className="page-title">
        <div>
          <p className="page-kicker">Preferências locais</p>
          <h1>Configurar preferências</h1>
          <span>
            Personalize os módulos e a meta de tempo de rotina. As preferências ficam salvas localmente.
          </span>
        </div>
        <button className="secondary-button" type="button" disabled={busy} onClick={() => void onReset()}>
          <ArrowCounterClockwise size={18} />
          Restaurar padrão
        </button>
      </div>

      {error && (
        <div className="error-banner" role="alert">
          {error}
        </div>
      )}

      <section className="panel settings-panel">
        <div className="settings-panel__intro">
          <i>
            <Timer size={25} weight="duotone" />
          </i>
          <div>
            <strong>Meta de tempo da rotina de farm</strong>
            <span>
              Define a duração estimada para o seu dia de farm. Ao atingir ou passar dessa meta, o contador
              mudará de cor para evitar que você esqueça a rotina rodando após terminar o jogo.
            </span>
          </div>
        </div>

        <div className="routine-settings-card">
          <div className="routine-settings-card__current">
            <Target size={22} weight="duotone" />
            <div>
              <span>Meta atual configurada:</span>
              <strong>{formatTargetDuration(targetMinutes)} ({targetMinutes} minutos)</strong>
            </div>
          </div>

          <div className="routine-settings-card__presets">
            <span className="routine-settings-label">Escolha uma meta rápida:</span>
            <div className="routine-target-presets">
              {PRESET_MINUTES.map((preset) => {
                const isSelected = targetMinutes === preset.minutes;
                return (
                  <button
                    key={preset.minutes}
                    type="button"
                    className={`routine-preset-btn ${isSelected ? "routine-preset-btn--active" : ""}`}
                    onClick={() => onSaveTargetMinutes?.(preset.minutes)}
                  >
                    {preset.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      <section className="panel settings-panel">
        <div className="settings-panel__intro">
          <i>
            <SlidersHorizontal size={25} weight="duotone" />
          </i>
          <div>
            <strong>Módulos do dashboard</strong>
            <span>
              Módulos ocultos são desmontados e deixam de executar animações ou carregamentos próprios.
            </span>
          </div>
        </div>
        <div className="module-settings-list">
          {dashboardModuleRegistry.map((module) => {
            const enabled = layout?.visibility[module.moduleKey] ?? module.defaultEnabled;
            return (
              <div className="module-setting" key={module.moduleKey}>
                <i>{enabled ? <Eye size={22} weight="duotone" /> : <EyeSlash size={22} weight="duotone" />}</i>
                <div>
                  <strong>{module.title}</strong>
                  <span>{module.description}</span>
                </div>
                <button
                  className={enabled ? "switch-control switch-control--on" : "switch-control"}
                  type="button"
                  role="switch"
                  aria-checked={enabled}
                  aria-label={`${enabled ? "Ocultar" : "Mostrar"} ${module.title}`}
                  disabled={busy}
                  onClick={() => void onToggle(module.moduleKey, !enabled)}
                >
                  <span />
                </button>
              </div>
            );
          })}
        </div>
      </section>

      <section className="panel settings-panel">
        <div className="settings-panel__intro">
          <i>
            <WindowsLogo size={25} weight="duotone" />
          </i>
          <div>
            <strong>Inicialização do sistema</strong>
            <span>
              Configure se o aplicativo deve ser iniciado automaticamente junto com o sistema operacional.
            </span>
          </div>
        </div>
        <div className="module-settings-list">
          <div className="module-setting">
            <i>
              <WindowsLogo size={22} weight="duotone" />
            </i>
            <div>
              <strong>Iniciar com o Windows</strong>
              <span>Executa o GF Farmer automaticamente ao ligar ou fazer login no computador.</span>
            </div>
            <button
              className={autostart ? "switch-control switch-control--on" : "switch-control"}
              type="button"
              role="switch"
              aria-checked={autostart}
              aria-label={`${autostart ? "Desativar" : "Ativar"} iniciar com o Windows`}
              disabled={autostartBusy || busy}
              onClick={() => void onToggleAutostart?.(!autostart)}
            >
              <span />
            </button>
          </div>
        </div>
      </section>
    </section>
  );
}
