from __future__ import annotations

from typing import Any

import secrets
import sqlite3
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import settings
from .data import _norm, get_data
from .schemas import CandidateDetail, CandidatePage, CandidateResult, Election, ElectionDeclaration, HealthResponse, LoginRequest, NominationRequest, NominationReview, Overview, ProfileFetchRequest, RagQuery, RagResponse, RegisterRequest
from .services.profiles import fetch_official_evidence
from .services.mongodb_profiles import get_profile_store
from .services.nda import CABINET_BY_YEAR, matches as minister_matches
from .services.rag import GroundedRag
from .services.workflow import _password_valid, current_user, get_mongo_mirror, get_workflow_store, issue_token, public_user, register_user, render_certificate_pdf, render_nomination_pdf, require_role


app = FastAPI(title="ELECTORaW API", version="1.0.0", description="Grounded Indian Lok Sabha election intelligence for 2014, 2019 and 2024.")
app.add_middleware(CORSMiddleware, allow_origins=list(settings.frontend_origins), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def data():
    return get_data()


def rag():
    instance = getattr(app.state, "rag", None)
    if instance is None:
        instance = GroundedRag(data(), settings.data_root)
        app.state.rag = instance
    return instance


def admin_guard(x_admin_token: str | None = Header(default=None)) -> None:
    if not settings.admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=403, detail="Administrator authorization is not configured or valid")


def officer_guard(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return require_role(user, "officer")


def candidate_guard(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return require_role(user, "elector")


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", data_backend=settings.data_backend, mysql_configured=bool(settings.mysql_user and settings.mysql_password), mongodb_configured=get_profile_store().connected, rag_chunks=len(rag().chunks), workflow_ready=True)


@app.get("/api/elections", response_model=list[Election])
def elections() -> list[dict[str, Any]]:
    return data().elections()


@app.get("/api/overview", response_model=Overview)
def overview(year: int = Query(2024, ge=2014, le=2024)) -> dict[str, Any]:
    if year not in (2014, 2019, 2024):
        raise HTTPException(status_code=400, detail="Supported election years are 2014, 2019 and 2024")
    return data().overview(year)


@app.get("/api/states")
def states(year: int = Query(2024, ge=2014, le=2024)) -> list[dict[str, Any]]:
    return data().states(year)


@app.get("/api/parties")
def parties(year: int = Query(2024, ge=2014, le=2024), limit: int = Query(20, ge=1, le=100)) -> list[dict[str, Any]]:
    return data().party_summaries(year, limit)


@app.get("/api/candidates", response_model=CandidatePage)
def candidates(year: int | None = Query(default=None), search: str | None = Query(default=None, max_length=120), state: str | None = Query(default=None, max_length=120), party: str | None = Query(default=None, max_length=120), limit: int = Query(25, ge=1, le=100), offset: int = Query(0, ge=0)) -> dict[str, Any]:
    rows, total = data().candidates(year, search, state, party, limit, offset)
    return {"items": [data().public_row(row) for row in rows], "total": total, "limit": limit, "offset": offset}


@app.get("/api/candidates/{candidate_id}", response_model=CandidateDetail)
def candidate_detail(candidate_id: str) -> dict[str, Any]:
    row = data().by_id(candidate_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Candidate result not found")
    history = data().history(row.candidate_name)
    profile = get_profile_store().get(row.candidate_name) or {"status": "profile", "completeness": 0, "message": "Election record and constituency source are available."}
    if "verification_status" in profile:
        profile = {**profile, "status": profile["verification_status"], "message": profile.get("bio", "Verified official profile evidence is available.")}
    return {**data().public_row(row), "profile": profile, "election_history": [data().public_row(item) for item in history]}


@app.get("/api/constituencies")
def constituencies(year: int = Query(2024, ge=2014, le=2024), search: str | None = Query(default=None, max_length=120), state: str | None = Query(default=None, max_length=120), limit: int = Query(100, ge=1, le=600)) -> list[dict[str, Any]]:
    return data().constituencies(year, search, state, limit)


def _public_winner(item: dict[str, Any]) -> dict[str, Any]:
    profile = get_profile_store().get(item["candidate_name"]) or {
        "status": "profile",
        "verification_status": "profile",
        "completeness": 0,
        "bio": "Election record and constituency source are available.",
        "source_references": [{"title": "Election Commission of India successful-candidate record", "url": "https://results.eci.gov.in/", "source_type": "official_election_result", "locator": item["source_file"]}],
    }
    if "verification_status" in profile:
        profile = {**profile, "status": profile["verification_status"], "message": profile.get("bio", "Verified public profile evidence is available.")}
    return {**item, "profile": profile}


@app.get("/api/winners")
def winners(year: int | None = Query(default=None, ge=2014, le=2024), search: str | None = Query(default=None, max_length=120), state: str | None = Query(default=None, max_length=120), limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)) -> dict[str, Any]:
    items, total = data().winners(year, search, state, limit, offset)
    return {"items": [_public_winner(item) for item in items], "total": total, "limit": limit, "offset": offset, "coverage": {"official_winners": total, "profiled": sum(bool(get_profile_store().get(item["candidate_name"])) for item in items)}}


@app.get("/api/winners/{winner_id}")
def winner_detail(winner_id: str) -> dict[str, Any]:
    item = data().winner_by_id(winner_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Winner record not found")
    history = [candidate for candidate in data().history(item["candidate_name"])]
    return {**_public_winner(item), "election_history": [data().public_row(candidate) for candidate in history]}


@app.get("/api/spotlight/nda-cabinet")
def nda_cabinet_spotlight(year: int = Query(2024, ge=2014, le=2024)) -> list[dict[str, Any]]:
    if year not in (2014, 2019, 2024):
        raise HTTPException(status_code=400, detail="Supported election years are 2014, 2019 and 2024")
    records, _ = data().winners(year=year, limit=1000)
    result = []
    local_party_logos = {"BJP": "/party-logos/bjp.svg", "TDP": "/party-logos/tdp.png", "JD(U)": "/party-logos/jdu.svg", "JD(S)": "/party-logos/jds.svg", "LJPRV": "/party-logos/ljp.svg", "LJP": "/party-logos/ljp.svg", "HAMS": "/party-logos/hams.svg"}
    for minister in CABINET_BY_YEAR.get(year, []):
        winner = next((item for item in records if minister_matches(item["candidate_name"], minister)), None)
        if not winner:
            continue
        result.append({
            **minister,
            "logo": local_party_logos.get(minister["party"], minister["logo"]),
            "winner": winner,
            "profile": _public_winner(winner)["profile"],
            "source_references": [
                {"title": "Prime Minister's Office — Union Council of Ministers", "url": "https://www.pmindia.gov.in/en/news_updates/portfolios-of-the-union-council-of-ministers-2/", "source_type": "official_government"},
                {"title": "Digital Sansad — Lok Sabha members", "url": "https://sansad.in/ls/members", "source_type": "official_government"},
            ],
        })
    return result


@app.post("/api/auth/register")
def auth_register(payload: RegisterRequest) -> dict[str, Any]:
    try:
        user, token = register_user(payload.model_dump())
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="An account with this email already exists") from exc
    return {"user": user, "token": token}


@app.post("/api/auth/login")
def auth_login(payload: LoginRequest) -> dict[str, Any]:
    user = get_workflow_store().get_user_by_email(payload.email)
    if not user or not _password_valid(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    return {"user": public_user(user), "token": issue_token(user)}


@app.get("/api/auth/me")
def auth_me(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return public_user(user)


@app.get("/api/workflow/storage")
def workflow_storage(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return {"rdbms": "MySQL", "rdbms_database": settings.mysql_database, "mongo": "connected" if get_mongo_mirror().connected else "fallback unavailable", "mongo_database": settings.mongodb_database, "role": user["role"]}


@app.get("/api/workflow/constituencies")
def workflow_constituencies(year: int = Query(2024, ge=2014, le=2024), state: str | None = Query(default=None, max_length=120), user: dict[str, Any] = Depends(officer_guard)) -> list[dict[str, Any]]:
    records, _ = data().winners(year=year, limit=1000, state=state)
    return [{"year": item["year"], "state": item["state"], "constituency": item["constituency"], "winner": item["winner"]} for item in records]


@app.get("/api/workflow/elections")
def workflow_elections(user: dict[str, Any] = Depends(current_user)) -> list[dict[str, Any]]:
    store = get_workflow_store()
    elections = store.list_elections()
    if user["role"] == "elector":
        elections = [item for item in elections if item["status"] == "open"]
    return [store.get_election(item["id"]) or item for item in elections]


@app.get("/api/workflow/elections/{election_id}")
def workflow_election_detail(election_id: str, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    election = get_workflow_store().get_election(election_id)
    if not election or election["status"] == "deleted":
        raise HTTPException(status_code=404, detail="Election declaration not found")
    if user["role"] == "elector" and election["status"] != "open":
        raise HTTPException(status_code=404, detail="Election declaration not found")
    return election


@app.post("/api/officer/elections")
def declare_election(payload: ElectionDeclaration, user: dict[str, Any] = Depends(officer_guard)) -> dict[str, Any]:
    try:
        from datetime import date
        date.fromisoformat(payload.election_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Enter a valid election date in YYYY-MM-DD format") from exc
    available, _ = data().winners(year=payload.year, limit=1000)
    by_key = {_norm(item["state"])+"|"+_norm(item["constituency"]): item for item in available}
    if payload.scope == "all":
        selected = available
    elif payload.scope == "state":
        if not payload.scope_state:
            raise HTTPException(status_code=400, detail="Choose a state for a state-wide declaration")
        selected = [item for item in available if _norm(item["state"]) == _norm(payload.scope_state)]
    else:
        selected = [by_key.get(_norm(item.get("state", ""))+"|"+_norm(item.get("constituency", ""))) for item in payload.constituencies]
        selected = [item for item in selected if item]
    if not selected:
        raise HTTPException(status_code=400, detail="The declaration must contain at least one constituency")
    return get_workflow_store().create_election(user["id"], payload.model_dump(), selected)


@app.post("/api/officer/elections/{election_id}/close")
def close_election(election_id: str, user: dict[str, Any] = Depends(officer_guard)) -> dict[str, Any]:
    election = get_workflow_store().get_election(election_id)
    if not election or election["status"] == "deleted":
        raise HTTPException(status_code=404, detail="Election declaration not found")
    return get_workflow_store().close_election(election_id, user["id"]) or {}


@app.delete("/api/officer/elections/{election_id}")
def delete_election(election_id: str, user: dict[str, Any] = Depends(officer_guard)) -> dict[str, Any]:
    election = get_workflow_store().get_election(election_id)
    if not election:
        raise HTTPException(status_code=404, detail="Election declaration not found")
    return get_workflow_store().delete_election(election_id, user["id"]) or {}


@app.post("/api/candidate/nominations")
def submit_nomination(payload: NominationRequest, user: dict[str, Any] = Depends(candidate_guard)) -> dict[str, Any]:
    store = get_workflow_store()
    try:
        age = int(str(payload.form.get("age", "")).strip())
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Age is required to submit a nomination") from exc
    if age < 25:
        raise HTTPException(status_code=400, detail="A candidate must be at least 25 years old to contest")
    election = store.get_election(payload.election_id)
    if not election or election["status"] != "open":
        raise HTTPException(status_code=400, detail="This election is not open for nominations")
    if not store.find_election_seat(payload.election_id, payload.state, payload.constituency):
        raise HTTPException(status_code=400, detail="That constituency is not included in the election declaration")
    form = {**payload.form, "registered_email": user["email"], "registered_phone": user.get("phone"), "registered_voter_id": user.get("voter_id")}
    try:
        nomination = store.create_nomination(user["id"], {**payload.model_dump(), "form": form})
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="You already submitted a nomination for this constituency in this election") from exc
    nomination["mongo_synced"] = get_mongo_mirror().mirror_nomination(nomination)
    return nomination


@app.get("/api/candidate/nominations")
def candidate_nominations(user: dict[str, Any] = Depends(candidate_guard)) -> list[dict[str, Any]]:
    return get_workflow_store().list_nominations(candidate_id=user["id"])


@app.get("/api/candidate/certificates")
def candidate_certificates(user: dict[str, Any] = Depends(candidate_guard)) -> list[dict[str, Any]]:
    return get_workflow_store().list_certificates(candidate_id=user["id"])


@app.get("/api/officer/nominations")
def officer_nominations(status: str | None = Query(default=None), user: dict[str, Any] = Depends(officer_guard)) -> list[dict[str, Any]]:
    return get_workflow_store().list_nominations(status=status)


@app.patch("/api/officer/nominations/{nomination_id}")
def review_nomination(nomination_id: str, payload: NominationReview, user: dict[str, Any] = Depends(officer_guard)) -> dict[str, Any]:
    nomination = get_workflow_store().get_nomination(nomination_id)
    if not nomination:
        raise HTTPException(status_code=404, detail="Nomination not found")
    try:
        updated = get_workflow_store().review_nomination(nomination_id, user["id"], payload.status, payload.is_winner, payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if updated:
        if payload.status == "accepted":
            officer = get_workflow_store().get_user(user["id"]) or user
            authenticated_at = updated.get("reviewed_at") or ""
            pdf_path = render_nomination_pdf({**updated, "authenticated_at": authenticated_at}, officer.get("full_name", "EC officer"))
            updated = get_workflow_store().authenticate_nomination(nomination_id, pdf_path, None, authenticated_at) or updated
        updated["mongo_synced"] = get_mongo_mirror().mirror_nomination(updated)
    return updated or {}


@app.get("/api/workflow/nominations/{nomination_id}/download")
def download_nomination(nomination_id: str, user: dict[str, Any] = Depends(current_user)) -> FileResponse:
    store = get_workflow_store()
    nomination = store.get_nomination(nomination_id)
    if not nomination or nomination["status"] != "accepted" or (user["role"] != "officer" and nomination["candidate_user_id"] != user["id"]):
        raise HTTPException(status_code=404, detail="Authenticated nomination record not found")
    path_value = nomination.get("nomination_pdf_path")
    if not path_value:
        # Backfill PDFs for nominations accepted before PDF authentication was added.
        officer_id = nomination.get("reviewed_by") or "system"
        officer = store.get_user(officer_id) or {"full_name": "EC officer"}
        authenticated_at = nomination.get("authenticated_at") or nomination.get("reviewed_at") or ""
        path_value = render_nomination_pdf({**nomination, "authenticated_at": authenticated_at}, officer.get("full_name", "EC officer"))
        nomination = store.authenticate_nomination(nomination_id, path_value, None, authenticated_at) or nomination
    else:
        # Re-render older PDFs so they also use the current approval-only wording.
        officer_id = nomination.get("reviewed_by") or "system"
        officer = store.get_user(officer_id) or {"full_name": "EC officer"}
        authenticated_at = nomination.get("authenticated_at") or nomination.get("reviewed_at") or ""
        path_value = render_nomination_pdf({**nomination, "authenticated_at": authenticated_at}, officer.get("full_name", "EC officer"))
        nomination = store.authenticate_nomination(nomination_id, path_value, None, authenticated_at) or nomination
    path = Path(path_value).resolve()
    directory = settings.certificate_dir.resolve()
    if not path.exists() or directory not in path.parents:
        raise HTTPException(status_code=404, detail="Nomination PDF file not found")
    return FileResponse(path, media_type="application/pdf", filename=f"nomination-{nomination_id}.pdf")


@app.post("/api/officer/nominations/{nomination_id}/certificate")
def award_certificate(nomination_id: str, user: dict[str, Any] = Depends(officer_guard)) -> dict[str, Any]:
    store = get_workflow_store()
    nomination = store.get_nomination(nomination_id)
    if not nomination:
        raise HTTPException(status_code=404, detail="Nomination not found")
    if nomination["status"] != "accepted" or not nomination["is_winner"]:
        raise HTTPException(status_code=400, detail="Accept the nomination and mark it as the winner before awarding a certificate")
    existing = store.get_certificate_for_nomination(nomination_id)
    if existing:
        return existing
    certificate_number = f"EAW-{nomination['election_year']}-{secrets.token_hex(4).upper()}"
    pdf_path = render_certificate_pdf(nomination, certificate_number)
    return store.create_certificate(nomination, user["id"], pdf_path, certificate_number)


@app.get("/api/workflow/certificates/{certificate_id}/download")
def download_certificate(certificate_id: str, user: dict[str, Any] = Depends(current_user)) -> FileResponse:
    certificate = get_workflow_store().get_certificate(certificate_id)
    if not certificate or (user["role"] != "officer" and certificate["candidate_user_id"] != user["id"]):
        raise HTTPException(status_code=404, detail="Certificate not found")
    path = Path(certificate["pdf_path"]).resolve()
    directory = settings.certificate_dir.resolve()
    if not path.exists() or directory not in path.parents:
        raise HTTPException(status_code=404, detail="Certificate file not found")
    return FileResponse(path, media_type="application/pdf", filename=f"{certificate['certificate_number']}.pdf")


@app.get("/api/sources")
def sources() -> list[dict[str, Any]]:
    return data().source_catalog()


@app.get("/api/profiles/featured")
def featured_profiles() -> list[dict[str, Any]]:
    profiles = get_profile_store().featured()
    enriched = []
    for profile in profiles:
        matches, _total = data().candidates(2024, profile.get("canonical_name"), limit=1)
        enriched.append({**profile, "candidate_result_id": matches[0].id if matches else None})
    return enriched


@app.post("/api/rag/query", response_model=RagResponse)
def rag_query(payload: RagQuery) -> dict[str, Any]:
    return rag().answer(payload.question, payload.year)


@app.get("/api/admin/index-status", dependencies=[Depends(admin_guard)])
def index_status() -> dict[str, Any]:
    engine = rag()
    return {"status": "ready" if engine.chunks and engine.vector_store.count else "empty", "chunks": len(engine.chunks), "embedding_backend": "local_hash_v1", "vector_db": "ChromaDB", "vector_collection": engine.vector_store.collection_name, "vector_count": engine.vector_store.count, "corpus": "Curated ECI processed outputs and repository methodology docs"}


@app.get("/api/vector/status")
def vector_status() -> dict[str, Any]:
    engine = rag()
    return {"active": True, "provider": "ChromaDB", "collection": engine.vector_store.collection_name, "count": engine.vector_store.count, "path": str(engine.vector_store.path), "embedding": "local_hash_v1"}


@app.get("/api/admin/profile-enrichment-policy", dependencies=[Depends(admin_guard)])
def profile_enrichment_policy() -> dict[str, Any]:
    return {"status": "ready", "mode": "controlled_admin_job", "allowed_sources": ["eci.gov.in", "sansad.in", "loksabha.nic.in", "rajyasabha.nic.in"], "note": "The app stores evidence and provenance separately; it does not claim a profile is verified until reviewed."}


@app.post("/api/admin/profiles/seed", dependencies=[Depends(admin_guard)])
def seed_profiles() -> dict[str, Any]:
    return get_profile_store().seed()


@app.post("/api/admin/profile-enrichment/preview", dependencies=[Depends(admin_guard)])
def profile_enrichment_preview(payload: ProfileFetchRequest) -> dict[str, Any]:
    try:
        return fetch_official_evidence(payload.source_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Official source could not be fetched: {type(exc).__name__}") from exc


@app.post("/api/admin/reindex", dependencies=[Depends(admin_guard)])
def reindex() -> dict[str, Any]:
    app.state.rag = GroundedRag(data(), settings.data_root)
    return {"status": "ready", "chunks": len(app.state.rag.chunks), "embedding_backend": "local_hash_v1", "vector_db": "ChromaDB", "vector_count": app.state.rag.vector_store.count}


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"name": "ELECTORaW API", "docs": "/docs", "health": "/api/health"}
