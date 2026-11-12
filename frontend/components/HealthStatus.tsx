"use client";

import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";

import { cx, focusRing } from "./ui";

/** Compact backend status indicator for the header. Click to recheck. */
export function HealthStatus() {
  const { data, error, loading, reload } = useApi("health", (signal) => api.health(signal));

  const state = loading ? "checking" : error ? "down" : "up";
  const label =
    state === "checking"
      ? "Checking backend…"
      : state === "down"
        ? `Backend unavailable: ${error}`
        : `Backend healthy (v${data?.version}, ${data?.agent_provider} agent)`;

  return (
    <button
      type="button"
      onClick={reload}
      title={`${label} — click to recheck`}
      className={cx(
        "inline-flex items-center gap-2 rounded-md px-1.5 py-1 text-xs sm:px-2 text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800",
        focusRing,
      )}
    >
      <span
        aria-hidden="true"
        className={cx(
          "h-2 w-2 rounded-full",
          state === "up" && "bg-emerald-500",
          state === "down" && "bg-red-500",
          state === "checking" && "animate-pulse bg-zinc-400",
        )}
      />
      <span role="status" aria-live="polite">
        <span className="hidden sm:inline">
          {state === "up" ? "Backend OK" : state === "down" ? "Backend down" : "Checking…"}
        </span>
        <span className="sr-only sm:hidden">{label}</span>
      </span>
    </button>
  );
}
