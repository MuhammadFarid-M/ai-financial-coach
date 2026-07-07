"""
Application entrypoint. Run with:  uvicorn app.main:app --reload

What happens here:
- Import the models so SQLAlchemy knows about every table.
- Base.metadata.create_all() creates any missing tables on startup. This is
  perfect for development and a first deploy. For a mature production app you'd
  switch to Alembic migrations (so schema changes are versioned) — noted as a
  next step, not needed yet.
- CORS middleware lets your Vite frontend (http://localhost:5173) call the API.
- Each feature's router is mounted.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (import registers tables on Base.metadata)
from app.config import settings
from app.database import Base, engine
from app.routers import auth, chat, profile, sessions

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Financial Workspace API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(sessions.router)
app.include_router(chat.router)


@app.get("/", tags=["health"])
def health():
    """Simple health check — Render pings this to confirm the service is up."""
    return {"status": "ok", "service": "ai-financial-workspace"}
