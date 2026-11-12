import { diffWordsWithSpace } from "diff";

export type SegmentType = "added" | "removed" | "unchanged";

export interface Segment {
  type: SegmentType;
  value: string;
}

/** Word-level diff that preserves whitespace and newlines. */
export function computeDiff(before: string, after: string): Segment[] {
  return diffWordsWithSpace(before, after).map((change) => ({
    type: change.added ? "added" : change.removed ? "removed" : "unchanged",
    value: change.value,
  }));
}

/** Segments for the "before" pane (unchanged + removed) and "after" pane (unchanged + added). */
export function splitPanes(segments: Segment[]): { before: Segment[]; after: Segment[] } {
  return {
    before: segments.filter((s) => s.type !== "added"),
    after: segments.filter((s) => s.type !== "removed"),
  };
}

export function diffStats(segments: Segment[]): { added: number; removed: number } {
  const words = (s: string) => s.split(/\s+/).filter(Boolean).length;
  return segments.reduce(
    (acc, s) => {
      if (s.type === "added") acc.added += words(s.value);
      if (s.type === "removed") acc.removed += words(s.value);
      return acc;
    },
    { added: 0, removed: 0 },
  );
}
