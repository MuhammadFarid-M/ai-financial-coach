"""
Session (strategy thread) routes.

- GET    /api/sessions/{user_id}            -> list a user's threads
- POST   /api/sessions                      -> create a thread
- DELETE /api/sessions/{session_id}         -> delete a thread (+ its messages, via cascade)
- GET    /api/sessions/{session_id}/messages -> load all messages in a thread
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import ensure_owner, get_current_user

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _get_owned_session(session_id, db, current_user) -> models.ChatSession:
    """Fetch a session and confirm it belongs to the logged-in user."""
    session = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.id == session_id)
        .first()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(session.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized for this session")
    return session


@router.get("/{user_id}", response_model=list[schemas.SessionResponse])
def list_sessions(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ensure_owner(user_id, current_user)
    return (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == user_id)
        .order_by(models.ChatSession.created_at.desc())
        .all()
    )


def new_session(db, user_id, title=None) -> models.ChatSession:
    """Create + persist a session, auto-numbering the title if none is given.

    Shared by the POST /api/sessions route AND the chat route (which creates a
    session on the fly for a brand-new thread), so the naming logic lives in
    exactly one place.
    """
    if not title:
        count = (
            db.query(models.ChatSession)
            .filter(models.ChatSession.user_id == user_id)
            .count()
        )
        title = f"Strategy Thread #{count + 1}"

    session = models.ChatSession(user_id=user_id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("", response_model=schemas.SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: schemas.SessionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ensure_owner(payload.user_id, current_user)
    return new_session(db, payload.user_id, payload.title)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    session = _get_owned_session(session_id, db, current_user)
    db.delete(session)  # cascade removes the thread's insights too
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{session_id}/messages", response_model=list[schemas.InsightResponse])
def get_session_messages(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_owned_session(session_id, db, current_user)  # authorization check
    return (
        db.query(models.Insight)
        .filter(models.Insight.session_id == session_id)
        .order_by(models.Insight.created_at.asc())
        .all()
    )
