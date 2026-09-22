export function formatVipRemaining(expiresAt: string, nowMs = Date.now()): string | null {
  const expiresMs = new Date(expiresAt).getTime();
  if (!Number.isFinite(expiresMs) || expiresMs <= nowMs) return null;
  const totalHours = Math.ceil((expiresMs - nowMs) / 3_600_000);
  const days = Math.floor(totalHours / 24);
  const hours = totalHours % 24;
  return days > 0 ? `${days}d ${hours}h` : `${hours}h`;
}
