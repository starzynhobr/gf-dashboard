import { useState } from "react";
import { Check, Target, Timer, X } from "@phosphor-icons/react";

interface RoutineTargetDialogProps {
  currentMinutes: number;
  onClose: () => void;
  onSave: (minutes: number) => void;
}

const PRESET_MINUTES = [
  { label: "2h", minutes: 120 },
  { label: "3h", minutes: 180 },
  { label: "3h30", minutes: 210 },
  { label: "4h", minutes: 240 },
  { label: "4h30", minutes: 270 },
  { label: "5h", minutes: 300 },
  { label: "6h", minutes: 360 },
];

export function RoutineTargetDialog({ currentMinutes, onClose, onSave }: RoutineTargetDialogProps) {
  const [hours, setHours] = useState(() => Math.floor(currentMinutes / 60));
  const [minutes, setMinutes] = useState(() => currentMinutes % 60);

  const totalMinutes = Math.max(15, hours * 60 + minutes);

  const handlePreset = (presetMin: number) => {
    setHours(Math.floor(presetMin / 60));
    setMinutes(presetMin % 60);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(totalMinutes);
  };

  return (
    <div className="day-dialog-backdrop" onClick={onClose}>
      <section
        className="day-dialog routine-target-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Configurar meta de tempo da rotina"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="day-dialog__header">
          <div className="day-dialog__identity">
            <i>
              <Timer size={25} weight="duotone" />
            </i>
            <div>
              <h2>Meta de tempo da rotina</h2>
              <span>Ajuste o tempo estimado para o seu farm diário.</span>
            </div>
          </div>
          <button className="icon-button" type="button" aria-label="Fechar" onClick={onClose}>
            <X size={21} />
          </button>
        </header>

        <form onSubmit={handleSubmit}>
          <div className="day-dialog__body routine-target-dialog__body">
            <div className="routine-target-dialog__summary">
              <Target size={22} weight="duotone" />
              <div>
                <strong>
                  Meta selecionada: {hours}h {minutes > 0 ? `${minutes}min` : ""} ({totalMinutes} minutos)
                </strong>
                <span>
                  O cronômetro mudará de estado (verde → âmbar → coral) conforme se aproxima ou passa dessa meta.
                </span>
              </div>
            </div>

            <div className="sale-form-field">
              <span>Atalhos rápidos</span>
              <div className="routine-target-presets">
                {PRESET_MINUTES.map((preset) => {
                  const isSelected = totalMinutes === preset.minutes;
                  return (
                    <button
                      key={preset.minutes}
                      type="button"
                      className={`routine-preset-btn ${isSelected ? "routine-preset-btn--active" : ""}`}
                      onClick={() => handlePreset(preset.minutes)}
                    >
                      {preset.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="routine-target-time-inputs">
              <label className="sale-form-field">
                <span>Horas</span>
                <input
                  type="number"
                  min="0"
                  max="12"
                  value={hours}
                  onChange={(e) => setHours(Math.max(0, Math.min(12, parseInt(e.target.value, 10) || 0)))}
                />
              </label>
              <label className="sale-form-field">
                <span>Minutos</span>
                <input
                  type="number"
                  min="0"
                  max="59"
                  step="5"
                  value={minutes}
                  onChange={(e) => setMinutes(Math.max(0, Math.min(59, parseInt(e.target.value, 10) || 0)))}
                />
              </label>
            </div>

            <p className="routine-target-hint">
              💡 <strong>Dica:</strong> Se você ainda está calibrando seu tempo, comece com uma meta ampla (ex: 4h).
              Conforme for registrando os dias, você saberá seu tempo ideal e poderá refiná-la a qualquer momento.
            </p>
          </div>

          <footer className="day-dialog__footer">
            <button className="secondary-button" type="button" onClick={onClose}>
              Cancelar
            </button>
            <button className="primary-button" type="submit">
              <Check size={18} weight="bold" />
              Salvar meta
            </button>
          </footer>
        </form>
      </section>
    </div>
  );
}
