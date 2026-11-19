# Security model

- The frontend contains no secrets; only `NEXT_PUBLIC_API_URL` is public configuration.
- MySQL and MongoDB credentials are read server-side from environment variables.
- Admin endpoints require an `ADMIN_TOKEN` header and are unavailable when it is not configured.
- Profile fetches are restricted to official allowlisted domains and use timeouts plus a clear user agent.
- Election data is read-only for ordinary users; there is no CSV ingestion endpoint.
- Pydantic bounds query sizes and search strings; the API uses no string-built SQL in the local path.
- Do not deploy with the placeholder secret key or without TLS at the reverse proxy.
