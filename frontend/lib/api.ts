import type {
  ActivityEvent,
  ContentEntry,
  ContentQuery,
  ContentSummary,
  EventType,
  HealthResponse,
  Page,
  Proposal,
  ProposalStatus,
} from "@/types/api";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const DEFAULT_TIMEOUT_MS = 8000;

type QueryValue = string | number | undefined | null;

export function buildQuery(params: Record<string, QueryValue>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

function detailMessage(body: unknown): string | undefined {
  if (!body || typeof body !== "object" || !("detail" in body)) return undefined;
  const detail = (body as { detail: unknown }).detail;
  if (typeof detail === "string") return detail;
  // FastAPI validation errors: [{loc, msg, ...}]
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((d) => (d && typeof d === "object" && "msg" in d ? String(d.msg) : String(d)))
      .join("; ");
  }
  return undefined;
}

interface RequestOptions {
  method?: "GET" | "POST";
  body?: unknown;
  signal?: AbortSignal;
}

async function request<T>(path: string, { method = "GET", body, signal }: RequestOptions = {}) {
  const timeout = AbortSignal.timeout(DEFAULT_TIMEOUT_MS);
  const combined = signal ? AbortSignal.any([signal, timeout]) : timeout;

  let response: Response;
  try {
    response = await fetch(path, {
      method,
      signal: combined,
      cache: "no-store",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "TimeoutError") {
      throw new ApiError("The backend did not respond in time.");
    }
    throw err;
  }

  if (!response.ok) {
    const parsed: unknown = await response.json().catch(() => undefined);
    const detail = detailMessage(parsed);
    // Requests go through the Next.js proxy, so a stopped backend shows up as a 5xx here.
    const message =
      detail ??
      (response.status >= 500
        ? `The backend is unavailable (HTTP ${response.status}). Is it running on port 8000?`
        : `Request failed with status ${response.status}.`);
    throw new ApiError(message, response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  health: (signal?: AbortSignal) => request<HealthResponse>("/api/health", { signal }),

  listContent: (query: ContentQuery, signal?: AbortSignal) =>
    request<Page<ContentSummary>>(`/api/content${buildQuery({ ...query })}`, { signal }),

  getContent: (id: string, signal?: AbortSignal) =>
    request<ContentEntry>(`/api/content/${encodeURIComponent(id)}`, { signal }),

  listProposals: (
    params: { status?: ProposalStatus; content_id?: string; limit?: number; offset?: number },
    signal?: AbortSignal,
  ) => request<Page<Proposal>>(`/api/proposals${buildQuery(params)}`, { signal }),

  getProposal: (id: string, signal?: AbortSignal) =>
    request<Proposal>(`/api/proposals/${encodeURIComponent(id)}`, { signal }),

  approveProposal: (id: string, note?: string) =>
    request<Proposal>(`/api/proposals/${encodeURIComponent(id)}/approve`, {
      method: "POST",
      body: { note: note?.trim() || null },
    }),

  rejectProposal: (id: string, note?: string) =>
    request<Proposal>(`/api/proposals/${encodeURIComponent(id)}/reject`, {
      method: "POST",
      body: { note: note?.trim() || null },
    }),

  listActivity: (
    params: { event_type?: EventType; limit?: number; offset?: number },
    signal?: AbortSignal,
  ) => request<Page<ActivityEvent>>(`/api/activity${buildQuery(params)}`, { signal }),
};

// Kept for the existing health card.
export const fetchHealth = api.health;

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return "Could not reach the backend. Is it running on port 8000?";
}
