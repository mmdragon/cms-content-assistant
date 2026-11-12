import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, api, buildQuery, errorMessage } from "./api";

function mockFetch(status: number, body?: unknown) {
  const fn = vi.fn().mockResolvedValue(
    new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => vi.unstubAllGlobals());

describe("buildQuery", () => {
  it("drops empty values and encodes the rest", () => {
    expect(buildQuery({ q: "Northstar Classic", category: undefined, status: "", offset: 0, limit: 20 })).toBe(
      "?q=Northstar+Classic&offset=0&limit=20",
    );
    expect(buildQuery({})).toBe("");
  });
});

describe("api", () => {
  it("lists content with filters as query params", async () => {
    const fetchFn = mockFetch(200, { items: [], total: 0, limit: 20, offset: 0 });
    await api.listContent({ q: "warranty", category: "faq", limit: 20 });
    expect(fetchFn.mock.calls[0][0]).toBe("/api/content?q=warranty&category=faq&limit=20");
  });

  it("approves with a POST and a JSON note", async () => {
    const fetchFn = mockFetch(200, { id: "prop-123456789abc", status: "approved" });
    await api.approveProposal("prop-123456789abc", "  looks good  ");
    const [url, init] = fetchFn.mock.calls[0];
    expect(url).toBe("/api/proposals/prop-123456789abc/approve");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ note: "looks good" });
  });

  it("sends a null note when none is given on reject", async () => {
    const fetchFn = mockFetch(200, { id: "prop-123456789abc", status: "rejected" });
    await api.rejectProposal("prop-123456789abc");
    expect(JSON.parse(fetchFn.mock.calls[0][1].body)).toEqual({ note: null });
  });

  it("surfaces the backend's detail message on conflicts", async () => {
    mockFetch(409, { detail: "Proposal 'prop-1' is already approved.", code: "conflict" });
    const err = await api.approveProposal("prop-1").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(409);
    expect((err as ApiError).message).toBe("Proposal 'prop-1' is already approved.");
  });

  it("joins FastAPI validation messages", async () => {
    mockFetch(422, { detail: [{ msg: "Input should be greater than 0" }, { msg: "Extra inputs are not permitted" }] });
    await expect(api.listContent({ limit: 0 })).rejects.toThrow(
      "Input should be greater than 0; Extra inputs are not permitted",
    );
  });

  it("explains a stopped backend behind the proxy", async () => {
    mockFetch(500);
    await expect(api.health()).rejects.toThrow(/backend is unavailable \(HTTP 500\)/);
  });

  it("gives a friendly message for network failures", () => {
    expect(errorMessage(new TypeError("Failed to fetch"))).toMatch(/Could not reach the backend/);
  });
});
