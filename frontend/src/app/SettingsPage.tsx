import { ArrowCounterClockwise, Eye, EyeSlash, SlidersHorizontal } from "@phosphor-icons/react";

import type { DashboardLayoutResult, DashboardModuleKey } from "../gateway/AppGateway";
import { dashboardModuleRegistry } from "./dashboardModuleRegistry";

export function SettingsPage({ layout, busy, error, onToggle, onReset }: {
  layout: DashboardLayoutResult | null;
  busy: boolean;
  error: string | null;
  onToggle: (moduleKey: DashboardModuleKey, enabled: boolean) => Promise<void>;
  onReset: () => Promise<void>;
}) {
  return <section className="management-page settings-page"><div className="page-title"><div><p className="page-kicker">Preferências locais</p><h1>Configurar visualização</h1><span>Escolha quais módulos aparecem na página Hoje. A preferência fica salva neste workspace.</span></div><button className="secondary-button" type="button" disabled={busy} onClick={() => void onReset()}><ArrowCounterClockwise size={18} />Restaurar padrão</button></div>
    {error && <div className="error-banner" role="alert">{error}</div>}
    <section className="panel settings-panel"><div className="settings-panel__intro"><i><SlidersHorizontal size={25} weight="duotone" /></i><div><strong>Módulos do dashboard</strong><span>Módulos ocultos são desmontados e deixam de executar animações ou carregamentos próprios.</span></div></div><div className="module-settings-list">{dashboardModuleRegistry.map((module) => { const enabled = layout?.visibility[module.moduleKey] ?? module.defaultEnabled; return <div className="module-setting" key={module.moduleKey}><i>{enabled ? <Eye size={22} weight="duotone" /> : <EyeSlash size={22} weight="duotone" />}</i><div><strong>{module.title}</strong><span>{module.description}</span></div><button className={enabled ? "switch-control switch-control--on" : "switch-control"} type="button" role="switch" aria-checked={enabled} aria-label={`${enabled ? "Ocultar" : "Mostrar"} ${module.title}`} disabled={busy} onClick={() => void onToggle(module.moduleKey, !enabled)}><span /></button></div>; })}</div></section>
  </section>;
}
