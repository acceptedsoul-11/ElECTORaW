"use client";

import Link from "next/link";
import IndiaMap from "./components/IndiaMap";
import { partyLogoFor } from "./components/PartyBadge";
import { useEffect, useMemo, useState, useRef } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
type Overview = { year:number; candidate_count:number; constituency_count:number; state_count:number; winner_count:number; total_votes:number; source_files:string[]; coverage_note?:string|null; top_parties:{party:string; candidates:number; seats:number; votes:number}[] };
type StateSummary = { state:string; candidates:number; constituencies:number; seats:number; votes:number };
type Minister = { name:string; party:string; portfolio:string; logo:string; winner:{id:string; constituency:string; state:string}; profile:{status:string; completeness:number; bio?:string}; source_references:{title:string;url:string}[] };

const format = (value:number) => new Intl.NumberFormat("en-IN").format(value);

function Header() {
  return <header className="topbar"><Link href="/" className="brand"><span className="brand-mark" aria-hidden="true"/>ELECTORaW</Link><nav className="nav"><Link href="/">Intelligence</Link><Link href="/candidates">Candidates</Link><Link href="/winners">Winners</Link><Link href="/ask">Ask ELECTORaW</Link><Link href="/methodology">Methodology</Link><Link href="/login">Access</Link></nav><span className="eyebrow">ECI · 2014—2024</span></header>;
}

export default function Home() {
  const [year, setYear] = useState(2024);
  const [overview, setOverview] = useState<Overview|null>(null);
  const [states, setStates] = useState<StateSummary[]>([]);
  const [ministers, setMinisters] = useState<Minister[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    setError("");
    Promise.all([fetch(`${API}/api/overview?year=${year}`).then(r => r.json()), fetch(`${API}/api/states?year=${year}`).then(r => r.json())])
      .then(([summary, stateRows]) => { setOverview(summary); setStates(stateRows); })
      .catch(() => setError("The intelligence service is unavailable. Start the FastAPI backend on port 8000 and refresh."));
  }, [year]);
  useEffect(() => { fetch(`${API}/api/spotlight/nda-cabinet?year=${year}`).then(r => r.json()).then(setMinisters).catch(() => setMinisters([])); }, [year]);
  const maxSeats = useMemo(() => Math.max(...states.map(s => s.seats), 1), [states]);
  return <div className="shell"><Header/><main className="main">
    <section className="hero"><div><div className="eyebrow">A clearer view of the republic</div><h1>India,<br/>decoded.</h1><p className="lede">Explore verified Lok Sabha results, candidate performance and source-aware context across three national elections — with every answer grounded in the record.</p></div><div className="hero-panel"><div className="panel-kicker">Selected election</div><div className="hero-number">{overview ? format(overview.winner_count) : "—"}</div><div>official winning seats</div><p className="hero-note">Complete ECI successful-candidate coverage. Detailed vote fields remain blank where the local workbook has no matching row.</p></div></section>
    <div className="year-tabs" role="tablist" aria-label="Election year"><span className="eyebrow" style={{alignSelf:"center", marginRight:8}}>Election year</span>{[2014,2019,2024].map(item => <button key={item} className={`year-tab ${year===item ? "selected" : ""}`} onClick={() => setYear(item)}>{item}</button>)}</div>
    {error ? <div className="note">{error}</div> : overview ? <><IndiaMap year={year} states={states} />
      <section className="stats" aria-label="Election overview"><div className="stat"><div className="stat-label">Candidates</div><div className="stat-value">{format(overview.candidate_count)}</div></div><div className="stat"><div className="stat-label">Constituencies</div><div className="stat-value">{format(overview.constituency_count)}</div></div><div className="stat"><div className="stat-label">States & UTs</div><div className="stat-value">{format(overview.state_count)}</div></div><div className="stat"><div className="stat-label">Votes recorded</div><div className="stat-value">{format(overview.total_votes)}</div></div></section>
      {overview.coverage_note && <p className="note" style={{marginTop:18}}>{overview.coverage_note}</p>}
      <section className="content-grid"><div className="card"><div className="section-head"><div><h2>Party performance</h2><p className="section-copy">Seats matched in the curated winner report, with candidate vote totals alongside.</p></div></div><div className="bars">{overview.top_parties.slice(0,8).map((party, index) => <div className="bar-row" key={party.party}><div className="bar-label" title={party.party}>{party.party}</div><div className="bar-track"><div className="bar-fill" style={{width:`${Math.max((party.seats / Math.max(overview.winner_count,1))*100, 2)}%`, opacity:1-index*.06}}/></div><div className="bar-count">{party.seats} seats</div></div>)}</div></div><div className="card"><h2>State lens</h2><p className="section-copy">A quick route into the geography of {year}.</p><div className="state-list">{states.slice(0,12).map(state => <div className="state-item" key={state.state}><div><div className="state-main">{state.state}</div><div className="state-meta">{state.constituencies} constituencies · {format(state.candidates)} candidates</div></div><span className="seat-pill">{state.seats} seats</span></div>)}</div></div></section>
      <section style={{marginTop:28}}><div className="section-head"><div><div className="eyebrow">Winner archive</div><h2>Find every winning record.</h2><p className="section-copy">The map is the overview; the winner archive is the complete seat-by-seat index, including the 2014 rows without detailed vote data.</p></div><Link className="button" href="/winners">Open winner archive →</Link></div></section><section id="cabinet-profiles" style={{marginTop:28}}><div className="section-head"><div><div className="eyebrow">Cabinet profiles · {year}</div><h2>Cabinet on the map.</h2><p className="section-copy">Lok Sabha winners with that year’s cabinet portfolios, party logos, and source-backed profile links.</p></div><Link className="button" href={`/winners?year=${year}`}>Browse all {year} winners →</Link></div><div className="minister-grid">{ministers.map(minister => <Link href={`/winners/${minister.winner.id}`} className="minister-tile" key={minister.name}><div className="minister-top"><img className="party-logo" src={minister.logo} alt={`${minister.party} logo`} loading="lazy" onError={event => { event.currentTarget.style.display = "none"; }}/><span className="party-logo-fallback">{minister.party}</span><span className="minister-party">{minister.party}</span></div><h3>{minister.name}</h3><div className="state-meta">{minister.winner.constituency}, {minister.winner.state}</div><p className="minister-portfolio">{minister.portfolio}</p><div className="profile-source">Open election/profile record ↗</div></Link>)}</div></section>
      <section className="cta"><div><div className="eyebrow">The grounded assistant</div><h2>Ask the record a better question.</h2><p>Get a concise answer backed by retrieved ECI evidence and visible citations.</p></div><Link className="button" href="/ask">Open Ask ELECTORaW →</Link></section>
    </> : <div className="loading">Loading the election record…</div>}
  </main><footer className="footer"><span>Built for clarity, with the source trail intact.</span><span>2014 · 2019 · 2024 Lok Sabha</span></footer></div>;
}
