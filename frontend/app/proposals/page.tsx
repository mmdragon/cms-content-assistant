import type { Metadata } from "next";
import { Suspense } from "react";

import { ProposalList } from "@/components/proposals/ProposalList";
import { LoadingState, PageHeader } from "@/components/ui";

export const metadata: Metadata = { title: "Proposals" };

export default function ProposalsPage() {
  return (
    <>
      <PageHeader
        title="Proposals"
        description="Edits drafted by the assistant. Nothing is applied until you approve it."
      />
      <Suspense fallback={<LoadingState label="Loading proposals…" />}>
        <ProposalList />
      </Suspense>
    </>
  );
}
