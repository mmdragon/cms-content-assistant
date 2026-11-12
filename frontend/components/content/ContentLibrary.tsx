"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { api } from "@/lib/api";
import { CATEGORY_LABELS, formatDate } from "@/lib/format";
import { useApi } from "@/lib/useApi";
import {
  CATEGORIES,
  CONTENT_SORTS,
  CONTENT_STATUSES,
  type Category,
  type ContentQuery,
  type ContentSort,
  type ContentStatus,
} from "@/types/api";

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

const PAGE_SIZE = 20;

const SORT_LABELS: Record<ContentSort, string> = {
  updated_desc: "Recently updated",
  updated_asc: "Least recently updated",
  title_asc: "Title A–Z",
};

function pick<T extends string>(value: string | null, allowed: readonly T[]): T | undefined {
  return allowed.includes(value as T) ? (value as T) : undefined;
}

export function useContentQuery(): ContentQuery {
  const params = useSearchParams();
  const offset = Number.parseInt(params.get("offset") ?? "0", 10);
  return {
    q: params.get("q")?.trim() || undefined,
    category: pick<Category>(params.get("category"), CATEGORIES),
    status: pick<ContentStatus>(params.get("status"), CONTENT_STATUSES),
    sort: pick<ContentSort>(params.get("sort"), CONTENT_SORTS),
    offset: Number.isFinite(offset) && offset > 0 ? offset : 0,
    limit: PAGE_SIZE,
  };
}

function SearchForm({ initial, onSearch }: { initial: string; onSearch: (q: string) => void }) {
  const [value, setValue] = useState(initial);
  return (
    <form
      role="search"
      className="flex flex-1 gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        onSearch(value);
      }}
    >
      <label htmlFor="content-search" className="sr-only">
        Search content
      </label>
      <input
        id="content-search"
        type="search"
        value={value}
        maxLength={200}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Search titles, body text, metadata, tags…"
        className={inputClasses}
      />
      <Button type="submit" variant="primary">
        Search
      </Button>
    </form>
  );
}

function FilterSelect<T extends string>({
  id,
  label,
  value,
  options,
  allLabel,
  optionLabel,
  onChange,
}: {
  id: string;
  label: string;
  value: T | undefined;
  options: readonly T[];
  allLabel?: string;
  optionLabel: (v: T) => string;
  onChange: (v: T | undefined) => void;
}) {
  return (
    <div className="min-w-0">
      <label htmlFor={id} className="mb-1 block text-xs font-medium text-zinc-600 dark:text-zinc-400">
        {label}
      </label>
      <select
        id={id}
        value={value ?? ""}
        onChange={(e) => onChange((e.target.value || undefined) as T | undefined)}
        className={inputClasses}
      >
        {allLabel && <option value="">{allLabel}</option>}
        {options.map((o) => (
          <option key={o} value={o}>
            {optionLabel(o)}
          </option>
        ))}
      </select>
    </div>
  );
}

export function ContentLibrary() {
  const router = useRouter();
  const pathname = usePathname();
  const query = useContentQuery();
  const queryKey = JSON.stringify(query);
  const { data, error, loading, reload } = useApi(`content:${queryKey}`, (signal) => api.listContent(query, signal));

  const update = (changes: Partial<ContentQuery>) => {
    const next = { ...query, ...changes };
    // Any filter change returns to the first page.
    if (!("offset" in changes)) next.offset = 0;
    const params = new URLSearchParams();
    if (next.q) params.set("q", next.q);
    if (next.category) params.set("category", next.category);
    if (next.status) params.set("status", next.status);
    if (next.sort && next.sort !== "updated_desc") params.set("sort", next.sort);
    if (next.offset) params.set("offset", String(next.offset));
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  };

  const hasFilters = Boolean(query.q || query.category || query.status);

  return (
    <div className="space-y-4">
      <Card className="space-y-3 p-4">
        <SearchForm key={query.q ?? ""} initial={query.q ?? ""} onSearch={(q) => update({ q: q.trim() || undefined })} />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <FilterSelect
            id="filter-category"
            label="Category"
            value={query.category}
            options={CATEGORIES}
            allLabel="All categories"
            optionLabel={(c) => CATEGORY_LABELS[c]}
            onChange={(category) => update({ category })}
          />
          <FilterSelect
            id="filter-status"
            label="Status"
            value={query.status}
            options={CONTENT_STATUSES}
            allLabel="All statuses"
            optionLabel={(s) => s[0].toUpperCase() + s.slice(1)}
            onChange={(status) => update({ status })}
          />
          <FilterSelect
            id="filter-sort"
            label="Sort by"
            value={query.sort ?? "updated_desc"}
            options={CONTENT_SORTS}
            optionLabel={(s) => SORT_LABELS[s]}
            onChange={(sort) => update({ sort })}
          />
        </div>
      </Card>

      <Card aria-labelledby="results-heading">
        <div className="flex items-center justify-between gap-2 border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
          <h2 id="results-heading" className="text-sm font-semibold">
            {data ? `${data.total} ${data.total === 1 ? "page" : "pages"}` : "Pages"}
            {query.q && <span className="font-normal text-zinc-500"> matching “{query.q}”</span>}
          </h2>
          {hasFilters && (
            <Button size="sm" variant="ghost" onClick={() => router.replace(pathname, { scroll: false })}>
              Clear filters
            </Button>
          )}
        </div>

        {error ? (
          <div className="p-4">
            <ErrorState message={error} onRetry={reload} />
          </div>
        ) : !data ? (
          <LoadingState label="Loading content…" />
        ) : data.items.length === 0 ? (
          <EmptyState title="No pages match">
            Try a different search term or clear the filters.
          </EmptyState>
        ) : (
          <div className={cx("overflow-x-auto transition-opacity", loading && "opacity-60")} aria-busy={loading}>
            <table className="w-full text-left text-sm">
              <caption className="sr-only">Content pages</caption>
              <thead className="bg-zinc-50 text-xs text-zinc-600 uppercase dark:bg-zinc-900/60 dark:text-zinc-400">
                <tr>
                  <th scope="col" className="px-4 py-2 font-medium">Title</th>
                  <th scope="col" className="hidden px-4 py-2 font-medium md:table-cell">Category</th>
                  <th scope="col" className="px-4 py-2 font-medium">Status</th>
                  <th scope="col" className="hidden px-4 py-2 font-medium whitespace-nowrap sm:table-cell">Updated</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
                {data.items.map((item) => (
                  <tr key={item.id} className="align-top hover:bg-zinc-50 dark:hover:bg-zinc-800/40">
                    <td className="max-w-xl px-4 py-3">
                      <Link
                        href={`/content/${item.id}`}
                        className={cx("font-medium text-blue-700 hover:underline dark:text-blue-400", focusRing)}
                      >
                        {item.title}
                      </Link>
                      <p className="mt-0.5 font-mono text-xs text-zinc-500">
                        {item.id} · /{item.slug}
                      </p>
                      <p className="mt-1 line-clamp-2 text-zinc-600 dark:text-zinc-400">{item.excerpt}</p>
                    </td>
                    <td className="hidden px-4 py-3 md:table-cell">
                      <Badge>{CATEGORY_LABELS[item.category]}</Badge>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={item.status} />
                    </td>
                    <td className="hidden px-4 py-3 whitespace-nowrap text-zinc-600 sm:table-cell dark:text-zinc-400">
                      <time dateTime={item.updated_at}>{formatDate(item.updated_at)}</time>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data && (
          <Pagination
            total={data.total}
            limit={data.limit}
            offset={data.offset}
            label="pages"
            onChange={(offset) => update({ offset })}
          />
        )}
      </Card>
    </div>
  );
}
