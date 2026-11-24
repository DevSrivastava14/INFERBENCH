import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { Benchmark } from "./Benchmark.jsx";

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
  expect(screen.getByRole("option", { name: "omitted" })).toBeTruthy();
  expect(screen.getByRole("option", { name: "false" })).toBeTruthy();
  expect(screen.queryByRole("option", { name: "true" })).toBeNull();
  expect(screen.getByRole("button", { name: "Run" })).toBeTruthy();
  expect(
    screen.getByText("Streaming is the benchmark path the runner already uses."),
  ).toBeTruthy();
  expect(
    screen.getByText("A cap on output tokens, not the number of tokens the model emitted."),
  ).toBeTruthy();
  expect(
    screen.getByText("Warm-up calls are stored and stay out of the measured set."),
  ).toBeTruthy();
  expect(
    screen.getByText("Run starts one job and returns before the model finishes."),
  ).toBeTruthy();
  expect(
    screen.getByText("Cancel stops new calls and cancels calls already in flight."),
  ).toBeTruthy();
  expect(screen.getByRole("button", { name: "Cancel" })).toBeTruthy();
  expect(document.body.textContent).not.toContain("num_ctx");
  expect(document.body.textContent).not.toContain("gemma3:1b");
  expect(document.body.textContent).not.toContain("qwen3.5:2b");
  expect(document.body.textContent).not.toMatch(/\d+\s*ms/);
  expect(fetchSpy).not.toHaveBeenCalled();
});

test("submitting qwen sends think false and a blank thread is omitted", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((url, options) => {
      if (options && options.method === "POST") {
        return jsonResponse({ id: 7, job_status: "PENDING" });
      }
      return jsonResponse({
        id: 7,
        job_status: "COMPLETED",
        succeeded_count: 1,
        failed_count: 2,
        latest_sample: {
          cpu_percent: 0,
          system_ram_used_bytes: 11,
        },
      });
    }),
  );
  render(<Benchmark />);
  fireEvent.change(screen.getByLabelText("model"), { target: { value: "qwen3.5:2b" } });
  fireEvent.change(screen.getByLabelText("prompt"), { target: { value: "Hi" } });
  fireEvent.click(screen.getByRole("button", { name: "Run" }));

  await waitFor(() => {
    expect(postedBody().think).toBe(false);
  });
  expect(postedBody()).not.toHaveProperty("num_thread");
  expect(postedBody()).not.toHaveProperty("num_ctx");
  expect(await screen.findByText("succeeded 1")).toBeTruthy();
  expect(screen.getByText("failed 2")).toBeTruthy();
  expect(screen.getByText("COMPLETED")).toBeTruthy();
  expect(screen.getByText("cpu_percent 0 system_ram_used_bytes 11")).toBeTruthy();
});

test("submitting gemma omits think", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((url, options) => {
      if (options && options.method === "POST") {
        return jsonResponse({ id: 8, job_status: "PENDING" });
      }
      return jsonResponse({
        id: 8,
        job_status: "COMPLETED",
        succeeded_count: 1,
        failed_count: 0,
        latest_sample: null,
      });
    }),
  );
  render(<Benchmark />);
  fireEvent.change(screen.getByLabelText("model"), { target: { value: "gemma3:1b" } });
  fireEvent.change(screen.getByLabelText("prompt"), { target: { value: "Hi" } });
  fireEvent.change(screen.getByLabelText("think"), { target: { value: "false" } });
  fireEvent.click(screen.getByRole("button", { name: "Run" }));

  await waitFor(() => {
    expect(fetch.mock.calls.some((item) => item[1] && item[1].method === "POST")).toBe(true);
  });
  expect(postedBody()).not.toHaveProperty("think");
  expect(postedBody().model).toBe("gemma3:1b");
  expect(await screen.findByText("COMPLETED")).toBeTruthy();
  expect(screen.queryByText(/cpu_percent/)).toBeNull();
});
