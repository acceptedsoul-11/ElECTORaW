# DBMS feature checklist

The SQL scripts in `database/mysql/` are the working schema and extension points.

| Concept | Implementation | Purpose |
|---|---|---|
| DDL/DML | `01_schema.sql`, controlled import scripts | Define and load normalized election facts |
| Primary/foreign keys | All core tables | Preserve referential integrity |
| Unique constraints | Contest, candidate-result, election-year and party keys | Prevent duplicate facts |
| Joins | `candidate_results` → candidates, parties, contests, elections | Compose candidate and election views |
| Aggregates | Candidate counts, party seats, state summaries | Dashboard analytics |
| Subqueries/CTEs | Use in analytics extensions for winner and ranking reports | Keep analytics close to the data |
| Indexes | `idx_candidate_name`, `idx_contest_election`, `idx_result_party`, winner index | Bound search and aggregation cost |
| Views | Add reusable national/state summary views in `04_analytics.sql` | Stable API-facing reporting layer |
| Transactions | Import and narrowly scoped repair scripts | Roll back partial administrative work |
| Window/ranking queries | Candidate rank and runner-up analysis | Compute margins without application-side scans |
| Check constraints | Vote, rank, turnout and year checks | Reject impossible values |

Example winner/margin query:

```sql
WITH ranked AS (
  SELECT ec.election_id, cv.constituency_name, c.candidate_name,
         cr.votes_received,
         DENSE_RANK() OVER (PARTITION BY ec.election_constituency_id ORDER BY cr.votes_received DESC) AS vote_rank
  FROM candidate_results cr
  JOIN candidates c ON c.candidate_id = cr.candidate_id
  JOIN election_constituencies ec ON ec.election_constituency_id = cr.election_constituency_id
  JOIN constituency_versions cv ON cv.constituency_version_id = ec.constituency_version_id
)
SELECT * FROM ranked WHERE vote_rank <= 2;
```
