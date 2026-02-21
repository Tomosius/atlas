# PostgreSQL

## Project

- Connection: `{{postgresql.database_url}}`
- Host: {{postgresql.host}} | Port: {{postgresql.port}}
- Database: {{postgresql.database}} | User: {{postgresql.user}}

## Connection

Always use `DATABASE_URL` for connection strings — never hardcode credentials:

```bash
# .env
DATABASE_URL=postgresql://user:password@localhost:5432/mydb
```

```python
# Python (psycopg3)
import psycopg
conn = psycopg.connect(os.environ["DATABASE_URL"])

# SQLAlchemy
from sqlalchemy import create_engine
engine = create_engine(os.environ["DATABASE_URL"])
```

## CLI Commands

```bash
psql $DATABASE_URL               # interactive session
psql $DATABASE_URL -c "SELECT 1" # run a single query
pg_dump $DATABASE_URL > dump.sql # export database
psql $DATABASE_URL < dump.sql    # import/restore
```

## Migrations

Use a migration tool — never run raw ALTER TABLE manually in production:

```bash
# Alembic (Python)
alembic revision --autogenerate -m "add users table"
alembic upgrade head
alembic downgrade -1

# Django
python manage.py makemigrations
python manage.py migrate
```

Migration rules:
- Always write a corresponding `downgrade` / reverse migration
- Never delete columns immediately — mark nullable first, then drop in a later migration
- Test migrations on a copy of production data before deploying

## Schema Conventions

- Table names: lowercase, plural, snake_case (`user_accounts`, not `UserAccount`)
- Primary key: `id BIGSERIAL PRIMARY KEY` or `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- Timestamps: `created_at TIMESTAMPTZ DEFAULT NOW()`, `updated_at TIMESTAMPTZ`
- Foreign keys: always add an index on the FK column
- Use `TIMESTAMPTZ` (with timezone) not `TIMESTAMP`

## Indexes

```sql
-- Index on foreign key
CREATE INDEX idx_orders_user_id ON orders(user_id);

-- Partial index for common filtered queries
CREATE INDEX idx_active_users ON users(email) WHERE deleted_at IS NULL;

-- Composite index — column order matters (most selective first)
CREATE INDEX idx_events_user_created ON events(user_id, created_at DESC);
```

## Transactions

```python
# psycopg3: use context manager
with psycopg.connect(DATABASE_URL) as conn:
    with conn.transaction():
        conn.execute("INSERT INTO ...")
        conn.execute("UPDATE ...")
# auto-commit on success, auto-rollback on exception
```

- Keep transactions short — long-held locks block other queries
- Avoid transactions that span HTTP requests

## Query Safety

Never interpolate values into SQL strings — always use parameterised queries:

```python
# WRONG — SQL injection risk
cur.execute(f"SELECT * FROM users WHERE email = '{email}'")

# CORRECT — parameterised
cur.execute("SELECT * FROM users WHERE email = %s", (email,))
```

## Docker (local dev)

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: myuser
      POSTGRES_PASSWORD: mypassword
      POSTGRES_DB: mydb
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```
