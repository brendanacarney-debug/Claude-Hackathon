"use client";

import { useEffect, useState } from "react";

function normalizeState(items: string[], stored: unknown): boolean[] {
  if (!Array.isArray(stored)) {
    return items.map(() => false);
  }

  return items.map((_, index) => Boolean(stored[index]));
}

export function ChecklistPanel({
  title,
  items,
  storageKey,
}: {
  title: string;
  items: string[];
  storageKey: string;
}) {
  const [checked, setChecked] = useState<boolean[]>(() => {
    if (typeof window === "undefined") {
      return items.map(() => false);
    }

    const stored = window.localStorage.getItem(storageKey);
    if (!stored) {
      return items.map(() => false);
    }

    try {
      return normalizeState(items, JSON.parse(stored));
    } catch {
      return items.map(() => false);
    }
  });

  useEffect(() => {
    window.localStorage.setItem(storageKey, JSON.stringify(checked));
  }, [checked, storageKey]);

  return (
    <section className="glass-card rounded-[1.8rem] p-5">
      <h3 className="text-lg font-semibold tracking-[-0.02em] text-[var(--app-ink)]">
        {title}
      </h3>
      <div className="mt-4 space-y-2">
        {items.map((item, index) => (
          <label
            key={`${storageKey}-${index}`}
            className="flex items-start gap-3 rounded-2xl px-2 py-2.5 transition hover:bg-[rgba(37,99,235,0.04)]"
          >
            <input
              type="checkbox"
              checked={checked[index] ?? false}
              onChange={() =>
                setChecked((current) =>
                  current.map((value, valueIndex) =>
                    valueIndex === index ? !value : value,
                  ),
                )
              }
              className="mt-1 h-4 w-4 rounded border-[var(--app-line)] text-[var(--accent-blue)]"
            />
            <span
              className={
                checked[index]
                  ? "text-sm leading-6 text-[var(--app-muted)] line-through"
                  : "text-sm leading-6 text-[var(--app-ink)]"
              }
            >
              {item}
            </span>
          </label>
        ))}
      </div>
    </section>
  );
}
