import { summarizeRisk } from "@/lib/results";
import type { Session } from "@/lib/types";

const palette = {
  urgent: {
    badge: "bg-[rgba(239,68,68,0.14)] text-[var(--accent-urgent)]",
    dot: "bg-[var(--accent-urgent)]",
  },
  moderate: {
    badge: "bg-[rgba(245,158,11,0.14)] text-[var(--accent-warning)]",
    dot: "bg-[var(--accent-warning)]",
  },
  low: {
    badge: "bg-[rgba(16,185,129,0.14)] text-[var(--accent-safe)]",
    dot: "bg-[var(--accent-safe)]",
  },
} as const;

export function RiskBadge({ session }: { session: Session }) {
  const risk = summarizeRisk(session);
  const colors = palette[risk.tone];
  const primaryCount =
    risk.tone === "urgent"
      ? risk.urgentCount
      : risk.tone === "moderate"
        ? risk.moderateCount
        : risk.lowCount;

  return (
    <div className="inline-flex items-center gap-3 rounded-full border border-[var(--app-line)] bg-white px-4 py-3 shadow-[0_18px_40px_-28px_rgba(15,23,42,0.45)]">
      <span className={`h-3 w-3 rounded-full ${colors.dot}`} />
      <div>
        <p
          className={`rounded-full px-2 py-1 text-xs font-semibold tracking-[0.16em] uppercase ${colors.badge}`}
        >
          {risk.label}
        </p>
        <p className="mt-2 text-sm text-[var(--app-muted)]">
          {primaryCount} {risk.tone} hazard{primaryCount === 1 ? "" : "s"} found
        </p>
      </div>
    </div>
  );
}
