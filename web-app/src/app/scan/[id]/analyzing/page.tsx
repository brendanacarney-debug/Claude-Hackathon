"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useSession } from "@/hooks/useSession";

export default function AnalyzingPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const sessionId = params.id;
  const { data, error } = useSession(sessionId);

  useEffect(() => {
    if (data && "hazards" in data) {
      router.replace(`/results/${sessionId}`);
    }
  }, [data, router, sessionId]);

  return (
    <section className="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center py-10">
      <div className="glass-card rounded-[2rem] p-8 text-center">
        <div className="mx-auto h-14 w-14 animate-pulse rounded-full bg-[rgba(37,99,235,0.18)]" />
        <h1 className="mt-6 text-3xl font-semibold tracking-[-0.03em] text-[var(--app-ink)]">
          Analyzing your home...
        </h1>
        <p className="mt-3 text-base leading-7 text-[var(--app-muted)]">
          We&apos;re turning the room model, hazard scoring, and checklist logic
          into the final results view.
        </p>
        <div className="mt-8 space-y-3 rounded-[1.6rem] bg-[var(--panel-soft)] p-5 text-left text-sm text-[var(--app-muted)]">
          <p>[x] Session created</p>
          <p>[ ] Building room visualization</p>
          <p>[ ] Scoring hazards and recommendations</p>
          <p>[ ] Generating checklist output</p>
        </div>
        {error ? (
          <p className="mt-5 rounded-2xl border border-[rgba(239,68,68,0.2)] bg-[rgba(239,68,68,0.08)] px-4 py-3 text-sm text-[var(--accent-urgent)]">
            {error}
          </p>
        ) : null}
      </div>
    </section>
  );
}
