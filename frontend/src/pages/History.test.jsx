import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";
import { History } from "./History.jsx";

afterEach(() => {
  vi.unstubAllGlobals();
});

function jsonResponse(body) {
  return Promise.resolve({
    ok: true,
    json: async () => body,
  });
}

function renderHistory() {
  return render(
    <MemoryRouter>
      <History />
    </MemoryRouter>,
  );
}

test("renders column headers and an empty body", async () => {
  vi.stubGlobal("fetch", vi.fn(() => jsonResponse([])));
  renderHistory();

  for (const name of [
    "source",
    "model",
    "profile name",
    "prompt",
    "num_predict",
    "warm-up count",
    "measured count",
    "concurrency",
    "think",
    "num_thread",
    "job status",
  ]) {
    expect(await screen.findByRole("columnheader", { name })).toBeTruthy();
  }

  expect(screen.getByText("Nothing is loaded.")).toBeTruthy();
  expect(document.body.textContent).not.toContain("gemma3:1b");
  expect(document.body.textContent).not.toContain("qwen3.5:2b");
  expect(document.body.textContent).not.toMatch(/\d+\s*ms/);
  expect(screen.queryByText("100")).toBeNull();
  expect(fetch).toHaveBeenCalledWith("/api/history");
});

test("renders returned rows, including the source, and a blank job status", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      jsonResponse([
        {
          source: "dashboard",
          id: 4,
          job_status: null,
          model: "gemma3:1b",
          profile_name: "short_prompt_short_output",
          prompt: "Hi",
          num_predict: 32,
          warmup_count: 2,
          measured_count: 3,
          concurrency: 1,
          think: null,
          num_thread: null,
        },
        {
          source: "model-comparison",
          id: 4,
          job_status: "COMPLETED",
          model: "qwen3.5:2b",
          profile_name: null,
          prompt: "Hi",
          num_predict: null,
          warmup_count: 2,
          measured_count: 3,
          concurrency: 1,
          think: false,
          num_thread: null,
        },
      ]),
    ),
  );
  renderHistory();

  expect(await screen.findByText("dashboard")).toBeTruthy();
  expect(screen.getByText("model-comparison")).toBeTruthy();
  expect(screen.getByText("gemma3:1b")).toBeTruthy();
  expect(screen.getByText("qwen3.5:2b")).toBeTruthy();
  expect(screen.getByText("COMPLETED")).toBeTruthy();
  expect(screen.getByText("false")).toBeTruthy();
  expect(screen.queryByText("null")).toBeNull();
  const dashboardRow = screen.getByText("dashboard").closest("tr");
  const status = dashboardRow.querySelector("td:last-child");
  expect(status.textContent).toBe("");
  const links = screen.getAllByRole("link", { name: "4" });
  expect(links[0].getAttribute("href")).toBe("/results?source=dashboard&id=4");
  expect(links[1].getAttribute("href")).toBe("/results?source=model-comparison&id=4");
  expect(screen.queryByText("100")).toBeNull();
});

test("a failed history load does not invent rows", async () => {
  vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("down"))));
  renderHistory();

  expect(await screen.findByText("The load failed.")).toBeTruthy();
  expect(screen.queryByText("gemma3:1b")).toBeNull();
  expect(screen.queryByText("100")).toBeNull();
});
