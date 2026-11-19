"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { clearSession, readError, readSession, workflowFetch } from "../lib/workflow";

type Election = { id: string; year: number; election_date?: string; title: string; scope: string; scope_state?: string; status: string; constituency_count: number; nomination_count: number; constituencies?: { state: string; constituency: string }[] };
type Seat = { year: number; state: string; constituency: string; winner: string };
type Nomination = { id: string; election_id: string; election_title: string; election_year: number; state: string; constituency: string; candidate_name: string; party?: string; status: string; is_winner: boolean; nomination_pdf_path?: string };

export default function OfficerPage() {
  const [ready, setReady] = useState(false);
  const [elections, setElections] = useState<Election[]>([]);
  const [nominations, setNominations] = useState<Nomination[]>([]);
  const [seats, setSeats] = useState<Seat[]>([]);
  const [year, setYear] = useState(2024);
  const [electionDate, setElectionDate] = useState("");
  const [state, setState] = useState("");
  const [scope, setScope] = useState("all");
  const [selected, setSelected] = useState<string[]>([]);
  const [title, setTitle] = useState("Lok Sabha constituency election");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const states = useMemo(() => Array.from(new Set(seats.map(item => item.state))).sort(), [seats]);
  const visibleSeats = useMemo(() => state ? seats.filter(item => item.state === state) : seats, [seats, state]);

  async function load() {
    const [electionsResponse, nominationsResponse] = await Promise.all([workflowFetch("/api/workflow/elections"), workflowFetch("/api/officer/nominations")]);
    if (electionsResponse.ok) setElections(await electionsResponse.json());
    if (nominationsResponse.ok) setNominations(await nominationsResponse.json());
  }

  useEffect(() => {
    const session = readSession();
    if (!session) { window.location.href = "/login"; return; }
    if (session.user.role !== "officer") { window.location.href = "/candidate"; return; }
    setReady(true);
    void load();
  }, []);

  useEffect(() => {
    if (ready) workflowFetch(`/api/workflow/constituencies?year=${year}`).then(response => response.ok ? response.json() : []).then(setSeats);
  }, [ready, year]);

  async function declare() {
    setError(""); setMessage("");
    const constituencies = scope === "selected" ? selected.map(key => { const [stateValue, ...rest] = key.split("|"); return { state: stateValue, constituency: rest.join("|") }; }) : [];
    const response = await workflowFetch("/api/officer/elections", { method: "POST", body: JSON.stringify({ year, election_date: electionDate, title, scope, scope_state: scope === "state" ? state : null, constituencies }) });
    if (!response.ok) { setError(await readError(response)); return; }
    setMessage("Election declared with the officer-entered date."); setSelected([]); setElectionDate(""); await load();
  }

  async function close(id: string) { const response = await workflowFetch(`/api/officer/elections/${id}/close`, { method: "POST" }); if (!response.ok) setError(await readError(response)); else await load(); }
  async function remove(id: string) { if (!window.confirm("Delete this declaration from the active workflow?")) return; const response = await workflowFetch(`/api/officer/elections/${id}`, { method: "DELETE" }); if (!response.ok) setError(await readError(response)); else await load(); }

  async function review(item: Nomination, status: "accepted" | "rejected", isWinner = false) {
    const response = await workflowFetch(`/api/officer/nominations/${item.id}`, { method: "PATCH", body: JSON.stringify({ status, is_winner: isWinner, note: isWinner ? "Marked winner by EC officer" : status === "accepted" ? "Accepted by EC officer" : "Rejected by EC officer" }) });
    if (!response.ok) { setError(await readError(response)); return; }
    setMessage(isWinner ? "Accepted nomination marked as winner." : status === "accepted" ? "Nomination accepted and approved by the Returning Officer." : "Nomination rejected.");
    await load();
  }

  async function award(item: Nomination) {
    const response = await workflowFetch(`/api/officer/nominations/${item.id}/certificate`, { method: "POST" });
    if (!response.ok) { setError(await readError(response)); return; }
    setMessage("Winner certificate awarded as a PDF."); await load();
  }

  async function download(path: string, filename: string) {
    const response = await workflowFetch(path);
    if (!response.ok) { setError(await readError(response)); return; }
    const blob = await response.blob(); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url);
  }

  if (!ready) return <div className="shell"><main className="main"><div className="loading">Opening the officer console…</div></main></div>;

  return <div className="shell">
    <header className="topbar"><Link href="/" className="brand"><span className="brand-mark" />ELECTORaW</Link><nav className="nav"><Link href="/">Intelligence</Link><Link href="/candidates">Candidates</Link><Link href="/officer" className="active">EC officer</Link><button className="nav-button" onClick={() => { clearSession(); window.location.href = "/login"; }}>Sign out</button></nav><span className="eyebrow">Officer console</span></header>
    <main className="main workflow-main"><div className="workflow-hero"><div><div className="eyebrow">Election administration</div><h1>Declare.<br />Review.<br />Certify.</h1><p className="lede">Control constituency declarations, decide nominations, approve accepted applications, and issue winner certificates.</p></div><div className="hero-panel"><div className="panel-kicker">Local storage</div><div className="hero-number">RDBMS</div><div>SQLite + MongoDB mirror</div><p className="hero-note">Every declaration, review, approval, and certificate action is recorded locally.</p></div></div>
      {message && <div className="success-banner">{message}</div>}{error && <div className="error-banner">{error}</div>}
      <section className="workflow-grid"><form className="card workflow-card" onSubmit={event => { event.preventDefault(); void declare(); }}><div className="eyebrow">Step 01</div><h2>Declare an election</h2><p className="section-copy">Enter the actual election date, then choose the reference result year and coverage.</p><label>Election title<input className="text-input" value={title} onChange={event => setTitle(event.target.value)} /></label><div className="form-grid"><label>Election date<input className="text-input" type="date" required value={electionDate} onChange={event => setElectionDate(event.target.value)} /></label><label>Reference result year<select className="select-input" value={year} onChange={event => { setYear(Number(event.target.value)); setSelected([]); }}>{[2014, 2019, 2024].map(item => <option key={item}>{item}</option>)}</select></label></div><label>Coverage<select className="select-input" value={scope} onChange={event => setScope(event.target.value)}><option value="all">All constituencies</option><option value="state">One state</option><option value="selected">Selected seats</option></select></label>{scope !== "all" && <label>State<select className="select-input" value={state} onChange={event => setState(event.target.value)}><option value="">Choose a state</option>{states.map(item => <option key={item}>{item}</option>)}</select></label>}{scope === "selected" && <div className="seat-picker">{visibleSeats.map(item => { const key = `${item.state}|${item.constituency}`; return <label className="check-row" key={key}><input type="checkbox" checked={selected.includes(key)} onChange={event => setSelected(event.target.checked ? [...selected, key] : selected.filter(value => value !== key))} /><span>{item.constituency}</span><small>{item.state}</small></label>; })}</div>}<button className="button" disabled={!electionDate}>Declare election</button></form>
        <div className="card workflow-card"><div className="eyebrow">Step 02</div><h2>Active declarations</h2><div className="workflow-list">{elections.length === 0 ? <p className="section-copy">No declarations yet.</p> : elections.map(item => <div className="workflow-row" key={item.id}><div><strong>{item.title}</strong><span>{item.election_date || "Date not recorded"} · reference {item.year} · {item.constituency_count} constituencies · {item.nomination_count} nominations</span></div><span className={`status-pill ${item.status}`}>{item.status}</span><div className="row-actions">{item.status === "open" && <button className="button small secondary" onClick={() => void close(item.id)}>Close</button>}<button className="button small danger" onClick={() => void remove(item.id)}>Delete</button></div></div>)}</div></div></section>
      <section className="card workflow-card"><div className="eyebrow">Step 03</div><h2>Nomination desk</h2><p className="section-copy">Three decisions: Accept, Reject, or Make winner after acceptance. Accepted nominations receive a nomination PDF naming the Returning Officer who approved them.</p><div className="workflow-list">{nominations.length === 0 ? <p className="section-copy">No nominations submitted yet.</p> : nominations.map(item => <div className="nomination-row" key={item.id}><div><strong>{item.candidate_name}</strong><span>{item.constituency}, {item.state} · {item.party || "Independent / not specified"}</span><small>{item.election_title} · {item.status}{item.is_winner ? " · winner" : ""}</small></div><div className="row-actions">{item.status === "pending" && <><button className="button small" onClick={() => void review(item, "accepted")}>Accept</button><button className="button small secondary" onClick={() => void review(item, "rejected")}>Reject</button></>}{item.status === "accepted" && !item.is_winner && <button className="button small" onClick={() => void review(item, "accepted", true)}>Make winner</button>}{item.status === "accepted" && <button className="button small secondary" onClick={() => void download(`/api/workflow/nominations/${item.id}/download`, `nomination-${item.id}.pdf`)}>Download nomination PDF</button>}{item.status === "accepted" && item.is_winner && <button className="button small" onClick={() => void award(item)}>Award winner certificate</button>}</div></div>)}</div></section>
      <section className="concept-grid"><div className="card concept-card"><div className="eyebrow">Decision flow</div><h3>Accept → winner</h3><p>Reject is available only while pending. A nomination must be accepted before the officer can mark it as winner.</p></div><div className="card concept-card"><div className="eyebrow">Approval record</div><h3>Returning Officer approval</h3><p>Acceptance generates a nomination PDF stating “Approved by Returning Officer” with the officer’s name.</p></div><div className="card concept-card"><div className="eyebrow">Integrity concept</div><h3>Audit trail</h3><p>Declaration, review, approval, winner, and certificate actions are recorded with the acting officer and timestamp.</p></div></section>
    </main>
  </div>;
}
