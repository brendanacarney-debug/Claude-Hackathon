"use client";

import { useEffect, useEffectEvent, useState } from "react";

import { getSessionFromApi } from "@/lib/api";
import type { Session, SessionSummary } from "@/lib/types";

export function useSession(sessionId: string) {
  const [data, setData] = useState<Session | SessionSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useEffectEvent(async () => {
    try {
      const nextValue = await getSessionFromApi(sessionId);
      setData(nextValue);
      setError(null);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "We could not load this session.",
      );
    }
  });

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => {
      void refresh();
    }, 2000);

    return () => window.clearInterval(interval);
  }, [sessionId]);

  return { data, error };
}
