import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { Benchmark } from "./Benchmark.jsx";

afterEach(() => {
  vi.unstubAllGlobals();
});

test("keeps runner fields in local state and does not fetch", () => {
  const fetchSpy = vi.fn();
  vi.stubGlobal("fetch", fetchSpy);
  render(<Benchmark />);

  expect(screen.getByLabelText("model").value).toBe("");
  expect(screen.getByLabelText("prompt").value).toBe("");
  expect(screen.getByLabelText("profile name").value).toBe("");
  expect(screen.getByLabelText("num_predict").value).toBe("");
  expect(screen.getByLabelText("warm-up count").value).toBe("");
  expect(screen.getByLabelText("measured count").value).toBe("");
  expect(screen.getByLabelText("concurrency").value).toBe("");
  expect(screen.getByLabelText("think").value).toBe("");
  expect(screen.getByLabelText("num_thread").value).toBe("");
  expect(screen.getByRole("option", { name: "short_prompt_short_output" })).toBeTruthy();
  expect(screen.getByRole("option", { name: "long_prompt_short_output" })).toBeTruthy();
  expect(screen.getByRole("option", { name: "short_prompt_long_output" })).toBeTruthy();
  expect(screen.getByRole("option", { name: "long_prompt_long_output" })).toBeTruthy();
  expect(
    screen.getByText("Streaming is the benchmark path the runner already uses."),
  ).toBeTruthy();
  expect(screen.queryByRole("button")).toBeNull();
  expect(document.body.textContent).not.toContain("num_ctx");
  expect(document.body.textContent).not.toContain("gemma3:1b");
  expect(document.body.textContent).not.toContain("qwen3.5:2b");
  expect(document.body.textContent).not.toMatch(/\d+\s*ms/);
  expect(fetchSpy).not.toHaveBeenCalled();
});
