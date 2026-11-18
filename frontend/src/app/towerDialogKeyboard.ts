import type { KeyboardEvent } from "react";

export function towerDialogKeyboard(event: KeyboardEvent<HTMLElement>, onClose: () => void, busy = false) {
  if (event.key === "Escape") {
    event.preventDefault();
    if (!busy) onClose();
    return;
  }
  if (event.key !== "Tab") return;
  const controls = event.currentTarget.querySelectorAll<HTMLElement>("button:not(:disabled), input:not(:disabled), [tabindex='0']");
  const first = controls[0];
  const last = controls[controls.length - 1];
  if (!first) { event.preventDefault(); return; }
  if (event.shiftKey && (document.activeElement === first || !event.currentTarget.contains(document.activeElement))) {
    event.preventDefault(); last.focus();
  } else if (!event.shiftKey && (document.activeElement === last || !event.currentTarget.contains(document.activeElement))) {
    event.preventDefault(); first.focus();
  }
}
