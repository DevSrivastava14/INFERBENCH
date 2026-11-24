import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";
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

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderResults(path = "/results") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/results" element={<Results />} />
      </Routes>
    </MemoryRouter>,
  );
}

test("lists metric names and does not draw a series", () => {
  const fetchSpy = vi.fn();
  vi.stubGlobal("fetch", fetchSpy);
  const { container } = renderResults();

  for (const name of metricNames) {
    expect(screen.getByText(name)).toBeTruthy();
  }
  expect(
    screen.getByText(
      "Time from the request start until the first generated content arrives. Unit: milliseconds.",
    ),
  ).toBeTruthy();
  expect(screen.getByText(/A blank value is unset/)).toBeTruthy();
  expect(screen.getAllByText("unset").length).toBeGreaterThan(0);
  expect(screen.getByText("No experiment is selected.")).toBeTruthy();
  expect(screen.queryByText("100")).toBeNull();
  expect(screen.queryByText("110")).toBeNull();
  expect(screen.queryByText("120")).toBeNull();
  expect(container.querySelector("svg")).toBeNull();
  expect(fetchSpy).not.toHaveBeenCalled();
});

test("shows stored values and the measured series for the selected id", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: async () => ({
          id: 4,
          job_status: null,
          summary: {
            ttft_ms: null,
            tpot_ms: null,
            average_ms: 15,
            generation_throughput_tps: 2,
            request_throughput_rps: 1,
            p50_ms: 16,
            p95_ms: 17,
            p99_ms: 18,
            error_rate: 0,
          },
          measured: [{ end_to_end_ms: 40 }, { end_to_end_ms: 50 }],
        }),
      }),
    ),
  );
  const { container } = renderResults("/results?source=dashboard&id=4");

  expect((await screen.findAllByText("40")).length).toBeGreaterThan(0);
  const list = screen.getByRole("list");
  expect(list.textContent).toContain("15");
  expect(list.textContent).toContain("16");
  expect(list.textContent).toContain("17");
  expect(list.textContent).toContain("18");
  expect(list.textContent).toContain("0");
  expect(screen.getAllByText("50").length).toBeGreaterThan(0);
  expect(screen.queryByText("100")).toBeNull();
  expect(screen.queryByText("110")).toBeNull();
  expect(screen.queryByText("120")).toBeNull();
  expect(container.querySelector("svg")).toBeTruthy();
  expect(fetch).toHaveBeenCalledWith("/api/experiments/dashboard/4");
});
