"use client";
import { AgentEvent, AgentName } from "@/lib/api";

/** The swarm as a petri dish: each agent is a colony. Activity makes it bloom; failures turn it red. */
const AGENTS: { id: AgentName; label: string; a: number; r: number }[] = [
  { id: "risk_oracle", label: "Risk oracle", a: -90, r: 0.62 },
  { id: "architect", label: "Architect", a: -35, r: 0.62 },
  { id: "synthetic_data", label: "Synthetic data", a: 20, r: 0.62 },
  { id: "execution", label: "Execution", a: 70, r: 0.62 },
  { id: "chaos", label: "Chaos", a: 125, r: 0.62 },
  { id: "vision", label: "Vision", a: 180, r: 0.62 },
  { id: "remediation", label: "Remediation", a: 235, r: 0.62 },
  { id: "verifier", label: "Verifier", a: 285, r: 0.35 },
  { id: "ship", label: "Ship", a: 0, r: 0 },
];

export function Dish({ events }: { events: AgentEvent[] }) {
  const recent = events.slice(-40);
  const state = (id: AgentName) => {
    const mine = recent.filter((e) => e.agent === id);
    if (!mine.length) return "idle";
    const last = mine[mine.length - 1];
    return last.kind === "error" || last.payload?.held === false || last.payload?.verified === false ? "fail" : Date.now() - new Date(last.ts).getTime() < 8000 ? "active" : "done";
  };
  const R = 200, C = 240;
  const pos = (a: number, r: number) => [C + Math.cos((a * Math.PI) / 180) * R * r, C + Math.sin((a * Math.PI) / 180) * R * r];
  const fill = { idle: "#CBD6C6", active: "#D98E04", done: "#1E6F5C", fail: "#B3261E" } as const;

  return (
    <svg viewBox="0 0 480 480" role="img" aria-label="Agent swarm status" className="w-full max-w-[520px]">
      <circle cx={C} cy={C} r={228} fill="#F8FAF5" stroke="#CBD6C6" strokeWidth={6} />
      <circle cx={C} cy={C} r={214} fill="none" stroke="#CBD6C6" strokeWidth={1} strokeDasharray="2 6" />
      {AGENTS.slice(0, -1).map((a, i) => {
        const b = AGENTS[(i + 1) % (AGENTS.length - 1)];
        const [x1, y1] = pos(a.a, a.r), [x2, y2] = pos(b.a, b.r);
        return <line key={a.id} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#CBD6C6" strokeWidth={2} />;
      })}
      {AGENTS.map((a) => {
        const [x, y] = pos(a.a, a.r), s = state(a.id);
        const n = recent.filter((e) => e.agent === a.id).length;
        return (
          <g key={a.id} transform={`translate(${x} ${y})`}>
            <circle r={18 + Math.min(n, 10) * 1.6} fill={fill[s]} opacity={0.9} className={s === "active" ? "colony-active" : ""} />
            <text y={a.id === "ship" ? 4 : 44} textAnchor="middle" className="fill-ink text-[11px] font-body">{a.label}</text>
          </g>
        );
      })}
    </svg>
  );
}
