import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HistoryChart } from "./HistoryChart";

function reading(day: number, coverage = 100) {
  return { bucket_start: `2026-09-${String(day).padStart(2, "0")}T00:00:00Z`, value: day * 10, coverage_percentage: coverage };
}

describe("history chart connections", () => {
  it("connects all adjacent readings, including partial coverage at either end", () => {
    const { container } = render(<HistoryChart points={[reading(2, 20), reading(3), reading(4), reading(5, 40), reading(6, 60)]} metric="occupancy" range="day" />);
    const circles = [...container.querySelectorAll("circle")];
    const expected = circles.map((circle, index) => `${index ? "L" : "M"}${circle.getAttribute("cx")},${circle.getAttribute("cy")}`).join(" ");
    expect(container.querySelectorAll(".chart-line")).toHaveLength(1);
    expect(container.querySelector(".chart-line")).toHaveAttribute("d", expected);
    expect(container.querySelector(".chart-area")).toHaveAttribute("d", `${expected} L740,258 L52,258 Z`);
    expect(container.querySelectorAll("circle.partial")).toHaveLength(3);
  });

  it("connects readings and shading across missing buckets without adding measurements", () => {
    const { container } = render(<HistoryChart points={[reading(2), reading(3, 50), reading(6, 30), reading(7)]} metric="occupancy" range="day" />);
    const circles = [...container.querySelectorAll("circle")];
    const lines = [...container.querySelectorAll(".chart-line")];
    const areas = [...container.querySelectorAll(".chart-area")];
    expect(circles).toHaveLength(4);
    expect(lines).toHaveLength(1);
    expect(areas).toHaveLength(1);
    const expected = circles.map((circle, index) => `${index ? "L" : "M"}${circle.getAttribute("cx")},${circle.getAttribute("cy")}`).join(" ");
    expect(lines[0]).toHaveAttribute("d", expected);
    expect(areas[0]).toHaveAttribute("d", `${expected} L740,258 L52,258 Z`);
  });

  it("renders an isolated partial reading without an invalid area", () => {
    const { container } = render(<HistoryChart points={[reading(2, 50)]} metric="percentage" range="week" />);
    expect(container.querySelectorAll("circle")).toHaveLength(1);
    expect(container.querySelectorAll(".chart-line, .chart-area")).toHaveLength(0);
  });
});
