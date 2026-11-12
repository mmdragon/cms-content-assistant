import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { AppNav, AppNavFallback } from "@/components/AppNav";
import { AppStateProvider } from "@/components/AppState";
import { AssistantPanel, AssistantToggle } from "@/components/AssistantPanel";
import { HealthStatus } from "@/components/HealthStatus";
import { focusRing } from "@/components/ui";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "CMS Content Assistant", template: "%s · CMS Content Assistant" },
  description: "Local, human-in-the-loop content audit assistant for a simulated headless CMS.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <a
          href="#main"
          className={`sr-only z-50 rounded-md bg-white px-3 py-2 text-sm font-medium shadow focus:not-sr-only focus:fixed focus:top-2 focus:left-2 dark:bg-zinc-900 ${focusRing}`}
        >
          Skip to content
        </a>
        <AppStateProvider>
          <header className="sticky top-0 z-30 h-14 border-b border-zinc-200 bg-white/90 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/90">
            <div className="mx-auto flex h-full max-w-[96rem] items-center gap-2 px-3 sm:gap-3 sm:px-4">
              <Link href="/" className={`mr-2 hidden shrink-0 rounded-md md:block ${focusRing}`}>
                <span className="block text-[11px] leading-tight font-medium text-blue-700 dark:text-blue-400">
                  Northstar Living
                </span>
                <span className="block text-sm leading-tight font-semibold">Content Assistant</span>
              </Link>
              <Suspense fallback={<AppNavFallback />}>
                <AppNav />
              </Suspense>
              <div className="ml-auto flex shrink-0 items-center gap-1 sm:gap-2">
                <HealthStatus />
                <AssistantToggle />
              </div>
            </div>
          </header>
          <div className="mx-auto flex w-full max-w-[96rem] flex-1">
            <main id="main" tabIndex={-1} className="min-w-0 flex-1 px-4 py-6 outline-none sm:py-8">
              {children}
            </main>
            <AssistantPanel />
          </div>
        </AppStateProvider>
      </body>
    </html>
  );
}
