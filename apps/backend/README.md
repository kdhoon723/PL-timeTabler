# PL-timeTabler backend

FastAPI serves the versioned catalog, curriculum evidence, optimization job queue,
and privacy-minimal timetable shares. PostgreSQL stores mutable job/share state;
the checked-in official fixtures remain the immutable data source for ingestion.

```bash
uv sync --all-groups
uv run timetabler-validate-data
uv run alembic -c ../../alembic.ini upgrade head
uv run timetabler-api
```

The optimizer runs as a separate process against the durable job queue. It imports
the request/result contracts from `timetabler.api.schemas` and never runs inside
the API event loop.

