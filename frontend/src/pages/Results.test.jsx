import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { Results } from "./Results.jsx";

const metricNames = [
  "TTFT",
  "TPOT",
  "end-to-end latency",
  "generation throughput",
  "request throughput",
  "P50",
  "P95",
  "P99",
  "error rate",
];

test("lists metric names and does not draw a series", () => {
  const { container } = render(<Results />);

  for (const name of metricNames) {
    expect(screen.getByText(name)).toBeTruthy();
  }
  expect(screen.getByText("No experiment is selected.")).toBeTruthy();
  expect(screen.queryByText("100")).toBeNull();
  expect(screen.queryByText("110")).toBeNull();
  expect(screen.queryByText("120")).toBeNull();
  expect(container.querySelector("svg")).toBeNull();
});
