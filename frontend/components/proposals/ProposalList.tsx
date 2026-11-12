"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { api } from "@/lib/api";
import { FIELD_LABELS, formatDateTime } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { PROPOSAL_STATUSES, type ProposalStatus } from "@/types/api";

import { useAppState } from "../AppState";
import { Card, EmptyState, ErrorState, LoadingState, Pagination, StatusBadge, cx, focusRing } from "../ui";

const PAGE_SIZE = 20;
type Tab = ProposalStatus | "all";
const TABS: { value: Tab; label: string }[] = [
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "all", label: "All" },
];

const EMPTY_COPY: Record<Tab, string> = {
  pending: "Nothing waiting for review. When the assistant drafts an edit, it appears here for you to approve or reject.",
  approved: "No approved proposals yet.",
  rejected: "No rejected proposals.",
  all: "No proposals yet. Ask the assistant to suggest updated wording and its drafts will appear here.",
};

export function ProposalList() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const { proposalsVersion } = useAppState();

  const rawTab = params.get("status");
  const tab: Tab = rawTab === "all" || PROPOSAL_STATUSES.includes(rawTab as ProposalStatus) ? (rawTab as Tab) : "pending";
  const offset = Math.max(0, Number.parseInt(params.get("offset") ?? "0", 10) || 0);

  const { data, error, loading, reload } = useApi(`proposals:${tab}:${offset}:${proposalsVersion}`, (signal) =>
    api.listProposals({ status: tab === "all" ? undefined : tab, limit: PAGE_SIZE, offset }, signal),
  );

  const go = (next: { tab?: Tab; offset?: number }) => {
    const qs = new URLSearchParams();
    const t = next.tab ?? tab;
    if (t !== "pending") qs.set("status", t);
    const o = next.tab ? 0 : (next.offset ?? offset);
    if (o) qs.set("offset", String(o));
    const s = qs.toString();
    router.replace(s ? `${pathname}?${s}` : pathname, { scroll: false });
  };

  return (
    <Card>
      <nav aria-label="Filter proposals by status" className="border-b border-zinc-200 px-2 dark:border-zinc-800">
        <ul className="flex gap-1 overflow-x-auto">
          {TABS.map((t) => (
            <li key={t.value}>
              <button
                type="button"
                aria-current={tab === t.value ? "page" : undefined}
                onClick={() => go({ tab: t.value })}
                className={cx(
                  "border-b-2 px-3 py-3 text-sm font-medium whitespace-nowrap",
                  tab === t.value
                    ? "border-blue-700 text-blue-700 dark:border-blue-400 dark:text-blue-400"
                    : "border-transparent text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100",
                  focusRing,
                )}
              >
                {t.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      {error ? (
        <div className="p-4">
          <ErrorState message={error} onRetry={reload} />
        </div>
      ) : !data ? (
        <LoadingState label="Loading proposals…" />
      ) : data.items.length === 0 ? (
        <EmptyState title="No proposals">{EMPTY_COPY[tab]}</EmptyState>
      ) : (
        <ul className={cx("divide-y divide-zinc-200 dark:divide-zinc-800", loading && "opacity-60")} aria-busy={loading}>
          {data.items.map((p) => (
            <li key={p.id}>
              <Link
                href={`/proposals/${p.id}`}
                className={cx("flex flex-col gap-1 px-4 py-3 hover:bg-zinc-50 sm:flex-row sm:items-center sm:gap-4 dark:hover:bg-zinc-800/40", focusRing)}
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">
                    {FIELD_LABELS[p.field_name]} <span className="font-normal text-zinc-500">on</span>{" "}
                    <span className="font-mono text-xs">{p.content_id}</span>
                  </p>
                  <p className="mt-0.5 line-clamp-1 text-sm text-zinc-600 dark:text-zinc-400">{p.rationale}</p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <time dateTime={p.created_at} className="text-xs text-zinc-500">
                    {formatDateTime(p.created_at)}
                  </time>
                  <StatusBadge status={p.status} />
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {data && (
        <Pagination total={data.total} limit={data.limit} offset={data.offset} label="proposals" onChange={(o) => go({ offset: o })} />
      )}
    </Card>
  );
}
