import { PrintButton } from "@/components/PrintButton";
import { formatProfileLabel } from "@/lib/results";
import { getRenderableSession } from "@/lib/server-data";

export default async function ChecklistPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const session = await getRenderableSession(id);
  const createdAt = new Date(session.created_at).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  return (
    <section className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 py-8 print:max-w-none print:py-0">
      <div className="flex flex-col gap-4 print:hidden">
        <PrintButton />
      </div>

      <article className="rounded-[2rem] border border-[var(--app-line)] bg-white p-8 shadow-[0_24px_50px_-34px_rgba(15,23,42,0.4)] print:rounded-none print:border-0 print:p-0 print:shadow-none">
        <h1 className="text-3xl font-semibold tracking-[-0.04em] text-[var(--app-ink)]">
          HomeRecover Scan
        </h1>
        <p className="mt-2 text-lg text-[var(--app-muted)]">
          Recovery Safety Checklist
        </p>
        <div className="mt-5 grid gap-2 text-sm text-[var(--app-muted)]">
          <p>Date: {createdAt}</p>
          <p>Profile: {formatProfileLabel(session.recovery_profile)}</p>
        </div>

        <section className="mt-8">
          <h2 className="text-lg font-semibold tracking-[0.12em] text-[var(--app-ink)] uppercase">
            Before Tonight
          </h2>
          <ul className="mt-4 space-y-3 text-base leading-7 text-[var(--app-ink)]">
            {session.checklist.first_night.map((item) => (
              <li key={item}>[ ] {item}</li>
            ))}
          </ul>
        </section>

        <section className="mt-8">
          <h2 className="text-lg font-semibold tracking-[0.12em] text-[var(--app-ink)] uppercase">
            Within The First 48 Hours
          </h2>
          <ul className="mt-4 space-y-3 text-base leading-7 text-[var(--app-ink)]">
            {session.checklist.first_48_hours.map((item) => (
              <li key={item}>[ ] {item}</li>
            ))}
          </ul>
        </section>

        <p className="mt-10 border-t border-[var(--app-line)] pt-6 text-sm leading-6 text-[var(--app-muted)]">
          {session.disclaimer}
        </p>
      </article>
    </section>
  );
}
