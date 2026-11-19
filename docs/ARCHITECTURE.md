# ELECTORaW architecture

```text
Next.js UI ──HTTP──> FastAPI API ──> MySQL (analytical facts + workflow records)
                              ├──> MongoDB (profile and workflow document mirrors)
                              ├──> local curated ECI artifacts (election corpus)
                              └──> ChromaDB (persistent vector retrieval)
```

The normalized MySQL schema stores analytical election facts and the `workflow_*` operational tables. The one-click launcher initializes MySQL and imports the curated ECI artifacts before starting the API; MongoDB stores document mirrors and ChromaDB stores persistent retrieval vectors.

The RAG agent is deliberately bounded: it classifies a question, checks structured election rows first for exact facts, retrieves ranked corpus chunks for context, attaches source locators, and abstains when it has insufficient evidence. Indexed content is treated as data, not instructions.

MongoDB stores the complementary `candidate_profiles` collection. The current seed contains three official Digital Sansad biographies (Narendra Modi, Rahul Gandhi and Akhilesh Yadav), each with aliases, provenance, completeness and evidence fields. Profile enrichment remains administrator-controlled; the safe fetch adapter only accepts allowlisted government domains, limits payload size, records provenance, and does not mark a profile verified automatically.
