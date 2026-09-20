"use client";
import { useState } from "react";
import { api } from "@/lib/api";

const FAULTS = [["latency", "Slow network"], ["packet_loss", "Dropped packets"], ["cpu_throttle", "CPU starvation"], ["db_outage", "Database outage"], ["dns_failure", "DNS failure"]] as const;

export default function Studio() {
  const [story, setStory] = useState("As a shopper, I can add a discounted item to my cart and pay with an expired card and see a clear error.");
  const [repo, setRepo] = useState(""); const [url, setUrl] = useState("http://demo-target:9898");
  const [mock, setMock] = useState<string | null>(null);
  const [faults, setFaults] = useState<string[]>(["latency"]); const [intensity, setIntensity] = useState(0.2);
  const [autonomy, setAutonomy] = useState<"observe" | "review" | "autopilot">("review");
  const [msg, setMsg] = useState("");

  const onFile = (f?: File) => { if (!f) return; const r = new FileReader(); r.onload = () => setMock((r.result as string).split(",")[1]); r.readAsDataURL(f); };
  const start = async () => {
    try {
      const run = await api<{ id: string }>("/runs", { method: "POST", body: JSON.stringify({ repo, target_url: url, user_story: story, mockup_b64: mock,
        chaos: faults.length ? { faults, intensity, duration_s: 60 } : null, autonomy }) });
      setMsg(`Run ${run.id.slice(0, 8)} started. Watch it in the Observatory.`);
    } catch (e: any) { setMsg(`Could not start the run: ${e.message}`); }
  };

  const field = "w-full bg-slide border border-rim rounded-plate px-3 py-2";
  return (
    <main className="max-w-3xl mx-auto p-6 flex flex-col gap-5">
      <h1 className="font-display text-4xl font-bold">Describe what should work</h1>
      <label className="flex flex-col gap-1">User story
        <textarea className={field} rows={4} value={story} onChange={(e) => setStory(e.target.value)} /></label>
      <div className="grid sm:grid-cols-2 gap-4">
        <label className="flex flex-col gap-1">GitHub repository<input className={field} placeholder="owner/name" value={repo} onChange={(e) => setRepo(e.target.value)} /></label>
        <label className="flex flex-col gap-1">App URL to test<input className={field} value={url} onChange={(e) => setUrl(e.target.value)} /></label>
      </div>
      <label className="flex flex-col gap-1">UI mockup (optional)
        <input type="file" accept="image/*" onChange={(e) => onFile(e.target.files?.[0])} className={field} />
        <span className="text-sm text-moss">The vision agent checks that the built page matches your design.</span></label>
      <fieldset className="border border-rim rounded-plate p-4">
        <legend className="px-2 font-display font-semibold">Break it on purpose</legend>
        <div className="flex flex-wrap gap-3">{FAULTS.map(([k, l]) => (
          <label key={k} className="flex items-center gap-2"><input type="checkbox" checked={faults.includes(k)} onChange={(e) => setFaults((f) => e.target.checked ? [...f, k] : f.filter((x) => x !== k))} />{l}</label>))}</div>
        <label className="flex items-center gap-3 mt-3">Intensity {Math.round(intensity * 100)}%
          <input type="range" min={0.05} max={0.3} step={0.05} value={intensity} onChange={(e) => setIntensity(+e.target.value)} />
          <span className="text-sm text-moss">Capped at 30% by policy.</span></label>
      </fieldset>
      <fieldset className="border border-rim rounded-plate p-4">
        <legend className="px-2 font-display font-semibold">How much can it do alone?</legend>
        {([["observe", "Observe: report only"], ["review", "Review: open PRs, a human approves"], ["autopilot", "Autopilot: merge verified, low-risk fixes"]] as const).map(([k, l]) => (
          <label key={k} className="flex items-center gap-2 py-1"><input type="radio" checked={autonomy === k} onChange={() => setAutonomy(k)} />{l}</label>))}
      </fieldset>
      <button onClick={start} disabled={!repo} className="self-start bg-culture text-white px-5 py-2 rounded-plate font-medium disabled:opacity-40">Start run</button>
      {msg && <p role="status" className="text-sm">{msg}</p>}
    </main>
  );
}
