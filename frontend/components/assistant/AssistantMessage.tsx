import Link from "next/link";

import { FIELD_LABELS } from "@/lib/format";
import type { AgentResponse, Finding } from "@/types/api";

import { Badge, StatusBadge, cx, focusRing } from "../ui";

const SEVERITY_TONE = { high: "red", medium: "amber", low: "neutral" } as const;

const FINDING_FIELD_LABELS: Record<string, string> = {
  ...FIELD_LABELS,
  updated_at: "Last updated",
  canonical_url: "Canonical URL",
};

function groupByPage(findings: Finding[]): { id: string; title: string; items: Finding[] }[] {
  const groups = new Map<string, { id: string; title: string; items: Finding[] }>();
  for (const f of findings) {
    const group = groups.get(f.content_id) ?? { id: f.content_id, title: f.title, items: [] };
    group.items.push(f);
    groups.set(f.content_id, group);
  }
  return [...groups.values()];
}

const linkClass = cx("font-medium text-blue-700 hover:underline dark:text-blue-400", focusRing);

export function AssistantMessage({ response }: { response: AgentResponse }) {
  const groups = groupByPage(response.findings);

  return (
    <div className="space-y-3">
      <p className="whitespace-pre-line">{response.message}</p>

      {response.notes.map((note) => (
        <p
          key={note}
          role="note"
          className="rounded-md border border-amber-300 bg-amber-50 p-2.5 text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200"
        >
          {note}
        </p>
      ))}

      {response.proposals.length > 0 && (
        <section aria-label="Drafted proposals" className="rounded-md border border-blue-200 bg-blue-50/60 p-3 dark:border-blue-900 dark:bg-blue-950/40">
          <h4 className="mb-2 text-xs font-semibold tracking-wide text-blue-900 uppercase dark:text-blue-200">
            {response.proposals.length} {response.proposals.length === 1 ? "draft" : "drafts"} awaiting your review
          </h4>
          <ul className="space-y-1.5">
            {response.proposals.map((p) => (
              <li key={p.proposal_id} className="flex items-center justify-between gap-2">
                <span className="min-w-0">
                  <span className="block truncate">{p.title}</span>
                  <span className="text-xs text-zinc-500">
                    {FIELD_LABELS[p.field_name]} · {p.content_id}
                  </span>
                </span>
                <Link href={`/proposals/${p.proposal_id}`} className={cx(linkClass, "shrink-0 text-xs")}>
                  Review →
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {groups.length > 0 && (
        <details open={groups.length <= 8} className="group">
          <summary className={cx("cursor-pointer text-xs font-semibold tracking-wide text-zinc-500 uppercase", focusRing)}>
            Evidence: {response.findings.length} {response.findings.length === 1 ? "finding" : "findings"} on{" "}
            {groups.length} {groups.length === 1 ? "page" : "pages"}
          </summary>
          <ul className="mt-2 space-y-3">
            {groups.map((g) => (
              <li key={g.id} className="rounded-md border border-zinc-200 p-2.5 dark:border-zinc-800">
                <Link href={`/content/${g.id}`} className={linkClass}>
                  {g.title}
                </Link>{" "}
                <span className="font-mono text-xs text-zinc-500">{g.id}</span>
                <ul className="mt-2 space-y-2.5">
                  {g.items.map((f, i) => (
                    <li key={i}>
                      <div className="flex flex-wrap items-center gap-1.5">
                        <Badge tone={SEVERITY_TONE[f.severity]}>{f.severity}</Badge>
                        <Badge>{FINDING_FIELD_LABELS[f.field] ?? f.field}</Badge>
                      </div>
                      {/* Excerpts are untrusted page text: rendered as plain text, never as HTML. */}
                      <blockquote className="mt-1.5 border-l-4 border-zinc-300 pl-2.5 text-zinc-700 italic dark:border-zinc-700 dark:text-zinc-300">
                        {f.excerpt}
                      </blockquote>
                      <p className="mt-1">{f.reason}</p>
                      <p className="mt-0.5 text-zinc-600 dark:text-zinc-400">
                        <span className="font-medium">Recommendation:</span> {f.recommendation}
                      </p>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </details>
      )}

      {response.tool_calls.length > 0 && (
        <details className="text-xs">
          <summary className={cx("cursor-pointer text-zinc-500", focusRing)}>
            Used {response.tool_calls.length} {response.tool_calls.length === 1 ? "tool call" : "tool calls"}
          </summary>
          <ol className="mt-2 space-y-1">
            {response.tool_calls.map((c, i) => (
              <li key={i} className="flex flex-wrap items-center gap-1.5">
                <code className="rounded bg-zinc-100 px-1.5 py-0.5 dark:bg-zinc-800">{c.tool_name}</code>
                <StatusBadge status={c.status} />
                <span className="text-zinc-500">{c.duration_ms} ms</span>
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  );
}
