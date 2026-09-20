export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const WS = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

export type AgentName = "risk_oracle" | "architect" | "synthetic_data" | "execution" | "chaos" | "vision" | "remediation" | "verifier" | "ship";
export type AgentEvent = { run_id: string; agent: AgentName; kind: string; payload: Record<string, any>; ts: string };
export type Patch = { id: string; run_id: string; title: string; root_cause: string; diff: string; confidence: number;
  verified_in_sandbox: boolean; pr_url?: string; state: "proposed" | "approved" | "rejected" | "merged" };

let token: string | null = null;
export async function auth() {
  if (token) return token;
  token = (await (await fetch(`${API}/dev/token?org=demo&role=admin`, { method: "POST" })).json()).token; // dev only; use OIDC in prod
  return token!;
}
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${API}${path}`, { ...init, headers: { "Content-Type": "application/json", Authorization: `Bearer ${await auth()}`, ...init.headers } });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}
