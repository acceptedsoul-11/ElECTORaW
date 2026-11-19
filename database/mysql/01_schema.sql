
CREATE DATABASE IF NOT EXISTS electoraw
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE electoraw;

-- =====================================================
-- 1. ELECTIONS
-- =====================================================

CREATE TABLE elections (
    election_id INT AUTO_INCREMENT PRIMARY KEY,
    election_year SMALLINT NOT NULL UNIQUE,
    election_name VARCHAR(150) NOT NULL,
    election_type VARCHAR(50) NOT NULL DEFAULT 'Lok Sabha',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT chk_election_year
        CHECK (election_year BETWEEN 1947 AND 2100)
);

-- =====================================================
-- 2. STATES AND UNION TERRITORIES
-- =====================================================

CREATE TABLE states (
    state_id INT AUTO_INCREMENT PRIMARY KEY,
    state_name VARCHAR(100) NOT NULL UNIQUE,
    state_code VARCHAR(10) UNIQUE
);

-- =====================================================
-- 3. STABLE CONSTITUENCY IDENTITIES
-- A constituency can have multiple historical versions.
-- =====================================================

CREATE TABLE constituencies (
    constituency_id INT AUTO_INCREMENT PRIMARY KEY,
    state_id INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_constituency_state
        FOREIGN KEY (state_id)
        REFERENCES states(state_id)
);

-- =====================================================
-- 4. HISTORICAL CONSTITUENCY VERSIONS
-- Records the name and delimitation-era validity.
-- =====================================================

CREATE TABLE constituency_versions (
    constituency_version_id INT AUTO_INCREMENT PRIMARY KEY,
    constituency_id INT NOT NULL,
    constituency_name VARCHAR(150) NOT NULL,
    delimitation_code VARCHAR(50) NOT NULL,
    valid_from_year SMALLINT NOT NULL,
    valid_to_year SMALLINT NULL,
    reservation_category ENUM('GENERAL', 'SC', 'ST')
        NOT NULL DEFAULT 'GENERAL',

    CONSTRAINT fk_version_constituency
        FOREIGN KEY (constituency_id)
        REFERENCES constituencies(constituency_id),

    CONSTRAINT uq_constituency_version
        UNIQUE (constituency_id, delimitation_code),

    CONSTRAINT chk_version_years
        CHECK (
            valid_to_year IS NULL
            OR valid_to_year >= valid_from_year
        )
);

-- =====================================================
-- 5. POLITICAL PARTIES
-- =====================================================

CREATE TABLE parties (
    party_id INT AUTO_INCREMENT PRIMARY KEY,
    party_name VARCHAR(200) NOT NULL UNIQUE,
    party_abbreviation VARCHAR(40) NULL UNIQUE,
    party_symbol VARCHAR(200) NULL
);

-- =====================================================
-- 6. CANDIDATES
-- Do not identify people by name alone.
-- candidate_id is the internal identity key.
-- =====================================================

CREATE TABLE candidates (
    candidate_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    candidate_name VARCHAR(200) NOT NULL,
    gender VARCHAR(30) NULL,
    source_identity_key VARCHAR(64) NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 7. CONSTITUENCY CONTESTS IN EACH ELECTION
-- =====================================================

CREATE TABLE election_constituencies (
    election_constituency_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    election_id INT NOT NULL,
    constituency_version_id INT NOT NULL,
    constituency_number INT NULL,
    registered_electors INT NULL,
    total_votes_polled INT NULL,
    valid_votes INT NULL,
    nota_votes INT NULL,
    turnout_percentage DECIMAL(6,3) NULL,

    CONSTRAINT fk_ec_election
        FOREIGN KEY (election_id)
        REFERENCES elections(election_id),

    CONSTRAINT fk_ec_constituency_version
        FOREIGN KEY (constituency_version_id)
        REFERENCES constituency_versions(constituency_version_id),

    CONSTRAINT uq_election_constituency
        UNIQUE (election_id, constituency_version_id),

    CONSTRAINT chk_ec_electors
        CHECK (registered_electors IS NULL OR registered_electors >= 0),

    CONSTRAINT chk_ec_votes
        CHECK (total_votes_polled IS NULL OR total_votes_polled >= 0),

    CONSTRAINT chk_ec_nota
        CHECK (nota_votes IS NULL OR nota_votes >= 0),

    CONSTRAINT chk_ec_turnout
        CHECK (
            turnout_percentage IS NULL
            OR turnout_percentage BETWEEN 0 AND 100
        )
);

-- =====================================================
-- 8. CANDIDATE RESULTS
-- One row per candidate in a constituency contest.
-- NOTA is stored separately in election_constituencies.
-- =====================================================

CREATE TABLE candidate_results (
    candidate_result_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    election_constituency_id BIGINT NOT NULL,
    candidate_id BIGINT NOT NULL,
    party_id INT NULL,
    votes_received INT NOT NULL,
    vote_share_percentage DECIMAL(7,4) NULL,
    position_rank INT NULL,
    candidate_age SMALLINT NULL,
    candidate_category VARCHAR(30) NULL,
    is_winner BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT fk_result_contest
        FOREIGN KEY (election_constituency_id)
        REFERENCES election_constituencies(election_constituency_id),

    CONSTRAINT fk_result_candidate
        FOREIGN KEY (candidate_id)
        REFERENCES candidates(candidate_id),

    CONSTRAINT fk_result_party
        FOREIGN KEY (party_id)
        REFERENCES parties(party_id),

    CONSTRAINT uq_candidate_per_contest
        UNIQUE (election_constituency_id, candidate_id),

    CONSTRAINT chk_result_votes
        CHECK (votes_received >= 0),

    CONSTRAINT chk_result_share
        CHECK (
            vote_share_percentage IS NULL
            OR vote_share_percentage BETWEEN 0 AND 100
        ),

    CONSTRAINT chk_result_rank
        CHECK (position_rank IS NULL OR position_rank > 0)
);

-- =====================================================
-- 9. PARLIAMENTARY MEMBERSHIP
-- Election victory and actual membership are different.
-- =====================================================

CREATE TABLE parliamentary_memberships (
    membership_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    candidate_id BIGINT NOT NULL,
    election_id INT NULL,
    start_date DATE NULL,
    end_date DATE NULL,
    membership_status ENUM(
        'ACTIVE',
        'ENDED',
        'UNVERIFIED'
    ) NOT NULL DEFAULT 'UNVERIFIED',
    source_url VARCHAR(1000) NULL,
    verified_at TIMESTAMP NULL,

    CONSTRAINT fk_membership_candidate
        FOREIGN KEY (candidate_id)
        REFERENCES candidates(candidate_id),

    CONSTRAINT fk_membership_election
        FOREIGN KEY (election_id)
        REFERENCES elections(election_id),

    CONSTRAINT chk_membership_dates
        CHECK (
            start_date IS NULL
            OR end_date IS NULL
            OR end_date >= start_date
        )
);

-- =====================================================
-- 10. DATA SOURCE REGISTRY
-- Tracks provenance for imported ECI reports and files.
-- =====================================================

CREATE TABLE data_sources (
    source_id INT AUTO_INCREMENT PRIMARY KEY,
    election_id INT NOT NULL,
    source_title VARCHAR(250) NOT NULL,
    source_type VARCHAR(60) NOT NULL,
    source_url VARCHAR(1000) NULL,
    original_filename VARCHAR(255) NULL,
    retrieved_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT NULL,

    CONSTRAINT fk_source_election
        FOREIGN KEY (election_id)
        REFERENCES elections(election_id)
);

-- =====================================================
-- 11. IMPORT BATCHES
-- Tracks each ingestion attempt and its validation status.
-- =====================================================

CREATE TABLE import_batches (
    import_batch_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    source_id INT NOT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    batch_status ENUM(
        'PENDING',
        'RUNNING',
        'COMPLETED',
        'FAILED'
    ) NOT NULL DEFAULT 'PENDING',
    rows_read INT NOT NULL DEFAULT 0,
    rows_imported INT NOT NULL DEFAULT 0,
    rows_rejected INT NOT NULL DEFAULT 0,
    error_summary TEXT NULL,

    CONSTRAINT fk_batch_source
        FOREIGN KEY (source_id)
        REFERENCES data_sources(source_id),

    CONSTRAINT chk_batch_counts
        CHECK (
            rows_read >= 0
            AND rows_imported >= 0
            AND rows_rejected >= 0
        )
);

-- =====================================================
-- 12. INDEXES FOR COMMON ANALYTICAL QUERIES
-- =====================================================

CREATE INDEX idx_candidate_name
    ON candidates(candidate_name);

CREATE INDEX idx_party_name
    ON parties(party_name);

CREATE INDEX idx_contest_election
    ON election_constituencies(election_id);

CREATE INDEX idx_result_candidate
    ON candidate_results(candidate_id);

CREATE INDEX idx_result_party
    ON candidate_results(party_id);

CREATE INDEX idx_result_winner
    ON candidate_results(is_winner);

CREATE INDEX idx_membership_status
    ON parliamentary_memberships(membership_status);

CREATE INDEX idx_import_status
    ON import_batches(batch_status);
