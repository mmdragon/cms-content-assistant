import { describe, expect, it } from "vitest";

import { computeDiff, diffStats, splitPanes } from "./diff";

describe("computeDiff", () => {
  it("marks replaced words and keeps the rest unchanged", () => {
    const segments = computeDiff("add the Northstar Classic plan", "add the Northstar Care plan");
    expect(segments.filter((s) => s.type === "removed").map((s) => s.value)).toEqual(["Classic"]);
    expect(segments.filter((s) => s.type === "added").map((s) => s.value)).toEqual(["Care"]);
    expect(diffStats(segments)).toEqual({ added: 1, removed: 1 });
  });

  it("treats an empty original as a pure addition", () => {
    const segments = computeDiff("", "New meta description");
    expect(segments).toEqual([{ type: "added", value: "New meta description" }]);
    expect(diffStats(segments)).toEqual({ added: 3, removed: 0 });
  });

  it("returns only unchanged segments for identical text", () => {
    expect(computeDiff("same text", "same text").every((s) => s.type === "unchanged")).toBe(true);
  });

  it("preserves newlines so multi-paragraph bodies render correctly", () => {
    const after = splitPanes(computeDiff("one\n\ntwo", "one\n\nthree")).after;
    expect(after.map((s) => s.value).join("")).toBe("one\n\nthree");
  });
});

describe("splitPanes", () => {
  it("reconstructs the original and proposed text exactly", () => {
    const before = "Every home includes the Northstar Classic plan.\nCall us.";
    const after = "Every new home includes the Northstar Care plan.\nCall us today.";
    const panes = splitPanes(computeDiff(before, after));
    expect(panes.before.map((s) => s.value).join("")).toBe(before);
    expect(panes.after.map((s) => s.value).join("")).toBe(after);
  });
});
