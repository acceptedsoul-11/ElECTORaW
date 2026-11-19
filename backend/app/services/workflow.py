from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Header, HTTPException

from ..config import settings


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _loads(value: str | None, fallback: Any) -> Any:
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


class RelationalWorkflowStore:
    """Legacy SQLite workflow store retained only for migration and tests."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings.workflow_db_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('elector', 'officer')),
                    phone TEXT,
                    voter_id TEXT,
                    state TEXT,
                    constituency TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

                CREATE TABLE IF NOT EXISTS elections (
                    id TEXT PRIMARY KEY,
                    year INTEGER NOT NULL,
                    election_date TEXT,
                    title TEXT NOT NULL,
                    scope TEXT NOT NULL CHECK (scope IN ('selected', 'state', 'all')),
                    scope_state TEXT,
                    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed', 'deleted')),
                    declared_by TEXT NOT NULL REFERENCES users(id),
                    declared_at TEXT NOT NULL,
                    closed_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_elections_status ON elections(status);

                CREATE TABLE IF NOT EXISTS election_constituencies (
                    id TEXT PRIMARY KEY,
                    election_id TEXT NOT NULL REFERENCES elections(id),
                    year INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    constituency TEXT NOT NULL,
                    UNIQUE(election_id, state, constituency)
                );

                CREATE TABLE IF NOT EXISTS nominations (
                    id TEXT PRIMARY KEY,
                    election_id TEXT NOT NULL REFERENCES elections(id),
                    candidate_user_id TEXT NOT NULL REFERENCES users(id),
                    state TEXT NOT NULL,
                    constituency TEXT NOT NULL,
                    candidate_name TEXT NOT NULL,
                    party TEXT,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected')),
                    is_winner INTEGER NOT NULL DEFAULT 0,
                    form_json TEXT NOT NULL,
                    submitted_at TEXT NOT NULL,
                    reviewed_at TEXT,
                    reviewed_by TEXT REFERENCES users(id),
                    review_note TEXT,
                    nomination_pdf_path TEXT,
                    digital_signature TEXT,
                    authenticated_at TEXT,
                    UNIQUE(election_id, state, constituency, candidate_user_id)
                );
                CREATE INDEX IF NOT EXISTS idx_nominations_status ON nominations(status);
                CREATE INDEX IF NOT EXISTS idx_nominations_candidate ON nominations(candidate_user_id);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_one_winner_per_seat ON nominations(election_id, state, constituency) WHERE is_winner = 1;

                CREATE TABLE IF NOT EXISTS certificates (
                    id TEXT PRIMARY KEY,
                    nomination_id TEXT NOT NULL UNIQUE REFERENCES nominations(id),
                    candidate_user_id TEXT NOT NULL REFERENCES users(id),
                    certificate_number TEXT NOT NULL UNIQUE,
                    pdf_path TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    issued_by TEXT NOT NULL REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS audit_log (
                    id TEXT PRIMARY KEY,
                    user_id TEXT REFERENCES users(id),
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT,
                    details_json TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )
            columns = {row["name"] for row in db.execute("PRAGMA table_info(elections)").fetchall()}
            if "election_date" not in columns:
                db.execute("ALTER TABLE elections ADD COLUMN election_date TEXT")
            nomination_columns = {row["name"] for row in db.execute("PRAGMA table_info(nominations)").fetchall()}
            if "nomination_pdf_path" not in nomination_columns:
                db.execute("ALTER TABLE nominations ADD COLUMN nomination_pdf_path TEXT")
            if "digital_signature" not in nomination_columns:
                db.execute("ALTER TABLE nominations ADD COLUMN digital_signature TEXT")
            if "authenticated_at" not in nomination_columns:
                db.execute("ALTER TABLE nominations ADD COLUMN authenticated_at TEXT")

    @staticmethod
    def _user(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {key: row[key] for key in row.keys()}

    @staticmethod
    def _election(row: sqlite3.Row, constituency_count: int = 0, nomination_count: int = 0) -> dict[str, Any]:
        return {**{key: row[key] for key in row.keys()}, "constituency_count": constituency_count, "nomination_count": nomination_count}

    @staticmethod
    def _nomination(row: sqlite3.Row) -> dict[str, Any]:
        result = {key: row[key] for key in row.keys()}
        result["form"] = _loads(result.pop("form_json", None), {})
        result["is_winner"] = bool(result["is_winner"])
        return result

    def create_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        user = {"id": uid("usr"), "created_at": now_iso(), **payload}
        with self._connect() as db:
            db.execute(
                "INSERT INTO users (id,email,password_hash,full_name,role,phone,voter_id,state,constituency,status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                tuple(user.get(key) for key in ("id", "email", "password_hash", "full_name", "role", "phone", "voter_id", "state", "constituency", "status", "created_at")),
            )
        return self.get_user(user["id"]) or user

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            return self._user(db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with self._connect() as db:
            return self._user(db.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone())

    def audit(self, user_id: str | None, action: str, entity_type: str, entity_id: str | None, details: Any = None) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO audit_log (id,user_id,action,entity_type,entity_id,details_json,created_at) VALUES (?,?,?,?,?,?,?)", (uid("audit"), user_id, action, entity_type, entity_id, _json(details or {}), now_iso()))

    def create_election(self, officer_id: str, payload: dict[str, Any], constituencies: list[dict[str, Any]]) -> dict[str, Any]:
        election_id = uid("elc")
        created_at = now_iso()
        with self._connect() as db:
            db.execute("INSERT INTO elections (id,year,election_date,title,scope,scope_state,status,declared_by,declared_at) VALUES (?,?,?,?,?,?,?,?,?)", (election_id, payload["year"], payload["election_date"], payload["title"], payload["scope"], payload.get("scope_state"), "open", officer_id, created_at))
            db.executemany("INSERT INTO election_constituencies (id,election_id,year,state,constituency) VALUES (?,?,?,?,?)", [(uid("seat"), election_id, payload["year"], item["state"], item["constituency"]) for item in constituencies])
        self.audit(officer_id, "declare", "election", election_id, {"scope": payload["scope"], "constituency_count": len(constituencies)})
        return self.get_election(election_id) or {}

    def list_elections(self, include_deleted: bool = False) -> list[dict[str, Any]]:
        query = "SELECT e.*, (SELECT COUNT(*) FROM election_constituencies ec WHERE ec.election_id=e.id) AS constituency_count, (SELECT COUNT(*) FROM nominations n WHERE n.election_id=e.id) AS nomination_count FROM elections e"
        if not include_deleted:
            query += " WHERE e.status != 'deleted'"
        query += " ORDER BY e.declared_at DESC"
        with self._connect() as db:
            return [self._election(row, row["constituency_count"], row["nomination_count"]) for row in db.execute(query).fetchall()]

    def get_election(self, election_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT e.*, (SELECT COUNT(*) FROM election_constituencies ec WHERE ec.election_id=e.id) AS constituency_count, (SELECT COUNT(*) FROM nominations n WHERE n.election_id=e.id) AS nomination_count FROM elections e WHERE e.id = ?", (election_id,)).fetchone()
            if not row:
                return None
            result = self._election(row, row["constituency_count"], row["nomination_count"])
            result["constituencies"] = [{key: seat[key] for key in seat.keys()} for seat in db.execute("SELECT id,year,state,constituency FROM election_constituencies WHERE election_id=? ORDER BY state,constituency", (election_id,)).fetchall()]
            return result

    def find_election_seat(self, election_id: str, state: str, constituency: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT id,year,state,constituency FROM election_constituencies WHERE election_id=? AND lower(state)=lower(?) AND lower(constituency)=lower(?)", (election_id, state, constituency)).fetchone()
            return {key: row[key] for key in row.keys()} if row else None

    def close_election(self, election_id: str, officer_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            db.execute("UPDATE elections SET status='closed', closed_at=? WHERE id=? AND status='open'", (now_iso(), election_id))
        self.audit(officer_id, "close", "election", election_id)
        return self.get_election(election_id)

    def delete_election(self, election_id: str, officer_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            db.execute("UPDATE elections SET status='deleted' WHERE id=? AND status != 'deleted'", (election_id,))
        self.audit(officer_id, "delete", "election", election_id)
        return self.get_election(election_id)

    def create_nomination(self, candidate_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        nomination_id = uid("nom")
        with self._connect() as db:
            db.execute("INSERT INTO nominations (id,election_id,candidate_user_id,state,constituency,candidate_name,party,status,is_winner,form_json,submitted_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (nomination_id, payload["election_id"], candidate_id, payload["state"], payload["constituency"], payload["candidate_name"], payload.get("party"), "pending", 0, _json(payload["form"]), now_iso()))
        return self.get_nomination(nomination_id) or {}

    def get_nomination(self, nomination_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            return self._nomination(db.execute("SELECT n.*, e.title AS election_title, e.year AS election_year, e.status AS election_status FROM nominations n JOIN elections e ON e.id=n.election_id WHERE n.id=?", (nomination_id,)).fetchone()) if db.execute("SELECT 1 FROM nominations WHERE id=?", (nomination_id,)).fetchone() else None

    def list_nominations(self, candidate_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        clauses: list[str] = []
        values: list[Any] = []
        if candidate_id:
            clauses.append("n.candidate_user_id=?")
            values.append(candidate_id)
        if status:
            clauses.append("n.status=?")
            values.append(status)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as db:
            rows = db.execute(f"SELECT n.*, e.title AS election_title, e.year AS election_year, e.status AS election_status FROM nominations n JOIN elections e ON e.id=n.election_id{where} ORDER BY n.submitted_at DESC", values).fetchall()
            return [self._nomination(row) for row in rows]

    def review_nomination(self, nomination_id: str, officer_id: str, status: str, is_winner: bool, note: str | None) -> dict[str, Any] | None:
        with self._connect() as db:
            current = db.execute("SELECT status FROM nominations WHERE id=?", (nomination_id,)).fetchone()
            if not current:
                return None
            if is_winner and status != "accepted":
                raise ValueError("Accept the nomination before marking it as the winner")
            if status == "rejected" and current["status"] != "pending":
                raise ValueError("Only pending nominations can be rejected")
            if status == "accepted" and current["status"] not in {"pending", "accepted"}:
                raise ValueError("This nomination cannot be accepted from its current status")
            if is_winner:
                existing = db.execute("SELECT id FROM nominations WHERE election_id=(SELECT election_id FROM nominations WHERE id=?) AND lower(state)=lower((SELECT state FROM nominations WHERE id=?)) AND lower(constituency)=lower((SELECT constituency FROM nominations WHERE id=?)) AND is_winner=1 AND id!=?", (nomination_id, nomination_id, nomination_id, nomination_id)).fetchone()
                if existing:
                    raise ValueError("A winner has already been recorded for this constituency")
            db.execute("UPDATE nominations SET status=?, is_winner=?, reviewed_at=?, reviewed_by=?, review_note=? WHERE id=?", (status, int(is_winner), now_iso(), officer_id, note, nomination_id))
        self.audit(officer_id, "review", "nomination", nomination_id, {"status": status, "is_winner": is_winner})
        return self.get_nomination(nomination_id)

    def authenticate_nomination(self, nomination_id: str, pdf_path: str, signature: str | None, authenticated_at: str) -> dict[str, Any] | None:
        with self._connect() as db:
            db.execute("UPDATE nominations SET nomination_pdf_path=?, digital_signature=?, authenticated_at=? WHERE id=?", (pdf_path, signature, authenticated_at, nomination_id))
        return self.get_nomination(nomination_id)

    def create_certificate(self, nomination: dict[str, Any], officer_id: str, pdf_path: str, certificate_number: str | None = None) -> dict[str, Any]:
        certificate_id = uid("cert")
        certificate_number = certificate_number or f"EAW-{datetime.now().year}-{secrets.token_hex(4).upper()}"
        issued_at = now_iso()
        with self._connect() as db:
            db.execute("INSERT INTO certificates (id,nomination_id,candidate_user_id,certificate_number,pdf_path,issued_at,issued_by) VALUES (?,?,?,?,?,?,?)", (certificate_id, nomination["id"], nomination["candidate_user_id"], certificate_number, pdf_path, issued_at, officer_id))
        self.audit(officer_id, "award", "certificate", certificate_id, {"nomination_id": nomination["id"]})
        return self.get_certificate(certificate_id) or {}

    def get_certificate(self, certificate_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT c.*, n.candidate_name, n.state, n.constituency, n.election_id FROM certificates c JOIN nominations n ON n.id=c.nomination_id WHERE c.id=?", (certificate_id,)).fetchone()
            return {key: row[key] for key in row.keys()} if row else None

    def get_certificate_for_nomination(self, nomination_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT id FROM certificates WHERE nomination_id=?", (nomination_id,)).fetchone()
            return self.get_certificate(row["id"]) if row else None

    def list_certificates(self, candidate_id: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as db:
            query = "SELECT c.*, n.candidate_name, n.state, n.constituency, n.election_id FROM certificates c JOIN nominations n ON n.id=c.nomination_id"
            values: tuple[Any, ...] = ()
            if candidate_id:
                query += " WHERE c.candidate_user_id=?"
                values = (candidate_id,)
            query += " ORDER BY c.issued_at DESC"
            return [{key: row[key] for key in row.keys()} for row in db.execute(query, values).fetchall()]


class MongoWorkflowMirror:
    """Best-effort Mongo mirror for registration and nomination documents."""

    def __init__(self) -> None:
        self.client = None
        self.db = None
        self._connect()

    def _connect(self) -> None:
        try:
            from pymongo import MongoClient
            self.client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=700, connectTimeoutMS=700)
            self.client.admin.command("ping")
            self.db = self.client[settings.mongodb_database]
            self.db.workflow_users.create_index("user_id", unique=True)
            self.db.workflow_nominations.create_index("nomination_id", unique=True)
        except Exception:
            self.client = None
            self.db = None

    @property
    def connected(self) -> bool:
        return self.db is not None

    def mirror_user(self, user: dict[str, Any]) -> bool:
        if self.db is None:
            self._connect()
        if self.db is None:
            return False
        try:
            safe = {key: user.get(key) for key in ("id", "email", "full_name", "role", "phone", "voter_id", "state", "constituency", "status", "created_at")}
            safe["user_id"] = safe.pop("id")
            self.db.workflow_users.update_one({"user_id": safe["user_id"]}, {"$set": safe}, upsert=True)
            return True
        except Exception:
            return False

    def mirror_nomination(self, nomination: dict[str, Any]) -> bool:
        if self.db is None:
            self._connect()
        if self.db is None:
            return False
        try:
            document = {key: value for key, value in nomination.items() if key not in {"_id"}}
            document["nomination_id"] = document.pop("id")
            self.db.workflow_nominations.update_one({"nomination_id": document["nomination_id"]}, {"$set": document}, upsert=True)
            return True
        except Exception:
            return False


def _password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def _password_valid(password: str, encoded: str) -> bool:
    try:
        _, salt_value, digest_value = encoded.split("$", 2)
        salt = base64.urlsafe_b64decode(salt_value.encode())
        expected = base64.urlsafe_b64decode(digest_value.encode())
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def register_user(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    store = get_workflow_store()
    email = payload["email"].lower().strip()
    if store.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = store.create_user({**payload, "email": email, "password_hash": _password_hash(payload.pop("password")), "status": "active"})
    mongo_synced = get_mongo_mirror().mirror_user(user)
    return public_user(user, mongo_synced), issue_token(user)


def public_user(user: dict[str, Any], mongo_synced: bool | None = None) -> dict[str, Any]:
    result = {key: user.get(key) for key in ("id", "email", "full_name", "role", "phone", "voter_id", "state", "constituency", "status", "created_at")}
    if mongo_synced is not None:
        result["mongo_synced"] = mongo_synced
    return result


def issue_token(user: dict[str, Any]) -> str:
    payload = {"sub": user["id"], "role": user["role"], "exp": int(datetime.now(timezone.utc).timestamp()) + 60 * 60 * 24 * 7}
    raw = base64.urlsafe_b64encode(_json(payload).encode()).decode().rstrip("=")
    signature = hmac.new(settings.app_secret_key.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return f"{raw}.{signature}"


def current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in to use this workflow")
    token = authorization.split(" ", 1)[1].strip()
    try:
        raw, signature = token.split(".", 1)
        expected = hmac.new(settings.app_secret_key.encode(), raw.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("bad signature")
        payload = _loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode(), {})
        if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("expired")
    except (ValueError, TypeError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="Your session is invalid or expired") from None
    user = get_workflow_store().get_user(str(payload.get("sub", "")))
    if not user or user.get("status") != "active":
        raise HTTPException(status_code=401, detail="Your account is not active")
    return user


def require_role(user: dict[str, Any], *roles: str) -> dict[str, Any]:
    if user.get("role") not in roles:
        raise HTTPException(status_code=403, detail="This action is restricted to the required role")
    return user


def get_workflow_store() -> Any:
    global _workflow_store
    try:
        return _workflow_store
    except NameError:
        if settings.workflow_backend != "mysql":
            raise RuntimeError("ELECTORaW requires MySQL for runtime workflow storage; set WORKFLOW_BACKEND=mysql")
        from .mysql_workflow import MySQLWorkflowStore
        _workflow_store = MySQLWorkflowStore()
        return _workflow_store


def get_mongo_mirror() -> MongoWorkflowMirror:
    global _mongo_mirror
    try:
        return _mongo_mirror
    except NameError:
        _mongo_mirror = MongoWorkflowMirror()
        return _mongo_mirror


def render_certificate_pdf(nomination: dict[str, Any], certificate_number: str) -> str:
    """Create a printable winner certificate and return its local path."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    directory = settings.certificate_dir
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{certificate_number}.pdf"
    document = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=24 * mm, leftMargin=24 * mm, topMargin=22 * mm, bottomMargin=22 * mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("CertificateTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=25, textColor=colors.HexColor("#173b49"), alignment=1, spaceAfter=12)
    body = ParagraphStyle("CertificateBody", parent=styles["BodyText"], fontSize=12, leading=20, alignment=1, textColor=colors.HexColor("#26373b"))
    small = ParagraphStyle("CertificateSmall", parent=styles["BodyText"], fontSize=9, leading=13, alignment=1, textColor=colors.HexColor("#607277"))
    story: list[Any] = [Spacer(1, 12 * mm), Paragraph("ELECTORaW", title), Paragraph("CERTIFICATE OF ELECTION", title), Spacer(1, 12 * mm)]
    story.append(Paragraph(f"This certificate records that <b>{nomination['candidate_name']}</b> was declared the winning candidate for <b>{nomination['constituency']}</b>, <b>{nomination['state']}</b>.", body))
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(f"Election: {nomination.get('election_title', 'Declared constituency election')} ({nomination.get('election_year', '')})", body))
    story.append(Paragraph(f"Party: {nomination.get('party') or 'Independent / not specified'}", body))
    story.append(Spacer(1, 18 * mm))
    table = Table([[Paragraph("Certificate number", small), Paragraph("Issued", small)], [Paragraph(f"<b>{certificate_number}</b>", body), Paragraph(datetime.now(timezone.utc).strftime("%d %B %Y"), body)]], colWidths=[75 * mm, 75 * mm])
    table.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#173b49")), ("INNERGRID", (0, 0), (-1, -1), .4, colors.HexColor("#b7c7c8")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef5f2")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9)]))
    story.append(table)
    story.append(Spacer(1, 18 * mm))
    story.append(Paragraph("Issued through the ELECTORaW election workflow. This document is generated from the approved nomination record.", small))
    document.build(story)
    return str(path)


def render_nomination_pdf(nomination: dict[str, Any], officer_name: str) -> str:
    """Create an officer-authenticated acceptance PDF for an accepted nomination."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    directory = settings.certificate_dir
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"nomination-{nomination['id']}.pdf"
    document = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=22 * mm, leftMargin=22 * mm, topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("NominationTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, textColor=colors.HexColor("#173b49"), alignment=1, spaceAfter=10)
    body = ParagraphStyle("NominationBody", parent=styles["BodyText"], fontSize=11, leading=17, textColor=colors.HexColor("#26373b"))
    small = ParagraphStyle("NominationSmall", parent=styles["BodyText"], fontSize=8, leading=12, textColor=colors.HexColor("#607277"))
    story: list[Any] = [Paragraph("ELECTORaW", title), Paragraph("NOMINATION ACCEPTANCE RECORD", title), Spacer(1, 8 * mm)]
    story.append(Paragraph(f"This record confirms that the nomination of <b>{nomination['candidate_name']}</b> for <b>{nomination['constituency']}</b>, <b>{nomination['state']}</b> was accepted by the election officer.", body))
    story.append(Spacer(1, 8 * mm))
    details = [[Paragraph("Election", small), Paragraph("Party / affiliation", small)], [Paragraph(f"{nomination.get('election_title', 'Declared constituency election')} · reference year {nomination.get('election_year', '')}", body), Paragraph(nomination.get("party") or "Independent / not specified", body)], [Paragraph("Accepted by", small), Paragraph("Authenticated", small)], [Paragraph(officer_name, body), Paragraph(nomination.get("authenticated_at", ""), body)]]
    table = Table(details, colWidths=[80 * mm, 80 * mm])
    table.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#173b49")), ("INNERGRID", (0, 0), (-1, -1), .4, colors.HexColor("#b7c7c8")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef5f2")), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef5f2")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story.extend([table, Spacer(1, 14 * mm), Paragraph(f"Approved by Returning Officer: <b>{officer_name}</b>", body), Paragraph("This PDF was generated after the Returning Officer accepted the nomination.", small)])
    document.build(story)
    return str(path)

