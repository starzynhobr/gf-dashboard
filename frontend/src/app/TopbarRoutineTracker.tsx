import { Pause, PencilSimple, Play, Stop, Warning } from "@phosphor-icons/react";
import type { WorkRoutineResult } from "../gateway/AppGateway";
import { formatTargetDuration } from "./routineFormatting";

interface TopbarRoutineTrackerProps {
  routine: WorkRoutineResult;
  routineBusy: boolean;
  targetMinutes: number;
  onUpdateRoutine: (action: "pause" | "resume" | "stop") => Promise<void>;
  onOpenTargetModal: () => void;
}

export function TopbarRoutineTracker({
  routine,
  routineBusy,
  targetMinutes,
  onUpdateRoutine,
  onOpenTargetModal,
}: TopbarRoutineTrackerProps) {
  const elapsed = routine.elapsedSeconds;
  const targetSeconds = Math.max(900, targetMinutes * 60); // min 15m
  const isOvertime = elapsed > targetSeconds;
  const isNear = !isOvertime && elapsed >= targetSeconds * 0.85;

  const phase: "normal" | "near" | "overtime" | "paused" =
    routine.status === "paused" ? "paused" : isOvertime ? "overtime" : isNear ? "near" : "normal";

  const hours = String(Math.floor(elapsed / 3600)).padStart(2, "0");
  const mins = String(Math.floor((elapsed % 3600) / 60)).padStart(2, "0");
  const secs = String(elapsed % 60).padStart(2, "0");
  const routineTime = `${hours}:${mins}:${secs}`;

  let diffText: string;
  if (routine.status === "paused") {
    diffText = "Pausada";
  } else if (isOvertime) {
    const extraMin = Math.floor((elapsed - targetSeconds) / 60);
    const eh = Math.floor(extraMin / 60);
    const em = extraMin % 60;
    diffText = eh > 0 ? `+${eh}h ${em}m extra` : `+${extraMin}m extra`;
  } else {
    const remMin = Math.ceil((targetSeconds - elapsed) / 60);
    const rh = Math.floor(remMin / 60);
    const rm = remMin % 60;
    diffText = rh > 0 ? `restam ${rh}h ${rm}m` : `restam ${remMin}m`;
  }

  const progressPercent = Math.min(100, Math.round((elapsed / targetSeconds) * 100));

  return (
    <div
      className={`topbar-routine-tracker topbar-routine-tracker--${phase}`}
      data-testid="topbar-routine-tracker"
      data-phase={phase}
    >
      <div className="topbar-routine-tracker__live-indicator">
        <span className="live-dot" />
        <span className="live-label">
          {routine.status === "paused" ? (
            "PAUSADA"
          ) : isOvertime ? (
            <>
              <Warning size={12} weight="bold" /> META ULTRAPASSADA
            </>
          ) : isNear ? (
            "RETA FINAL"
          ) : (
            "EM ANDAMENTO"
          )}
        </span>
      </div>

      <div className="topbar-routine-tracker__main">
        <div className="topbar-routine-tracker__time-row">
          <strong className="topbar-routine-tracker__time" data-testid="topbar-routine-time">
            {routineTime}
          </strong>

          <div className="topbar-routine-tracker__meta-group">
            <button
              type="button"
              className="topbar-routine-tracker__target-btn"
              title="Ajustar meta de tempo"
              onClick={onOpenTargetModal}
            >
              <span>Meta: {formatTargetDuration(targetMinutes)}</span>
              <PencilSimple size={12} weight="bold" />
            </button>
            <span className={`topbar-routine-tracker__diff topbar-routine-tracker__diff--${phase}`}>
              {diffText}
            </span>
          </div>
        </div>

        <div
          className="topbar-routine-tracker__progress-track"
          title={`Progresso da meta: ${progressPercent}%`}
        >
          <div
            className="topbar-routine-tracker__progress-fill"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      <div className="topbar-routine-tracker__actions">
        <button
          type="button"
          className="topbar-routine-tracker__action-btn topbar-routine-tracker__action-btn--pause"
          aria-label={routine.status === "running" ? "Pausar rotina" : "Retomar rotina"}
          disabled={routineBusy}
          onClick={() => void onUpdateRoutine(routine.status === "running" ? "pause" : "resume")}
        >
          {routine.status === "running" ? <Pause size={16} weight="fill" /> : <Play size={16} weight="fill" />}
        </button>

        <button
          type="button"
          className="topbar-routine-tracker__action-btn topbar-routine-tracker__action-btn--stop"
          aria-label="Encerrar rotina"
          disabled={routineBusy}
          onClick={() => void onUpdateRoutine("stop")}
        >
          <Stop size={15} weight="fill" />
          <span>Encerrar</span>
        </button>
      </div>
    </div>
  );
}
