"use client";

import { useId, useMemo, useState } from "react";

import { computeDiff, diffStats, splitPanes, type Segment } from "@/lib/diff";

import { cx, focusRing } from "../ui";

function Segments({ segments }: { segments: Segment[] }) {
  return (
    <>
      {segments.map((s, i) =>
        s.type === "added" ? (
          <ins
            key={i}
            className="rounded-sm bg-emerald-100 text-emerald-900 no-underline decoration-emerald-600 dark:bg-emerald-900/60 dark:text-emerald-100"
          >
            {s.value}
          </ins>
        ) : s.type === "removed" ? (
          <del key={i} className="rounded-sm bg-red-100 text-red-900 decoration-red-600 dark:bg-red-900/60 dark:text-red-100">
            {s.value}
          </del>
        ) : (
          <span key={i}>{s.value}</span>
        ),
      )}
    </>
  );
}

function Pane({ label, empty, segments }: { label: string; empty: boolean; segments: Segment[] }) {
  return (
    <div className="min-w-0">
      <h3 className="mb-1 text-xs font-semibold tracking-wide text-zinc-500 uppercase">{label}</h3>
      <div className="min-h-12 rounded-md border border-zinc-200 bg-zinc-50 p-3 text-sm leading-relaxed whitespace-pre-wrap break-words dark:border-zinc-800 dark:bg-zinc-950">
        {empty ? <span className="text-zinc-400 italic">(empty)</span> : <Segments segments={segments} />}
      </div>
    </div>
  );
}

type Mode = "split" | "inline";

export function DiffView({ before, after }: { before: string | null; after: string }) {
  const [mode, setMode] = useState<Mode>("split");
  const groupId = useId();
  const segments = useMemo(() => computeDiff(before ?? "", after), [before, after]);
  const panes = useMemo(() => splitPanes(segments), [segments]);
  const stats = useMemo(() => diffStats(segments), [segments]);

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          <span className="font-medium text-emerald-700 dark:text-emerald-400">+{stats.added}</span> words added,{" "}
          <span className="font-medium text-red-700 dark:text-red-400">−{stats.removed}</span> removed
        </p>
        <div role="radiogroup" aria-label="Diff layout" className="inline-flex rounded-md border border-zinc-300 p-0.5 dark:border-zinc-700">
          {(["split", "inline"] as const).map((m) => (
            <label
              key={m}
              className={cx(
                "cursor-pointer rounded px-2.5 py-1 text-xs font-medium has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-blue-600",
                mode === m ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900" : "text-zinc-700 dark:text-zinc-300",
              )}
            >
              <input
                type="radio"
                name={`${groupId}-mode`}
                value={m}
                checked={mode === m}
                onChange={() => setMode(m)}
                className={cx("sr-only", focusRing)}
              />
              {m === "split" ? "Side by side" : "Inline"}
            </label>
          ))}
        </div>
      </div>

      <p className="sr-only">Removed text is marked as deleted and added text as inserted.</p>
      {mode === "split" ? (
        <div className="grid gap-4 md:grid-cols-2">
          <Pane label="Before" empty={!before} segments={panes.before} />
          <Pane label="After" empty={!after} segments={panes.after} />
        </div>
      ) : (
        <Pane label="Changes" empty={false} segments={segments} />
      )}
    </div>
  );
}
