import type { Metadata } from "next";
import { Suspense } from "react";

import { ActivityLog } from "@/components/activity/ActivityLog";
import { LoadingState, PageHeader } from "@/components/ui";

export const metadata: Metadata = { title: "Activity" };

export default function ActivityPage() {
  return (
    <>
      <PageHeader
        title="Activity log"
        description="Every tool call, proposal, approval, rejection, and assistant error, newest first. Secrets are redacted."
      />
      <Suspense fallback={<LoadingState label="Loading activity…" />}>
        <ActivityLog />
      </Suspense>
    </>
  );
}
