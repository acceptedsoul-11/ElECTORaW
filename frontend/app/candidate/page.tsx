"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { clearSession, readError, readSession, workflowFetch } from "../lib/workflow";

type Seat = { state: string; constituency: string; winner?: string };
type Election = { id: string; year: number; election_date?: string; title: string; status: string; constituencies: Seat[] };
type Nomination = { id: string; election_title: string; election_year: number; candidate_name: string; party?: string; state: string; constituency: string; status: string; is_winner: boolean; nomination_pdf_path?: string };
type Certificate = { id: string; certificate_number: string; candidate_name: string; constituency: string; state: string; issued_at: string };

export default function CandidatePage() {
  const [ready, setReady] = useState(false);
  const [user, setUser] = useState<{ full_name: string; email: string } | null>(null);
  const [elections, setElections] = useState<Election[]>([]);
  const [nominations, setNominations] = useState<Nomination[]>([]);
  const [certificates, setCertificates] = useState<Certificate[]>([]);
  const [electionId, setElectionId] = useState("");
  const [state, setState] = useState("");
  const [constituency, setConstituency] = useState("");
  const [form, setForm] = useState({ candidate_name: "", party: "", age: "", gender: "", address: "", education: "", proposer_name: "", proposer_voter_id: "", affidavit: "", documents: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const election = elections.find(item => item.id === electionId);
  const states = useMemo(() => Array.from(new Set((election?.constituencies || []).map(item => item.state))).sort(), [election]);
  const seats = (election?.constituencies || []).filter(item => !state || item.state === state);

  async function load() {
    const [electionsResponse, nominationsResponse, certificatesResponse] = await Promise.all([
      workflowFetch("/api/workflow/elections"),
      workflowFetch("/api/candidate/nominations"),
      workflowFetch("/api/candidate/certificates"),
    ]);
    if (electionsResponse.ok) {
      const list = await electionsResponse.json() as Election[];
      setElections(list);
      if (list[0]) setElectionId(current => current || list[0].id);
    }
    if (nominationsResponse.ok) setNominations(await nominationsResponse.json());
    if (certificatesResponse.ok) setCertificates(await certificatesResponse.json());
  }

  useEffect(() => {
    const session = readSession();
    if (!session) { window.location.href = "/login"; return; }
    if (session.user.role !== "elector") { window.location.href = "/officer"; return; }
    setUser({ full_name: session.user.full_name, email: session.user.email });
    setForm(value => ({ ...value, candidate_name: session.user.full_name }));
    setReady(true);
    void load();
  }, []);

  async function submit() {
    setError("");
    setMessage("");
    const response = await workflowFetch("/api/candidate/nominations", {
      method: "POST",
      body: JSON.stringify({
        election_id: electionId,
        state,
        constituency,
        candidate_name: form.candidate_name,
        party: form.party || null,
        form: { ...form, documents: form.documents.split(",").map(item => item.trim()).filter(Boolean) },
      }),
    });
    if (!response.ok) { setError(await readError(response)); return; }
    setMessage("Nomination submitted. It is now visible to the EC officer for review.");
    setConstituency("");
    await load();
  }

  async function download(id: string, number: string) {
    const response = await workflowFetch(`/api/workflow/certificates/${id}/download`);
    if (!response.ok) { setError(await readError(response)); return; }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${number}.pdf`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function downloadNomination(id: string) {
    const response = await workflowFetch(`/api/workflow/nominations/${id}/download`);
    if (!response.ok) { setError(await readError(response)); return; }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `nomination-${id}.pdf`;
    link.click();
    URL.revokeObjectURL(url);
  }

  if (!ready) return <div className="shell"><main className="main"><div className="loading">Opening the candidate portal…</div></main></div>;

  return <div className="shell">
    <header className="topbar"><Link href="/" className="brand"><span className="brand-mark" />ELECTORaW</Link><nav className="nav"><Link href="/">Intelligence</Link><Link href="/candidates">Candidates</Link><Link href="/candidate" className="active">Candidate portal</Link><button className="nav-button" onClick={() => { clearSession(); window.location.href = "/login"; }}>Sign out</button></nav><span className="eyebrow">{user?.full_name}</span></header>
    <main className="main workflow-main"><div className="workflow-hero"><div><div className="eyebrow">Candidate services</div><h1>Put your<br />name forward.</h1><p className="lede">Complete the online nomination form for an election declared by an EC officer. If your nomination is accepted and you are marked winner, your certificate appears here as a PDF.</p></div><div className="hero-panel"><div className="panel-kicker">Your account</div><div className="hero-number">{nominations.length}</div><div>nomination records</div><p className="hero-note">{user?.email}</p></div></div>
      {message && <div className="success-banner">{message}</div>}{error && <div className="error-banner">{error}</div>}
      <section className="workflow-grid"><form className="card workflow-card" onSubmit={event => { event.preventDefault(); void submit(); }}><div className="eyebrow">Nomination form</div><h2>Submit an application</h2>
        {elections.length === 0 ? <p className="section-copy">No EC officer has declared an open election yet.</p> : <>
          <label>Open election<select className="select-input" value={electionId} onChange={event => { setElectionId(event.target.value); setState(""); setConstituency(""); }}>{elections.map(item => <option key={item.id} value={item.id}>{item.title} · {item.year}{item.election_date ? ` · ${item.election_date}` : ""}</option>)}</select></label>
          <div className="form-grid"><label>State<select className="select-input" required value={state} onChange={event => { setState(event.target.value); setConstituency(""); }}><option value="">Choose state</option>{states.map(item => <option key={item}>{item}</option>)}</select></label><label>Constituency<select className="select-input" required value={constituency} onChange={event => setConstituency(event.target.value)} disabled={!state}><option value="">{state ? "Choose constituency" : "Select state first"}</option>{seats.map(item => <option key={item.constituency}>{item.constituency}</option>)}</select></label></div>
          <label>Candidate name<input className="text-input" required value={form.candidate_name} onChange={event => setForm({ ...form, candidate_name: event.target.value })} /></label>
          <div className="form-grid"><label>Party / affiliation<input className="text-input" value={form.party} onChange={event => setForm({ ...form, party: event.target.value })} /></label><label>Age<input className="text-input" type="number" min="25" max="120" required value={form.age} onChange={event => setForm({ ...form, age: event.target.value })} /><span className="field-hint">Minimum age to contest: 25</span></label></div>
          <div className="form-grid"><label>Gender<input className="text-input" value={form.gender} onChange={event => setForm({ ...form, gender: event.target.value })} /></label><label>Education<input className="text-input" value={form.education} onChange={event => setForm({ ...form, education: event.target.value })} /></label></div>
          <label>Address<textarea className="text-input textarea" value={form.address} onChange={event => setForm({ ...form, address: event.target.value })} /></label>
          <div className="form-grid"><label>Proposer name<input className="text-input" value={form.proposer_name} onChange={event => setForm({ ...form, proposer_name: event.target.value })} /></label><label>Proposer voter ID<input className="text-input" value={form.proposer_voter_id} onChange={event => setForm({ ...form, proposer_voter_id: event.target.value })} /></label></div>
          <label>Document names <span className="field-hint">comma-separated</span><input className="text-input" placeholder="Affidavit, voter ID, photograph" value={form.documents} onChange={event => setForm({ ...form, documents: event.target.value })} /></label>
          <label>Declaration<textarea className="text-input textarea" required value={form.affidavit} onChange={event => setForm({ ...form, affidavit: event.target.value })} placeholder="I declare that the information supplied is accurate…" /></label>
          <button className="button" disabled={!elections.length || !state || !constituency}>Submit nomination</button>
        </>}
      </form>
      <div className="card workflow-card"><div className="eyebrow">Your records</div><h2>Nominations</h2><div className="workflow-list">{nominations.length === 0 ? <p className="section-copy">Submitted nominations will appear here.</p> : nominations.map(item => <div className="nomination-row" key={item.id}><div><strong>{item.candidate_name}</strong><span>{item.constituency}, {item.state} · {item.party || "Independent / not specified"}</span><small>{item.election_title} · {item.status}{item.is_winner ? " · winner" : ""}</small></div><div className="row-actions"><span className={`status-pill ${item.status}`}>{item.status}</span>{item.status === "accepted" && <button className="button small secondary" onClick={() => void downloadNomination(item.id)}>Download nomination PDF</button>}</div></div>)}</div><h2 style={{ marginTop: 28 }}>Certificates</h2><div className="workflow-list">{certificates.length === 0 ? <p className="section-copy">A certificate appears after an officer awards it.</p> : certificates.map(item => <div className="nomination-row" key={item.id}><div><strong>{item.certificate_number}</strong><span>{item.constituency}, {item.state}</span><small>{new Date(item.issued_at).toLocaleDateString("en-IN")}</small></div><button className="button small" onClick={() => void download(item.id, item.certificate_number)}>Download PDF</button></div>)}</div></div></section>
      <section className="concept-grid"><div className="card concept-card"><div className="eyebrow">Eligibility rule</div><h3>Age 25 minimum</h3><p>The nomination form and API both reject candidates younger than 25 before an application enters the workflow.</p></div><div className="card concept-card"><div className="eyebrow">Form design</div><h3>Structured + flexible</h3><p>Identity and constituency fields remain relational; supporting declarations and document lists are preserved as a Mongo-friendly form document.</p></div><div className="card concept-card"><div className="eyebrow">Certificate design</div><h3>Print-ready proof</h3><p>The generated certificate uses the election date, constituency, party, issue date, and officer-approved winner status.</p></div></section>
    </main>
  </div>;
}
