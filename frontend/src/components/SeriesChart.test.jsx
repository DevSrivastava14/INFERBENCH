import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { SeriesChart } from "./SeriesChart.jsx";

function strokes(container) {
  return [...container.querySelectorAll("[stroke]")].map((node) =>
    node.getAttribute("stroke"),
  );
}

describe("SeriesChart", () => {
  test("draws the series it is given", () => {
    const { container } = render(<SeriesChart series={[100, 110, 120]} />);

    expect(screen.getAllByText("100").length).toBeGreaterThan(0);
    expect(screen.getAllByText("110").length).toBeGreaterThan(0);
    expect(screen.getAllByText("120").length).toBeGreaterThan(0);
    expect(screen.getByText("sample")).toBeTruthy();
    expect(screen.getByText("ms")).toBeTruthy();

    const used = strokes(container);
    expect(used).toContain("var(--ink)");
    expect(used).toContain("var(--accent)");
    expect(used).toContain("var(--grid)");
  });

  test("draws nothing when no series is passed", () => {
    const { container } = render(<SeriesChart />);
    expect(container.querySelector("svg")).toBeNull();
    expect(screen.queryByText("100")).toBeNull();
  });
});
