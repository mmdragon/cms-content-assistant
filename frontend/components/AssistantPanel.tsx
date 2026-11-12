"use client";

import { useEffect, useRef } from "react";

import { useAppState } from "./AppState";
import { Badge, Button, cx, focusRing, inputClasses } from "./ui";

const EXAMPLE_PROMPTS = [
  "Find pages that still mention the discontinued Northstar Classic plan.",
  "Which pages have missing or overly long metadata?",
  "List pages not updated in the last 18 months.",
  "Check for broken internal links.",
];

export function AssistantToggle() {
  const { assistantOpen, setAssistantOpen } = useAppState();
  return (
    <Button
      variant={assistantOpen ? "primary" : "secondary"}
      size="sm"
      aria-expanded={assistantOpen}
      aria-controls="assistant-panel"
      onClick={() => setAssistantOpen(!assistantOpen)}
    >
      <svg aria-hidden="true" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4 sm:hidden">
        <path d="M3 4.5A2.5 2.5 0 0 1 5.5 2h9A2.5 2.5 0 0 1 17 4.5v6a2.5 2.5 0 0 1-2.5 2.5H9l-3.6 3.1A.75.75 0 0 1 4.2 15.5V13A2.5 2.5 0 0 1 3 10.5v-6Z" />
      </svg>
      <span className="sr-only sm:not-sr-only">Assistant</span>
    </Button>
  );
}

/**
 * Side panel for the content assistant. On large screens it sits beside the page;
 * on small screens it overlays it. The conversation is wired up in the next phase.
 */
export function AssistantPanel() {
  const { assistantOpen, setAssistantOpen } = useAppState();
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    if (!assistantOpen) return;
    headingRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setAssistantOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      // Return focus to the toggle so keyboard users don't lose their place.
      document.querySelector<HTMLElement>('[aria-controls="assistant-panel"]')?.focus();
    };
  }, [assistantOpen, setAssistantOpen]);

  if (!assistantOpen) return null;

  return (
    <aside
      id="assistant-panel"
      aria-labelledby="assistant-heading"
      className={cx(
        "fixed inset-0 z-40 flex flex-col bg-white dark:bg-zinc-950",
        "lg:sticky lg:top-14 lg:inset-auto lg:z-auto lg:h-[calc(100dvh-3.5rem)] lg:w-96 lg:shrink-0 lg:border-l lg:border-zinc-200 lg:dark:border-zinc-800",
      )}
    >
      <div className="flex items-center justify-between gap-2 border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
        <div className="flex items-center gap-2">
          <h2 id="assistant-heading" ref={headingRef} tabIndex={-1} className="font-semibold outline-none">
            Content assistant
          </h2>
          <Badge tone="violet">Demo mode</Badge>
        </div>
        <Button variant="ghost" size="sm" onClick={() => setAssistantOpen(false)} aria-label="Close assistant">
          ✕
        </Button>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-4 text-sm">
        <p className="text-zinc-600 dark:text-zinc-400">
          Ask about stale content, metadata, duplicate titles, or broken links. The assistant cites the page and
          exact excerpt for every finding, and can only draft proposals — you approve every change.
        </p>
        <div
          role="note"
          className="rounded-md border border-amber-300 bg-amber-50 p-3 text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200"
        >
          The assistant is not connected yet. The example prompts below show what it will handle.
        </div>
        <div>
          <h3 className="mb-2 text-xs font-semibold tracking-wide text-zinc-500 uppercase">Example prompts</h3>
          <ul className="space-y-2">
            {EXAMPLE_PROMPTS.map((p) => (
              <li key={p} className="rounded-md border border-zinc-200 p-2.5 text-zinc-700 dark:border-zinc-800 dark:text-zinc-300">
                {p}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <form className="border-t border-zinc-200 p-3 dark:border-zinc-800" onSubmit={(e) => e.preventDefault()}>
        <label htmlFor="assistant-input" className="sr-only">
          Message the assistant
        </label>
        <div className="flex gap-2">
          <input id="assistant-input" disabled placeholder="Not connected yet" className={inputClasses} />
          <button type="submit" disabled className={cx("rounded-md bg-blue-700 px-3 text-sm text-white opacity-50", focusRing)}>
            Send
          </button>
        </div>
      </form>
    </aside>
  );
}
