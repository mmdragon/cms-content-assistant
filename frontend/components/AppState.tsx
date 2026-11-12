"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

interface AppStateValue {
  /** Bumped whenever proposals change, so counts and lists elsewhere refetch. */
  proposalsVersion: number;
  notifyProposalsChanged: () => void;
  assistantOpen: boolean;
  setAssistantOpen: (open: boolean) => void;
}

const AppStateContext = createContext<AppStateValue | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [proposalsVersion, setVersion] = useState(0);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const notifyProposalsChanged = useCallback(() => setVersion((v) => v + 1), []);

  const value = useMemo(
    () => ({ proposalsVersion, notifyProposalsChanged, assistantOpen, setAssistantOpen }),
    [proposalsVersion, notifyProposalsChanged, assistantOpen],
  );
  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState(): AppStateValue {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error("useAppState must be used inside <AppStateProvider>");
  return ctx;
}
