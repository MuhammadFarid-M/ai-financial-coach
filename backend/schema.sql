-- ============================================================================
--  REFERENCE SCHEMA  (optional)
-- ----------------------------------------------------------------------------
--  You do NOT need to run this. When the FastAPI app starts, SQLAlchemy
--  creates these tables automatically (Base.metadata.create_all).
--
--  This file exists so you can SEE the structure and, if you prefer, build
--  the schema by hand. If you DO run it manually, let SQLAlchemy own the
--  tables afterwards to avoid the two definitions drifting apart.
-- ============================================================================

-- gen_random_uuid() needs pgcrypto (only relevant for manual inserts).
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    username        VARCHAR(100) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);

CREATE TABLE IF NOT EXISTS profiles (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL UNIQUE REFERENCES users (id) ON DELETE CASCADE,
    monthly_income   NUMERIC(14, 2) DEFAULT 0,
    monthly_expenses NUMERIC(14, 2) DEFAULT 0,
    savings_goal     NUMERIC(14, 2) DEFAULT 0,
    risk_tolerance   VARCHAR(100) DEFAULT 'Moderate'
);

CREATE TABLE IF NOT EXISTS sessions (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    title      VARCHAR(255) NOT NULL DEFAULT 'New Strategy Thread',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS insights (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    session_id              UUID NOT NULL REFERENCES sessions (id) ON DELETE CASCADE,
    user_prompt             TEXT NOT NULL,
    conversational_response TEXT NOT NULL,
    chart_bool              BOOLEAN DEFAULT FALSE,
    chart_data              JSONB,
    created_at              TIMESTAMPTZ DEFAULT now()
);
