import { Suspense } from "react";

import { ContentDetail } from "@/components/content/ContentDetail";
import { LoadingState } from "@/components/ui";

export default function ContentDetailPage() {
  return (
    <Suspense fallback={<LoadingState label="Loading page…" rows={6} />}>
      <ContentDetail />
    </Suspense>
  );
}
