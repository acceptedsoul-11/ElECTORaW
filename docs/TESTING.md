# Testing

Backend tests use FastAPI’s `TestClient` and the checked-in processed data.

```powershell
cd backend
python -m pytest
```

The tests cover health/election metadata, the 2014 candidate baseline and limitation note, candidate search, a cited RAG answer, and a safe unsupported-question path. Frontend build verification is:

```powershell
cd frontend
npm install
npm run build
```

Service-backed MySQL, MongoDB and external LLM behavior requires those services and credentials; it is not reported as verified by the local tests.
