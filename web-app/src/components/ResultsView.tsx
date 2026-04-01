"use client";

import Link from "next/link";
import { useState } from "react";

import { ChecklistPanel } from "@/components/ChecklistPanel";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { HazardCard } from "@/components/HazardCard";
import { RiskBadge } from "@/components/RiskBadge";
import { RoomViewer3D } from "@/components/RoomViewer3D";
import { ToggleButton } from "@/components/ToggleButton";
import {
  describeRoute,
  formatProfileLabel,
  recommendationMap,
  sortHazards,
} from "@/lib/results";
import type { Session } from "@/lib/types";

export function ResultsView({ session }: { session: Session }) {
  const [showHazards, setShowHazards] = useState(true);
  const [showSafePath, setShowSafePath] = useState(true);
  const [showRearrangements, setShowRearrangements] = useState(true);
  const [shareState, setShareState] = useState<"idle" | "copied" | "failed">("idle");

  const recommendations = recommendationMap(session.recommendations);
  const sortedHazards = sortHazards(session.hazards, session.recommendations);
  const scanDate = new Date(session.created_at).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  async function handleShare() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setShareState("copied");
    } catch {
      setShareState("failed");
    } finally {
      window.setTimeout(() => setShareState("idle"), 1800);
    }
  }

  return (
    <section className="space-y-8 py-6">
      <header className="glass-card rounded-[2rem] p-6 md:p-8">
        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div className="space-y-4">
            <RiskBadge session={session} />
            <div>
              <h1 className="text-3xl font-semibold tracking-[-0.04em] text-[var(--app-ink)] md:text-4xl">
                Spatial safety review
              </h1>
              <p className="mt-3 max-w-2xl text-base leading-7 text-[var(--app-muted)]">
                Profile: {formatProfileLabel(session.recovery_profile)}. Scanned
                route: {describeRoute(session)}. Generated {scanDate}.
              </p>
            </div>
          </div>
          <div className="rounded-[1.6rem] bg-[var(--panel-soft)] px-5 py-4 text-sm leading-6 text-[var(--app-muted)]">
            <p className="font-semibold text-[var(--app-ink)]">Safe-path clearance</p>
            <p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-[var(--accent-blue)]">
              {(session.safe_path.min_width_m * 100).toFixed(0)} cm
            </p>
            <p className="mt-2">
              {session.safe_path.width_ok
                ? "Meets walker clearance target."
                : "Below the 90 cm walker clearance target."}
            </p>
          </div>
        </div>
      </header>

      <section className="glass-card rounded-[2rem] p-5 md:p-6">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-2xl font-semibold tracking-[-0.03em] text-[var(--app-ink)]">
              3D Room Viewer
            </h2>
            <p className="mt-2 text-sm leading-6 text-[var(--app-muted)]">
              Toggle hazards, the safe path, and suggested furniture changes to
              compare the current room with the recommended setup.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <ToggleButton
              active={showHazards}
              onClick={() => setShowHazards((value) => !value)}
              color="red"
            >
              Hazards
            </ToggleButton>
            <ToggleButton
              active={showSafePath}
              onClick={() => setShowSafePath((value) => !value)}
              color="green"
            >
              Safe Path
            </ToggleButton>
            <ToggleButton
              active={showRearrangements}
              onClick={() => setShowRearrangements((value) => !value)}
              color="blue"
            >
              Suggested Changes
            </ToggleButton>
          </div>
        </div>

        <RoomViewer3D
          session={session}
          showHazards={showHazards}
          showSafePath={showSafePath}
          showRearrangements={showRearrangements}
        />
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-[-0.03em] text-[var(--app-ink)]">
            Hazards and Recommendations
          </h2>
          <p className="mt-2 text-sm leading-6 text-[var(--app-muted)]">
            Items are ordered by severity first, then by the recommended action priority.
          </p>
        </div>
        <div className="grid gap-4 xl:grid-cols-2">
          {sortedHazards.map((hazard) => {
            const recommendation = hazard.recommendation_ids
              .map((recommendationId) => recommendations.get(recommendationId))
              .find(Boolean);

            return (
              <HazardCard
                key={hazard.hazard_id}
                hazard={hazard}
                recommendation={recommendation}
              />
            );
          })}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <ChecklistPanel
          title="Before tonight"
          items={session.checklist.first_night}
          storageKey={`${session.session_id}:first-night`}
        />
        <ChecklistPanel
          title="Within the first 48 hours"
          items={session.checklist.first_48_hours}
          storageKey={`${session.session_id}:first-48-hours`}
        />
      </section>

      <DisclaimerBanner>{session.disclaimer}</DisclaimerBanner>

      <div className="flex flex-col gap-3 sm:flex-row">
        <Link
          href={`/results/${session.session_id}/checklist`}
          target="_blank"
          rel="noreferrer"
          className="inline-flex h-12 items-center justify-center rounded-full bg-[var(--accent-blue)] px-6 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-[#1d4ed8]"
        >
          Print Checklist
        </Link>
        <button
          type="button"
          onClick={handleShare}
          className="inline-flex h-12 items-center justify-center rounded-full border border-[var(--app-line)] bg-white px-6 text-sm font-semibold text-[var(--app-ink)] transition hover:-translate-y-0.5"
        >
          {shareState === "copied"
            ? "Link copied"
            : shareState === "failed"
              ? "Copy failed"
              : "Share Link"}
        </button>
        <Link
          href="/"
          className="inline-flex h-12 items-center justify-center rounded-full border border-[var(--app-line)] bg-white px-6 text-sm font-semibold text-[var(--app-ink)] transition hover:-translate-y-0.5"
        >
          New Scan
        </Link>
      </div>
    </section>
  );
}
