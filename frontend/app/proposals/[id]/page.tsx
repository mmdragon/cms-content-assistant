import { Suspense } from "react";

import { ProposalReview } from "@/components/proposals/ProposalReview";
import { LoadingState } from "@/components/ui";

export default function ProposalReviewPage() {
  return (
    <Suspense fallback={<LoadingState label="Loading proposal…" rows={6} />}>
      <ProposalReview />
    </Suspense>
  );
}
