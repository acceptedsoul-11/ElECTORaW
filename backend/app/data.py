from __future__ import annotations

import csv
import hashlib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import settings


YEARS = (2014, 2019, 2024)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _int(value: str | None) -> int | None:
    try:
        return int(float(value)) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _float(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _norm(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


@dataclass(frozen=True)
class Row:
    id: str
    year: int
    source_file: str
    state: str
    constituency: str
    candidate_name: str
    party: str | None
    party_symbol: str | None
    votes: int
    vote_share: float | None
    total_votes_polled: int | None
    valid_votes: int | None
    total_electors: int | None
    gender: str | None
    age: int | None
    category: str | None
    winner: bool


class ElectionData:
    """Read-only canonical data access for local development and demos.

    Production deployments can switch the backend to MySQL while retaining the
    same API contract. The CSV mode is intentionally backed by the curated ECI
    processing outputs already checked into this repository.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or settings.data_root
        self.rows: list[Row] = []
        self._official_winners: list[dict[str, Any]] = []
        self._winner_keys: set[tuple[int, str, str, str]] = set()
        self._winner_names: dict[tuple[int, str, str], str] = {}
        self._winner_rows: dict[str, Row | None] = {}
        self._official_by_id: dict[str, dict[str, Any]] = {}
        self._load_winners()
        self._load_rows()
        self._build_winner_index()

    def _load_winners(self) -> None:
        # Keep both matched and unmatched official winner rows. The detailed
        # result workbooks have 32 missing 2014 rows, but the ECI successful-
        # candidates workbook still gives us the authoritative winner record.
        for filename, match_status in (("official_winners_matched.csv", "matched"), ("official_winners_unmatched.csv", "official_only"), ("official_winners_supplemental.csv", "official_only")):
            path = self.root / filename
            if not path.exists():
                continue
            with path.open(newline="", encoding="utf-8-sig") as handle:
                for item in csv.DictReader(handle):
                    year = _int(item.get("year"))
                    if year is None:
                        continue
                    state = _clean(item.get("state")) or "Unknown"
                    constituency = _clean(item.get("constituency")) or "Unknown"
                    winner = _clean(item.get("winner")) or "Unknown winner"
                    candidate_name = _clean(item.get("candidate_name_db")) or winner
                    record = {
                        "id": hashlib.sha1(f"winner|{year}|{state}|{constituency}".encode()).hexdigest()[:20],
                        "year": year, "state": state, "constituency": constituency,
                        "winner": winner, "party": _clean(item.get("party")),
                        "candidate_name": candidate_name, "match_status": match_status,
                        "source_file": _clean(item.get("source_file")) or filename,
                        "source_sheet": _clean(item.get("source_sheet")),
                    }
                    self._official_winners.append(record)
                    state_key = _norm(state)
                    constituency_key = _norm(constituency)
                    candidate_key = _norm(candidate_name)
                    self._winner_keys.add((year, state_key, constituency_key, candidate_key))
                    self._winner_names[(year, state_key, constituency_key)] = candidate_name

        self._official_winners.sort(key=lambda item: (item["year"], item["state"], item["constituency"]))
        self._official_by_id = {item["id"]: item for item in self._official_winners}

    def _load_rows(self) -> None:
        for year in YEARS:
            path = self.root / f"candidate_results_{year}.csv"
            if not path.exists():
                continue
            with path.open(newline="", encoding="utf-8-sig") as handle:
                for index, item in enumerate(csv.DictReader(handle), start=2):
                    if (item.get("is_nota") or "").strip().lower() == "true" or _norm(item.get("candidate_name")) == "nota" or _norm(item.get("party_name_source")) == "nota":
                        continue
                    state = _clean(item.get("state_name")) or "Unknown"
                    constituency = _clean(item.get("constituency_name")) or "Unknown"
                    name = _clean(item.get("candidate_name")) or "Unknown candidate"
                    key = (year, _norm(state), _norm(constituency), _norm(name))
                    stable = hashlib.sha1(f"{year}|{state}|{constituency}|{name}|{index}".encode()).hexdigest()[:16]
                    self.rows.append(Row(
                        id=stable,
                        year=year,
                        source_file=_clean(item.get("source_file")) or path.name,
                        state=state,
                        constituency=constituency,
                        candidate_name=name,
                        party=_clean(item.get("party_name_source")),
                        party_symbol=_clean(item.get("party_symbol")),
                        votes=_int(item.get("votes_received")) or 0,
                        vote_share=_float(item.get("vote_share_valid_pct")) or _float(item.get("vote_share_polled_pct")),
                        total_votes_polled=_int(item.get("total_votes_polled")),
                        valid_votes=_int(item.get("valid_votes")),
                        total_electors=_int(item.get("total_electors")),
                        gender=_clean(item.get("gender")),
                        age=_int(item.get("age")),
                        category=_clean(item.get("category")),
                        winner=key in self._winner_keys,
                    ))
        # A small number of source rows repeat a matched winner name within the
        # same contest. Keep exactly one authoritative row per matched contest,
        # choosing the highest-vote matching row and leaving the source rows
        # themselves untouched for auditability.
        matched_by_contest: dict[tuple[int, str, str], list[int]] = defaultdict(list)
        for index, row in enumerate(self.rows):
            if row.winner:
                matched_by_contest[(row.year, _norm(row.state), _norm(row.constituency))].append(index)
        for indexes in matched_by_contest.values():
            if len(indexes) <= 1:
                continue
            winner_index = max(indexes, key=lambda index: self.rows[index].votes)
            for index in indexes:
                if index == winner_index:
                    continue
                row = self.rows[index]
                self.rows[index] = Row(**{**row.__dict__, "winner": False})

    def _build_winner_index(self) -> None:
        """Match official winner records to detailed rows once at startup.

        The old request path scanned every candidate row for every winner. A
        state selection could therefore repeat tens of millions of comparisons.
        This index makes winner and state lookups bounded by the requested rows.
        """
        by_contest: dict[tuple[int, str, str], list[Row]] = defaultdict(list)
        by_exact: dict[tuple[int, str, str, str], list[Row]] = defaultdict(list)
        for row in self.rows:
            contest_key = (row.year, _norm(row.state), _norm(row.constituency))
            by_contest[contest_key].append(row)
            by_exact[(*contest_key, _norm(row.candidate_name))].append(row)
        for official in self._official_winners:
            contest_key = (official["year"], _norm(official["state"]), _norm(official["constituency"]))
            candidates = by_exact.get((*contest_key, _norm(official["candidate_name"])), [])
            if not candidates:
                candidates = [row for row in by_contest.get(contest_key, []) if row.winner]
            self._winner_rows[official["id"]] = max(candidates, key=lambda row: row.votes) if candidates else None

    def _rows(self, year: int | None = None) -> list[Row]:
        return [row for row in self.rows if year is None or row.year == year]

    @staticmethod
    def public_row(row: Row) -> dict[str, Any]:
        return {
            "id": row.id, "year": row.year, "candidate_name": row.candidate_name,
            "party": row.party, "party_symbol": row.party_symbol, "state": row.state,
            "constituency": row.constituency, "votes": row.votes, "vote_share": row.vote_share,
            "winner": row.winner, "gender": row.gender, "age": row.age,
            "category": row.category, "source_file": row.source_file,
        }

    def elections(self) -> list[dict[str, Any]]:
        result = []
        for year in YEARS:
            rows = self._rows(year)
            result.append({
                "year": year, "name": f"Lok Sabha General Election {year}",
                "candidate_count": len(rows),
                "constituency_count": len({(r.state, r.constituency) for r in rows}),
                "winner_count": len([item for item in self._official_winners if item["year"] == year]),
                "source_coverage": "Curated ECI processing output",
            })
        return result

    def overview(self, year: int) -> dict[str, Any]:
        rows = self._rows(year)
        parties = self.party_summaries(year, 8)
        return {
            "year": year,
            "candidate_count": len(rows),
            "constituency_count": len({(r.state, r.constituency) for r in rows}),
            "state_count": len({r.state for r in rows}),
            "winner_count": len([item for item in self._official_winners if item["year"] == year]),
            "total_votes": sum(r.votes for r in rows),
            "source_files": sorted({r.source_file for r in rows}),
            "coverage_note": "NOTA is excluded from candidate counts. All official successful candidates are listed; 32 unmatched 2014 winners in Chhattisgarh and Odisha have no matching detailed-result row, so their vote fields are intentionally blank." if year == 2014 else None,
            "top_parties": parties,
        }

    def party_summaries(self, year: int, limit: int = 20) -> list[dict[str, Any]]:
        groups: dict[str, dict[str, int]] = defaultdict(lambda: {"candidates": 0, "seats": 0, "votes": 0})
        for row in self._rows(year):
            party = row.party or "Unspecified"
            groups[party]["candidates"] += 1
            groups[party]["seats"] += int(row.winner)
            groups[party]["votes"] += row.votes
        for winner in self._official_winners:
            if winner["year"] == year and winner["party"]:
                groups[winner["party"]]["seats"] += 1
        # Every row above was counted as a seat from the candidate table; use
        # the official list for the seat total so missing 2014 detail rows are
        # still represented.
        for values in groups.values():
            values["seats"] = 0
        for winner in self._official_winners:
            if winner["year"] == year:
                groups[winner["party"] or "Unspecified"]["seats"] += 1
        return [
            {"party": party, **values}
            for party, values in sorted(groups.items(), key=lambda item: (-item[1]["seats"], -item[1]["votes"], item[0]))[:limit]
        ]

    def states(self, year: int) -> list[dict[str, Any]]:
        groups: dict[str, list[Row]] = defaultdict(list)
        for row in self._rows(year):
            groups[_norm(row.state).replace("nct of delhi", "delhi").replace("orissa", "odisha")].append(row)
        result = []
        official_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in self._official_winners:
            if item["year"] == year:
                official_groups[_norm(item["state"]).replace("nct of delhi", "delhi").replace("orissa", "odisha")].append(item)
        display_names = {key: (items[0]["state"] if items else key) for key, items in official_groups.items()}
        for state_key, rows in groups.items():
            official_seats = len(official_groups.get(state_key, []))
            result.append({
                "state": display_names.get(state_key, rows[0].state), "candidates": len(rows),
                "constituencies": len({r.constituency for r in rows}),
                "seats": official_seats, "votes": sum(r.votes for r in rows),
            })
        known_states = {state_key for state_key in groups}
        for state_key, winners in official_groups.items():
            if state_key not in known_states:
                result.append({"state": winners[0]["state"], "candidates": 0, "constituencies": 0, "seats": len(winners), "votes": 0})
        return sorted(result, key=lambda item: (-item["seats"], item["state"]))

    def winners(self, year: int | None = None, search: str | None = None, state: str | None = None, limit: int = 100, offset: int = 0) -> tuple[list[dict[str, Any]], int]:
        query = _norm(search)
        filtered = [item for item in self._official_winners if (year is None or item["year"] == year) and (not state or _norm(item["state"]) == _norm(state))]
        if query:
            filtered = [item for item in filtered if any(query in _norm(item.get(key)) for key in ("winner", "candidate_name", "party", "state", "constituency"))]
        enriched = []
        for item in filtered:
            match = self._winner_rows.get(item["id"])
            enriched.append({**item, "candidate_result_id": match.id if match else None, "votes": match.votes if match else None, "vote_share": match.vote_share if match else None, "source_file": match.source_file if match else item["source_file"]})
        return enriched[offset:offset + limit], len(enriched)

    def winner_by_id(self, winner_id: str) -> dict[str, Any] | None:
        item = self._official_by_id.get(winner_id)
        if item is None:
            return None
        rows, _ = self.winners(year=item["year"], search=item["winner"], limit=10)
        return next((row for row in rows if row["id"] == winner_id), None)

    def candidates(self, year: int | None = None, search: str | None = None, state: str | None = None, party: str | None = None, limit: int = 25, offset: int = 0) -> tuple[list[Row], int]:
        query = _norm(search)
        filtered = [r for r in self._rows(year) if (not query or query in _norm(r.candidate_name) or query in _norm(r.constituency) or query in _norm(r.state) or query in _norm(r.party)) and (not state or _norm(r.state) == _norm(state)) and (not party or _norm(r.party) == _norm(party))]
        filtered.sort(key=lambda r: (-int(r.winner), -r.votes, r.candidate_name))
        return filtered[offset:offset + limit], len(filtered)

    def by_id(self, candidate_id: str) -> Row | None:
        return next((row for row in self.rows if row.id == candidate_id), None)

    def history(self, candidate_name: str) -> list[Row]:
        return [r for r in self.rows if _norm(r.candidate_name) == _norm(candidate_name)]

    def constituencies(self, year: int, search: str | None = None, state: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        groups: dict[tuple[str, str], list[Row]] = defaultdict(list)
        query = _norm(search)
        for row in self._rows(year):
            if state and _norm(row.state) != _norm(state):
                continue
            if query and query not in _norm(row.state) and query not in _norm(row.constituency) and query not in _norm(row.candidate_name) and query not in _norm(row.party):
                continue
            groups[(row.state, row.constituency)].append(row)
        result = []
        for (state_name, constituency), rows in groups.items():
            ranked = sorted(rows, key=lambda r: (-r.votes, r.candidate_name))
            winner = next((r for r in rows if r.winner), ranked[0] if ranked else None)
            runner_up = next((r for r in ranked if not winner or r.id != winner.id), None)
            result.append({
                "year": year, "state": state_name, "constituency": constituency,
                "winner": self.public_row(winner) if winner else None,
                "candidate_count": len(rows), "total_votes": sum(r.votes for r in rows),
                "margin": winner.votes - runner_up.votes if winner and runner_up else None,
                "source_file": winner.source_file if winner else rows[0].source_file,
            })
        result.sort(key=lambda item: (item["state"], item["constituency"]))
        return result[:limit]

    def source_catalog(self) -> list[dict[str, Any]]:
        return [
            {"title": "ECI constituency-wise detailed results", "source_type": "official_local", "locator": "data/processed/candidate_results_2014.csv, candidate_results_2019.csv, candidate_results_2024.csv", "years": [2014, 2019, 2024]},
            {"title": "ECI official successful candidates — matched winners", "source_type": "official_local", "locator": "data/processed/official_winners_matched.csv", "years": [2014, 2019, 2024]},
            {"title": "ECI official successful candidates — unmatched 2014 records", "source_type": "coverage_note", "locator": "data/processed/official_winners_unmatched.csv", "years": [2014]},
            {"title": "ECI official successful candidates — complete winner index", "source_type": "official_local", "locator": "data/processed/official_winners_matched.csv + official_winners_unmatched.csv + official_winners_supplemental.csv", "years": [2014, 2019, 2024]},
        ]


@lru_cache(maxsize=1)
def get_data() -> Any:
    if settings.data_backend == "mysql":
        from .services.mysql_analytics import MySQLElectionData
        return MySQLElectionData()
    return ElectionData()
