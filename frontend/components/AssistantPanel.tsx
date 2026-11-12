"use client";

import { useEffect, useRef, useState } from "react";

import { MAX_MESSAGE_CHARS, api, errorMessage } from "@/lib/api";
import type { AgentResponse, ChatMessage } from "@/types/api";

import { useAppState } from "./AppState";
import { AssistantMessage } from "./assistant/AssistantMessage";
import { Badge, Button, cx, focusRing, inputClasses } from "./ui";

export const EXAMPLE_PROMPTS = [
  "Find pages that still mention the discontinued Northstar Classic plan. Suggest updated wording, but do not apply any changes.",
  "Which pages have missing or overly long metadata?",
  "List pages not updated in the last 18 months.",
  "Check for broken internal links.",
  "Are there duplicate titles?",
  "Tell me about ns-027",
];

export type Turn =
  | { id: number; role: "user"; text: string }
  | { id: number; role: "assistant"; response: AgentResponse }
  | { id: number; role: "error"; text: string; retry: string };

const STORAGE_KEY = "cms-assistant-conversation";

function loadTurns(): Turn[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Turn[]) : [];
  } catch {
    return [];
  }
}

function saveTurns(turns: Turn[]): void {
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(turns));
  } catch {
    // Storage unavailable (private mode, quota): the conversation just won't survive a reload.
  }
}

/** Conversation history sent to the backend: user text and the assistant's prose replies. */
export function toHistory(turns: Turn[]): ChatMessage[] {
  return turns.flatMap((t): ChatMessage[] => {
    if (t.role === "user") return [{ role: "user", content: t.text }];
    if (t.role === "assistant")
      return [{ role: "assistant", content: t.response.message.slice(0, MAX_MESSAGE_CHARS) }];
    return [];
  });
}

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

export function Conversation() {
  const { notifyProposalsChanged } = useAppState();
  const [turns, setTurns] = useState<Turn[]>(loadTurns);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const lastTurnRef = useRef<HTMLLIElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const nextId = useRef(turns.reduce((max, t) => Math.max(max, t.id), 0) + 1);

  useEffect(() => {
    saveTurns(turns);
    // Show the start of the newest turn, so long replies are read from their summary down.
    lastTurnRef.current?.scrollIntoView?.({ block: "start" });
  }, [turns]);

  useEffect(() => {
    if (pending) endRef.current?.scrollIntoView?.({ block: "end" });
  }, [pending]);

  const send = async (text: string, base: Turn[] = turns) => {
    const trimmed = text.trim();
    if (!trimmed || pending) return;
    const userTurn: Turn = { id: nextId.current++, role: "user", text: trimmed };
    const withUser = [...base, userTurn];
    setTurns(withUser);
    setDraft("");
    setPending(true);
    try {
      const response = await api.chat([...toHistory(base), { role: "user", content: trimmed }]);
      setTurns((prev) => [...prev, { id: nextId.current++, role: "assistant", response }]);
      if (response.proposals.length > 0) notifyProposalsChanged();
    } catch (err) {
      setTurns((prev) => [...prev, { id: nextId.current++, role: "error", text: errorMessage(err), retry: trimmed }]);
    } finally {
      setPending(false);
      inputRef.current?.focus();
    }
  };

  const retry = (turn: Extract<Turn, { role: "error" }>) => {
    // Drop the failed exchange (the user turn and its error) and send it again.
    const index = turns.findIndex((t) => t.id === turn.id);
    void send(turn.retry, turns.slice(0, Math.max(0, index - 1)));
  };

  return (
    <>
      <div className="flex-1 space-y-4 overflow-y-auto p-4 text-sm" aria-live="polite" aria-busy={pending}>
        <p className="rounded-md bg-violet-50 p-2.5 text-xs text-violet-900 dark:bg-violet-950 dark:text-violet-200">
          <strong>Demo mode:</strong> responses are rule-based and deterministic — no AI model is used. Every
          finding cites a page and an exact excerpt, and the assistant can only draft proposals. You approve every
          change.
        </p>

        {turns.length === 0 && (
          <div>
            <h3 className="mb-2 text-xs font-semibold tracking-wide text-zinc-500 uppercase">Try asking</h3>
            <ul className="space-y-2">
              {EXAMPLE_PROMPTS.map((p) => (
                <li key={p}>
                  <button
                    type="button"
                    onClick={() => void send(p)}
                    disabled={pending}
                    className={cx(
                      "w-full rounded-md border border-zinc-200 p-2.5 text-left text-zinc-700 hover:border-blue-400 hover:bg-blue-50 dark:border-zinc-800 dark:text-zinc-300 dark:hover:bg-blue-950/40",
                      focusRing,
                    )}
                  >
                    {p}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <ol className="space-y-4">
          {turns.map((turn, i) => (
            <li key={turn.id} ref={i === turns.length - 1 ? lastTurnRef : undefined} className="scroll-mt-2">
              {turn.role === "user" ? (
                <div className="ml-8 rounded-lg bg-blue-700 px-3 py-2 text-white">
                  <span className="sr-only">You said: </span>
                  {turn.text}
                </div>
              ) : turn.role === "assistant" ? (
                <div className="mr-2 rounded-lg border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-900">
                  <span className="sr-only">Assistant replied: </span>
                  <AssistantMessage response={turn.response} />
                </div>
              ) : (
                <div role="alert" className="mr-2 rounded-lg border border-red-200 bg-red-50 p-3 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
                  <p>{turn.text}</p>
                  <Button size="sm" className="mt-2" onClick={() => retry(turn)} disabled={pending}>
                    Try again
                  </Button>
                </div>
              )}
            </li>
          ))}
        </ol>

        {pending && (
          <p role="status" className="flex items-center gap-2 text-zinc-500">
            <span aria-hidden="true" className="h-2 w-2 animate-pulse rounded-full bg-violet-500" />
            Checking the content…
          </p>
        )}
        <div ref={endRef} />
      </div>

      <form
        className="border-t border-zinc-200 p-3 dark:border-zinc-800"
        onSubmit={(e) => {
          e.preventDefault();
          void send(draft);
        }}
      >
        <div className="mb-2 flex items-center justify-between">
          <label htmlFor="assistant-input" className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
            Ask about your content
          </label>
          {turns.length > 0 && (
            <button
              type="button"
              onClick={() => setTurns([])}
              disabled={pending}
              className={cx("text-xs text-zinc-500 hover:text-zinc-900 hover:underline dark:hover:text-zinc-100", focusRing)}
            >
              Clear conversation
            </button>
          )}
        </div>
        <div className="flex items-end gap-2">
          <textarea
            id="assistant-input"
            ref={inputRef}
            rows={2}
            value={draft}
            maxLength={MAX_MESSAGE_CHARS}
            disabled={pending}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                void send(draft);
              }
            }}
            placeholder="e.g. Which pages mention “splash pad”?"
            className={cx(inputClasses, "resize-none")}
          />
          <Button type="submit" variant="primary" disabled={pending || !draft.trim()}>
            Send
          </Button>
        </div>
        <p className="mt-1 text-[11px] text-zinc-500">Enter to send · Shift+Enter for a new line</p>
      </form>
    </>
  );
}

/**
 * Side panel for the content assistant. On large screens it sits beside the page;
 * on small screens it covers it.
 */
export function AssistantPanel() {
  const { assistantOpen, setAssistantOpen } = useAppState();
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    if (!assistantOpen) return;
    headingRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !document.querySelector("dialog[open]")) setAssistantOpen(false);
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
        "lg:sticky lg:top-14 lg:inset-auto lg:z-auto lg:h-[calc(100dvh-3.5rem)] lg:w-[28rem] lg:shrink-0 lg:border-l lg:border-zinc-200 lg:dark:border-zinc-800",
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
      <Conversation />
    </aside>
  );
}
