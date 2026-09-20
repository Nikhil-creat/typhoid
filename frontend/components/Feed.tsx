"use client";
import { AgentEvent } from "@/lib/api";
import { cn } from "@/lib/utils";

const tone: Record<string, string> = { error: "border-pathogen", chaos: "border-colony", patch: "border-culture", visual_diff: "border-colony" };

export function Feed({ events }: { events: AgentEvent[] }) {
  if (!events.length)
    return <p className="text-moss text-sm p-4">No activity yet. Start a run from the Test Studio and the swarm's reasoning appears here.</p>;
  return (
    <ol className="flex flex-col gap-2 overflow-y-auto max-h-[70vh] pr-1" aria-live="polite">
      {[...events].reverse().map((e, i) => (
        <li key={i} className={cn("border-l-4 bg-slide rounded-plate px-3 py-2 text-sm", tone[e.kind] ?? "border-rim")}>
          <div className="flex justify-between text-xs text-moss">
            <span className="font-medium text-ink">{e.agent.replace("_", " ")}</span>
            <time>{new Date(e.ts).toLocaleTimeString()}</time>
          </div>
          <p className="mt-1 break-words">{summarise(e)}</p>
        </li>
      ))}
    </ol>
  );
}

function summarise(e: AgentEvent) {
  const p = e.payload;
  if (e.kind === "chaos") return `Hypothesis "${p.hypothesis}" ${p.held ? "held" : "broke"}.`;
  if (e.kind === "patch") return p.pr_url ? `Opened ${p.pr_url}` : `Draft patch "${p.title}" (${Math.round(p.confidence * 100)}% confident, attempt ${p.attempt}).`;
  if (e.kind === "visual_diff") return `Visual change on ${p.viewport}: ${p.summary ?? "analysing"}`;
  if (e.kind === "result" && "passed" in p) return `${p.passed} passed, ${p.failed} failed.`;
  if (e.kind === "error") return p.message ?? "Something went wrong.";
  return JSON.stringify(p).slice(0, 240);
}
