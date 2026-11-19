from __future__ import annotations

from collections import defaultdict
from typing import Any

import mysql.connector

from ..config import settings
from ..data import Row, YEARS, _norm


class MySQLElectionData:
    """Read-only analytical data access backed by the electoraw MySQL schema."""

    def _query(self, sql: str, values: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        connection = mysql.connector.connect(host=settings.mysql_host, port=settings.mysql_port, database=settings.mysql_database, user=settings.mysql_user, password=settings.mysql_password, connection_timeout=5)
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute(sql, values)
            rows = cursor.fetchall()
            cursor.close()
            return rows
        finally:
            connection.close()

    @staticmethod
    def _row(item: dict[str, Any]) -> Row:
        return Row(id=str(item["candidate_result_id"]), year=int(item["year"]), source_file=item.get("source_file") or "MySQL ECI import", state=item["state"], constituency=item["constituency"], candidate_name=item["candidate_name"], party=item.get("party"), party_symbol=item.get("party_symbol"), votes=int(item.get("votes") or 0), vote_share=float(item["vote_share"]) if item.get("vote_share") is not None else None, total_votes_polled=item.get("total_votes_polled"), valid_votes=item.get("valid_votes"), total_electors=item.get("total_electors"), gender=item.get("gender"), age=item.get("age"), category=item.get("category"), winner=bool(item.get("winner")))

    @staticmethod
    def public_row(row: Row) -> dict[str, Any]:
        return {"id": row.id, "year": row.year, "candidate_name": row.candidate_name, "party": row.party, "party_symbol": row.party_symbol, "state": row.state, "constituency": row.constituency, "votes": row.votes, "vote_share": row.vote_share, "winner": row.winner, "gender": row.gender, "age": row.age, "category": row.category, "source_file": row.source_file}

    def _detail_sql(self, where: str = "", order: str = "") -> str:
        return f"""SELECT cr.candidate_result_id, e.election_year AS year, COALESCE(ds.original_filename, 'MySQL ECI import') AS source_file, s.state_name AS state, cv.constituency_name AS constituency, c.candidate_name, p.party_name AS party, COALESCE(p.party_symbol,p.party_abbreviation) AS party_symbol, cr.votes_received AS votes, cr.vote_share_percentage AS vote_share, cr.is_winner AS winner, ec.total_votes_polled, ec.valid_votes, ec.registered_electors AS total_electors, c.gender, cr.candidate_age AS age, cr.candidate_category AS category FROM candidate_results cr JOIN candidates c ON c.candidate_id=cr.candidate_id JOIN election_constituencies ec ON ec.election_constituency_id=cr.election_constituency_id JOIN elections e ON e.election_id=ec.election_id JOIN constituency_versions cv ON cv.constituency_version_id=ec.constituency_version_id JOIN constituencies co ON co.constituency_id=cv.constituency_id JOIN states s ON s.state_id=co.state_id LEFT JOIN parties p ON p.party_id=cr.party_id LEFT JOIN data_sources ds ON ds.election_id=e.election_id {where} {order}"""

    def _rows(self, year: int | None = None) -> list[Row]:
        where = " WHERE e.election_year=%s" if year is not None else ""
        values = (year,) if year is not None else ()
        return [self._row(row) for row in self._query(self._detail_sql(where, "ORDER BY e.election_year,cr.is_winner DESC,cr.votes_received DESC"), values)]

    def elections(self) -> list[dict[str, Any]]:
        rows = self._query("SELECT e.election_year AS year, COUNT(DISTINCT cr.candidate_result_id) AS candidate_count, COUNT(DISTINCT ec.election_constituency_id) AS constituency_count FROM elections e LEFT JOIN election_constituencies ec ON ec.election_id=e.election_id LEFT JOIN candidate_results cr ON cr.election_constituency_id=ec.election_constituency_id GROUP BY e.election_id,e.election_year ORDER BY e.election_year")
        winners = {row["election_year"]: row["count"] for row in self._query("SELECT election_year, COUNT(*) AS count FROM official_winners GROUP BY election_year")}
        return [{"year": int(row["year"]), "name": f"Lok Sabha General Election {row['year']}", "candidate_count": int(row["candidate_count"] or 0), "constituency_count": int(winners.get(row["year"], row["constituency_count"] or 0)), "winner_count": int(winners.get(row["year"], 0)), "source_coverage": "MySQL normalized ECI import"} for row in rows]

    def overview(self, year: int) -> dict[str, Any]:
        row = self._query("SELECT COUNT(DISTINCT cr.candidate_result_id) AS candidate_count, COUNT(DISTINCT ec.election_constituency_id) AS constituency_count, COUNT(DISTINCT s.state_id) AS state_count, COALESCE(SUM(cr.votes_received),0) AS total_votes FROM candidate_results cr JOIN election_constituencies ec ON ec.election_constituency_id=cr.election_constituency_id JOIN elections e ON e.election_id=ec.election_id JOIN constituency_versions cv ON cv.constituency_version_id=ec.constituency_version_id JOIN constituencies co ON co.constituency_id=cv.constituency_id JOIN states s ON s.state_id=co.state_id WHERE e.election_year=%s", (year,))[0]
        winner_count = self._query("SELECT COUNT(*) AS count FROM official_winners WHERE election_year=%s", (year,))[0]["count"]
        return {"year": year, "candidate_count": int(row["candidate_count"] or 0), "constituency_count": int(winner_count or row["constituency_count"] or 0), "state_count": int(row["state_count"] or 0), "winner_count": int(winner_count), "total_votes": int(row["total_votes"] or 0), "source_files": ["MySQL normalized ECI import"], "coverage_note": "NOTA is excluded from candidate counts. Official successful candidates are listed in the MySQL official_winners table; unmatched records have blank detailed-result fields." if year == 2014 else None, "top_parties": self.party_summaries(year, 8)}

    def party_summaries(self, year: int, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._query("SELECT COALESCE(p.party_name,'Unspecified') AS party, COUNT(*) AS candidates, COALESCE(SUM(cr.votes_received),0) AS votes FROM candidate_results cr JOIN election_constituencies ec ON ec.election_constituency_id=cr.election_constituency_id JOIN elections e ON e.election_id=ec.election_id LEFT JOIN parties p ON p.party_id=cr.party_id WHERE e.election_year=%s GROUP BY COALESCE(p.party_name,'Unspecified')", (year,))
        seats = self._query("SELECT COALESCE(party_name,'Unspecified') AS party, COUNT(*) AS seats FROM official_winners WHERE election_year=%s GROUP BY COALESCE(party_name,'Unspecified')", (year,))
        seat_map = {row["party"]: int(row["seats"]) for row in seats}
        result = [{"party": row["party"], "candidates": int(row["candidates"]), "seats": seat_map.get(row["party"], 0), "votes": int(row["votes"] or 0)} for row in rows]
        result.sort(key=lambda item: (-item["seats"], -item["votes"], item["party"]))
        return result[:limit]

    def states(self, year: int) -> list[dict[str, Any]]:
        rows = self._query("SELECT s.state_name AS state, COUNT(DISTINCT cr.candidate_result_id) AS candidates, COUNT(DISTINCT ec.election_constituency_id) AS constituencies, COALESCE(SUM(cr.votes_received),0) AS votes FROM candidate_results cr JOIN election_constituencies ec ON ec.election_constituency_id=cr.election_constituency_id JOIN elections e ON e.election_id=ec.election_id JOIN constituency_versions cv ON cv.constituency_version_id=ec.constituency_version_id JOIN constituencies co ON co.constituency_id=cv.constituency_id JOIN states s ON s.state_id=co.state_id WHERE e.election_year=%s GROUP BY s.state_name", (year,))
        seats = self._query("SELECT state_name AS state, COUNT(*) AS seats, COUNT(*) AS constituencies FROM official_winners WHERE election_year=%s GROUP BY state_name", (year,))
        seat_map = {row["state"]: int(row["seats"]) for row in seats}
        result = [{"state": row["state"], "candidates": int(row["candidates"]), "constituencies": int(next((seat["constituencies"] for seat in seats if seat["state"] == row["state"]), row["constituencies"])), "seats": seat_map.get(row["state"], 0), "votes": int(row["votes"] or 0)} for row in rows]
        known = {row["state"] for row in rows}
        result.extend({"state": row["state"], "candidates": 0, "constituencies": 0, "seats": int(row["seats"]), "votes": 0} for row in seats if row["state"] not in known)
        return sorted(result, key=lambda item: (-item["seats"], item["state"]))

    def winners(self, year: int | None = None, search: str | None = None, state: str | None = None, limit: int = 100, offset: int = 0) -> tuple[list[dict[str, Any]], int]:
        clauses, values = [], []
        if year is not None:
            clauses.append("ow.election_year=%s")
            values.append(year)
        if state:
            clauses.append("LOWER(ow.state_name)=LOWER(%s)")
            values.append(state)
        if search:
            clauses.append("(LOWER(ow.winner_name) LIKE LOWER(%s) OR LOWER(ow.constituency_name) LIKE LOWER(%s) OR LOWER(COALESCE(ow.party_name,'')) LIKE LOWER(%s) OR LOWER(ow.state_name) LIKE LOWER(%s))")
            values.extend([f"%{search}%"] * 4)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self._query(f"SELECT ow.winner_id AS id, ow.election_year AS year, ow.state_name AS state, ow.constituency_name AS constituency, ow.winner_name AS winner, ow.party_name AS party, COALESCE(ow.candidate_name_db,ow.winner_name) AS candidate_name, ow.match_status, ow.source_file, ow.source_sheet, cr.candidate_result_id, cr.votes_received AS votes, cr.vote_share_percentage AS vote_share FROM official_winners ow LEFT JOIN candidate_results cr ON cr.candidate_result_id=ow.candidate_result_id {where} ORDER BY ow.election_year,ow.state_name,ow.constituency_name", tuple(values))
        return rows[offset:offset + limit], len(rows)

    def winner_by_id(self, winner_id: str) -> dict[str, Any] | None:
        rows, _ = self.winners(search=None, limit=100000)
        return next((row for row in rows if row["id"] == winner_id), None)

    def candidates(self, year: int | None = None, search: str | None = None, state: str | None = None, party: str | None = None, limit: int = 25, offset: int = 0) -> tuple[list[Row], int]:
        clauses, values = [], []
        if year is not None:
            clauses.append("e.election_year=%s")
            values.append(year)
        if state:
            clauses.append("LOWER(s.state_name)=LOWER(%s)")
            values.append(state)
        if party:
            clauses.append("LOWER(COALESCE(p.party_name,''))=LOWER(%s)")
            values.append(party)
        if search:
            clauses.append("(LOWER(c.candidate_name) LIKE LOWER(%s) OR LOWER(cv.constituency_name) LIKE LOWER(%s) OR LOWER(s.state_name) LIKE LOWER(%s) OR LOWER(COALESCE(p.party_name,'')) LIKE LOWER(%s))")
            values.extend([f"%{search}%"] * 4)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = [self._row(row) for row in self._query(self._detail_sql(where, "ORDER BY cr.is_winner DESC,cr.votes_received DESC,c.candidate_name"), tuple(values))]
        return rows[offset:offset + limit], len(rows)

    def by_id(self, candidate_id: str) -> Row | None:
        rows, _ = self.candidates(limit=1, offset=0, search=None)
        row = self._query(self._detail_sql(" WHERE cr.candidate_result_id=%s", "LIMIT 1"), (candidate_id,))
        return self._row(row[0]) if row else None

    def history(self, candidate_name: str) -> list[Row]:
        return [self._row(row) for row in self._query(self._detail_sql(" WHERE LOWER(c.candidate_name)=LOWER(%s)", "ORDER BY e.election_year"), (candidate_name,))]

    def constituencies(self, year: int, search: str | None = None, state: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        clauses, values = ["e.election_year=%s"], [year]
        if state:
            clauses.append("LOWER(s.state_name)=LOWER(%s)")
            values.append(state)
        if search:
            clauses.append("(LOWER(s.state_name) LIKE LOWER(%s) OR LOWER(cv.constituency_name) LIKE LOWER(%s))")
            values.extend([f"%{search}%"] * 2)
        rows = self._query(self._detail_sql(" WHERE " + " AND ".join(clauses), "ORDER BY s.state_name,cv.constituency_name"), tuple(values))
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[(row["state"], row["constituency"])].append(row)
        official = {(row["state_name"], row["constituency_name"]): row for row in self._query("SELECT * FROM official_winners WHERE election_year=%s", (year,))}
        result = []
        for key, items in grouped.items():
            ranked = sorted(items, key=lambda item: (-int(item["votes"] or 0), item["candidate_name"]))
            winner = next((item for item in items if item["winner"]), ranked[0] if ranked else None)
            runner = ranked[1] if len(ranked) > 1 else None
            result.append({"year": year, "state": key[0], "constituency": key[1], "winner": self.public_row(self._row(winner)) if winner else None, "candidate_count": len(items), "total_votes": sum(int(item["votes"] or 0) for item in items), "margin": int(winner["votes"] - runner["votes"]) if winner and runner else None, "source_file": winner.get("source_file") if winner else "MySQL ECI import"})
        for key, item in official.items():
            if key not in grouped:
                result.append({"year": year, "state": key[0], "constituency": key[1], "winner": {"id": item["winner_id"], "year": year, "candidate_name": item["candidate_name_db"] or item["winner_name"], "party": item["party_name"], "state": key[0], "constituency": key[1], "votes": None, "vote_share": None, "winner": True, "source_file": item["source_file"]}, "candidate_count": 0, "total_votes": 0, "margin": None, "source_file": item["source_file"]})
        return result[:limit]

    def source_catalog(self) -> list[dict[str, Any]]:
        return [{"title": "ECI normalized election results", "source_type": "mysql", "locator": "electoraw.elections, candidate_results, official_winners", "years": list(YEARS)}]
