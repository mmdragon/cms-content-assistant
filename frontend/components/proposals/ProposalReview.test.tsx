import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, api } from "@/lib/api";
import type { ContentEntry, Proposal } from "@/types/api";

import { AppStateProvider } from "../AppState";
import { ProposalReview } from "./ProposalReview";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "prop-123456789abc" }),
}));

const ORIGINAL = "Homeowners can add the Northstar Classic plan.";

const proposal: Proposal = {
  id: "prop-123456789abc",
  content_id: "ns-036",
  field_name: "content",
  original_value: ORIGINAL,
  proposed_value: "Homeowners can add the Northstar Care plan.",
  rationale: "Northstar Classic was discontinued.",
  evidence_excerpt: "add the Northstar Classic plan",
  status: "pending",
  created_at: "2026-11-12T10:00:00Z",
  reviewed_at: null,
  review_note: null,
};

const entry: ContentEntry = {
  id: "ns-036",
  title: "Home Warranty",
  slug: "warranty",
  content: ORIGINAL,
  category: "landing",
  status: "published",
  created_at: "2023-07-01T15:00:00Z",
  updated_at: "2025-06-30T15:00:00Z",
  meta_title: "Home Warranty | Northstar Living",
  meta_description: "Warranty coverage.",
  canonical_url: "https://www.northstarliving.example/warranty",
  tags: [],
};

function renderReview() {
  return render(
    <AppStateProvider>
      <ProposalReview />
    </AppStateProvider>,
  );
}

beforeEach(() => {
  vi.spyOn(api, "getContent").mockResolvedValue(entry);
});

describe("ProposalReview", () => {
  it("shows rationale, evidence, and the page title", async () => {
    vi.spyOn(api, "getProposal").mockResolvedValue(proposal);
    renderReview();

    expect(await screen.findByRole("heading", { name: "Proposed edit: Body content" })).toBeTruthy();
    expect(screen.getByText("Northstar Classic was discontinued.")).toBeTruthy();
    expect(screen.getByText("add the Northstar Classic plan")).toBeTruthy();
    expect(await screen.findByRole("link", { name: "Home Warranty" })).toBeTruthy();
  });

  it("only applies a change after the editor confirms in the dialog", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "getProposal").mockResolvedValue(proposal);
    const approve = vi.spyOn(api, "approveProposal").mockResolvedValue({ ...proposal, status: "approved" });
    renderReview();

    await user.click(await screen.findByRole("button", { name: "Approve and apply" }));
    expect(approve).not.toHaveBeenCalled();

    const dialog = screen.getByRole("dialog", { name: "Apply this change?" });
    await user.type(screen.getByLabelText(/Note/), "Verified with product team");
    await user.click(
      screen.getAllByRole("button", { name: "Approve and apply" }).find((b) => dialog.contains(b)) as HTMLElement,
    );

    await waitFor(() => expect(approve).toHaveBeenCalledWith("prop-123456789abc", "Verified with product team"));
  });

  it("cancelling the dialog does not call the API", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "getProposal").mockResolvedValue(proposal);
    const reject = vi.spyOn(api, "rejectProposal");
    renderReview();

    await user.click(await screen.findByRole("button", { name: "Reject" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(reject).not.toHaveBeenCalled();
  });

  it("shows the server's conflict message inside the dialog", async () => {
    const user = userEvent.setup();
    vi.spyOn(api, "getProposal").mockResolvedValue(proposal);
    vi.spyOn(api, "approveProposal").mockRejectedValue(new ApiError("Proposal is already approved.", 409));
    renderReview();

    await user.click(await screen.findByRole("button", { name: "Approve and apply" }));
    const dialog = screen.getByRole("dialog");
    await user.click(
      screen.getAllByRole("button", { name: "Approve and apply" }).find((b) => dialog.contains(b)) as HTMLElement,
    );
    expect(await screen.findByText("Proposal is already approved.")).toBeTruthy();
  });

  it("disables approval when the page changed since the proposal was drafted", async () => {
    vi.spyOn(api, "getProposal").mockResolvedValue(proposal);
    vi.spyOn(api, "getContent").mockResolvedValue({ ...entry, content: "Edited by hand." });
    renderReview();

    expect(await screen.findByText(/changed after the proposal was drafted/)).toBeTruthy();
    expect((screen.getByRole("button", { name: "Approve and apply" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("hides review actions once a proposal has been decided", async () => {
    vi.spyOn(api, "getProposal").mockResolvedValue({
      ...proposal,
      status: "rejected",
      reviewed_at: "2026-11-12T11:00:00Z",
      review_note: "Not now",
    });
    renderReview();

    expect(await screen.findByText("Not now")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Approve and apply" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Reject" })).toBeNull();
  });
});
