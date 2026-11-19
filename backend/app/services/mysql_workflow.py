from __future__ import annotations

import json
import re
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

import mysql.connector

from ..config import settings
from .workflow import _json, _loads, now_iso, uid


def _mysql_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def _mysql_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def _iso(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


class MySQLWorkflowStore:
    """Transactional MySQL workflow store used by the application runtime."""

    def __init__(self) -> None:
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[Any]:
        connection = mysql.connector.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            database=settings.mysql_database,
            user=settings.mysql_user,
            password=settings.mysql_password,
            connection_timeout=5,
        )
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        schema = Path(__file__).resolve().parents[3] / "database" / "mysql" / "02_workflow_schema.sql"
        statements = []
        for part in schema.read_text(encoding="utf-8").split(";"):
            cleaned = re.sub(r"(?m)^\s*--.*$", "", part).strip()
            if cleaned:
                statements.append(cleaned)
        with self._connection() as db:
            cursor = db.cursor()
            for statement in statements:
                cursor.execute(statement)
            # Legacy SQLite declarations may predate the required date field.
            # New API declarations still require a date; old rows remain nullable.
            cursor.execute("ALTER TABLE workflow_elections MODIFY COLUMN election_date DATE NULL")
            cursor.close()

    @staticmethod
    def _row(row: dict[str, Any] | None) -> dict[str, Any] | None:
        if row is None:
            return None
        result = {key: _iso(value) for key, value in row.items()}
        for key in ("is_winner",):
            result[key] = bool(row.get(key))
        return result

    @classmethod
    def _nomination(cls, row: dict[str, Any] | None) -> dict[str, Any] | None:
        result = cls._row(row)
        if result is None:
            return None
        raw_form = row.get("form_json")
        result["form"] = raw_form if isinstance(raw_form, dict) else _loads(raw_form, {})
        result.pop("form_json", None)
        return result

    def _fetchone(self, query: str, values: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self._connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute(query, values)
            row = cursor.fetchone()
            cursor.close()
            return row

    def create_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        user = {"id": uid("usr"), "created_at": now_iso(), **payload}
        with self._connection() as db:
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO workflow_users (id,email,password_hash,full_name,role,phone,voter_id,state,constituency,status,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                tuple(user.get(key) for key in ("id", "email", "password_hash", "full_name", "role", "phone", "voter_id", "state", "constituency", "status", "created_at")),
            )
            cursor.close()
        return self.get_user(user["id"]) or user

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return self._row(self._fetchone("SELECT * FROM workflow_users WHERE id=%s", (user_id,)))

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        return self._row(self._fetchone("SELECT * FROM workflow_users WHERE email=%s", (email.lower().strip(),)))

    def audit(self, user_id: str | None, action: str, entity_type: str, entity_id: str | None, details: Any = None) -> None:
        with self._connection() as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO workflow_audit_log (id,user_id,action,entity_type,entity_id,details_json,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)", (uid("audit"), user_id, action, entity_type, entity_id, _json(details or {}), _mysql_datetime(now_iso())))
            cursor.close()

    def create_election(self, officer_id: str, payload: dict[str, Any], constituencies: list[dict[str, Any]]) -> dict[str, Any]:
        election_id, created_at = uid("elc"), now_iso()
        with self._connection() as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO workflow_elections (id,year,election_date,title,scope,scope_state,status,declared_by,declared_at) VALUES (%s,%s,%s,%s,%s,%s,'open',%s,%s)", (election_id, payload["year"], _mysql_date(payload["election_date"]), payload["title"], payload["scope"], payload.get("scope_state"), officer_id, _mysql_datetime(created_at)))
            cursor.executemany("INSERT INTO workflow_election_constituencies (id,election_id,year,state,constituency) VALUES (%s,%s,%s,%s,%s)", [(uid("seat"), election_id, payload["year"], item["state"], item["constituency"]) for item in constituencies])
            cursor.close()
        self.audit(officer_id, "declare", "election", election_id, {"scope": payload["scope"], "constituency_count": len(constituencies)})
        return self.get_election(election_id) or {}

    def list_elections(self, include_deleted: bool = False) -> list[dict[str, Any]]:
        query = "SELECT e.*, (SELECT COUNT(*) FROM workflow_election_constituencies ec WHERE ec.election_id=e.id) AS constituency_count, (SELECT COUNT(*) FROM workflow_nominations n WHERE n.election_id=e.id) AS nomination_count FROM workflow_elections e"
        if not include_deleted:
            query += " WHERE e.status != 'deleted'"
        query += " ORDER BY e.declared_at DESC"
        with self._connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()
        return [{**self._row(row), "constituency_count": row["constituency_count"], "nomination_count": row["nomination_count"]} for row in rows]

    def get_election(self, election_id: str) -> dict[str, Any] | None:
        row = self._fetchone("SELECT e.*, (SELECT COUNT(*) FROM workflow_election_constituencies ec WHERE ec.election_id=e.id) AS constituency_count, (SELECT COUNT(*) FROM workflow_nominations n WHERE n.election_id=e.id) AS nomination_count FROM workflow_elections e WHERE e.id=%s", (election_id,))
        if not row:
            return None
        result = {**self._row(row), "constituency_count": row["constituency_count"], "nomination_count": row["nomination_count"]}
        with self._connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT id,year,state,constituency FROM workflow_election_constituencies WHERE election_id=%s ORDER BY state,constituency", (election_id,))
            result["constituencies"] = cursor.fetchall()
            cursor.close()
        return result

    def find_election_seat(self, election_id: str, state: str, constituency: str) -> dict[str, Any] | None:
        return self._row(self._fetchone("SELECT id,year,state,constituency FROM workflow_election_constituencies WHERE election_id=%s AND LOWER(state)=LOWER(%s) AND LOWER(constituency)=LOWER(%s)", (election_id, state, constituency)))

    def close_election(self, election_id: str, officer_id: str) -> dict[str, Any] | None:
        with self._connection() as db:
            cursor = db.cursor()
            cursor.execute("UPDATE workflow_elections SET status='closed', closed_at=%s WHERE id=%s AND status='open'", (_mysql_datetime(now_iso()), election_id))
            cursor.close()
        self.audit(officer_id, "close", "election", election_id)
        return self.get_election(election_id)

    def delete_election(self, election_id: str, officer_id: str) -> dict[str, Any] | None:
        with self._connection() as db:
            cursor = db.cursor()
            cursor.execute("UPDATE workflow_elections SET status='deleted' WHERE id=%s AND status != 'deleted'", (election_id,))
            cursor.close()
        self.audit(officer_id, "delete", "election", election_id)
        return self.get_election(election_id)

    def create_nomination(self, candidate_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        nomination_id = uid("nom")
        with self._connection() as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO workflow_nominations (id,election_id,candidate_user_id,state,constituency,candidate_name,party,status,is_winner,form_json,submitted_at) VALUES (%s,%s,%s,%s,%s,%s,%s,'pending',FALSE,%s,%s)", (nomination_id, payload["election_id"], candidate_id, payload["state"], payload["constituency"], payload["candidate_name"], payload.get("party"), _json(payload["form"]), _mysql_datetime(now_iso())))
            cursor.close()
        return self.get_nomination(nomination_id) or {}

    def get_nomination(self, nomination_id: str) -> dict[str, Any] | None:
        row = self._fetchone("SELECT n.*, e.title AS election_title, e.year AS election_year, e.status AS election_status FROM workflow_nominations n JOIN workflow_elections e ON e.id=n.election_id WHERE n.id=%s", (nomination_id,))
        return self._nomination(row)

    def list_nominations(self, candidate_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        clauses, values = [], []
        if candidate_id:
            clauses.append("n.candidate_user_id=%s")
            values.append(candidate_id)
        if status:
            clauses.append("n.status=%s")
            values.append(status)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        query = f"SELECT n.*, e.title AS election_title, e.year AS election_year, e.status AS election_status FROM workflow_nominations n JOIN workflow_elections e ON e.id=n.election_id{where} ORDER BY n.submitted_at DESC"
        with self._connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute(query, tuple(values))
            rows = cursor.fetchall()
            cursor.close()
        return [self._nomination(row) for row in rows]

    def review_nomination(self, nomination_id: str, officer_id: str, status: str, is_winner: bool, note: str | None) -> dict[str, Any] | None:
        current = self._fetchone("SELECT status FROM workflow_nominations WHERE id=%s", (nomination_id,))
        if not current:
            return None
        if is_winner and status != "accepted":
            raise ValueError("Accept the nomination before marking it as the winner")
        if status == "rejected" and current["status"] != "pending":
            raise ValueError("Only pending nominations can be rejected")
        if status == "accepted" and current["status"] not in {"pending", "accepted"}:
            raise ValueError("This nomination cannot be accepted from its current status")
        reviewed_at = now_iso()
        try:
            with self._connection() as db:
                cursor = db.cursor()
                cursor.execute("UPDATE workflow_nominations SET status=%s,is_winner=%s,reviewed_at=%s,reviewed_by=%s,review_note=%s WHERE id=%s", (status, is_winner, _mysql_datetime(reviewed_at), officer_id, note, nomination_id))
                cursor.close()
        except mysql.connector.Error as exc:
            if exc.errno == 1062:
                raise ValueError("A winner has already been recorded for this constituency") from exc
            raise
        self.audit(officer_id, "review", "nomination", nomination_id, {"status": status, "is_winner": is_winner})
        return self.get_nomination(nomination_id)

    def authenticate_nomination(self, nomination_id: str, pdf_path: str, signature: str | None, authenticated_at: str) -> dict[str, Any] | None:
        with self._connection() as db:
            cursor = db.cursor()
            cursor.execute("UPDATE workflow_nominations SET nomination_pdf_path=%s,digital_signature=%s,authenticated_at=%s WHERE id=%s", (pdf_path, signature, _mysql_datetime(authenticated_at), nomination_id))
            cursor.close()
        return self.get_nomination(nomination_id)

    def create_certificate(self, nomination: dict[str, Any], officer_id: str, pdf_path: str, certificate_number: str | None = None) -> dict[str, Any]:
        certificate_id = uid("cert")
        certificate_number = certificate_number or f"EAW-{datetime.now().year}-{uid('')[-8:].upper()}"
        with self._connection() as db:
            cursor = db.cursor()
            cursor.execute("INSERT INTO workflow_certificates (id,nomination_id,candidate_user_id,certificate_number,pdf_path,issued_at,issued_by) VALUES (%s,%s,%s,%s,%s,%s,%s)", (certificate_id, nomination["id"], nomination["candidate_user_id"], certificate_number, pdf_path, _mysql_datetime(now_iso()), officer_id))
            cursor.close()
        self.audit(officer_id, "award", "certificate", certificate_id, {"nomination_id": nomination["id"]})
        return self.get_certificate(certificate_id) or {}

    def get_certificate(self, certificate_id: str) -> dict[str, Any] | None:
        return self._row(self._fetchone("SELECT c.*, n.candidate_name, n.state, n.constituency, n.election_id FROM workflow_certificates c JOIN workflow_nominations n ON n.id=c.nomination_id WHERE c.id=%s", (certificate_id,)))

    def get_certificate_for_nomination(self, nomination_id: str) -> dict[str, Any] | None:
        row = self._fetchone("SELECT id FROM workflow_certificates WHERE nomination_id=%s", (nomination_id,))
        return self.get_certificate(row["id"]) if row else None

    def list_certificates(self, candidate_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT c.*, n.candidate_name, n.state, n.constituency, n.election_id FROM workflow_certificates c JOIN workflow_nominations n ON n.id=c.nomination_id"
        values: tuple[Any, ...] = ()
        if candidate_id:
            query += " WHERE c.candidate_user_id=%s"
            values = (candidate_id,)
        query += " ORDER BY c.issued_at DESC"
        with self._connection() as db:
            cursor = db.cursor(dictionary=True)
            cursor.execute(query, values)
            rows = cursor.fetchall()
            cursor.close()
        return [self._row(row) for row in rows]

