import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CMS Content Assistant",
  description: "Local, human-in-the-loop content audit assistant for a simulated headless CMS.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
