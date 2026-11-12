"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import { EVENT_TYPES, type ActivityEvent, type EventType } from "@/types/api";

import { useAppState } from "../AppState";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  Pagination,
  StatusBadge,
  cx,
  focusRing,
  inputClasses,
} from "../ui";

const PAGE_SIZE = 25;

const EVENT_LABELS: Record<EventType, string> = {
  tool_call: "Tool call",
  proposal_created: "Proposal created",
  proposal_approved: "Proposal approved",
  proposal_rejected: "Proposal rejected",
  error: "Error",
};

function summary(event: ActivityEvent): string {
  const d = event.details;
  if (event.event_type === "tool_call") {
    const result = d.result as Record<string, unknown> | undefined;
    if (d.error) return String(d.error);
    if (result && "total_found" in result) return `${String(result.total_found)} found`;
    if (result && "proposal_id" in result) return `Created ${String(result.proposal_id)}`;
    return "Completed";
  }
  if (d.note) return `Note: ${String(d.note)}`;
  if (d.rationale) return String(d.rationale);
  if (d.content_id && d.field_name) return `${String(d.content_id)} · ${String(d.field_name)}`;
  return "";
}

function ProposalLink({ id }: { id: unknown }) {
  if (typeof id !== "string") return null;
  return (
    <Link href={`/proposals/${id}`} className={cx("font-mono text-xs text-blue-700 hover:underline dark:text-blue-400", focusRing)}>
      {id}
    </Link>
  );
}

export function ActivityLog() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const { proposalsVersion } = useAppState();

  const rawType = params.get("event_type");
  const eventType = EVENT_TYPES.includes(rawType as EventType) ? (rawType as EventType) : undefined;
  const offset = Math.max(0, Number.parseInt(params.get("offset") ?? "0", 10) || 0);

  const { data, error, loading, reload } = useApi(
    `activity:${eventType ?? "all"}:${offset}:${proposalsVersion}`,
    (signal) => api.listActivity({ event_type: eventType, limit: PAGE_SIZE, offset }, signal),
  );

  const go = (next: { eventType?: EventType | null; offset?: number }) => {
    const qs = new URLSearchParams();
    const t = next.eventType === null ? undefined : (next.eventType ?? eventType);
    if (t) qs.set("event_type", t);
    const o = "eventType" in next ? 0 : (next.offset ?? offset);
    if (o) qs.set("offset", String(o));
    const s = qs.toString();
    router.replace(s ? `${pathname}?${s}` : pathname, { scroll: false });
  };

  return (
    <Card>
      <div className="flex flex-wrap items-end justify-between gap-3 border-b border-zinc-200 p-4 dark:border-zinc-800">
        <div className="w-full sm:w-64">
          <label htmlFor="event-type" className="mb-1 block text-xs font-medium text-zinc-600 dark:text-zinc-400">
            Event type
          </label>
          <select
            id="event-type"
            value={eventType ?? ""}
            onChange={(e) => go({ eventType: (e.target.value || null) as EventType | null })}
            className={inputClasses}
          >
            <option value="">All events</option>
            {EVENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {EVENT_LABELS[t]}
              </option>
            ))}
          </select>
        </div>
        <Button size="sm" onClick={reload} disabled={loading}>
          Refresh
        </Button>
      </div>

      {error ? (
        <div className="p-4">
          <ErrorState message={error} onRetry={reload} />
        </div>
      ) : !data ? (
        <LoadingState label="Loading activity…" />
      ) : data.items.length === 0 ? (
        <EmptyState title="No activity yet">
          Tool calls, proposals, approvals, and rejections are recorded here as they happen.
        </EmptyState>
      ) : (
        <ol className={cx("divide-y divide-zinc-200 dark:divide-zinc-800", loading && "opacity-60")} aria-busy={loading}>
          {data.items.map((event) => (
            <li key={event.id} className="px-4 py-3">
              <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:gap-4">
                <time dateTime={event.created_at} className="shrink-0 text-xs text-zinc-500 sm:w-48 sm:pt-0.5">
                  {formatDateTime(event.created_at)}
                </time>
                <div className="min-w-0 flex-1">
                  <p className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="font-medium">{EVENT_LABELS[event.event_type] ?? event.event_type}</span>
                    {event.tool_name && <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs dark:bg-zinc-800">{event.tool_name}</code>}
                    <Badge tone={event.actor === "editor" ? "blue" : event.actor === "assistant" ? "violet" : "neutral"}>
                      {event.actor}
                    </Badge>
                    <StatusBadge status={event.status} />
                    <ProposalLink id={event.details.proposal_id} />
                  </p>
                  {summary(event) && <p className="mt-1 text-sm break-words text-zinc-600 dark:text-zinc-400">{summary(event)}</p>}
                  <details className="mt-1 text-xs">
                    <summary className={cx("cursor-pointer text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200", focusRing)}>
                      Details
                    </summary>
                    <pre className="mt-2 overflow-x-auto rounded-md bg-zinc-50 p-3 text-xs dark:bg-zinc-950">
                      {JSON.stringify(event.details, null, 2)}
                    </pre>
                  </details>
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}
      {data && (
        <Pagination total={data.total} limit={data.limit} offset={data.offset} label="events" onChange={(o) => go({ offset: o })} />
      )}
    </Card>
  );
}
