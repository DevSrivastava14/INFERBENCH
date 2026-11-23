import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { Overview } from "./Overview.jsx";

test("shows five empty regions and no sample", () => {
  render(<Overview />);

  for (const name of [
    "Inference engines",
    "Models",
    "Hardware",
    "Recent experiments",
    "Current CPU and RAM",
  ]) {
    expect(screen.getByRole("heading", { name })).toBeTruthy();
  }

  expect(screen.getAllByText("Nothing is loaded.")).toHaveLength(5);

  const text = document.body.textContent;
  expect(text).not.toContain("Ollama");
  expect(text).not.toContain("gemma3:1b");
  expect(text).not.toContain("qwen3.5:2b");
  expect(text).not.toContain("%");
  expect(text).not.toMatch(/\d/);
});
