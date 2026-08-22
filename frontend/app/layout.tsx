import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI DevOps Configuration Reviewer",
  description: "Find risks in DevOps configuration before production.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
