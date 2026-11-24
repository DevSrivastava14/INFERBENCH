import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { Comparisons } from "./Comparisons.jsx";

afterEach(() => {
  vi.unstubAllGlobals();
});

function jsonResponse(body) {
  return Promise.resolve({
    ok: true,
    json: async () => body,
  });
}

function postedBody() {
  const call = fetch.mock.calls.find((item) => item[1] && item[1].method === "POST");
  return JSON.parse(call[1].body);
}

const forbidden = /\b(better|worse|improved|winner|recommend|best)\b/i;

test("starts empty and does not fetch", () => {
  const fetchSpy = vi.fn();
  vi.stubGlobal("fetch", fetchSpy);
  render(<Comparisons />);

  expect(screen.getByLabelText("baseline source")).toBeTruthy();
  expect(screen.getByLabelText("baseline id")).toBeTruthy();
  expect(screen.getByLabelText("candidate source")).toBeTruthy();
  expect(screen.getByLabelText("candidate id")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Compare" })).toBeTruthy();
  expect(screen.getByText("Nothing is loaded.")).toBeTruthy();
  expect(document.body.textContent).not.toMatch(forbidden);
  expect(fetchSpy).not.toHaveBeenCalled();
});

test("renders a fixture delta and includes the sign sentence when the payload has one", async () => {
  const payload = {
    average_ms_delta: 11,
    median_ms_delta: 12,
    p50_ms_delta: 13,
    p95_ms_delta: 14,
    p99_ms_delta: 15,
    error_rate_delta: 0,
    generation_throughput_tps_delta: 16,
    request_throughput_rps_delta: 17,
    baseline_phase_label: "baseline-label",
    candidate_phase_label: "candidate-label",
    setting_differences: [{ field: "concurrency", baseline: "1", candidate: "2" }],
    sign_sentence: "Request throughput is higher and P95 is lower.",
  };
  expect(payload).not.toHaveProperty("winner");
  vi.stubGlobal("fetch", vi.fn(() => jsonResponse(payload)));
  render(<Comparisons />);
  fireEvent.change(screen.getByLabelText("baseline source"), {
    target: { value: "dashboard" },
  });
  fireEvent.change(screen.getByLabelText("baseline id"), { target: { value: "1" } });
  fireEvent.change(screen.getByLabelText("candidate source"), {
    target: { value: "model-comparison" },
  });
  fireEvent.change(screen.getByLabelText("candidate id"), { target: { value: "2" } });
  fireEvent.click(screen.getByRole("button", { name: "Compare" }));

  expect(await screen.findByText("Request throughput is higher and P95 is lower.")).toBeTruthy();
  expect(postedBody()).toEqual({
    baseline: { source: "dashboard", id: 1 },
    candidate: { source: "model-comparison", id: 2 },
  });
  expect(postedBody()).not.toHaveProperty("winner");
  expect(fetch.mock.calls[0][0]).toBe("/api/compare");
  const text = document.body.textContent;
  expect(text).toContain("average_ms_delta 11");
  expect(text).toContain("median_ms_delta 12");
  expect(text).toContain("p50_ms_delta 13");
  expect(text).toContain("p95_ms_delta 14");
  expect(text).toContain("p99_ms_delta 15");
  expect(text).toContain("error_rate_delta 0");
  expect(text).toContain("generation_throughput_tps_delta 16");
  expect(text).toContain("request_throughput_rps_delta 17");
  expect(text).toContain("baseline_phase_label baseline-label");
  expect(text).toContain("candidate_phase_label candidate-label");
  expect(text).toContain("concurrency");
  expect(text).not.toMatch(forbidden);
  expect(text).not.toContain("winner");
});

test("omits the sign sentence when the payload has none and leaves a null delta blank", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      jsonResponse({
        average_ms_delta: null,
        median_ms_delta: 2,
        p50_ms_delta: null,
        p95_ms_delta: null,
        p99_ms_delta: null,
        error_rate_delta: null,
        generation_throughput_tps_delta: null,
        request_throughput_rps_delta: null,
        baseline_phase_label: "left",
        candidate_phase_label: "right",
        setting_differences: [],
      }),
    ),
  );
  render(<Comparisons />);
  fireEvent.change(screen.getByLabelText("baseline id"), { target: { value: "4" } });
  fireEvent.change(screen.getByLabelText("candidate id"), { target: { value: "5" } });
  fireEvent.click(screen.getByRole("button", { name: "Compare" }));

  expect(await screen.findByText("median_ms_delta 2")).toBeTruthy();
  expect(document.body.textContent).toContain("average_ms_delta");
  expect(document.body.textContent).not.toContain("average_ms_delta 0");
  expect(document.body.textContent).not.toContain("Request throughput is");
  expect(document.body.textContent).not.toContain("winner");
});
