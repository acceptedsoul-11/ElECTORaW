"""Idempotently copy the legacy SQLite workflow into MySQL electoraw."""

from __future__ import annotations

import sqlite3
import re
from datetime import datetime
from pathlib import Path

import mysql.connector

from ..config import settings
from .mysql_workflow import MySQLWorkflowStore


def dt(value: str | None):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None) if value else None


def phone(value: str | None) -> str | None:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits if len(digits) == 10 else None


def main() -> None:
    sqlite_path = settings.workflow_db_path
    if not sqlite_path.exists():
        print(f"SQLite source not found: {sqlite_path}")
        return

    MySQLWorkflowStore()
    mysql_db = mysql.connector.connect(host=settings.mysql_host, port=settings.mysql_port, database=settings.mysql_database, user=settings.mysql_user, password=settings.mysql_password, connection_timeout=5)
    sqlite_db = sqlite3.connect(sqlite_path)
    sqlite_db.row_factory = sqlite3.Row
    try:
        cursor = mysql_db.cursor()
        counts: dict[str, int] = {}
        users = sqlite_db.execute("SELECT * FROM users").fetchall()
        for row in users:
            cursor.execute("INSERT INTO workflow_users (id,email,password_hash,full_name,role,phone,voter_id,state,constituency,status,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE email=VALUES(email),password_hash=VALUES(password_hash),full_name=VALUES(full_name),role=VALUES(role),phone=VALUES(phone),voter_id=VALUES(voter_id),state=VALUES(state),constituency=VALUES(constituency),status=VALUES(status)", (row["id"], row["email"], row["password_hash"], row["full_name"], row["role"], phone(row["phone"]), row["voter_id"], row["state"], row["constituency"], row["status"], dt(row["created_at"])))
        counts["users"] = len(users)

        elections = sqlite_db.execute("SELECT * FROM elections").fetchall()
        for row in elections:
            cursor.execute("INSERT INTO workflow_elections (id,year,election_date,title,scope,scope_state,status,declared_by,declared_at,closed_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE year=VALUES(year),election_date=VALUES(election_date),title=VALUES(title),scope=VALUES(scope),scope_state=VALUES(scope_state),status=VALUES(status),declared_by=VALUES(declared_by),closed_at=VALUES(closed_at)", (row["id"], row["year"], row["election_date"], row["title"], row["scope"], row["scope_state"], row["status"], row["declared_by"], dt(row["declared_at"]), dt(row["closed_at"])))
        counts["elections"] = len(elections)

        seats = sqlite_db.execute("SELECT * FROM election_constituencies").fetchall()
        for row in seats:
            cursor.execute("INSERT INTO workflow_election_constituencies (id,election_id,year,state,constituency) VALUES (%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE year=VALUES(year),state=VALUES(state),constituency=VALUES(constituency)", tuple(row[key] for key in ("id", "election_id", "year", "state", "constituency")))
        counts["election_constituencies"] = len(seats)

        nominations = sqlite_db.execute("SELECT * FROM nominations").fetchall()
        for row in nominations:
            cursor.execute("INSERT INTO workflow_nominations (id,election_id,candidate_user_id,state,constituency,candidate_name,party,status,is_winner,form_json,submitted_at,reviewed_at,reviewed_by,review_note,nomination_pdf_path,digital_signature,authenticated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE status=VALUES(status),is_winner=VALUES(is_winner),form_json=VALUES(form_json),reviewed_at=VALUES(reviewed_at),reviewed_by=VALUES(reviewed_by),review_note=VALUES(review_note),nomination_pdf_path=VALUES(nomination_pdf_path),digital_signature=NULL,authenticated_at=VALUES(authenticated_at)", (row["id"], row["election_id"], row["candidate_user_id"], row["state"], row["constituency"], row["candidate_name"], row["party"], row["status"], bool(row["is_winner"]), row["form_json"], dt(row["submitted_at"]), dt(row["reviewed_at"]), row["reviewed_by"], row["review_note"], row["nomination_pdf_path"], None, dt(row["authenticated_at"])))
        counts["nominations"] = len(nominations)

        certificates = sqlite_db.execute("SELECT * FROM certificates").fetchall()
        for row in certificates:
            cursor.execute("INSERT INTO workflow_certificates (id,nomination_id,candidate_user_id,certificate_number,pdf_path,issued_at,issued_by) VALUES (%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE certificate_number=VALUES(certificate_number),pdf_path=VALUES(pdf_path),issued_at=VALUES(issued_at),issued_by=VALUES(issued_by)", (row["id"], row["nomination_id"], row["candidate_user_id"], row["certificate_number"], row["pdf_path"], dt(row["issued_at"]), row["issued_by"]))
        counts["certificates"] = len(certificates)

        audits = sqlite_db.execute("SELECT * FROM audit_log").fetchall()
        for row in audits:
            cursor.execute("INSERT INTO workflow_audit_log (id,user_id,action,entity_type,entity_id,details_json,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE details_json=VALUES(details_json)", (row["id"], row["user_id"], row["action"], row["entity_type"], row["entity_id"], row["details_json"], dt(row["created_at"])))
        counts["audit_log"] = len(audits)
        mysql_db.commit()
        print("SQLite to MySQL workflow migration complete")
        for table, count in counts.items():
            print(f"{table}: {count}")
    finally:
        sqlite_db.close()
        mysql_db.close()


if __name__ == "__main__":
    main()
