"use client";

import { motion } from "framer-motion";

export default function Home() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: "easeOut" }}
      className="grid flex-1 items-center gap-12 py-10 md:grid-cols-[1.05fr_0.95fr] md:py-16"
    >
      <div className="space-y-8">
        <div className="inline-flex items-center gap-3 rounded-full border border-[var(--app-line)] bg-white/90 px-4 py-2 text-xs font-semibold tracking-[0.18em] text-[var(--app-muted)] uppercase shadow-[0_18px_40px_-28px_rgba(15,23,42,0.45)]">
          <span className="h-2.5 w-2.5 rounded-full bg-[var(--accent-safe)]" />
          Recovery-Ready Home Scan
        </div>
        <div className="space-y-5">
          <h1 className="max-w-3xl text-5xl leading-[1.02] font-semibold tracking-[-0.045em] text-balance text-[var(--app-ink)] md:text-7xl">
            Prepare the home before the first walk to the bathroom.
          </h1>
          <p className="max-w-2xl text-lg leading-8 text-[var(--app-muted)] md:text-xl">
            Scan the bedroom-to-bathroom route, then turn the results into a clear
            safety plan with hazard scoring, safe-path guidance, and a 3D room
            visualization caregivers can act on right away.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <a
            className="inline-flex h-14 items-center justify-center rounded-full bg-[var(--accent-blue)] px-7 text-sm font-semibold text-white shadow-[0_22px_40px_-24px_rgba(37,99,235,0.9)] transition hover:-translate-y-0.5 hover:bg-[#1d4ed8]"
            href="/scan/profile"
          >
            Start Scan
          </a>
          <a
            className="inline-flex h-14 items-center justify-center rounded-full border border-[var(--app-line)] bg-white/85 px-7 text-sm font-semibold text-[var(--app-ink)] transition hover:-translate-y-0.5 hover:border-[var(--accent-blue)] hover:text-[var(--accent-blue)]"
            href="/demo"
          >
            Open Demo
          </a>
        </div>
        <p className="max-w-xl text-sm leading-6 text-[var(--app-muted)]">
          Environmental guidance only. This tool does not replace discharge
          instructions, occupational therapy advice, or clinical judgment.
        </p>
      </div>

      <div className="grid gap-4 md:justify-self-end">
        <div className="rounded-[2rem] border border-[var(--app-line)] bg-white/92 p-6 shadow-[0_30px_60px_-34px_rgba(15,23,42,0.35)]">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold tracking-[0.18em] text-[var(--app-muted)] uppercase">
                Demo Outcome
              </p>
              <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em]">
                High-risk route identified
              </h2>
            </div>
            <div className="rounded-2xl bg-[rgba(239,68,68,0.12)] px-3 py-2 text-sm font-semibold text-[var(--accent-urgent)]">
              3 urgent
            </div>
          </div>
          <div className="grid gap-3">
            <div className="rounded-2xl bg-[var(--panel-soft)] p-4">
              <p className="text-sm font-semibold text-[var(--app-ink)]">
                Bed to bathroom safe-path width
              </p>
              <p className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-[var(--accent-urgent)]">
                68 cm
              </p>
              <p className="mt-2 text-sm text-[var(--app-muted)]">
                Below the 90 cm walker clearance target for the selected profile.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-[var(--app-line)] p-4">
                <p className="text-xs font-semibold tracking-[0.16em] text-[var(--app-muted)] uppercase">
                  Hazard
                </p>
                <p className="mt-3 text-sm leading-6 text-[var(--app-ink)]">
                  Loose rug on the direct night route
                </p>
              </div>
              <div className="rounded-2xl border border-[var(--app-line)] p-4">
                <p className="text-xs font-semibold tracking-[0.16em] text-[var(--app-muted)] uppercase">
                  Recommendation
                </p>
                <p className="mt-3 text-sm leading-6 text-[var(--app-ink)]">
                  Remove the rug and move the chair to the far wall
                </p>
              </div>
              <div className="rounded-2xl border border-[var(--app-line)] p-4">
                <p className="text-xs font-semibold tracking-[0.16em] text-[var(--app-muted)] uppercase">
                  Viewer
                </p>
                <p className="mt-3 text-sm leading-6 text-[var(--app-ink)]">
                  3D overlay with hazards, safe path, and ghost moves
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.section>
  );
}
