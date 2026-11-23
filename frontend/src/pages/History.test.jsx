import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { History } from "./History.jsx";

test("renders column headers and an empty body", () => {
  render(<History />);

  for (const name of [
    "model",
    "profile name",
    "prompt",
    "num_predict",
    "warm-up count",
    "measured count",
    "concurrency",
    "think",
    "num_thread",
  ]) {
    expect(screen.getByRole("columnheader", { name })).toBeTruthy();
  }

  expect(screen.getByText("Nothing is loaded.")).toBeTruthy();
  expect(document.body.textContent).not.toContain("gemma3:1b");
  expect(document.body.textContent).not.toContain("qwen3.5:2b");
  expect(document.body.textContent).not.toMatch(/\d+\s*ms/);
  expect(screen.queryByText("100")).toBeNull();
});
