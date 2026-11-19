from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..data import ElectionData, Row, _norm
from ..config import settings
from .vector_store import LocalVectorStore


@dataclass(frozen=True)
class Chunk:
    id: str
    title: str
    text: str
    locator: str
    source_type: str
    year: int | None


class GroundedRag:
    """Grounded local RAG engine with persistent ChromaDB retrieval.

    ChromaDB is the only retrieval backend. The structured answer planner keeps
    electoral facts bounded to the curated corpus, while all semantic retrieval
    comes from the persistent local Chroma collection.
    """

    def __init__(self, data: ElectionData, root: Path) -> None:
        self.data = data
        self.root = root
        self.chunks = self._build_chunks()
        self._chunks_by_id = {chunk.id: chunk for chunk in self.chunks}
        self.vector_store = LocalVectorStore(settings.vector_db_path, settings.vector_collection)
        self.vector_store.upsert(self.chunks)

    def _build_chunks(self) -> list[Chunk]:
        chunks: list[Chunk] = []
        seen_ids: set[str] = set()

        def add_chunk(chunk: Chunk) -> None:
            # Multiple source rows can resolve to the same state/seat key;
            # Chroma requires IDs to be unique within one upsert call.
            if chunk.id not in seen_ids:
                seen_ids.add(chunk.id)
                chunks.append(chunk)

        for year in (2014, 2019, 2024):
            for item in self.data.constituencies(year, limit=1000):
                winner = item.get("winner") or {}
                text = (
                    f"{year} Lok Sabha election. Constituency {item['constituency']} in {item['state']}. "
                    f"Winner {winner.get('candidate_name', 'not matched')} for {winner.get('party', 'party not recorded')}. "
                    f"Winner votes {winner.get('votes', 'not available')}. Margin {item.get('margin', 'not available')}. "
                    f"Candidate count {item['candidate_count']}. Total candidate votes {item['total_votes']}."
                )
                add_chunk(Chunk(
                    id=f"contest-{year}-{_norm(item['state'])}-{_norm(item['constituency'])}",
                    title=f"{year} · {item['constituency']}, {item['state']}", text=text,
                    locator=f"data/processed/candidate_results_{year}.csv", source_type="official_local", year=year,
                ))
        for path in sorted((self.root.parent.parent / "docs").glob("*.md")):
            try:
                text = path.read_text(encoding="utf-8")[:25000]
            except OSError:
                continue
            add_chunk(Chunk(id=f"doc-{path.stem}", title=path.stem.replace("_", " "), text=text, locator=str(path.relative_to(self.root.parent.parent)), source_type="methodology", year=None))
        return chunks

    def retrieve(self, question: str, year: int | None = None, top_k: int = 5) -> list[tuple[Chunk, float]]:
        return self.vector_store.query(question, self._chunks_by_id, year, top_k)

    def _find_rows(self, question: str, year: int | None) -> list[Row]:
        candidates = self.data._rows(year)
        q = _norm(question)
        exact = [r for r in candidates if _norm(r.constituency) in q or _norm(r.candidate_name) in q or _norm(r.state) in q]
        return sorted(exact, key=lambda r: (-int(r.winner), -r.votes))

    def _state_from_question(self, question: str, year: int | None) -> str | None:
        """Return the canonical state name mentioned in a question, if any."""
        if year is None:
            return None
        normalized_question = _norm(question)
        for item in self.data.states(year):
            state = item.get("state")
            if state and _norm(state) in normalized_question:
                return state
        return None

    @staticmethod
    def _clean_retrieval_text(text: str) -> str:
        """Keep document retrieval readable instead of exposing raw Markdown."""
        cleaned = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
        cleaned = cleaned.replace("`", "")
        cleaned = re.sub(r"^\s*[-*]\s+", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def answer(self, question: str, year: int | None = None) -> dict[str, Any]:
        q = question.strip()
        lowered = q.lower()
        parsed_year = next((candidate for candidate in (2014, 2019, 2024) if str(candidate) in lowered), None)
        scope_year = year or parsed_year
        retrieved = self.retrieve(q, scope_year)
        rows = self._find_rows(q, scope_year)
        asks_winner = any(token in lowered for token in ("winner", "won", "elected", "candidate", "seat")) or "winning candidate" in lowered or "winning candidates" in lowered
        asks_votes = any(token in lowered for token in ("vote", "margin", "polled", "how many"))
        asks_performance = any(token in lowered for token in ("strongest party", "best party", "top party", "party performance", "most seats"))
        asks_all = any(token in lowered for token in ("every", "all", "each", "complete list", "list of"))
        state_name = self._state_from_question(q, scope_year)
        asks_state_winners = bool(state_name and asks_winner and asks_all)
        query_type = "state_winner_list" if asks_state_winners else ("structured_lookup" if asks_winner or asks_votes or asks_performance else "document_retrieval")
        citations = [
            {"id": chunk.id, "title": chunk.title, "source_type": chunk.source_type, "locator": chunk.locator, "excerpt": chunk.text[:280], "year": chunk.year}
            for chunk, _score in retrieved[:4]
        ]

        if asks_state_winners and state_name and scope_year:
            winners, _total = self.data.winners(year=scope_year, state=state_name, limit=1000)
            if winners:
                lines = [f"{state_name} has {len(winners)} recorded winning constituencies in {scope_year}:", ""]
                lines.extend(
                    f"{index}. {item.get('winner') or item.get('candidate_name') or 'Winner not recorded'} — {item.get('constituency', 'Constituency not recorded')} · {item.get('party') or 'Party not recorded'}"
                    for index, item in enumerate(winners, start=1)
                )
                return {"answer": "\n".join(lines), "mode": "hybrid", "citations": citations, "retrieved_chunks": len(retrieved), "query_type": query_type}

        if asks_performance and scope_year:
            parties = self.data.party_summaries(scope_year, 1)
            if parties:
                leader = parties[0]
                answer = f"{leader['party']} had the strongest seat performance in {scope_year}, winning {leader['seats']} Lok Sabha seats in the curated election record."
                return {"answer": answer, "mode": "hybrid", "citations": citations, "retrieved_chunks": len(retrieved), "query_type": query_type}

        if rows and (asks_winner or asks_votes):
            winner = next((r for r in rows if r.winner), None)
            focus = winner or rows[0]
            if asks_winner and winner:
                party = winner.party or "a party not recorded in the curated file"
                answer = f"{winner.candidate_name} won {winner.constituency}, {winner.state} in {winner.year}. They represented {party} and received {winner.votes:,} votes."
            elif asks_votes:
                if "margin" in lowered:
                    contest = [row for row in self.data._rows(focus.year) if _norm(row.state) == _norm(focus.state) and _norm(row.constituency) == _norm(focus.constituency)]
                    ranked = sorted(contest, key=lambda row: (-row.votes, row.candidate_name))
                    margin = ranked[0].votes - ranked[1].votes if len(ranked) > 1 else None
                    answer = f"{focus.candidate_name} won {focus.constituency}, {focus.state} in {focus.year}. The winning margin was {margin:,} votes." if margin is not None else f"The winning margin for {focus.constituency}, {focus.state} is not present in the available detailed result."
                else:
                    answer = f"{focus.candidate_name} recorded {focus.votes:,} votes in {focus.constituency}, {focus.state} ({focus.year}). The result lists {focus.party or 'no party'} and a {focus.vote_share:.2f}% vote share." if focus.vote_share is not None else f"{focus.candidate_name} recorded {focus.votes:,} votes in {focus.constituency}, {focus.state} ({focus.year})."
            else:
                answer = f"The closest grounded result is {focus.candidate_name} in {focus.constituency}, {focus.state} ({focus.year})."
            return {"answer": answer, "mode": "hybrid", "citations": citations, "retrieved_chunks": len(retrieved), "query_type": query_type}

        if retrieved:
            lines = ["I found grounded context in the curated ELECTORaW corpus:"]
            for chunk, _score in retrieved[:3]:
                snippet = self._clean_retrieval_text(chunk.text)
                lines.append(f"• {snippet[:360]}")
            lines.append("Ask for a specific year, state, constituency, candidate, or party to get a structured result.")
            return {"answer": "\n".join(lines), "mode": "retrieval", "citations": citations, "retrieved_chunks": len(retrieved), "query_type": query_type}

        return {"answer": "I couldn’t find enough evidence in the curated 2014, 2019, and 2024 corpus to answer that safely. Try naming a year and constituency, candidate, party, or state.", "mode": "insufficient_evidence", "citations": [], "retrieved_chunks": 0, "query_type": "unsupported"}
