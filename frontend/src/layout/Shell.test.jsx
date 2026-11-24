import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

afterEach(() => {
  vi.unstubAllGlobals();
  window.history.pushState({}, "", "/");
});

test("the rail links Comparisons and Routing", async () => {
  window.history.pushState({}, "", "/comparisons");
  vi.stubGlobal("fetch", vi.fn());
  const { App } = await import("../App.jsx");
  render(<App />);

  expect(screen.getByRole("link", { name: "Comparisons" }).getAttribute("href")).toBe(
    "/comparisons",
  );
  expect(screen.getByRole("link", { name: "Routing" }).getAttribute("href")).toBe("/routing");
  expect(screen.getByRole("heading", { name: "Comparisons" })).toBeTruthy();
  expect(fetch).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("link", { name: "Routing" }));
  expect(await screen.findByRole("heading", { name: "Routing" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Route" })).toBeTruthy();
});
