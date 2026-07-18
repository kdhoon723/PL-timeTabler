# PL-timeTabler backend

FastAPI serves the active versioned catalog, lossless DREAMS history lookup,
curriculum evidence, account-owned academic records, and the optimization queue.
PostgreSQL stores mutable state, the searchable historical archive, and normalized
2016-2026 curriculum/graduation requirements; checked-in fixtures and their
checksums remain the immutable ingestion source.

```bash
uv sync --all-groups
uv run timetabler-validate-data
uv run timetabler-normalize-requirements
uv run timetabler-normalize-graduation-requirements
uv run alembic -c ../../alembic.ini upgrade head
uv run timetabler-ingest
uv run timetabler-api
```

The optimizer runs as a separate process against the durable job queue. It imports
the request/result contracts from `timetabler.api.schemas` and never runs inside
the API event loop.

The root Compose stack also exposes a local-only, read-only Pgweb console at
`http://127.0.0.1:18081` for inspecting the actual PostgreSQL schema and rows.
