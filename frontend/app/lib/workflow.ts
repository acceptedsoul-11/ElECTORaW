"use client";

export const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
export type Session = { token:string; user:{id:string; email:string; full_name:string; role:"elector"|"officer"; phone?:string; voter_id?:string; state?:string; constituency?:string} };
const KEY = "electoraw_workflow_session";

export function readSession(): Session | null {
  try { return JSON.parse(window.localStorage.getItem(KEY) || "null") as Session | null; } catch { return null; }
}

export function saveSession(session: Session) { window.localStorage.setItem(KEY, JSON.stringify(session)); }
export function clearSession() { window.localStorage.removeItem(KEY); }

export async function workflowFetch(path:string, init:RequestInit = {}) {
  const session = readSession();
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (session?.token) headers.set("Authorization", `Bearer ${session.token}`);
  return fetch(`${API}${path}`, {...init, headers});
}

export async function readError(response:Response) {
  try { const body = await response.json(); return body.detail || "The request could not be completed."; } catch { return "The request could not be completed."; }
}
