"""Authentication routes: /auth/signup and /auth/login."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.security import create_access_token, hash_password, password_problems, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=schemas.AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: schemas.SignupRequest, db: Session = Depends(get_db)):
    # Enforce the unique-email rule with a clean 400 instead of a raw DB error.
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Enforce password strength server-side (the browser can be bypassed).
    problems = password_problems(payload.password)
    if problems:
        raise HTTPException(
            status_code=400,
            detail="Password must have " + ", ".join(problems) + ".",
        )

    user = models.User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),  # never store plain text
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return schemas.AuthResponse(access_token=token, user_id=user.id, username=user.username)


@router.post("/login", response_model=schemas.AuthResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    # Same generic message whether the email or password was wrong -> don't
    # leak which accounts exist.
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id)
    return schemas.AuthResponse(access_token=token, user_id=user.id, username=user.username)
