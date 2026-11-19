# ELECTORaW ER diagram and relationship schema

This document reflects the current repository design. ELECTORaW has two relational domains:

- MySQL is the normalized analytical schema and the runtime operational workflow database.
- The legacy SQLite file is a migration source only; new workflow operations use MySQL `workflow_*` tables.

MongoDB stores document mirrors and profile documents; ChromaDB stores RAG chunks and is not a relational model.

## 1. System-level storage relationship

```mermaid
flowchart LR
    UI[Next.js UI] --> API[FastAPI API]
    API --> MYSQL[(MySQL electoraw database)]
    MYSQL --> WF[(workflow_* tables)]
    API --> MONGO[(MongoDB document store)]
    API --> CHROMA[(ChromaDB vector collection)]
    API --> FILES[(Local PDF files)]
    WF -. mirrors registration and nominations .-> MONGO
    WF -. certificate and nomination paths .-> FILES
    CHROMA -. retrieves corpus chunks .-> API
```

## 2. Analytical election ER diagram — MySQL

```mermaid
erDiagram
    ELECTIONS ||--o{ ELECTION_CONSTITUENCIES : contains
    STATES ||--o{ CONSTITUENCIES : has
    CONSTITUENCIES ||--o{ CONSTITUENCY_VERSIONS : changes_through
    CONSTITUENCY_VERSIONS ||--o{ ELECTION_CONSTITUENCIES : identifies
    ELECTION_CONSTITUENCIES ||--o{ CANDIDATE_RESULTS : records
    CANDIDATES ||--o{ CANDIDATE_RESULTS : contests
    PARTIES o|--o{ CANDIDATE_RESULTS : represents
    CANDIDATES ||--o{ PARLIAMENTARY_MEMBERSHIPS : holds
    ELECTIONS o|--o{ PARLIAMENTARY_MEMBERSHIPS : may_start
    ELECTIONS ||--o{ DATA_SOURCES : documented_by
    DATA_SOURCES ||--o{ IMPORT_BATCHES : ingested_as

    ELECTIONS {
        int election_id PK
        smallint election_year UK
        varchar election_name
        varchar election_type
    }
    STATES {
        int state_id PK
        varchar state_name UK
        varchar state_code UK
    }
    CONSTITUENCIES {
        int constituency_id PK
        int state_id FK
    }
    CONSTITUENCY_VERSIONS {
        int constituency_version_id PK
        int constituency_id FK
        varchar constituency_name
        varchar delimitation_code
        smallint valid_from_year
        smallint valid_to_year
        enum reservation_category
    }
    ELECTION_CONSTITUENCIES {
        bigint election_constituency_id PK
        int election_id FK
        int constituency_version_id FK
        int constituency_number
        int registered_electors
        int total_votes_polled
        int nota_votes
        decimal turnout_percentage
    }
    CANDIDATES {
        bigint candidate_id PK
        varchar candidate_name
        varchar gender
    }
    PARTIES {
        int party_id PK
        varchar party_name UK
        varchar party_abbreviation UK
    }
    CANDIDATE_RESULTS {
        bigint candidate_result_id PK
        bigint election_constituency_id FK
        bigint candidate_id FK
        int party_id FK
        int votes_received
        int position_rank
        boolean is_winner
    }
    PARLIAMENTARY_MEMBERSHIPS {
        bigint membership_id PK
        bigint candidate_id FK
        int election_id FK
        enum membership_status
        date start_date
        date end_date
    }
    DATA_SOURCES {
        int source_id PK
        int election_id FK
        varchar source_type
        varchar source_url
    }
    IMPORT_BATCHES {
        bigint import_batch_id PK
        int source_id FK
        enum batch_status
        int rows_read
        int rows_imported
        int rows_rejected
    }
```

### Analytical relationship schema

| Table | Primary key | Important foreign keys | Relationship / purpose |
|---|---|---|---|
| `states` | `state_id` | — | One state has many stable constituency identities. |
| `constituencies` | `constituency_id` | `state_id → states` | Stable identity independent of historical naming. |
| `constituency_versions` | `constituency_version_id` | `constituency_id → constituencies` | Name, delimitation period, and reservation category for a constituency. |
| `elections` | `election_id` | — | One election year and election definition. |
| `election_constituencies` | `election_constituency_id` | `election_id → elections`; `constituency_version_id → constituency_versions` | The seat as contested in one election. |
| `candidates` | `candidate_id` | — | Stable person identity; do not use name as the key. |
| `parties` | `party_id` | — | Party reference data. |
| `candidate_results` | `candidate_result_id` | contest, candidate, optional party | One candidate’s result in one seat; `is_winner` identifies the official winner row. |
| `parliamentary_memberships` | `membership_id` | candidate; optional election | Separates election victory from actual membership and verification. |
| `data_sources` | `source_id` | `election_id → elections` | Provenance registry for official files and URLs. |
| `import_batches` | `import_batch_id` | `source_id → data_sources` | Ingestion run and validation counts. |

## 3. Operational workflow ER diagram — MySQL workflow_* tables

```mermaid
erDiagram
    USERS ||--o{ ELECTIONS : declares
    ELECTIONS ||--o{ ELECTION_CONSTITUENCIES : opens_for
    USERS ||--o{ NOMINATIONS : submits
    ELECTIONS ||--o{ NOMINATIONS : receives
    USERS o|--o{ NOMINATIONS : reviews
    NOMINATIONS ||--o| CERTIFICATES : earns
    USERS ||--o{ CERTIFICATES : issues
    USERS o|--o{ AUDIT_LOG : performs

    USERS {
        text id PK
        text email UK
        text full_name
        text role "elector or officer"
        text phone
        text state
        text constituency
        text status
    }
    ELECTIONS {
        text id PK
        int year
        date election_date
        text title
        text scope "selected, state, all"
        text status "open, closed, deleted"
        text declared_by FK
        datetime declared_at
        datetime closed_at
    }
    ELECTION_CONSTITUENCIES {
        text id PK
        text election_id FK
        int year
        text state
        text constituency
    }
    NOMINATIONS {
        text id PK
        text election_id FK
        text candidate_user_id FK
        text state
        text constituency
        text candidate_name
        text party
        text status "pending, accepted, rejected"
        boolean is_winner
        json form_json
        datetime submitted_at
        datetime reviewed_at
        text reviewed_by FK
        text review_note
        text nomination_pdf_path
        datetime authenticated_at
    }
    CERTIFICATES {
        text id PK
        text nomination_id FK UK
        text candidate_user_id FK
        text certificate_number UK
        text pdf_path
        datetime issued_at
        text issued_by FK
    }
    AUDIT_LOG {
        text id PK
        text user_id FK
        text action
        text entity_type
        text entity_id
        json details_json
        datetime created_at
    }
```

### Workflow relationship schema

| Table | Primary key | Important foreign keys / constraints | Relationship / purpose |
|---|---|---|---|
| `users` | `id` | unique `email`; role check | Registration identity for electors/candidates and EC officers. |
| `elections` | `id` | `declared_by → users` | Officer-created declaration with entered election date and lifecycle status. |
| `election_constituencies` | `id` | `election_id → elections`; unique election/state/constituency | Materialized seats included by a declaration. |
| `nominations` | `id` | election, candidate user, reviewing officer → `users` | Candidate application, review state, winner flag, form JSON, approval PDF path. |
| `certificates` | `id` | unique `nomination_id`; candidate and issuing officer → `users` | One winner certificate per nomination. |
| `audit_log` | `id` | optional `user_id → users` | Reviewable record of declarations, reviews, approvals, winner decisions, and awards. |

## 4. Document and vector relationships

These stores are intentionally represented as logical relationships rather than SQL foreign keys.

```mermaid
flowchart TB
    USER_SQL[MySQL workflow_users.id] -. mirrored as user_id .-> MUSER[(MongoDB workflow_users)]
    NOM_SQL[MySQL workflow_nominations.id] -. mirrored as nomination_id .-> MNOM[(MongoDB workflow_nominations)]
    PROFILE[(MongoDB candidate_profiles)] -. person_key and aliases .-> CANDIDATE[Candidate identity / profile lookup]
    SOURCE[Curated election CSVs and source documents] --> CHUNK[Chunking and metadata]
    CHUNK --> VECTOR[(ChromaDB electoraw_corpus)]
    QUESTION[RAG question] --> VECTOR
    VECTOR --> ANSWER[Grounded answer with source references]
```

- `workflow_users` and `workflow_nominations` are best-effort MongoDB mirrors; MySQL remains the transactional source for role workflow state.
- `candidate_profiles` contains profile/provenance documents and does not replace the relational `candidates` identity.
- ChromaDB stores embeddings and metadata for retrieval; it has no candidate/election foreign-key enforcement.
- PDF files are filesystem artifacts referenced by `nominations.nomination_pdf_path` and `certificates.pdf_path`.
- The nullable `nominations.digital_signature` column remains only for migration compatibility; current approval PDFs do not generate or display a digital signature. `authenticated_at` is the stored approval timestamp.

## 5. Core workflow rules

1. An officer declares an election and its included seats in one relational workflow.
2. An elector submits at most one nomination for a candidate/election/seat combination.
3. A nomination transitions `pending → accepted` or `pending → rejected`.
4. Only an accepted nomination can become a winner.
5. The partial unique winner index permits at most one winner per election/state/constituency.
6. Only an accepted winner can receive one certificate.
7. Acceptance creates a nomination PDF whose visible approval line is `Approved by Returning Officer: <name>`.
8. Every administrative transition is recorded in `audit_log` and mirrored nomination documents are updated in MongoDB when available.
