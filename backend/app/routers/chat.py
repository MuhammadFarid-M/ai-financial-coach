"""
The AI core endpoint.

POST /api/chat does the real work:
  1. Confirm the session belongs to the user.
  2. Resolve the financial metrics (use the live payload if sent, else the
     saved profile from the database).
  3. Call the AI engine to produce advice + optional chart data.
  4. Persist the prompt/response as an Insight row (this IS the "save to
     history" step — there's no separate write path, which avoids the
     duplication implied by the blueprint's separate /insights endpoint).
  5. Return the saved row.

GET /history/{user_id}/sessions returns every session with its messages,
chronologically — handy for exports or restoring full continuity.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.ai_engine import generate_strategy
from app.database import get_db
from app.routers.sessions import new_session
from app.security import ensure_owner, get_current_user

router = APIRouter(tags=["chat"])


@router.post("/api/chat", response_model=schemas.InsightResponse)
def chat(
    payload: schemas.ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ensure_owner(payload.user_id, current_user)

    # If a session_id was given, fetch + authorize it now. If not, we'll create
    # one AFTER the AI call so we can name it from the AI-generated title.
    existing_session = None
    if payload.session_id is not None:
        existing_session = (
            db.query(models.ChatSession)
            .filter(
                models.ChatSession.id == payload.session_id,
                models.ChatSession.user_id == payload.user_id,
            )
            .first()
        )
        if existing_session is None:
            raise HTTPException(status_code=404, detail="Session not found")

    # The AI's financial context comes from the saved profile — never from the
    # request body. This keeps the numbers authoritative and unspoofable.
    profile = (
        db.query(models.Profile)
        .filter(models.Profile.user_id == payload.user_id)
        .first()
    )
    if profile is None:
        raise HTTPException(
            status_code=400,
            detail="No financial profile found. Save your profile before chatting.",
        )

    text, chart_bool, chart_data, title = generate_strategy(
        payload.prompt,
        float(profile.monthly_income),
        float(profile.monthly_expenses),
        float(profile.current_savings),
        profile.risk_tolerance,
    )

    # New thread? Name it from the AI's title. Existing thread keeps its name.
    session = existing_session or new_session(db, payload.user_id, title=title)

    insight = models.Insight(
        user_id=payload.user_id,
        session_id=session.id,
        user_prompt=payload.prompt,
        conversational_response=text,
        chart_bool=chart_bool,
        chart_data=chart_data,
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return insight


@router.get("/history/{user_id}/sessions")
def get_full_history(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ensure_owner(user_id, current_user)
    sessions = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == user_id)
        .order_by(models.ChatSession.created_at.asc())
        .all()
    )
    return [
        {
            "session_id": str(s.id),
            "title": s.title,
            "created_at": s.created_at,
            "messages": [
                {
                    "id": str(m.id),
                    "user_prompt": m.user_prompt,
                    "conversational_response": m.conversational_response,
                    "chart_bool": m.chart_bool,
                    "chart_data": m.chart_data,
                    "created_at": m.created_at,
                }
                for m in s.insights
            ],
        }
        for s in sessions
    ]
