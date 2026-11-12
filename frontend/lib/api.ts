import type { HealthResponse } from "@/types/api";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const DEFAULT_TIMEOUT_MS = 5000;

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const timeout = AbortSignal.timeout(DEFAULT_TIMEOUT_MS);
  const combined = signal ? AbortSignal.any([signal, timeout]) : timeout;

  let response: Response;
  try {
    response = await fetch(path, { signal: combined, cache: "no-store" });
  } catch (err) {
    if (err instanceof DOMException && err.name === "TimeoutError") {
      throw new ApiError("The backend did not respond in time.");
    }
    throw err;
  }

  if (!response.ok) {
    // Requests go through the Next.js proxy, so a stopped backend shows up as a 5xx here.
    const message =
      response.status >= 500
        ? `The backend is unavailable (HTTP ${response.status}). Is it running on port 8000?`
        : `Request failed with status ${response.status}.`;
    throw new ApiError(message, response.status);
  }
  return (await response.json()) as T;
}

export function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return getJson<HealthResponse>("/api/health", signal);
}
