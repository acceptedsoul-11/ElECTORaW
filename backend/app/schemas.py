from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Election(BaseModel):
    year: int
    name: str
    candidate_count: int
    constituency_count: int
    winner_count: int
    source_coverage: str


class Overview(BaseModel):
    year: int
    candidate_count: int
    constituency_count: int
    state_count: int
    winner_count: int
    total_votes: int
    source_files: list[str]
    coverage_note: str | None = None
    top_parties: list[dict[str, Any]]


class CandidateResult(BaseModel):
    id: str
    year: int
    candidate_name: str
    party: str | None = None
    party_symbol: str | None = None
    state: str
    constituency: str
    votes: int
    vote_share: float | None = None
    winner: bool = False
    gender: str | None = None
    age: int | None = None
    category: str | None = None
    source_file: str


class CandidateDetail(CandidateResult):
    profile: dict[str, Any]
    election_history: list[CandidateResult]


class CandidatePage(BaseModel):
    items: list[CandidateResult]
    total: int
    limit: int
    offset: int


class Constituency(BaseModel):
    year: int
    state: str
    constituency: str
    winner: CandidateResult | None = None
    candidate_count: int
    total_votes: int
    margin: int | None = None
    source_file: str


class PartySummary(BaseModel):
    party: str
    candidates: int
    seats: int
    votes: int


class Citation(BaseModel):
    id: str
    title: str
    source_type: str
    locator: str
    excerpt: str
    year: int | None = None


class RagQuery(BaseModel):
    question: str = Field(min_length=3, max_length=800)
    year: int | None = Field(default=None, ge=2014, le=2024)
    session_id: str | None = Field(default=None, max_length=80)


class RagResponse(BaseModel):
    answer: str
    mode: Literal["structured", "retrieval", "hybrid", "insufficient_evidence"]
    citations: list[Citation]
    retrieved_chunks: int
    query_type: str


class HealthResponse(BaseModel):
    status: str
    data_backend: str
    mysql_configured: bool
    mongodb_configured: bool
    rag_chunks: int
    workflow_ready: bool = True


class ProfileFetchRequest(BaseModel):
    source_url: str = Field(min_length=10, max_length=1000)


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=5, max_length=240)
    password: str = Field(min_length=8, max_length=200)
    role: Literal["elector", "officer"]
    phone: str | None = Field(default=None, min_length=10, max_length=10, pattern=r"^\d{10}$")
    voter_id: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=120)
    constituency: str | None = Field(default=None, max_length=160)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=240)
    password: str = Field(min_length=1, max_length=200)


class ElectionDeclaration(BaseModel):
    year: int = Field(ge=2014, le=2024)
    election_date: str = Field(min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")
    title: str = Field(min_length=3, max_length=180)
    scope: Literal["selected", "state", "all"]
    scope_state: str | None = Field(default=None, max_length=120)
    constituencies: list[dict[str, str]] = Field(default_factory=list, max_length=600)


class NominationRequest(BaseModel):
    election_id: str = Field(min_length=4, max_length=80)
    state: str = Field(min_length=2, max_length=120)
    constituency: str = Field(min_length=2, max_length=160)
    candidate_name: str = Field(min_length=2, max_length=160)
    party: str | None = Field(default=None, max_length=120)
    form: dict[str, Any] = Field(default_factory=dict)


class NominationReview(BaseModel):
    status: Literal["accepted", "rejected"]
    is_winner: bool = False
    note: str | None = Field(default=None, max_length=500)

