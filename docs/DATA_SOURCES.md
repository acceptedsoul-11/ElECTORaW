# Data sources and coverage

The application currently exposes only source artifacts that exist in the repository:

- `data/processed/candidate_results_2014.csv`
- `data/processed/candidate_results_2019.csv`
- `data/processed/candidate_results_2024.csv`
- `data/processed/official_winners_matched.csv`
- `data/processed/official_winners_unmatched.csv`

These are derived from Election Commission of India workbooks listed in each row’s `source_file` field. Retrieval is local and reproducible; no external page is claimed as ingested when it is not present locally.

The interactive state boundary layer is the checked-in GeoJSON from [geohacker/india](https://github.com/geohacker/india/blob/master/state/india_state.geojson); election values are joined to it by normalized state name and are never inferred from geometry.

PoK is shown as a clearly labeled disputed-region overlay only. It is not treated as an Indian state, parliamentary constituency, or source of Lok Sabha seat data.

NOTA rows are intentionally excluded from the candidate result API. The 2014 detailed results omit individual rows for Chhattisgarh and Odisha; 32 official winner records remain unmatched and are presented as a coverage limitation.

The winner archive combines `official_winners_matched.csv`, `official_winners_unmatched.csv`, and the supplemental Surat successful-candidate record, so it exposes all 1,629 official winning-seat records from 2014, 2019 and 2024. The 32 unmatched 2014 records and the uncontested Surat record intentionally have no detailed vote total rather than being fabricated.

The profile adapter supports controlled, administrator-triggered retrieval from official government domains only (`eci.gov.in`, `sansad.in`, `loksabha.nic.in`, `rajyasabha.nic.in`). The optional `python -m backend.app.services.scrape_winner_profiles --all` job uses exact-name Wikidata/Wikipedia matching as a secondary-source discovery pass; it stores the source URL, retrieval date and verification status and never labels that material as an official biography. Official Digital Sansad biographies remain the preferred source and override bulk secondary results.
