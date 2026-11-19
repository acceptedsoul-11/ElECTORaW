"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
type Citation = { id:string; title:string; source_type:string; locator:string; excerpt:string; year?:number|null };
type Answer = { answer:string; mode:string; citations:Citation[]; retrieved_chunks:number; query_type:string };
type VectorStatus = { active:boolean; provider:string; collection:string; count:number; embedding:string };

function Header() { return <header className="topbar"><Link href="/" className="brand"><span className="brand-mark" aria-hidden="true"/>ELECTORaW</Link><nav className="nav"><Link href="/">Intelligence</Link><Link href="/candidates">Candidates</Link><Link href="/ask" className="active">Ask ELECTORaW</Link><Link href="/methodology">Methodology</Link></nav><Link href="/login" className="access-chip">Access ↗</Link><span className="eyebrow">Grounded answers</span></header>; }

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [year, setYear] = useState<number|undefined>(undefined);
  const [answer, setAnswer] = useState<Answer|null>(null);
  const [vectorStatus, setVectorStatus] = useState<VectorStatus|null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const suggestions = ["Who won Varanasi in 2024?", "What was the winning margin in Wayanad in 2019?", "Show me the strongest party performance in 2014"];
  useEffect(() => { fetch(`${API}/api/vector/status`).then(response => response.ok ? response.json() : null).then(setVectorStatus).catch(() => setVectorStatus(null)); }, []);
  async function ask(text = question) { if (text.trim().length < 3) return; setQuestion(text); setLoading(true); setError(""); setAnswer(null); try { const response = await fetch(`${API}/api/rag/query`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({question:text, year}) }); if (!response.ok) throw new Error(); setAnswer(await response.json()); } catch { setError("The grounded assistant could not reach the API. Check that the backend is running."); } finally { setLoading(false); } }
  return <div className="shell"><Header/><main className="main ask-layout"><section className="ask-intro"><div className="eyebrow">Evidence over guesswork</div><h1 style={{fontSize:"clamp(3.2rem,6vw,5.6rem)"}}>Ask the<br/>record.</h1><p className="lede">A compact research agent for the 2014, 2019 and 2024 Lok Sabha corpus. Ask in plain language and get a direct answer from the structured election record.</p><div className="year-tabs" style={{marginTop:26}}><span className="eyebrow" style={{alignSelf:"center", marginRight:8}}>Scope</span><button className={`year-tab ${!year ? "selected" : ""}`} onClick={()=>setYear(undefined)}>All years</button>{[2014,2019,2024].map(item=><button key={item} className={`year-tab ${year===item ? "selected" : ""}`} onClick={()=>setYear(item)}>{item}</button>)}</div><div className="vector-status">{vectorStatus ? `${vectorStatus.provider} · ${vectorStatus.count.toLocaleString("en-IN")} vectors` : "Preparing local vector index…"}</div></section><div className="card"><form className="question-box" onSubmit={e=>{e.preventDefault(); void ask();}}><input className="question-input" value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Try “Who won Varanasi in 2024?”" aria-label="Ask a question"/><button className="button" type="submit" disabled={loading}>{loading ? "Searching…" : "Ask"}</button></form><div className="suggestions">{suggestions.map(item=><button className="suggestion" key={item} onClick={()=>void ask(item)}>{item}</button>)}</div></div>{error && <p className="note" style={{marginTop:18}}>{error}</p>}{loading && <div className="card" style={{marginTop:18}}><div className="answer-status">Retrieving evidence</div><p className="loading">Checking the election index…</p></div>}{answer && <article className="card answer-card" style={{marginTop:18}}><div className="answer-status">{answer.mode.replaceAll("_", " ")}</div><div className="answer-copy">{answer.answer}</div><div className="answer-meta">{answer.retrieved_chunks} evidence chunks retrieved · {answer.query_type.replaceAll("_", " ")}</div></article>}</main><footer className="footer"><span>Answers are bounded by the election record.</span><Link href="/methodology">Read the methodology →</Link></footer></div>;
}
