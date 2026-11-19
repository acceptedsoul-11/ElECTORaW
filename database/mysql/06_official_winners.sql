USE electoraw;

CREATE TABLE IF NOT EXISTS official_winners (
    winner_id VARCHAR(64) PRIMARY KEY,
    election_year SMALLINT NOT NULL,
    state_name VARCHAR(120) NOT NULL,
    constituency_name VARCHAR(160) NOT NULL,
    winner_name VARCHAR(200) NOT NULL,
    party_name VARCHAR(200) NULL,
    candidate_name_db VARCHAR(200) NULL,
    match_status VARCHAR(30) NOT NULL,
    source_file VARCHAR(255) NULL,
    source_sheet VARCHAR(255) NULL,
    candidate_result_id BIGINT NULL,
    UNIQUE KEY uq_official_winner_seat (election_year, state_name, constituency_name),
    INDEX idx_official_winner_year (election_year),
    INDEX idx_official_winner_state (state_name)
);
