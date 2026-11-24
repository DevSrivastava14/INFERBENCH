import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { Overview } from "./Overview.jsx";

afterEach(() => {
  vi.unstubAllGlobals();
});

function jsonResponse(body, ok = true) {
  return Promise.resolve({
    ok,
    json: async () => body,
  });
}

test("a failed load does not invent a sample or a model list", async () => {
  vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("down"))));
  render(<Overview />);

  expect(await screen.findByText("The load failed.")).toBeTruthy();
  expect(screen.queryByText("Nothing is loaded.")).toBeNull();
  const text = document.body.textContent;
  expect(text).not.toContain("gemma3:1b");
  expect(text).not.toContain("qwen3.5:2b");
  expect(text).not.toContain("Ollama");
  expect(text).not.toContain("%");
  expect(text).not.toMatch(/\d/);
  expect(fetch).toHaveBeenCalledWith("/api/overview");
});

test("fills the five regions from the payload, including a cpu sample of 0", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      jsonResponse({
        inference_engines: [{ name: "ollama", version: "0.test" }],
        models: [{ name: "gemma3:1b" }],
        hardware: {
          cpu_model: "fixture-cpu",
          logical_cpu_count: 4,
          total_ram_bytes: 8,
          python_version: "3.x",
        },
        recent_experiments: [],
        sample: {
          cpu_percent: 0,
          system_ram_used_bytes: 3,
          system_ram_total_bytes: 8,
        },
      }),
    ),
  );
  render(<Overview />);

  expect(await screen.findByText("cpu_percent 0")).toBeTruthy();
  expect(screen.getByText("ollama 0.test")).toBeTruthy();
  expect(screen.getByText("gemma3:1b")).toBeTruthy();
  expect(screen.getByText("cpu_model fixture-cpu")).toBeTruthy();
  expect(screen.getByText("Nothing is loaded.")).toBeTruthy();
  expect(screen.queryByText("qwen3.5:2b")).toBeNull();
  expect(document.body.textContent).not.toContain("100");
});
