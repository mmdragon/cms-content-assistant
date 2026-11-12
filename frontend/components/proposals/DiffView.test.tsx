import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { DiffView } from "./DiffView";

describe("DiffView", () => {
  it("shows removed text in Before and added text in After", () => {
    const { container } = render(<DiffView before="the Northstar Classic plan" after="the Northstar Care plan" />);

    expect(container.querySelector("del")?.textContent).toBe("Classic");
    expect(container.querySelector("ins")?.textContent).toBe("Care");
    expect(screen.getByText("Before").nextElementSibling?.textContent).toBe("the Northstar Classic plan");
    expect(screen.getByText("After").nextElementSibling?.textContent).toBe("the Northstar Care plan");
  });

  it("labels an empty original value", () => {
    render(<DiffView before={null} after="A new description" />);
    const before = screen.getByText("Before").nextElementSibling as HTMLElement;
    expect(within(before).getByText("(empty)")).toBeTruthy();
  });

  it("switches to the inline layout with the keyboard-accessible radio group", async () => {
    const user = userEvent.setup();
    const { container } = render(<DiffView before="old words" after="new words" />);

    await user.click(screen.getByRole("radio", { name: "Inline" }));

    expect(screen.queryByText("Before")).toBeNull();
    expect(screen.getByText("Changes")).toBeTruthy();
    expect(container.querySelectorAll("ins, del")).toHaveLength(2);
  });

  it("renders page text literally, never as HTML", () => {
    const { container } = render(<DiffView before="safe" after={'<img src=x onerror="alert(1)">'} />);
    expect(container.querySelector("img")).toBeNull();
    expect(container.textContent).toContain('<img src=x onerror="alert(1)">');
  });
});
