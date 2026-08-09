import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "StokVigil AI — Market Intelligence Watchtower",
  description: "Pure Factual Stock Alert System & Demat Intelligence Platform",
  manifest: "/manifest.json",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet" />
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#06B6D4" />
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
      </head>
      <body style={{ background: '#070913', color: '#f8fafc', fontFamily: "'Inter', sans-serif", minHeight: '100vh' }}>
        {children}
      </body>
    </html>
  );
}
