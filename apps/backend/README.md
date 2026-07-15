# PL-timeTabler backend

FastAPI serves the active versioned catalog, lossless DREAMS history lookup,
curriculum evidence, account-owned academic records, and the optimization queue.
PostgreSQL stores mutable state plus the searchable historical archive; checked-in
fixtures and their checksums remain the immutable ingestion source.

```bash
uv sync --all-groups
uv run timetabler-validate-data
uv run alembic -c ../../alembic.ini upgrade head
uv run timetabler-import-dreams-history
uv run timetabler-api
```

The optimizer runs as a separate process against the durable job queue. It imports
the request/result contracts from `timetabler.api.schemas` and never runs inside
the API event loop.
