import { useEffect, useState } from "react";

export type Hand = { handedness: string; gesture: string | null; confidence: number };
export type Det = { label: string; score: number; box: number[] };
export type Status = {
  running: boolean; simulate: boolean | null; error: string | null;
  metrics: { fps: number; latency_ms: number; ram_mb: number; cpu: number };
  state: { hands: Hand[]; objects: Det[]; gesture: string | null; confidence: number; interactions?: unknown[] };
  control: { enabled: boolean; pending: string | null };
  settings: any; recording: { name: string; target: number; count: number } | null;
  custom: Record<string, number>; model: any; phone: { active: boolean; connected: boolean };
  events: { ts: number; kind: string; name: string; value: number }[];
};

export async function api<T = any>(path: string, method = "GET", body?: unknown): Promise<T> {
  const token = localStorage.getItem("token") || "";
  const r = await fetch(path, {
    method, headers: { "Content-Type": "application/json", "X-Token": token },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `Erreur ${r.status}`);
  return r.json();
}

/** Statut temps réel via WebSocket (reconnexion automatique). null = backend injoignable. */
export function useStatus(): Status | null {
  const [s, setS] = useState<Status | null>(null);
  useEffect(() => {
    let ws: WebSocket, timer: number, dead = false;
    const connect = () => {
      ws = new WebSocket(`ws://${location.host}/ws`);
      ws.onmessage = (e) => setS(JSON.parse(e.data));
      ws.onclose = () => { setS(null); if (!dead) timer = window.setTimeout(connect, 1500); };
    };
    connect();
    return () => { dead = true; clearTimeout(timer); ws?.close(); };
  }, []);
  return s;
}

export const fmtTime = (ts: number) => new Date(ts * 1000).toLocaleTimeString("fr-FR");
