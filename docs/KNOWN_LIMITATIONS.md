# Known limitations

- The repository has no active database service or credentials guaranteed in the development environment, so the default runtime uses the curated processed CSV artifacts. MySQL remains the production schema and integration target.
- 2014 has 32 unmatched official winners in Chhattisgarh and Odisha; the application does not invent detailed candidate rows for them.
- The local MongoDB profile collection currently contains three seeded official Digital Sansad biographies; broader MP coverage still requires the controlled enrichment workflow and review.
- The local RAG engine uses persistent ChromaDB with deterministic `local_hash_v1` embeddings as its only retrieval backend. A neural embedding model can be added later if semantic recall needs further improvement.
- Constituency map geometry is not included because no verified boundary asset is present; the API provides a searchable list fallback.
