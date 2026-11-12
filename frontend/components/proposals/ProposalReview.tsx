"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { api, errorMessage } from "@/lib/api";
import { FIELD_LABELS, formatDateTime } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import type { ContentEntry, Proposal } from "@/types/api";

import { useAppState } from "../AppState";
import { Button, Card, ErrorState, LoadingState, PageHeader, StatusBadge, cx, focusRing } from "../ui";
import { ConfirmDialog } from "./ConfirmDialog";
import { DiffView } from "./DiffView";

type Action = "approve" | "reject";

function currentValue(entry: ContentEntry, proposal: Proposal): string | null {
  return entry[proposal.field_name];
}

function ReviewActions({ proposal, stale, onDone }: { proposal: Proposal; stale: boolean; onDone: () => void }) {
  const { notifyProposalsChanged } = useAppState();
  const [action, setAction] = useState<Action | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  const close = () => {
    if (busy) return;
    setAction(null);
    setError(undefined);
  };

  const confirm = async (note: string) => {
    if (!action) return;
    setBusy(true);
    setError(undefined);
    try {
      if (action === "approve") await api.approveProposal(proposal.id, note);
      else await api.rejectProposal(proposal.id, note);
      setAction(null);
      notifyProposalsChanged();
      onDone();
    } catch (err) {
      setError(errorMessage(err));
      // A conflict means the server state moved on; refresh what's shown behind the dialog.
      onDone();
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="flex flex-wrap gap-2">
        <Button variant="primary" onClick={() => setAction("approve")} disabled={stale}>
          Approve and apply
        </Button>
        <Button variant="secondary" onClick={() => setAction("reject")}>
          Reject
        </Button>
      </div>
      <ConfirmDialog
        open={action !== null}
        title={action === "approve" ? "Apply this change?" : "Reject this proposal?"}
        description={
          action === "approve" ? (
            <>
              This updates the <strong>{FIELD_LABELS[proposal.field_name].toLowerCase()}</strong> of page{" "}
              <span className="font-mono">{proposal.content_id}</span> in the content store. It will not be
              published to a live site.
            </>
          ) : (
            <>The page stays unchanged. The proposal is kept as rejected in the history.</>
          )
        }
        confirmLabel={action === "approve" ? "Approve and apply" : "Reject proposal"}
        confirmVariant={action === "approve" ? "primary" : "danger"}
        busy={busy}
        error={error}
        onConfirm={confirm}
        onClose={close}
      />
    </>
  );
}

export function ProposalReview() {
  const { id } = useParams<{ id: string }>();
  const proposal = useApi(`proposal:${id}`, (signal) => api.getProposal(id, signal));
  const contentId = proposal.data?.content_id ?? null;
  const content = useApi(contentId && `proposal-content:${contentId}`, (signal) =>
    api.getContent(contentId as string, signal),
  );

  const reloadAll = () => {
    proposal.reload();
    content.reload();
  };

  if (proposal.error) {
    return (
      <>
        <PageHeader title="Proposal not available" breadcrumb={{ href: "/proposals", label: "Proposals" }} />
        <ErrorState message={proposal.error} onRetry={proposal.reload} />
      </>
    );
  }
  if (!proposal.data) return <LoadingState label="Loading proposal…" rows={6} />;

  const p = proposal.data;
  const entry = content.data;
  const stale = p.status === "pending" && entry !== undefined && currentValue(entry, p) !== p.original_value;

  return (
    <>
      <PageHeader
        breadcrumb={{ href: "/proposals", label: "Proposals" }}
        title={`Proposed edit: ${FIELD_LABELS[p.field_name]}`}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <StatusBadge status={p.status} />
            <span>
              on{" "}
              <Link
                href={`/content/${p.content_id}`}
                className={cx("font-medium text-blue-700 hover:underline dark:text-blue-400", focusRing)}
              >
                {entry ? entry.title : p.content_id}
              </Link>{" "}
              <span className="font-mono text-xs">({p.content_id})</span>
            </span>
          </span>
        }
        actions={p.status === "pending" ? <ReviewActions proposal={p} stale={stale} onDone={reloadAll} /> : undefined}
      />

      {stale && (
        <div
          role="alert"
          className="mb-6 rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200"
        >
          This page&apos;s {FIELD_LABELS[p.field_name].toLowerCase()} changed after the proposal was drafted, so
          it can&apos;t be applied safely. Reject it and ask the assistant for a fresh proposal.
        </div>
      )}
      {content.error && (
        <div className="mb-6">
          <ErrorState message={`Couldn't load the page: ${content.error}`} onRetry={content.reload} />
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <Card aria-labelledby="diff-heading" className="p-4">
          <h2 id="diff-heading" className="mb-3 text-sm font-semibold">
            Before and after
          </h2>
          <DiffView before={p.original_value} after={p.proposed_value} />
        </Card>

        <div className="space-y-6">
          <Card aria-labelledby="why-heading" className="p-4">
            <h2 id="why-heading" className="text-sm font-semibold">
              Why this change
            </h2>
            <p className="mt-2 text-sm">{p.rationale}</p>
            <h3 className="mt-4 text-xs font-semibold tracking-wide text-zinc-500 uppercase">Evidence from the page</h3>
            <blockquote className="mt-1 border-l-4 border-zinc-300 pl-3 text-sm text-zinc-700 italic dark:border-zinc-700 dark:text-zinc-300">
              {p.evidence_excerpt}
            </blockquote>
          </Card>

          <Card aria-labelledby="history-heading" className="p-4">
            <h2 id="history-heading" className="text-sm font-semibold">
              History
            </h2>
            <dl className="mt-2 space-y-2 text-sm">
              <div>
                <dt className="text-xs text-zinc-500">Drafted by the assistant</dt>
                <dd>{formatDateTime(p.created_at)}</dd>
              </div>
              {p.reviewed_at && (
                <div>
                  <dt className="text-xs text-zinc-500">{p.status === "approved" ? "Approved" : "Rejected"} by an editor</dt>
                  <dd>{formatDateTime(p.reviewed_at)}</dd>
                </div>
              )}
              {p.review_note && (
                <div>
                  <dt className="text-xs text-zinc-500">Review note</dt>
                  <dd>{p.review_note}</dd>
                </div>
              )}
              <div>
                <dt className="text-xs text-zinc-500">Proposal id</dt>
                <dd className="font-mono text-xs">{p.id}</dd>
              </div>
            </dl>
          </Card>
        </div>
      </div>
    </>
  );
}
