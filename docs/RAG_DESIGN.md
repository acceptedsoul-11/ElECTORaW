# RAG design

The implemented local agent has four bounded stages:

1. **Classification** — identify structured election lookups (winner, votes, margin, party) versus document retrieval.
2. **Structured retrieval** — search the curated result rows and official winner matches, preserving year and constituency context.
3. **Corpus retrieval** — build deterministic constituency summary chunks plus repository methodology chunks, embed them with the local `local_hash_v1` embedding function, and persist/search them in ChromaDB under `database/chroma`. Chunk IDs are stable and source locators are retained.
4. **Grounded response** — compose a deterministic answer from matched rows and retrieved evidence, return citations, or abstain when no evidence is available.

This is a real retrieval pipeline, not a canned response. ChromaDB is local and does not require a paid embedding or generation provider. ChromaDB is the only retrieval backend in the runtime; startup fails clearly if the persistent collection cannot be opened instead of silently switching to a different index. Optional provider variables are reserved for a future generation layer; any such layer must receive only bounded retrieved context and must retain the citation contract.

For a larger production deployment, the local Chroma collection can be moved to a managed Chroma server after measuring corpus size and retrieval quality. Do not silently mix profile text into the official results corpus.
