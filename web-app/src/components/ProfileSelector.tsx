"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { startTransition, useState } from "react";

import { analyzeSession, createSession } from "@/lib/api";
import type { RecoveryProfile } from "@/lib/types";

const demoMode = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

export function ProfileSelector({
  profiles,
}: {
  profiles: RecoveryProfile[];
}) {
  const router = useRouter();
  const [selectedProfile, setSelectedProfile] = useState(
    profiles[0]?.profile_id ?? "walker_after_fall",
  );
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleContinue() {
    try {
      setIsSubmitting(true);
      setError(null);

      const session = await createSession(selectedProfile);

      if (demoMode) {
        await analyzeSession(session.session_id);
        router.push(`/scan/${session.session_id}/analyzing`);
        return;
      }

      router.push(`/scan/capture?session=${session.session_id}`);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "We could not start the scan right now.",
      );
    } finally {
      startTransition(() => {
        setIsSubmitting(false);
      });
    }
  }

  return (
    <div className="grid gap-6">
      {profiles.map((profile) => {
        const isSelected = selectedProfile === profile.profile_id;

        return (
          <button
            key={profile.profile_id}
            type="button"
            onClick={() => setSelectedProfile(profile.profile_id)}
            className={`glass-card rounded-[1.8rem] p-6 text-left transition ${
              isSelected
                ? "border-[rgba(37,99,235,0.28)] shadow-[0_24px_52px_-30px_rgba(37,99,235,0.55)]"
                : "hover:-translate-y-0.5"
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-semibold tracking-[-0.03em] text-[var(--app-ink)]">
                  {profile.label}
                </h2>
                <p className="mt-3 text-sm leading-6 text-[var(--app-muted)]">
                  Built for patients using a walker after a fall, fracture, or
                  similar mobility event.
                </p>
              </div>
              <span
                className={`mt-1 flex h-6 w-6 items-center justify-center rounded-full border ${
                  isSelected
                    ? "border-[var(--accent-blue)] bg-[var(--accent-blue)] text-white"
                    : "border-[var(--app-line)] bg-white text-transparent"
                }`}
              >
                *
              </span>
            </div>
            <div className="mt-5 grid gap-2 text-sm text-[var(--app-ink)]">
              {profile.constraints.map((constraint) => (
                <p key={constraint}>- {constraint.replace(/_/g, " ")}</p>
              ))}
            </div>
          </button>
        );
      })}

      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          onClick={handleContinue}
          disabled={isSubmitting}
          className="inline-flex h-12 items-center justify-center rounded-full bg-[var(--accent-blue)] px-6 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting
            ? "Starting..."
            : demoMode
              ? "Open Demo Analysis"
              : "Continue to Capture"}
        </button>
        <Link
          href="/demo"
          className="inline-flex h-12 items-center justify-center rounded-full border border-[var(--app-line)] bg-white px-6 text-sm font-semibold text-[var(--app-ink)] transition hover:-translate-y-0.5"
        >
          View Fixture Demo
        </Link>
      </div>

      {error ? (
        <p className="rounded-2xl border border-[rgba(239,68,68,0.2)] bg-[rgba(239,68,68,0.08)] px-4 py-3 text-sm text-[var(--accent-urgent)]">
          {error}
        </p>
      ) : null}
    </div>
  );
}
