"use client";
import { useEffect, useRef, useState } from "react";
import { AgentEvent, WS, auth } from "./api";

/** Live event stream with auto-reconnect and a steering channel back to the swarm. */
export function useEvents(runId?: string) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [live, setLive] = useState(false);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    let stop = false, retry = 0;
    const connect = async () => {
      const t = await auth();
      const s = new WebSocket(`${WS}/ws/events?token=${t}${runId ? `&run_id=${runId}` : ""}`);
      ws.current = s;
      s.onopen = () => { setLive(true); retry = 0; };
      s.onmessage = (m) => setEvents((e) => [...e.slice(-399), JSON.parse(m.data)]);
      s.onclose = () => { setLive(false); if (!stop) setTimeout(connect, Math.min(1000 * 2 ** retry++, 15000)); };
    };
    connect();
    return () => { stop = true; ws.current?.close(); };
  }, [runId]);

  const send = (op: "pause" | "resume" | "steer", body: object = {}) => ws.current?.send(JSON.stringify({ op, run_id: runId, ...body }));
  return { events, live, send };
}
