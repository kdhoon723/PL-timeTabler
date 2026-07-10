# Database migrations

Run from `apps/backend` so the locked environment is active:

```bash
uv run alembic -c ../../alembic.ini upgrade head
```

Production uses PostgreSQL 18. Migrations are the only supported way to create or
change a deployed schema; `auto_create_schema` exists solely for isolated API tests.

