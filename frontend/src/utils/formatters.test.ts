import { describe, expect, it } from "vitest";
import { formatOccupancy, formatPercentage, formatStatus, formatTimestamp } from "./formatters";

describe("formatters", () => {
  it("keeps zero distinct from unavailable occupancy", () => {
    expect(formatOccupancy(0)).toBe("0");
    expect(formatOccupancy(null)).toBe("Unavailable");
  });
  it("caps displayed percentages", () => {
    expect(formatPercentage(127)).toBe("100%");
    expect(formatPercentage(null)).toBe("Unavailable");
  });
  it("formats known statuses", () => expect(formatStatus("stale")).toBe("Stale"));
  it("handles invalid timestamps", () => expect(formatTimestamp("bad-date")).toBe("Unavailable"));
});
