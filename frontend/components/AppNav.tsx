"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { api } from "@/lib/api";
import { useApi } from "@/lib/useApi";

import { useAppState } from "./AppState";
import { cx, focusRing } from "./ui";

const LINKS = [
  { href: "/", label: "Content", match: (p: string) => p === "/" || p.startsWith("/content") },
  { href: "/proposals", label: "Proposals", match: (p: string) => p.startsWith("/proposals") },
  { href: "/activity", label: "Activity", match: (p: string) => p.startsWith("/activity") },
];

function PendingCount() {
  const { proposalsVersion } = useAppState();
  const { data } = useApi(`pending-count:${proposalsVersion}`, (signal) =>
    api.listProposals({ status: "pending", limit: 1 }, signal),
  );
  if (!data || data.total === 0) return null;
  return (
    <span className="ml-1.5 rounded-full bg-amber-500 px-1.5 py-0.5 text-[11px] leading-none font-semibold text-white">
      {data.total}
      <span className="sr-only"> pending</span>
    </span>
  );
}

export function AppNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className="min-w-0 overflow-x-auto">
      <ul className="flex items-center gap-0.5 sm:gap-1">
        {LINKS.map((link) => {
          const active = link.match(pathname);
          return (
            <li key={link.href}>
              <Link
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={cx(
                  "inline-flex items-center rounded-md px-2 py-1.5 text-sm font-medium whitespace-nowrap sm:px-3",
                  active
                    ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                    : "text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800",
                  focusRing,
                )}
              >
                {link.label}
                {link.href === "/proposals" && <PendingCount />}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function AppNavFallback() {
  return (
    <ul className="flex items-center gap-1" aria-hidden="true">
      {LINKS.map((l) => (
        <li key={l.href} className="px-3 py-1.5 text-sm font-medium text-zinc-400">
          {l.label}
        </li>
      ))}
    </ul>
  );
}
