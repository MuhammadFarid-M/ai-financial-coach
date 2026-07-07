"""
The database layer: one engine, one session factory, one Base.

Key idea (good practice): the rest of the app NEVER creates its own
database connection. It asks for a session through the `get_db` dependency,
and FastAPI guarantees the session is closed afterwards.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# `pool_pre_ping` checks a connection is still alive before using it.
# This prevents "connection already closed" errors after the DB or a
# cloud provider drops idle connections.
engine = create_engine(settings.sqlalchemy_url, pool_pre_ping=True)

# A factory that produces new Session objects bound to our engine.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Every ORM model will inherit from this Base.
Base = declarative_base()


def get_db():
    """
    FastAPI dependency. Yields a session, then always closes it.

    Usage in a route:
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
