"""Populate analytical MySQL tables from the curated local ECI artifacts."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import mysql.connector

from ..config import settings
from .import_eci_to_mysql_data import main as import_candidate_results
from .initialize_mysql import main as initialize_mysql


def clean(value: str | None) -> str:
    return " ".join((value or "").strip().split())


def winner_id(year: int, state: str, constituency: str) -> str:
    return hashlib.sha256(f"winner|{year}|{state}|{constituency}".encode()).hexdigest()[:20]


def load_official_winners() -> int:
    root = Path(__file__).resolve().parents[3] / "data" / "processed"
    rows: dict[str, dict[str, str]] = {}
    for filename, status in (("official_winners_matched.csv", "matched"), ("official_winners_unmatched.csv", "official_only"), ("official_winners_supplemental.csv", "official_only")):
        path = root / filename
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8-sig") as handle:
            for item in csv.DictReader(handle):
                year, state, constituency = int(item["year"]), clean(item["state"]), clean(item["constituency"])
                key = winner_id(year, state, constituency)
                rows[key] = {"winner_id": key, "election_year": str(year), "state_name": state, "constituency_name": constituency, "winner_name": clean(item.get("winner")), "party_name": clean(item.get("party")) or None, "candidate_name_db": clean(item.get("candidate_name_db")) or None, "match_status": status, "source_file": clean(item.get("source_file")) or filename, "source_sheet": clean(item.get("source_sheet")) or None, "candidate_result_id": item.get("candidate_result_id") or None}
    connection = mysql.connector.connect(host=settings.mysql_host, port=settings.mysql_port, database=settings.mysql_database, user=settings.mysql_user, password=settings.mysql_password, connection_timeout=5)
    try:
        cursor = connection.cursor()
        for item in rows.values():
            cursor.execute("INSERT INTO official_winners (winner_id,election_year,state_name,constituency_name,winner_name,party_name,candidate_name_db,match_status,source_file,source_sheet,candidate_result_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE winner_name=VALUES(winner_name),party_name=VALUES(party_name),candidate_name_db=VALUES(candidate_name_db),match_status=VALUES(match_status),source_file=VALUES(source_file),source_sheet=VALUES(source_sheet),candidate_result_id=VALUES(candidate_result_id)", (
                item["winner_id"], item["election_year"], item["state_name"], item["constituency_name"],
                item["winner_name"], item["party_name"], item["candidate_name_db"], item["match_status"],
                item["source_file"], item["source_sheet"], item["candidate_result_id"],
            ))
        # Official winners are the authority; this flags matched detailed rows.
        cursor.execute("CREATE TEMPORARY TABLE tmp_winner_matches AS SELECT ow.winner_id,MIN(cr.candidate_result_id) AS candidate_result_id FROM official_winners ow JOIN elections e ON e.election_year=ow.election_year JOIN election_constituencies ec ON ec.election_id=e.election_id JOIN constituency_versions cv ON cv.constituency_version_id=ec.constituency_version_id JOIN constituencies co ON co.constituency_id=cv.constituency_id JOIN states s ON s.state_id=co.state_id JOIN candidate_results cr ON cr.election_constituency_id=ec.election_constituency_id JOIN candidates c ON c.candidate_id=cr.candidate_id WHERE LOWER(ow.state_name)=LOWER(s.state_name) AND LOWER(ow.constituency_name)=LOWER(cv.constituency_name) AND LOWER(COALESCE(ow.candidate_name_db,ow.winner_name))=LOWER(c.candidate_name) GROUP BY ow.winner_id")
        cursor.execute("UPDATE candidate_results SET is_winner=FALSE")
        cursor.execute("UPDATE candidate_results cr JOIN tmp_winner_matches wm ON wm.candidate_result_id=cr.candidate_result_id SET cr.is_winner=TRUE")
        cursor.execute("UPDATE official_winners ow JOIN tmp_winner_matches wm ON wm.winner_id=ow.winner_id SET ow.candidate_result_id=wm.candidate_result_id")
        connection.commit()
        cursor.close()
    finally:
        connection.close()
    return len(rows)


def main() -> None:
    initialize_mysql()
    connection = mysql.connector.connect(host=settings.mysql_host, port=settings.mysql_port, database=settings.mysql_database, user=settings.mysql_user, password=settings.mysql_password, connection_timeout=5)
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM candidate_results")
        has_results = cursor.fetchone()[0] > 0
        cursor.execute("SELECT COUNT(*) FROM official_winners")
        has_winners = cursor.fetchone()[0] > 0
        cursor.close()
    finally:
        connection.close()
    if not has_results:
        import_candidate_results()
    winner_count = load_official_winners()
    print(f"MySQL analytical data ready; official winners: {winner_count}")


if __name__ == "__main__":
    main()
