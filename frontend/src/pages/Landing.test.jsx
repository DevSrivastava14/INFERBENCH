import { act, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { landingPurpose } from "../copy.js";

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  window.history.pushState({}, "", "/");
});

test("the landing states the purpose and then opens Overview", async () => {
  vi.useFakeTimers();
  window.history.pushState({}, "", "/");
  vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
  const { App } = await import("../App.jsx");
  render(<App />);

  expect(screen.getByRole("heading", { name: landingPurpose })).toBeTruthy();
  expect(screen.queryByRole("heading", { name: "Overview" })).toBeNull();

  await act(async () => {
    await vi.advanceTimersByTimeAsync(3600);
  });

  expect(screen.getByRole("heading", { name: "Overview" })).toBeTruthy();
  expect(screen.queryByRole("heading", { name: landingPurpose })).toBeNull();
});
