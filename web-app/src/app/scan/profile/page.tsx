import { ProfileSelector } from "@/components/ProfileSelector";
import { getRenderableProfiles } from "@/lib/server-data";

export default async function ProfilePage() {
  const profiles = await getRenderableProfiles();

  return (
    <section className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 py-8">
      <div className="space-y-3">
        <p className="text-sm font-semibold tracking-[0.18em] text-[var(--app-muted)] uppercase">
          Recovery Profile
        </p>
        <h1 className="text-4xl font-semibold tracking-[-0.04em] text-[var(--app-ink)]">
          Choose the recovery plan we should optimize for
        </h1>
        <p className="max-w-2xl text-base leading-7 text-[var(--app-muted)]">
          This viewer and checklist already understand the walker-after-fall
          profile from Tasks 3 and 4, so that is the profile we surface first.
        </p>
      </div>
      <ProfileSelector profiles={profiles} />
    </section>
  );
}
