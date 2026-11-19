## `candidate_profiles`

The profile collection is complementary to MySQL and never replaces structured election results.

```json
{
  "person_key": "sansad:4589",
  "canonical_name": "Narendra Modi",
  "aliases": ["NARENDRA MODI"],
  "party": "Bharatiya Janata Party",
  "current_constituency": "Varanasi",
  "current_state": "Uttar Pradesh",
  "bio": "...",
  "birth": {"date": "YYYY-MM-DD", "place": "..."},
  "education": "...",
  "career": ["..."],
  "verification_status": "official_source",
  "completeness": 82,
  "source_references": [{"title": "...", "url": "...", "source_type": "official_government"}],
  "last_successful_refresh": "YYYY-MM-DD"
}
```

Indexes: unique `person_key` and multikey `aliases`. The API resolves profiles by canonical name/alias after retrieving the candidate result, preserving the separation between person evidence and contest facts.
