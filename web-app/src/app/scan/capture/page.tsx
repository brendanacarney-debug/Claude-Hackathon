"use client";

import Link from "next/link";
import { use } from "react";
import { useRouter } from "next/navigation";

import { CaptureGuide } from "@/components/CaptureGuide";
import { analyzeSession, uploadPhotos } from "@/lib/api";

export default function CapturePage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const params = use(searchParams);
  const sessionId = typeof params.session === "string" ? params.session : null;
  const router = useRouter();

  if (!sessionId) {
    return (
      <section className="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center justify-center gap-4 py-10 text-center">
        <p className="text-base text-[var(--app-muted)]">
          No session found. Please select a profile first.
        </p>
        <Link
          href="/scan/profile"
          className="inline-flex h-11 items-center justify-center rounded-full bg-[var(--accent-blue)] px-6 text-sm font-semibold text-white transition hover:-translate-y-0.5"
        >
          Choose Profile
        </Link>
      </section>
    );
  }

  const activeSessionId = sessionId;

  async function handleComplete(photos: File[], roomTypes: string[]) {
    await uploadPhotos(activeSessionId, photos, roomTypes);
    await analyzeSession(activeSessionId);
    router.push(`/scan/${activeSessionId}/analyzing`);
  }

  return (
    <section className="mx-auto flex w-full max-w-lg flex-1 flex-col gap-6 px-4 py-8">
      <div>
        <p className="text-xs font-semibold tracking-[0.18em] text-[var(--app-muted)] uppercase">
          Step 2 of 3
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-[var(--app-ink)]">
          Photograph your home
        </h1>
        <p className="mt-3 text-base leading-7 text-[var(--app-muted)]">
          We&apos;ll guide you through three photos - bedroom, bathroom, and
          hallway. Keep the camera steady and capture the full room.
        </p>
      </div>
      <CaptureGuide onComplete={handleComplete} />
    </section>
  );
}
