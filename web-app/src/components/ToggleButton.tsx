"use client";

import clsx from "clsx";

const palette = {
  blue: {
    active:
      "border-[rgba(37,99,235,0.28)] bg-[rgba(37,99,235,0.12)] text-[var(--accent-blue)]",
    idle:
      "border-[var(--app-line)] bg-white text-[var(--app-muted)] hover:text-[var(--app-ink)]",
  },
  green: {
    active:
      "border-[rgba(16,185,129,0.28)] bg-[rgba(16,185,129,0.12)] text-[var(--accent-safe)]",
    idle:
      "border-[var(--app-line)] bg-white text-[var(--app-muted)] hover:text-[var(--app-ink)]",
  },
  red: {
    active:
      "border-[rgba(239,68,68,0.28)] bg-[rgba(239,68,68,0.12)] text-[var(--accent-urgent)]",
    idle:
      "border-[var(--app-line)] bg-white text-[var(--app-muted)] hover:text-[var(--app-ink)]",
  },
} as const;

export function ToggleButton({
  active,
  color,
  onClick,
  children,
}: {
  active: boolean;
  color: keyof typeof palette;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        "inline-flex h-11 items-center justify-center rounded-full border px-4 text-sm font-semibold transition hover:-translate-y-0.5",
        active ? palette[color].active : palette[color].idle,
      )}
    >
      {children}
    </button>
  );
}
