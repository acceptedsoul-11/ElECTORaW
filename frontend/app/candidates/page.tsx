"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { PartyBadge } from "../components/PartyBadge";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
type Winner = { id:string; year:number; state:string; constituency:string; winner:string; party?:string; votes?:number|null; profile:{status:string; completeness:number} };
type StateSummary = { state:string; seats:number };
const format = (value:number) => new Intl.NumberFormat("en-IN").format(value);

function Header(){return <header className="topbar"><Link href="/" className="brand"><span className="brand-mark"/>ELECTORaW</Link><nav className="nav"><Link href="/">Intelligence</Link><Link href="/candidates" className="active">Candidates</Link><Link href="/winners">Winners</Link><Link href="/ask">Ask ELECTORaW</Link><Link href="/methodology">Methodology</Link></nav><Link href="/login" className="access-chip">Access ↗</Link><span className="eyebrow">Winning candidates</span></header>}

export default function CandidatesPage(){
  const [year, setYear] = useState<number|undefined>(undefined);
  const [query, setQuery] = useState("");
  const [state, setState] = useState("");
  const [items, setItems] = useState<Winner[]>([]);
  const [states, setStates] = useState<StateSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => { const params = new URLSearchParams(window.location.search); const initialYear = Number(params.get("year")); if ([2014, 2019, 2024].includes(initialYear)) setYear(initialYear); setState(params.get("state") || ""); }, []);
  useEffect(() => { fetch(`${API}/api/states?year=${year || 2024}`).then(response => response.json()).then(setStates).catch(() => setStates([])); }, [year]);
  useEffect(() => { const handle = setTimeout(() => { setLoading(true); const params = new URLSearchParams({ limit:"100", offset:String(offset) }); if (year) params.set("year", String(year)); if (query) params.set("search", query); if (state) params.set("state", state); fetch(`${API}/api/winners?${params}`).then(response => response.json()).then(data => { setItems(data.items || []); setTotal(data.total || 0); }).catch(() => { setItems([]); setTotal(0); }).finally(() => setLoading(false)); }, 200); return () => clearTimeout(handle); }, [year, query, state, offset]);

  const selectYear = (value:number|undefined) => { setYear(value); setOffset(0); };
  const selectState = (value:string) => { setState(value); setOffset(0); };
  const search = (value:string) => { setQuery(value); setOffset(0); };
  return <div className="shell"><Header/><main className="main"><div className="eyebrow">Complete winner index</div><h1 style={{fontSize:"clamp(3.2rem,6vw,5.4rem)"}}>Winning<br/>candidates.</h1><p className="lede">Every official successful candidate from 2014, 2019 and 2024 is listed here by constituency. Open any row for its profile, source trail, election history, and party mark.</p><div className="winner-summary"><div><strong>{format(total)}</strong><span>{year ? `${year} winners` : "winners across all years"}</span></div><div><strong>1,629</strong><span>official seat records</span></div><div><strong>100</strong><span>records per page</span></div></div><section className="winner-filters card"><input className="search-input" value={query} onChange={event => search(event.target.value)} placeholder="Search winner, constituency, party, or state"/><div className="filter-row"><div className="year-tabs">{[[undefined,"All years"],[2014,"2014"],[2019,"2019"],[2024,"2024"]].map(([value,label]) => <button key={String(value)} className={`year-tab ${year === value ? "selected" : ""}`} onClick={() => selectYear(value as number|undefined)}>{label}</button>)}</div><select className="select-input" value={state} onChange={event => selectState(event.target.value)}><option value="">All states & UTs</option>{states.map(item => <option key={item.state} value={item.state}>{item.state} · {item.seats} seats</option>)}</select></div></section><section className="winner-results"><div className="section-head"><div><div className="eyebrow">{loading ? "Refreshing" : "Official records"}</div><h2>{format(total)} winning candidates</h2></div><div className="section-copy">{total ? `${offset + 1}–${Math.min(offset + items.length, total)} shown` : "No matches"}</div></div>{loading ? <div className="loading">Loading all winning candidates…</div> : items.length === 0 ? <div className="card loading">No winning candidates match those filters.</div> : <div className="winner-table">{items.map(item => <Link className="winner-row" href={`/winners/${item.id}`} key={item.id}><div className="winner-year">{item.year}</div><div><div className="result-title"><PartyBadge party={item.party}/>{item.winner}</div><div className="result-meta">{item.constituency}, {item.state} · {item.party || "Party not recorded"}</div></div><div className="winner-evidence">Open profile ↗</div><div className="result-votes">{item.votes == null ? "—" : format(item.votes)}<br/><small>{item.votes == null ? "no detail row" : "votes"}</small></div></Link>)}</div>}<div className="pagination"><button className="button secondary" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 100))}>← Previous</button><span>Page {Math.floor(offset / 100) + 1} of {Math.max(1, Math.ceil(total / 100))}</span><button className="button secondary" disabled={offset + 100 >= total} onClick={() => setOffset(offset + 100)}>Next →</button></div></section></main><footer className="footer"><span>Election facts: Election Commission of India.</span><span>Every winner opens a profile/evidence page.</span></footer></div>;
}
