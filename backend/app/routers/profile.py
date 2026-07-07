"""Profile routes: POST /api/save-profile and GET /profile/{user_id}."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import ensure_owner, get_current_user

router = APIRouter(tags=["profile"])


@router.post("/api/save-profile", response_model=schemas.ProfileResponse)
def save_profile(
    payload: schemas.ProfileRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ensure_owner(payload.user_id, current_user)

    # "Upsert": update the existing profile, or create one if it's the first time.
    profile = (
        db.query(models.Profile)
        .filter(models.Profile.user_id == payload.user_id)
        .first()
    )
    if profile is None:
        profile = models.Profile(user_id=payload.user_id)
        db.add(profile)

    profile.monthly_income = payload.monthly_income
    profile.monthly_expenses = payload.monthly_expenses
    profile.current_savings = payload.current_savings
    profile.risk_tolerance = payload.risk_tolerance

    db.commit()
    db.refresh(profile)
    return profile


@router.get("/profile/{user_id}", response_model=schemas.ProfileResponse)
def get_profile(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ensure_owner(user_id, current_user)
    profile = (
        db.query(models.Profile).filter(models.Profile.user_id == user_id).first()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile
