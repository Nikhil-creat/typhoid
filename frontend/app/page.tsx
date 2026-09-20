"use client";
import { useEffect, useState } from "react";
import { Dish } from "@/components/Dish";
import { Feed } from "@/components/Feed";
import { api } from "@/lib/api";
import { useEvents } from "@/lib/useEvents";

type Run = { id: string; status: string; risk_score: number | null; request: { repo: string } };

export default function Observatory() {
  const { events, live, send } = useEvents();
  const [runs, setRuns] = useState<Run[]>([]);
  useEffect(() => { api<Run[]>("/runs").then(setRuns).catch(() => {}); const t = setInterval(() => api<Run[]>("/runs").then(setRuns).catch(() => {}), 5000); return () => clearInterval(t); }, []);
  const heat = events.filter((e) => e.kind === "visual_diff").slice(-1)[0];

  return (
    <main className="grid gap-6 p-6 lg:grid-cols-[1fr_420px]">
      <section>
        <h1 className="font-display text-4xl font-bold">The swarm is {live ? "watching" : "offline"}</h1>
        <p className="text-moss mt-1 max-w-prose">Nine agents plan, break, judge and repair your app. Colonies grow with activity and turn red when something breaks.</p>
        <div className="mt-4 flex justify-center"><Dish events={events} /></div>
        {heat && (
          <div className="mt-4 bg-slide border border-rim rounded-plate p-4">
            <h2 className="font-display text-lg font-semibold">Latest visual change</h2>
            <p className="text-sm mt-1">{heat.payload.summary ?? "Analysing the difference…"}</p>
          </div>
        )}
      </section>
      <aside className="flex flex-col gap-6">
        <div className="bg-slide border border-rim rounded-plate p-4">
          <h2 className="font-display text-lg font-semibold mb-2">Recent runs</h2>
          {runs.length === 0 ? <p className="text-sm text-moss">No runs yet.</p> : (
            <ul className="divide-y divide-rim">
              {runs.slice(0, 6).map((r) => (
                <li key={r.id} className="py-2 flex justify-between text-sm">
                  <span className="truncate">{r.request.repo}</span>
                  <span className="flex gap-3">
                    {r.risk_score != null && <span title="Predicted regression risk">{Math.round(r.risk_score * 100)}% risk</span>}
                    <b className={r.status === "failed" ? "text-pathogen" : r.status === "passed" ? "text-culture" : "text-colony"}>{r.status.replace("_", " ")}</b>
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="bg-slide border border-rim rounded-plate p-4">
          <div className="flex justify-between items-center mb-2">
            <h2 className="font-display text-lg font-semibold">Live reasoning</h2>
            <div className="flex gap-2 text-xs">
              <button onClick={() => send("pause")} className="px-2 py-1 border border-rim rounded-plate">Pause</button>
              <button onClick={() => send("resume")} className="px-2 py-1 border border-rim rounded-plate">Resume</button>
            </div>
          </div>
          <Feed events={events} />
        </div>
      </aside>
    </main>
  );
}
