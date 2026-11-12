"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import type { ReactNode } from "react";

import { api } from "@/lib/api";
import {
  CATEGORY_LABELS,
  FIELD_LABELS,
  META_DESCRIPTION_MAX,
  META_TITLE_MAX,
  formatDate,
  formatDateTime,
} from "@/lib/format";
import { useApi } from "@/lib/useApi";

import { useAppState } from "../AppState";
import { Badge, Card, EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge, cx, focusRing } from "../ui";

function CharCount({ value, max }: { value: string | null; max: number }) {
  const len = value?.trim().length ?? 0;
  if (len === 0) return <Badge tone="red">Missing</Badge>;
  return <Badge tone={len > max ? "amber" : "neutral"}>{len > max ? `${len}/${max} — too long` : `${len}/${max}`}</Badge>;
}

function Field({ label, children, extra }: { label: string; children: ReactNode; extra?: ReactNode }) {
  return (
    <div className="py-3">
      <dt className="flex items-center justify-between gap-2 text-xs font-medium text-zinc-500">
        {label}
        {extra}
      </dt>
      <dd className="mt-1 text-sm break-words">{children}</dd>
    </div>
  );
}

function Empty() {
  return <span className="text-zinc-400 italic">Not set</span>;
}

function RelatedProposals({ contentId }: { contentId: string }) {
  const { proposalsVersion } = useAppState();
  const { data, error } = useApi(`proposals-for:${contentId}:${proposalsVersion}`, (signal) =>
    api.listProposals({ content_id: contentId, limit: 20 }, signal),
  );
  return (
    <Card aria-labelledby="proposals-heading">
      <h2 id="proposals-heading" className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold dark:border-zinc-800">
        Proposals for this page
      </h2>
      {error ? (
        <div className="p-4">
          <ErrorState message={error} />
        </div>
      ) : !data ? (
        <LoadingState rows={2} />
      ) : data.items.length === 0 ? (
        <p className="px-4 py-6 text-sm text-zinc-500">No proposals yet.</p>
      ) : (
        <ul className="divide-y divide-zinc-200 dark:divide-zinc-800">
          {data.items.map((p) => (
            <li key={p.id}>
              <Link
                href={`/proposals/${p.id}`}
                className={cx("flex items-center justify-between gap-2 px-4 py-3 text-sm hover:bg-zinc-50 dark:hover:bg-zinc-800/40", focusRing)}
              >
                <span>
                  <span className="font-medium">{FIELD_LABELS[p.field_name]}</span>
                  <span className="block text-xs text-zinc-500">{formatDateTime(p.created_at)}</span>
                </span>
                <StatusBadge status={p.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function ContentDetail() {
  const { id } = useParams<{ id: string }>();
  const { data, error, reload } = useApi(`content-detail:${id}`, (signal) => api.getContent(id, signal));

  if (error) {
    return (
      <>
        <PageHeader title="Page not available" breadcrumb={{ href: "/", label: "Content library" }} />
        <ErrorState message={error} onRetry={error.includes("not found") ? undefined : reload} />
      </>
    );
  }
  if (!data) return <LoadingState label="Loading page…" rows={6} />;

  return (
    <>
      <PageHeader
        breadcrumb={{ href: "/", label: "Content library" }}
        title={data.title}
        description={
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs">{data.id}</span>
            <StatusBadge status={data.status} />
            <Badge>{CATEGORY_LABELS[data.category]}</Badge>
            <span className="text-sm">Updated {formatDate(data.updated_at)}</span>
          </span>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <Card aria-labelledby="body-heading">
          <h2 id="body-heading" className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold dark:border-zinc-800">
            Body content
          </h2>
          {data.content.trim() ? (
            // Rendered as plain text on purpose: CMS content is untrusted and never interpreted as HTML.
            <div className="px-4 py-4 text-sm leading-relaxed whitespace-pre-wrap">{data.content}</div>
          ) : (
            <EmptyState title="This page has no body content." />
          )}
        </Card>

        <div className="space-y-6">
          <Card aria-labelledby="meta-heading">
            <h2 id="meta-heading" className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold dark:border-zinc-800">
              Metadata
            </h2>
            <dl className="divide-y divide-zinc-200 px-4 dark:divide-zinc-800">
              <Field label="Meta title" extra={<CharCount value={data.meta_title} max={META_TITLE_MAX} />}>
                {data.meta_title?.trim() ? data.meta_title : <Empty />}
              </Field>
              <Field
                label="Meta description"
                extra={<CharCount value={data.meta_description} max={META_DESCRIPTION_MAX} />}
              >
                {data.meta_description?.trim() ? data.meta_description : <Empty />}
              </Field>
              <Field label="Slug">
                <span className="font-mono text-xs">/{data.slug}</span>
              </Field>
              <Field label="Canonical URL">
                {data.canonical_url ? <span className="font-mono text-xs">{data.canonical_url}</span> : <Empty />}
              </Field>
              <Field label="Tags">
                {data.tags.length ? (
                  <span className="flex flex-wrap gap-1">
                    {data.tags.map((t) => (
                      <Badge key={t}>{t}</Badge>
                    ))}
                  </span>
                ) : (
                  <Empty />
                )}
              </Field>
              <Field label="Created">{formatDateTime(data.created_at)}</Field>
              <Field label="Last updated">{formatDateTime(data.updated_at)}</Field>
            </dl>
          </Card>
          <RelatedProposals contentId={data.id} />
        </div>
      </div>
    </>
  );
}
