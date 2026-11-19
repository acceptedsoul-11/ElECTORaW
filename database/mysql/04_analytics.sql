USE electoraw;

CREATE OR REPLACE VIEW vw_national_election_summary AS
SELECT e.election_year,
       COUNT(DISTINCT ec.election_constituency_id) AS constituency_count,
       COUNT(DISTINCT cr.candidate_id) AS candidate_count,
       SUM(cr.votes_received) AS candidate_votes,
       SUM(CASE WHEN cr.is_winner = TRUE THEN 1 ELSE 0 END) AS verified_winner_flags
FROM elections e
JOIN election_constituencies ec ON ec.election_id = e.election_id
JOIN candidate_results cr ON cr.election_constituency_id = ec.election_constituency_id
GROUP BY e.election_year;

CREATE OR REPLACE VIEW vw_party_election_summary AS
SELECT e.election_year,
       COALESCE(p.party_name, 'Unspecified') AS party_name,
       COUNT(*) AS candidate_results,
       SUM(cr.votes_received) AS votes_received,
       SUM(CASE WHEN cr.is_winner = TRUE THEN 1 ELSE 0 END) AS seats_won
FROM elections e
JOIN election_constituencies ec ON ec.election_id = e.election_id
JOIN candidate_results cr ON cr.election_constituency_id = ec.election_constituency_id
LEFT JOIN parties p ON p.party_id = cr.party_id
GROUP BY e.election_year, p.party_name;
