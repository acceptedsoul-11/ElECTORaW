# ELECTORaW

ELECTORaW is a source-aware Indian Lok Sabha election intelligence app for the 2014, 2019 and 2024 general elections. It combines curated ECI result artifacts, a FastAPI API, a polished Next.js interface, and a grounded retrieval agent that refuses to guess when evidence is missing.

## What works now

- National dashboard with real candidate, constituency, state and vote aggregates.
- Interactive state-boundary map with seat-intensity shading, keyboard-accessible state selection, and a linked winner preview.
- Clearly labeled PoK/disputed-region overlay with no fabricated constituency or seat data.
- Complete winner archive for the official 2014, 2019 and 2024 successful-candidate records (1,628 seat records), including 2014 records whose detailed vote rows are absent.
- NDA cabinet spotlight for 21 2024 Lok Sabha winners, with party marks, portfolios, and profile links.
- Candidate and constituency exploration with bounded search and profile history.
- Winner flags sourced from `official_winners_matched.csv`; NOTA is excluded from candidate results.
- RAG assistant using structured lookups plus persistent local ChromaDB retrieval over election summaries and methodology documents.
- Visible citation locators for every grounded RAG response.
- MongoDB candidate-profile collection seeded with three official Digital Sansad biographies, surfaced in dashboard spotlight tiles and candidate detail pages.
- Controlled profile-enrichment policy and an allowlisted official-source fetcher for administrator jobs.
- Optional MySQL, MongoDB and OpenAI-compatible configuration points without making local preview dependent on those services.

## Start locally

### Backend

```powershell
cd backend
python -m pip install -r requirements.txt
$env:PYTHONPATH = "."
python -m uvicorn app.main:app --reload --port 8000
```

Open the API docs at `http://127.0.0.1:8000/docs`.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

With MongoDB running locally, seed the verified profile collection with:

```powershell
cd backend
python -m app.services.seed_mongodb_profiles
```

To refresh the optional bulk biography cache, run the bounded provenance-aware job from the repository root. It keeps exact-name secondary matches labeled as secondary and never replaces reviewed official biographies:

```powershell
$env:PYTHONPATH = "backend"
python -m backend.app.services.scrape_winner_profiles --all
```

Copy `.env.example` to `.env` at the repository root for database settings. Copy `frontend/.env.example` to `frontend/.env.local` only when the API is not on the default URL.

## Data and integrity

The local runtime reads the curated `data/processed/candidate_results_*.csv` artifacts and the matched official-winner report. It does not expose a CSV upload workflow. Production database mode should use the normalized MySQL schema in `database/mysql/01_schema.sql`; CSV mode is the reproducible local/demo path when a database is not available.

The known 2014 coverage limitation is intentionally visible in the UI: 32 official winners from Chhattisgarh and Odisha have no matched detailed-result row and are not fabricated.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [DBMS features](docs/DBMS_FEATURES.md)
- [Data sources](docs/DATA_SOURCES.md)
- [RAG design](docs/RAG_DESIGN.md)
- [Security](docs/SECURITY.md)
- [Testing](docs/TESTING.md)
- [Known limitations](docs/KNOWN_LIMITATIONS.md)
