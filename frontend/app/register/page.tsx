"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { API, saveSession } from "../lib/workflow";

type StateOption = { state: string };
type ConstituencyOption = { state: string; constituency: string };

export default function RegisterPage() {
  const [form, setForm] = useState({ full_name: "", email: "", password: "", role: "elector", phone: "", state: "", constituency: "" });
  const [states, setStates] = useState<StateOption[]>([]);
  const [constituencies, setConstituencies] = useState<ConstituencyOption[]>([]);
  const [loadingStates, setLoadingStates] = useState(true);
  const [loadingConstituencies, setLoadingConstituencies] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API}/api/states?year=2024`)
      .then(async response => { if (!response.ok) throw new Error("Could not load states"); return response.json() as Promise<StateOption[]>; })
      .then(items => { if (!cancelled) setStates(items); })
      .catch(() => { if (!cancelled) setError("Election lists are unavailable. Start the local FastAPI backend and refresh this page."); })
      .finally(() => { if (!cancelled) setLoadingStates(false); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!form.state) { setConstituencies([]); return; }
    let cancelled = false;
    setLoadingConstituencies(true);
    setConstituencies([]);
    fetch(`${API}/api/constituencies?year=2024&state=${encodeURIComponent(form.state)}&limit=600`)
      .then(async response => { if (!response.ok) throw new Error("Could not load constituencies"); return response.json() as Promise<ConstituencyOption[]>; })
      .then(items => { if (!cancelled) setConstituencies(items); })
      .catch(() => { if (!cancelled) setError("Could not load constituencies for that state."); })
      .finally(() => { if (!cancelled) setLoadingConstituencies(false); });
    return () => { cancelled = true; };
  }, [form.state]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API}/api/auth/register`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...form, phone: form.phone || null }) });
      if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || "Registration failed"); }
      saveSession(await response.json());
      window.location.href = form.role === "officer" ? "/officer" : "/candidate";
    } catch (caught) {
      setError(caught instanceof TypeError ? "The local API is not reachable. Start the FastAPI backend on port 8000 and try again." : caught instanceof Error ? caught.message : "Registration failed");
    } finally { setLoading(false); }
  }

  return <div className="shell">
    <header className="topbar"><Link href="/" className="brand"><span className="brand-mark" />ELECTORaW</Link><nav className="nav"><Link href="/">Intelligence</Link><Link href="/candidates">Candidates</Link><Link href="/ask">Ask ELECTORaW</Link><Link href="/login">Sign in</Link></nav><Link href="/login" className="access-chip">Access ↗</Link><span className="eyebrow">Create account</span></header>
    <main className="main auth-layout"><div><div className="eyebrow">Local election workflow</div><h1>Register<br />your access.</h1><p className="lede">Use one account for the public intelligence pages and the role-specific election workflow. Elector accounts use the candidate nomination portal; officer accounts manage declarations and decisions.</p></div>
      <form className="card auth-card" onSubmit={submit}><h2>Registration</h2><p className="section-copy">Your registration details are stored in the local RDBMS and mirrored to MongoDB when available.</p>
        <label>Full name<input className="text-input" required value={form.full_name} onChange={event => setForm({ ...form, full_name: event.target.value })} /></label>
        <label>Email<input className="text-input" type="email" required value={form.email} onChange={event => setForm({ ...form, email: event.target.value })} /></label>
        <label>Password<input className="text-input" type="password" minLength={8} required value={form.password} onChange={event => setForm({ ...form, password: event.target.value })} /></label>
        <label>Register as<select className="select-input" value={form.role} onChange={event => setForm({ ...form, role: event.target.value })}><option value="elector">Elector / candidate</option><option value="officer">EC officer</option></select></label>
        <label>Mobile number<input className="text-input" type="tel" inputMode="numeric" minLength={10} maxLength={10} pattern="[0-9]{10}" placeholder="10-digit mobile number" value={form.phone} onChange={event => setForm({ ...form, phone: event.target.value.replace(/\D/g, "").slice(0, 10) })} /></label>
        <div className="form-grid"><label>State<select className="select-input" required value={form.state} onChange={event => setForm({ ...form, state: event.target.value, constituency: "" })} disabled={loadingStates}><option value="">{loadingStates ? "Loading states…" : "Choose a state"}</option>{states.map(item => <option key={item.state} value={item.state}>{item.state}</option>)}</select></label>
          <label>Constituency<select className="select-input" required value={form.constituency} onChange={event => setForm({ ...form, constituency: event.target.value })} disabled={!form.state || loadingConstituencies}><option value="">{!form.state ? "Select state first" : loadingConstituencies ? "Loading constituencies…" : "Choose a constituency"}</option>{constituencies.map(item => <option key={item.constituency} value={item.constituency}>{item.constituency}</option>)}</select></label></div>
        {error && <p className="form-error">{error}</p>}<button className="button" disabled={loading || loadingStates || !form.state || !form.constituency}>{loading ? "Creating account…" : "Create account"}</button><p className="section-copy">Already registered? <Link href="/login" className="inline-link">Sign in →</Link></p>
      </form>
    </main>
  </div>;
}
