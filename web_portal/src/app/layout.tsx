import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "StokVigil AI — Market Intelligence Watchtower",
  description: "Pure Factual Stock Alert System & Demat Intelligence Platform",
  manifest: "/manifest.json",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#10B981" />
      </head>
      <body className="bg-darkBg text-gray-100 min-h-screen font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
