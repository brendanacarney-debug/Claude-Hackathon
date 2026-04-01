import { hazardAccent } from "@/lib/results";
import type { Hazard, Recommendation } from "@/lib/types";

export function HazardCard({
  hazard,
  recommendation,
}: {
  hazard: Hazard;
  recommendation?: Recommendation;
}) {
  const accent = hazardAccent(hazard.severity);

  return (
    <article
      className="glass-card rounded-[1.6rem] p-5"
      style={{ borderLeftWidth: 6, borderLeftColor: accent }}
    >
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span
          className="rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-[0.18em] uppercase"
          style={{
            backgroundColor:
              hazard.severity === "urgent"
                ? "rgba(239,68,68,0.12)"
                : hazard.severity === "moderate"
                  ? "rgba(245,158,11,0.12)"
                  : "rgba(16,185,129,0.12)",
            color: accent,
          }}
        >
          {hazard.severity}
        </span>
        <span className="text-sm text-[var(--app-muted)]">
          {hazard.class.replace(/_/g, " ")}
        </span>
      </div>
      <p className="text-base leading-7 text-[var(--app-ink)]">{hazard.explanation}</p>
      {recommendation ? (
        <div className="mt-4 rounded-2xl bg-[var(--panel-soft)] p-4">
          <p className="text-sm font-semibold text-[var(--accent-blue)]">
            Recommendation
          </p>
          <p className="mt-2 text-sm leading-6 text-[var(--app-ink)]">
            {recommendation.text}
          </p>
          <p className="mt-3 text-xs leading-5 text-[var(--app-muted)]">
            Benefit: {recommendation.expected_benefit}
          </p>
        </div>
      ) : null}
    </article>
  );
}
