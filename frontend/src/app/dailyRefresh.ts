export function millisecondsUntilNextLocalMidnight(now = new Date()): number {
  const nextMidnight = new Date(now);
  nextMidnight.setHours(24, 0, 0, 25);
  return Math.max(1, nextMidnight.getTime() - now.getTime());
}
