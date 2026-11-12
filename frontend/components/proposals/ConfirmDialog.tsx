"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";

import { Button, inputClasses } from "../ui";

/**
 * Modal confirmation built on the native <dialog> element (focus trap, Esc to close,
 * and focus restoration come from the browser).
 */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  confirmVariant,
  busy,
  error,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  description: ReactNode;
  confirmLabel: string;
  confirmVariant: "primary" | "danger";
  busy: boolean;
  error?: string;
  onConfirm: (note: string) => void;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [note, setNote] = useState("");
  const titleId = useId();
  const noteId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onClose={onClose}
      onCancel={(e) => {
        if (busy) e.preventDefault();
      }}
      className="m-auto w-[min(32rem,calc(100vw-2rem))] rounded-lg border border-zinc-200 bg-white p-0 text-zinc-900 shadow-xl backdrop:bg-black/40 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-100"
    >
      <form
        method="dialog"
        className="space-y-4 p-5"
        onSubmit={(e) => {
          e.preventDefault();
          onConfirm(note);
        }}
      >
        <h2 id={titleId} className="text-lg font-semibold">
          {title}
        </h2>
        <div className="text-sm text-zinc-600 dark:text-zinc-400">{description}</div>
        <div>
          <label htmlFor={noteId} className="mb-1 block text-sm font-medium">
            Note <span className="font-normal text-zinc-500">(optional, saved to the activity log)</span>
          </label>
          <textarea
            id={noteId}
            value={note}
            maxLength={500}
            rows={3}
            onChange={(e) => setNote(e.target.value)}
            className={inputClasses}
          />
        </div>
        {error && (
          <p role="alert" className="rounded-md bg-red-50 p-3 text-sm text-red-800 dark:bg-red-950 dark:text-red-200">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button type="submit" variant={confirmVariant} disabled={busy} aria-busy={busy}>
            {busy ? "Working…" : confirmLabel}
          </Button>
        </div>
      </form>
    </dialog>
  );
}
