import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { Routing } from "./Routing.jsx";

afterEach(() => {
  vi.unstubAllGlobals();
});

function jsonResponse(body, ok = true) {
  return Promise.resolve({
    ok,
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
  render(<Routing />);

  expect(screen.getByLabelText("policy").value).toBe("static");
  expect(screen.getByRole("option", { name: "workload_aware" })).toBeTruthy();
  expect(screen.getByRole("option", { name: "latency_constrained" })).toBeTruthy();
  expect(screen.getByRole("option", { name: "availability_aware" })).toBeTruthy();
  expect(screen.getByLabelText("stored p95_ms")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Route" })).toBeTruthy();
  expect(
    screen.getByText("Static returns the configured model and keeps that name when a constraint fails."),
  ).toBeTruthy();
  expect(
    screen.getByText(
      "Workload-aware selection is the lowest stored P95 for the requested profile among models that pass the capability and size filters.",
    ),
  ).toBeTruthy();
  expect(
    screen.getByText(
      "Latency-constrained adds the caller's latency budget as a further filter, then uses that same P95 rank.",
    ),
  ).toBeTruthy();
  expect(
    screen.getByText(
      "Availability-aware uses that P95 rank, then selects the next eligible model when the preferred model is unavailable.",
    ),
  ).toBeTruthy();
  expect(screen.getByText("Nothing is loaded.")).toBeTruthy();
  expect(document.body.textContent).not.toMatch(forbidden);
  expect(fetchSpy).not.toHaveBeenCalled();
});

test("posts stored catalog latency and renders the fixture decision", async () => {
  const payload = {
    policy: "static",
    selected_model: "gemma3:1b",
    preferred_model: "qwen3.5:2b",
    reason: "static policy returns the configured model",
    fallback_count: 0,
    failed_constraints: ["size"],
  };
  expect(payload).not.toHaveProperty("winner");
  vi.stubGlobal("fetch", vi.fn(() => jsonResponse(payload)));
  render(<Routing />);
  fireEvent.change(screen.getByLabelText("profile name"), {
    target: { value: "short_prompt_short_output" },
  });
  fireEvent.change(screen.getByLabelText("static model"), {
    target: { value: "gemma3:1b" },
  });
  fireEvent.change(screen.getByLabelText("catalog model"), {
    target: { value: "gemma3:1b" },
  });
  fireEvent.change(screen.getByLabelText("stored p95_ms"), { target: { value: "40" } });
  fireEvent.click(screen.getByRole("button", { name: "Route" }));

  expect(await screen.findByText("reason static policy returns the configured model")).toBeTruthy();
  const body = postedBody();
  expect(fetch.mock.calls[0][0]).toBe("/api/route");
  expect(body.policy).toBe("static");
  expect(body.catalog[0].model).toBe("gemma3:1b");
  expect(body.catalog[0].measurements.short_prompt_short_output).toEqual({ p95_ms: 40 });
  expect(body.request.static_model).toBe("gemma3:1b");
  expect(body.request.profile_name).toBe("short_prompt_short_output");
  expect(body).not.toHaveProperty("winner");
  const text = document.body.textContent;
  expect(text).toContain("selected_model gemma3:1b");
  expect(text).toContain("preferred_model qwen3.5:2b");
  expect(text).toContain("fallback_count 0");
  expect(text).toContain("size");
  expect(text).not.toMatch(forbidden);
  expect(text).not.toContain("winner");
});

test("a failed route shows the load-failed sentence", async () => {
  vi.stubGlobal("fetch", vi.fn(() => jsonResponse({}, false)));
  render(<Routing />);
  fireEvent.click(screen.getByRole("button", { name: "Route" }));

  expect(await screen.findByText("The load failed.")).toBeTruthy();
  expect(document.body.textContent).not.toContain("selected_model");
  expect(document.body.textContent).not.toContain("winner");
});
