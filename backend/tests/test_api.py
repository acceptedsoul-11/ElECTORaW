from app.main import candidate_detail, candidates, elections, featured_profiles, health, overview, rag_query
from app.schemas import RagQuery


def test_health_and_elections():
    assert health().status == "ok"
    assert [item["year"] for item in elections()] == [2014, 2019, 2024]


def test_overview_excludes_nota_and_has_2014_note():
    payload = overview(2014)
    assert payload["candidate_count"] == 7844
    assert "unmatched" in payload["coverage_note"]


def test_candidate_search_and_grounded_rag():
    response = candidates(2024, "Modi", None, None, 25, 0)
    assert response["total"] >= 1
    rag = rag_query(RagQuery(question="Who won Varanasi in 2024?", year=2024))
    assert rag["citations"]
    assert "Varanasi" in rag["answer"]


def test_unknown_rag_question_abstains():
    response = rag_query(RagQuery(question="Tell me the result of a fictional moon constituency"))
    assert response["mode"] in {"insufficient_evidence", "retrieval"}


def test_profile_spotlight_and_candidate_join():
    profiles = featured_profiles()
    assert {item["canonical_name"] for item in profiles} >= {"Narendra Modi", "Rahul Gandhi", "Akhilesh Yadav"}
    result = candidates(2024, "Narendra Modi", None, None, 1, 0)
    detail = candidate_detail(result["items"][0]["id"])
    assert detail["profile"]["status"] == "official_source"
    assert detail["profile"]["source_references"][0]["url"].startswith("https://sansad.in/")
