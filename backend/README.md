# AI Financial Workspace — Backend

FastAPI + PostgreSQL backend for the AI Financial Workspace app.

## Project layout

```
backend/
├── app/
│   ├── config.py          # env-var settings (one validated source of truth)
│   ├── database.py        # engine, session factory, get_db dependency
│   ├── models.py          # SQLAlchemy ORM models (the tables)
│   ├── schemas.py         # Pydantic request/response shapes
│   ├── security.py        # password hashing + JWT + auth dependency
│   ├── ai_engine.py       # OpenRouter call + offline fallback
│   ├── main.py            # app entrypoint (CORS, routers, table creation)
│   └── routers/
│       ├── auth.py        # /auth/signup, /auth/login
│       ├── profile.py     # /api/save-profile, /profile/{user_id}
│       ├── sessions.py    # /api/sessions ... (list/create/delete/messages)
│       └── chat.py        # /api/chat, /history/{user_id}/sessions
├── requirements.txt
├── schema.sql             # reference DDL (optional — app auto-creates tables)
├── test_smoke.py          # end-to-end test of every endpoint
├── .env.example           # copy to .env and fill in
└── .gitignore
```

## 1. Set up the database (local Postgres)

Install PostgreSQL, then in `psql` (as a superuser):

```sql
CREATE USER coach_user WITH PASSWORD 'coach_pass';
CREATE DATABASE ai_financial_coach OWNER coach_user;
GRANT ALL PRIVILEGES ON DATABASE ai_financial_coach TO coach_user;
```

You do **not** need to create tables — the app does that on startup.

## 2. Configure environment

```bash
cp .env.example .env
# edit .env: set a real SECRET_KEY, and paste your OPENROUTER_API_KEY (or leave blank)
```

Generate a secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## 3. Install & run

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API is now at http://localhost:8000 — interactive docs at http://localhost:8000/docs

## 4. Test

```bash
python test_smoke.py
```

Runs signup → profile → session → chat → history → delete through real endpoints.

## AI modes

- **Offline mode** (no `OPENROUTER_API_KEY`): returns a deterministic, locally
  computed budget. Good for development and testing.
- **Live mode** (key set): calls OpenRouter, which returns structured advice +
  chart data. If the call fails for any reason, it falls back to offline mode.

## Notes for production

- Tables are created with `create_all` on startup. For versioned schema changes
  later, switch to **Alembic** migrations.
- Auth derives the user from the JWT and checks ownership on every protected
  route, so the `user_id` in the URL can't be spoofed.
