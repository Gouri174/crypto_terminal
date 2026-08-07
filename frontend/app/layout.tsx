import type { Metadata } from "next";
import Link from "next/link";
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
      <body>
        <nav className="border-b border-border px-6 py-3 flex items-center gap-6 text-sm">
          <span className="font-bold text-gray-200">Crypto AI Terminal</span>
          <Link href="/" className="text-gray-400 hover:text-gray-100">
            Dashboard
          </Link>
          <Link href="/assistant" className="text-gray-400 hover:text-gray-100">
            AI Assistant
          </Link>
        </nav>
        {children}
      </body>
    </html>
  );
}
