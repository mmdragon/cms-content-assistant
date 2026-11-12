import { Suspense } from "react";

import { ContentLibrary } from "@/components/content/ContentLibrary";
import { LoadingState, PageHeader } from "@/components/ui";

export default function ContentPage() {
  return (
    <>
      <PageHeader
        title="Content library"
        description="Search and filter every page in the Northstar Living site. Nothing changes without your approval."
      />
      <Suspense fallback={<LoadingState label="Loading content…" />}>
        <ContentLibrary />
      </Suspense>
    </>
  );
}
