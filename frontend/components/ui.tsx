import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

export function cx(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

export const focusRing =
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600";

// ---- Buttons ----------------------------------------------------------------

type Variant = "primary" | "secondary" | "danger" | "ghost";

const variantClasses: Record<Variant, string> = {
  primary: "bg-blue-700 text-white hover:bg-blue-800 disabled:bg-blue-700/50",
  secondary:
    "border border-zinc-300 bg-white text-zinc-900 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:hover:bg-zinc-800",
  danger: "bg-red-700 text-white hover:bg-red-800 disabled:bg-red-700/50",
  ghost: "text-zinc-700 hover:bg-zinc-100 dark:text-zinc-300 dark:hover:bg-zinc-800",
};

export function buttonClasses(variant: Variant = "secondary", size: "sm" | "md" = "md") {
  return cx(
    "inline-flex items-center justify-center gap-2 rounded-md font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60",
    size === "sm" ? "px-2.5 py-1 text-sm" : "px-3.5 py-2 text-sm",
    variantClasses[variant],
    focusRing,
  );
}

export function Button({
  variant = "secondary",
  size = "md",
  className,
  ...props
}: ComponentProps<"button"> & { variant?: Variant; size?: "sm" | "md" }) {
  return <button type="button" className={cx(buttonClasses(variant, size), className)} {...props} />;
}

// ---- Badges -----------------------------------------------------------------

type Tone = "neutral" | "green" | "amber" | "red" | "blue" | "violet";

const toneClasses: Record<Tone, string> = {
  neutral: "bg-zinc-100 text-zinc-700 ring-zinc-300 dark:bg-zinc-800 dark:text-zinc-300 dark:ring-zinc-700",
  green: "bg-emerald-50 text-emerald-800 ring-emerald-600/30 dark:bg-emerald-950 dark:text-emerald-300",
  amber: "bg-amber-50 text-amber-800 ring-amber-600/30 dark:bg-amber-950 dark:text-amber-300",
  red: "bg-red-50 text-red-800 ring-red-600/30 dark:bg-red-950 dark:text-red-300",
  blue: "bg-blue-50 text-blue-800 ring-blue-600/30 dark:bg-blue-950 dark:text-blue-300",
  violet: "bg-violet-50 text-violet-800 ring-violet-600/30 dark:bg-violet-950 dark:text-violet-300",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ring-1 ring-inset",
        toneClasses[tone],
      )}
    >
      {children}
    </span>
  );
}

const statusTones: Record<string, Tone> = {
  published: "green",
  draft: "amber",
  archived: "neutral",
  pending: "amber",
  approved: "green",
  rejected: "neutral",
  ok: "green",
  conflict: "red",
  error: "red",
  timeout: "red",
  invalid_arguments: "red",
  unknown_tool: "red",
  not_found: "amber",
  output_too_large: "red",
};

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={statusTones[status] ?? "neutral"}>{status.replaceAll("_", " ")}</Badge>;
}

// ---- Layout pieces ----------------------------------------------------------

export function Card({ className, ...props }: ComponentProps<"section">) {
  return (
    <section
      className={cx(
        "rounded-lg border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900",
        className,
      )}
      {...props}
    />
  );
}

export function PageHeader({
  title,
  description,
  actions,
  breadcrumb,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  breadcrumb?: { href: string; label: string };
}) {
  return (
    <header className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        {breadcrumb && (
          <Link
            href={breadcrumb.href}
            className={cx("mb-2 inline-block text-sm text-blue-700 hover:underline dark:text-blue-400", focusRing)}
          >
            ← {breadcrumb.label}
          </Link>
        )}
        <h1 className="text-2xl font-semibold tracking-tight break-words">{title}</h1>
        {description && <p className="mt-1 text-zinc-600 dark:text-zinc-400">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

// ---- States -----------------------------------------------------------------

export function LoadingState({ label = "Loading…", rows = 5 }: { label?: string; rows?: number }) {
  return (
    <div role="status" aria-live="polite" className="space-y-3 p-4">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} aria-hidden="true" className="h-10 animate-pulse rounded bg-zinc-100 dark:bg-zinc-800" />
      ))}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="flex flex-col items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200"
    >
      <p className="font-medium">{message}</p>
      {onRetry && (
        <Button size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 px-4 py-12 text-center">
      <p className="font-medium">{title}</p>
      {children && <div className="max-w-md text-sm text-zinc-600 dark:text-zinc-400">{children}</div>}
    </div>
  );
}

// ---- Form controls ----------------------------------------------------------

export const inputClasses = cx(
  "block w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100",
  focusRing,
);

export function Pagination({
  total,
  limit,
  offset,
  onChange,
  label = "results",
}: {
  total: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
  label?: string;
}) {
  if (total === 0) return null;
  const from = offset + 1;
  const to = Math.min(offset + limit, total);
  return (
    <nav
      aria-label="Pagination"
      className="flex items-center justify-between gap-3 border-t border-zinc-200 px-4 py-3 text-sm dark:border-zinc-800"
    >
      <p className="text-zinc-600 dark:text-zinc-400">
        {from}–{to} of {total} {label}
      </p>
      <div className="flex gap-2">
        <Button size="sm" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>
          Previous
        </Button>
        <Button size="sm" disabled={to >= total} onClick={() => onChange(offset + limit)}>
          Next
        </Button>
      </div>
    </nav>
  );
}
