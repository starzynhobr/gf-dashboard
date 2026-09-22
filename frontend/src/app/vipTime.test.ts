import { describe, expect, it } from "vitest";

import { formatVipRemaining } from "./vipTime";

describe("formatVipRemaining", () => {
  it("shows remaining days and hours compactly", () => {
    const now = new Date("2026-09-08T12:00:00Z").getTime();
    expect(formatVipRemaining("2026-10-05T22:00:00Z", now)).toBe("27d 10h");
  });

  it("does not show expired VIPs", () => {
    const now = new Date("2026-09-08T12:00:00Z").getTime();
    expect(formatVipRemaining("2026-09-08T11:59:59Z", now)).toBeNull();
  });
});
