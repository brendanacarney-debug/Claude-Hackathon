import type { Metadata } from "next";
import Link from "next/link";
import { IBM_Plex_Mono, Manrope } from "next/font/google";
import "./globals.css";

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
});

const plexMono = IBM_Plex_Mono({
  variable: "--font-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "HomeRecover Scan",
  description:
    "3D room safety visualization for recovery-at-home planning after discharge.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${manrope.variable} ${plexMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-[var(--app-bg)] text-[var(--app-ink)]">
        <div className="absolute inset-x-0 top-0 -z-10 h-[28rem] bg-[radial-gradient(circle_at_top,_rgba(37,99,235,0.16),_transparent_62%)]" />
        <div className="absolute inset-x-0 top-32 -z-10 h-[24rem] bg-[linear-gradient(180deg,_rgba(244,244,245,0.96),_rgba(248,250,252,0.4),_transparent)]" />
        <div className="min-h-full">
          <header className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-5 md:px-10">
            <Link
              className="inline-flex items-center gap-3 text-sm font-semibold tracking-[0.18em] text-[var(--app-ink)] uppercase"
              href="/"
            >
              <span className="flex h-10 w-10 items-center justify-center rounded-2xl border border-[var(--app-line)] bg-white/80 text-[var(--accent-blue)] shadow-[0_14px_40px_-24px_rgba(15,23,42,0.55)]">
                HR
              </span>
              <span>HomeRecover Scan</span>
            </Link>
            <nav className="hidden items-center gap-4 text-sm text-[var(--app-muted)] md:flex">
              <Link className="transition hover:text-[var(--app-ink)]" href="/demo">
                Demo
              </Link>
              <Link
                className="transition hover:text-[var(--app-ink)]"
                href="/scan/profile"
              >
                Start Scan
              </Link>
            </nav>
          </header>
          <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-6 pb-12 md:px-10">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
