# ELECTORaW role workflow

The role workflow is local-first and keeps the analytical election corpus separate from operational records.

## Storage model

- MySQL database `electoraw` is the runtime relational DBMS for workflow records. Operational tables use the `workflow_` prefix and are created by `database/mysql/02_workflow_schema.sql`.
- The legacy SQLite file at `database/electoraw_workflow.sqlite3` is a migration source only; `backend/app/services/migrate_sqlite_to_mysql.py` copies it idempotently into MySQL.
- MongoDB mirrors registration documents in `workflow_users` and nomination documents in `workflow_nominations`.
- Password hashes are stored only in MySQL; they are never mirrored to MongoDB.
- Certificates are generated as PDF files under `database/certificates/` and referenced by the MySQL `workflow_certificates` table.

## Roles

- `elector`: candidate portal. Submit a nomination to an open declared election, track review status, and download an awarded certificate.
- `officer`: EC officer console. Declare elections for selected seats, one state, or all seats; close or soft-delete declarations; review nominations; mark winners; and award certificates.

## RDBMS concepts represented in the UI

- Normalization: workflow users, elections, election constituencies, nominations, certificates, and audit events are separate MySQL tables.
- Referential integrity: foreign keys connect declarations, seats, nominations, and certificates.
- Constraints: role/status checks, unique emails, one nomination per candidate/seat/election, and one certificate per nomination.
- Transactions: declaration creation writes the election and all selected constituency rows together; certificate issuance writes the certificate reference after the PDF is created.
- Auditability: declaration, close, delete, review, and award actions record the acting user and timestamp.

## Certificate design

The generated A4 certificate uses the ELECTORaW identity, a restrained navy/green layout, certificate number, candidate, constituency, state, election title/year, party, issue date, and the officer-approved winner status. It is intentionally print-friendly and downloadable from both the officer and candidate workflows where permitted.
