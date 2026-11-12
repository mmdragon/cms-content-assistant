import { HealthStatus } from "@/components/HealthStatus";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-4 py-12">
      <header>
        <p className="text-sm font-medium text-blue-700 dark:text-blue-400">Northstar Living</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">CMS Content Assistant</h1>
        <p className="mt-2 text-zinc-600 dark:text-zinc-400">
          Search content, find stale or broken pages, and review AI-proposed edits. Nothing is
          changed without your approval.
        </p>
      </header>
      <HealthStatus />
    </main>
  );
}
