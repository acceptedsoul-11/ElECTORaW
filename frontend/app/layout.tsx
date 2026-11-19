import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "ELECTORaW · Election intelligence",
  description: "A grounded, source-aware view of India's 2014, 2019 and 2024 Lok Sabha elections.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en-IN"><body>{children}<Link href="/login" className="global-access">Access ↗</Link></body></html>;
}
