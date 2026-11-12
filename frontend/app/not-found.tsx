import Link from "next/link";

import { PageHeader, buttonClasses } from "@/components/ui";

export default function NotFound() {
  return (
    <>
      <PageHeader title="Page not found" description="That address doesn't match any screen in this app." />
      <Link href="/" className={buttonClasses("primary")}>
        Back to the content library
      </Link>
    </>
  );
}
