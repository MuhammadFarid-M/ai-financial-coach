# AI Financial Workspace

A personal-finance AI coach. Users set up a financial profile (income, expenses,
savings goal, risk tolerance), then chat with an AI strategist that returns
tailored guidance — including structured **allocation breakdowns** rendered as
charts. Conversations are organized into threads ("Strategy Threads") and
persisted so history is preserved across sessions.

> **Status:** Backend + database are complete and tested end-to-end.
> Frontend (React + Vite) is next.

---

## Features

- **Authentication** — email/username signup and login, bcrypt-hashed passwords, JWT-based sessions.
- **Financial profile** — one profile per user (income, expenses, savings goal, risk tolerance), stored and editable.
- **Strategy Threads** — create, list, and delete conversation threads; deleting a thread cascades to its messages.
- **AI coaching** — grounded in the user's own numbers; returns a strategy plus an optional allocation chart.
- **Offline fallback** — a deterministic calculator runs when no AI key is configured, so the app works during development.
- **Conversation history** — every exchange is saved and can be replayed per thread in chronological order.
- **Security** — protected routes require a valid token; ownership checks block one user from reading another's data.

---

## Tech stack

| Layer     | Technology                                              |
| --------- | ------------------------------------------------------- |
| Backend   | Python, FastAPI, Uvicorn                                |
| ORM / DB  | SQLAlchemy 2.0, PostgreSQL 16                            |
| Auth      | passlib (bcrypt), python-jose (JWT)                      |
| Validation| Pydantic v2, pydantic-settings                          |
| AI        | OpenRouter (OpenAI-compatible API) + offline calculator |
| Frontend  | React + Vite _(planned)_                                |
| Deploy    | Render (web service + managed Postgres)                 |

---

## Project structure

```
ai-financial-workspace/
├── backend/
│   ├── app/
│   │   ├── config.py        # env-driven settings (single source of truth)
│   │   ├── database.py      # engine, session factory, get_db dependency
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   ├── schemas.py       # Pydantic request/response contracts
│   │   ├── security.py      # password hashing, JWT, auth + ownership guards
│   │   ├── ai_engine.py     # OpenRouter call + offline fallback
│   │   ├── main.py          # app instance, CORS, router wiring
│   │   └── routers/
│   │       ├── auth.py      # /auth/*
│   │       ├── profile.py   # /api/save-profile, /profile/*
│   │       ├── sessions.py  # /api/sessions/*
│   │       └── chat.py      # /api/chat, /history/*
│   ├── schema.sql           # raw DDL to create the database by hand
│   ├── requirements.txt
│   ├── render.yaml          # Render Blueprint (one-click deploy)
│   ├── .env.example         # copy to .env
│   └── README.md            # backend-specific quickstart
└── frontend/                # (coming next)
```

---

## Database schema

Four tables, all with UUID primary keys. Foreign keys use `ON DELETE CASCADE`,
so removing a parent row cleans up its children automatically.

| Table      | Key columns                                                                                     | Purpose                          |
| ---------- | ----------------------------------------------------------------------------------------------- | -------------------------------- |
| `users`    | `id`, `email` (unique), `username`, `hashed_password`                                            | Account records                  |
| `profiles` | `id`, `user_id` (unique FK), `monthly_income`, `monthly_expenses`, `savings_goal`, `risk_tolerance` | One financial profile per user   |
| `sessions` | `id`, `user_id` (FK), `title`, `created_at`                                                      | A "Strategy Thread"              |
| `insights` | `id`, `user_id` (FK), `session_id` (FK), `user_prompt`, `conversational_response`, `chart_bool`, `chart_data` (JSONB), `created_at` | Stored chat exchanges |

Relationships: a **user** has one **profile** and many **sessions**; a
**session** has many **insights**.

---

## Getting started (local)

### Prerequisites

- Python 3.11+
- PostgreSQL 13+ running locally
- (Optional) an OpenRouter API key for live AI responses

### 1. Set up the database

```bash
createdb ai_financial_coach
psql -U postgres -d ai_financial_coach -f backend/schema.sql
```

### 2. Set up the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then edit .env (see below)
```

### 3. Run

```bash
uvicorn app.main:app --reload
```

- API: http://localhost:8000
- Interactive docs (Swagger): http://localhost:8000/docs

Leaving `OPENROUTER_API_KEY` blank uses the built-in offline calculator, so
every endpoint works before you wire up the real AI.

---

## Environment variables

Configured in `backend/.env` locally, and in the Render dashboard in production.

| Variable                      | Required | Description                                                        |
| ----------------------------- | -------- | ------------------------------------------------------------------ |
| `DATABASE_URL`                | Yes      | e.g. `postgresql+psycopg2://postgres:postgres@localhost:5432/ai_financial_coach` |
| `JWT_SECRET`                  | Yes      | Long random string. Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `JWT_ALGORITHM`               | No       | Defaults to `HS256`                                                |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No       | Token lifetime in minutes (default `1440`)                         |
| `OPENROUTER_API_KEY`          | No       | Leave blank to use the offline calculator                          |
| `OPENROUTER_MODEL`            | No       | Any model id from https://openrouter.ai/models                     |
| `CORS_ORIGINS`                | No       | Comma-separated allowed frontend origins                           |

---

## API reference

Protected routes require an `Authorization: Bearer <token>` header. A token is
returned by both signup and login.

### Auth

| Method | Path            | Body                              | Returns                                   |
| ------ | --------------- | --------------------------------- | ----------------------------------------- |
| POST   | `/auth/signup`  | `email`, `username`, `password`   | `access_token`, `user_id`, `username`     |
| POST   | `/auth/login`   | `email`, `password`               | `access_token`, `user_id`, `username`     |

### Profile

| Method | Path                          | Auth | Description                          |
| ------ | ----------------------------- | ---- | ----------------------------------- |
| POST   | `/api/save-profile`           | Yes  | Create or update the user's profile |
| GET    | `/profile/{user_id}`          | Yes  | Fetch the user's profile            |
| POST   | `/profile/{user_id}/insights` | Yes  | Manually persist a chat exchange    |

### Sessions

| Method | Path                          | Auth | Description                             |
| ------ | ----------------------------- | ---- | -------------------------------------- |
| GET    | `/api/sessions/{user_id}`     | Yes  | List the user's threads                |
| POST   | `/api/sessions`               | Yes  | Create a thread (auto-titled if empty) |
| DELETE | `/api/sessions/{session_id}`  | Yes  | Delete a thread and its messages       |

### Chat & history

| Method | Path                          | Auth | Description                                       |
| ------ | ----------------------------- | ---- | ------------------------------------------------ |
| POST   | `/api/chat`                   | Yes  | Send a prompt; returns strategy + optional chart |
| GET    | `/history/{user_id}/sessions` | Yes  | All threads with messages in chronological order |

### Health

| Method | Path | Description        |
| ------ | ---- | ------------------ |
| GET    | `/`  | Service heartbeat  |

---

## The AI engine

`app/ai_engine.py` exposes `generate_strategy(prompt, profile)`, which returns:

```json
{
  "response": "markdown strategy text",
  "chart": { "labels": ["Savings Goal", "Equity", "Debt", "Cash Buffer"],
             "values": [300000, 105000, 30000, 15000] }
}
```

- **With `OPENROUTER_API_KEY` set:** the profile numbers and prompt are sent to
  OpenRouter, which is instructed to reply in strict JSON so the optional chart
  can be parsed reliably. Parsing is defensive (stray code fences are stripped;
  on failure it degrades to plain text).
- **Without a key:** an offline calculator funds the savings goal from the
  monthly surplus, then splits the remainder across equity / debt / cash by risk
  tolerance (Aggressive 70/20/10, Moderate 50/35/15, Conservative 30/50/20).

`chart` is included only for allocation-style questions; otherwise it is `null`.

---

## Deployment (Render)

`backend/render.yaml` is a Blueprint that provisions the web service **and** a
managed PostgreSQL database together.

1. Push the repo to GitHub.
2. In Render, create a new **Blueprint** from the repo.
3. Render injects `DATABASE_URL` automatically and generates `JWT_SECRET`.
4. Add `OPENROUTER_API_KEY` in the dashboard (kept secret, never committed).
5. After the frontend is deployed, set `CORS_ORIGINS` to its URL.

> Render hands out `DATABASE_URL` starting with `postgres://`; the app rewrites
> it to the `postgresql+psycopg2://` form SQLAlchemy 2.0 requires, so no manual
> fix is needed.

---

## Roadmap

- [x] Database schema
- [x] Backend API (auth, profile, sessions, chat, history)
- [x] Offline AI fallback
- [ ] React + Vite frontend
- [ ] Live OpenRouter integration verified end-to-end
- [ ] Production deployment (Render)

---

## Security notes

- Passwords are hashed with bcrypt and never stored or returned in plain text.
- Login returns the same generic error for unknown emails and wrong passwords,
  so account existence isn't leaked.
- Protected endpoints verify the token's user matches the `user_id` being acted
  on, preventing one user from accessing another's data.
- Secrets live only in environment variables — never in the repo.

---

