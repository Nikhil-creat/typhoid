"use client";
import { useEffect, useState } from "react";
import { api, Patch } from "@/lib/api";

export default function Incidents() {
  const [patches, setPatches] = useState<Patch[]>([]);
  const [err, setErr] = useState("");
  const load = () => api<Patch[]>("/patches").then(setPatches).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);
  const decide = async (id: string, d: "approve" | "reject") => {
    try { await api(`/patches/${id}/${d}`, { method: "POST" }); load(); } catch (e: any) { setErr(e.message); }
  };
  return (
    <main className="max-w-4xl mx-auto p-6 flex flex-col gap-5">
      <h1 className="font-display text-4xl font-bold">Fixes waiting for you</h1>
      {err && <p role="alert" className="text-pathogen text-sm">{err}</p>}
      {patches.length === 0 && <p className="text-moss">Nothing to review. When the swarm finds and fixes a bug, the patch shows up here.</p>}
      {patches.map((p) => (
        <article key={p.id} className="bg-slide border border-rim rounded-plate p-5">
          <div className="flex justify-between gap-4">
            <h2 className="font-display text-xl font-semibold">{p.title}</h2>
            <span className={p.verified_in_sandbox ? "text-culture" : "text-colony"}>{p.verified_in_sandbox ? "Verified in sandbox" : "Not verified"} · {Math.round(p.confidence * 100)}%</span>
          </div>
          <p className="mt-2"><b>Root cause:</b> {p.root_cause}</p>
          <pre className="mt-3 bg-ink text-agar rounded-plate p-3 text-xs overflow-x-auto max-h-72">{p.diff}</pre>
          <div className="mt-3 flex gap-3 items-center">
            {p.pr_url && <a className="underline" href={p.pr_url}>Open pull request</a>}
            <span className="ml-auto text-sm text-moss">{p.state}</span>
            {p.state === "proposed" && <>
              <button onClick={() => decide(p.id, "reject")} className="px-3 py-1.5 border border-rim rounded-plate">Reject</button>
              <button onClick={() => decide(p.id, "approve")} disabled={!p.verified_in_sandbox} className="px-3 py-1.5 bg-culture text-white rounded-plate disabled:opacity-40">Approve and merge</button></>}
          </div>
        </article>))}
    </main>
  );
}
