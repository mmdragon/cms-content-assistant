"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, fetchHealth } from "@/lib/api";
import type { HealthResponse } from "@/types/api";

type State =
  | { kind: "loading" }
  | { kind: "ok"; data: HealthResponse }
  | { kind: "error"; message: string };

export function HealthStatus() {
  const [state, setState] = useState<State>({ kind: "loading" });

  // Only sets state asynchronously, so it is safe to call from an effect.
  const load = useCallback((signal?: AbortSignal) => {
    fetchHealth(signal)
      .then((data) => setState({ kind: "ok", data }))
      .catch((err: unknown) => {
        if (signal?.aborted) return;
        const message =
          err instanceof ApiError
            ? err.message
            : "Could not reach the backend. Is it running on port 8000?";
        setState({ kind: "error", message });
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const recheck = () => {
    setState({ kind: "loading" });
    load();
  };

  return (
    <section
      aria-labelledby="health-heading"
      className="rounded-lg border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className="flex items-center justify-between gap-4">
        <h2 id="health-heading" className="text-base font-semibold">
          Backend status
        </h2>
        <button
          type="button"
          onClick={recheck}
          disabled={state.kind === "loading"}
          className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium hover:bg-zinc-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
        >
          Recheck
        </button>
      </div>

      <div role="status" aria-live="polite" className="mt-3 text-sm">
        {state.kind === "loading" && <p className="text-zinc-500">Checking backend…</p>}

        {state.kind === "ok" && (
          <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1">
            <dt className="text-zinc-500">Status</dt>
            <dd className="flex items-center gap-2 font-medium text-emerald-700 dark:text-emerald-400">
              <span aria-hidden="true" className="h-2 w-2 rounded-full bg-emerald-500" />
              Healthy
            </dd>
            <dt className="text-zinc-500">Version</dt>
            <dd>{state.data.version}</dd>
            <dt className="text-zinc-500">Environment</dt>
            <dd>{state.data.environment}</dd>
            <dt className="text-zinc-500">Agent provider</dt>
            <dd>{state.data.agent_provider}</dd>
          </dl>
        )}

        {state.kind === "error" && (
          <p className="flex items-center gap-2 font-medium text-red-700 dark:text-red-400">
            <span aria-hidden="true" className="h-2 w-2 rounded-full bg-red-500" />
            {state.message}
          </p>
        )}
      </div>
    </section>
  );
}
