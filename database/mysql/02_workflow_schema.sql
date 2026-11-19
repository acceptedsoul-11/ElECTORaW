USE electoraw;

-- Operational workflow tables live in the same MySQL database as the
-- analytical schema, but use a workflow_ prefix to avoid colliding with
-- the normalized election-facts tables.

CREATE TABLE IF NOT EXISTS workflow_users (
    id VARCHAR(80) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(500) NOT NULL,
    full_name VARCHAR(200) NOT NULL,
    role ENUM('elector', 'officer') NOT NULL,
    phone VARCHAR(20) NULL,
    voter_id VARCHAR(80) NULL,
    state VARCHAR(120) NULL,
    constituency VARCHAR(160) NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    created_at DATETIME(6) NOT NULL,
    INDEX idx_workflow_users_role (role)
);

CREATE TABLE IF NOT EXISTS workflow_elections (
    id VARCHAR(80) PRIMARY KEY,
    year SMALLINT NOT NULL,
    election_date DATE NULL,
    title VARCHAR(250) NOT NULL,
    scope ENUM('selected', 'state', 'all') NOT NULL,
    scope_state VARCHAR(120) NULL,
    status ENUM('open', 'closed', 'deleted') NOT NULL DEFAULT 'open',
    declared_by VARCHAR(80) NOT NULL,
    declared_at DATETIME(6) NOT NULL,
    closed_at DATETIME(6) NULL,
    CONSTRAINT fk_workflow_election_officer FOREIGN KEY (declared_by) REFERENCES workflow_users(id),
    INDEX idx_workflow_elections_status (status)
);

CREATE TABLE IF NOT EXISTS workflow_election_constituencies (
    id VARCHAR(80) PRIMARY KEY,
    election_id VARCHAR(80) NOT NULL,
    year SMALLINT NOT NULL,
    state VARCHAR(120) NOT NULL,
    constituency VARCHAR(160) NOT NULL,
    CONSTRAINT fk_workflow_seat_election FOREIGN KEY (election_id) REFERENCES workflow_elections(id),
    CONSTRAINT uq_workflow_election_seat UNIQUE (election_id, state, constituency)
);

CREATE TABLE IF NOT EXISTS workflow_nominations (
    id VARCHAR(80) PRIMARY KEY,
    election_id VARCHAR(80) NOT NULL,
    candidate_user_id VARCHAR(80) NOT NULL,
    state VARCHAR(120) NOT NULL,
    constituency VARCHAR(160) NOT NULL,
    candidate_name VARCHAR(200) NOT NULL,
    party VARCHAR(200) NULL,
    status ENUM('pending', 'accepted', 'rejected') NOT NULL DEFAULT 'pending',
    is_winner BOOLEAN NOT NULL DEFAULT FALSE,
    form_json JSON NOT NULL,
    submitted_at DATETIME(6) NOT NULL,
    reviewed_at DATETIME(6) NULL,
    reviewed_by VARCHAR(80) NULL,
    review_note TEXT NULL,
    nomination_pdf_path VARCHAR(1000) NULL,
    digital_signature VARCHAR(500) NULL,
    authenticated_at DATETIME(6) NULL,
    winner_key VARCHAR(500) GENERATED ALWAYS AS (
        CASE WHEN is_winner THEN CONCAT(election_id, '|', LOWER(state), '|', LOWER(constituency)) ELSE NULL END
    ) STORED,
    CONSTRAINT fk_workflow_nomination_election FOREIGN KEY (election_id) REFERENCES workflow_elections(id),
    CONSTRAINT fk_workflow_nomination_candidate FOREIGN KEY (candidate_user_id) REFERENCES workflow_users(id),
    CONSTRAINT fk_workflow_nomination_reviewer FOREIGN KEY (reviewed_by) REFERENCES workflow_users(id),
    CONSTRAINT uq_workflow_nomination_candidate_seat UNIQUE (election_id, state, constituency, candidate_user_id),
    CONSTRAINT uq_workflow_one_winner_per_seat UNIQUE (winner_key),
    INDEX idx_workflow_nominations_status (status),
    INDEX idx_workflow_nominations_candidate (candidate_user_id)
);

CREATE TABLE IF NOT EXISTS workflow_certificates (
    id VARCHAR(80) PRIMARY KEY,
    nomination_id VARCHAR(80) NOT NULL UNIQUE,
    candidate_user_id VARCHAR(80) NOT NULL,
    certificate_number VARCHAR(100) NOT NULL UNIQUE,
    pdf_path VARCHAR(1000) NOT NULL,
    issued_at DATETIME(6) NOT NULL,
    issued_by VARCHAR(80) NOT NULL,
    CONSTRAINT fk_workflow_certificate_nomination FOREIGN KEY (nomination_id) REFERENCES workflow_nominations(id),
    CONSTRAINT fk_workflow_certificate_candidate FOREIGN KEY (candidate_user_id) REFERENCES workflow_users(id),
    CONSTRAINT fk_workflow_certificate_officer FOREIGN KEY (issued_by) REFERENCES workflow_users(id)
);

CREATE TABLE IF NOT EXISTS workflow_audit_log (
    id VARCHAR(80) PRIMARY KEY,
    user_id VARCHAR(80) NULL,
    action VARCHAR(80) NOT NULL,
    entity_type VARCHAR(80) NOT NULL,
    entity_id VARCHAR(80) NULL,
    details_json JSON NULL,
    created_at DATETIME(6) NOT NULL,
    CONSTRAINT fk_workflow_audit_user FOREIGN KEY (user_id) REFERENCES workflow_users(id),
    INDEX idx_workflow_audit_entity (entity_type, entity_id),
    INDEX idx_workflow_audit_created (created_at)
);
