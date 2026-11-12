"use client";

import { useCallback, useEffect, useEffectEvent, useState } from "react";

import { errorMessage } from "@/lib/api";

type Settled<T> =
  | { key: string; kind: "ok"; data: T }
  | { key: string; kind: "error"; error: string; data: T | undefined };

export interface ApiState<T> {
  /** Latest data. While a new request is loading this still holds the previous result. */
  data: T | undefined;
  error: string | undefined;
  loading: boolean;
  reload: () => void;
}

/**
 * Fetch data for `key`, refetching whenever `key` changes. Pass `null` to skip.
 * State is keyed by request, so "loading" is derived instead of set inside the effect.
 */
export function useApi<T>(key: string | null, fetcher: (signal: AbortSignal) => Promise<T>): ApiState<T> {
  const [nonce, setNonce] = useState(0);
  const [settled, setSettled] = useState<Settled<T> | undefined>(undefined);
  const requestKey = key === null ? null : `${key}#${nonce}`;

  const run = useEffectEvent((signal: AbortSignal, forKey: string) => {
    fetcher(signal)
      .then((data) => setSettled({ key: forKey, kind: "ok", data }))
      .catch((err: unknown) => {
        if (signal.aborted) return;
        setSettled((prev) => ({
          key: forKey,
          kind: "error",
          error: errorMessage(err),
          data: prev?.data,
        }));
      });
  });

  useEffect(() => {
    if (requestKey === null) return;
    const controller = new AbortController();
    run(controller.signal, requestKey);
    return () => controller.abort();
  }, [requestKey]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  return {
    data: settled?.data,
    error: settled?.kind === "error" && settled.key === requestKey ? settled.error : undefined,
    loading: requestKey !== null && settled?.key !== requestKey,
    reload,
  };
}
