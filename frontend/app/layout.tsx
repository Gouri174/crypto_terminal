import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Crypto AI Terminal",
  description: "AI-ranked crypto trade setups. Analysis only, not financial advice.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
