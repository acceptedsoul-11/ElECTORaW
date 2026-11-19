USE electoraw;

-- Window ranking: derive a winner and runner-up margin per contest.
WITH ranked_results AS (
    SELECT ec.election_constituency_id,
           cv.constituency_name,
           c.candidate_name,
           cr.votes_received,
           DENSE_RANK() OVER (
               PARTITION BY ec.election_constituency_id
               ORDER BY cr.votes_received DESC
           ) AS vote_rank
    FROM candidate_results cr
    JOIN candidates c ON c.candidate_id = cr.candidate_id
    JOIN election_constituencies ec ON ec.election_constituency_id = cr.election_constituency_id
    JOIN constituency_versions cv ON cv.constituency_version_id = ec.constituency_version_id
)
SELECT election_constituency_id, constituency_name,
       MAX(CASE WHEN vote_rank = 1 THEN candidate_name END) AS winner_name,
       MAX(CASE WHEN vote_rank = 1 THEN votes_received END)
         - MAX(CASE WHEN vote_rank = 2 THEN votes_received END) AS margin
FROM ranked_results
GROUP BY election_constituency_id, constituency_name;

-- Correlated subquery: candidates whose votes exceed the average in their contest.
SELECT cr.candidate_result_id, c.candidate_name, cr.votes_received
FROM candidate_results cr
JOIN candidates c ON c.candidate_id = cr.candidate_id
WHERE cr.votes_received > (
    SELECT AVG(other.votes_received)
    FROM candidate_results other
    WHERE other.election_constituency_id = cr.election_constituency_id
);

-- Transaction pattern used by narrowly scoped administrative repairs:
-- START TRANSACTION;
-- UPDATE candidate_results SET is_winner = TRUE WHERE candidate_result_id = ?;
-- ROLLBACK; -- use COMMIT only after an authoritative audit
