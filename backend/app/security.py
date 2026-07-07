"""
Authentication primitives, kept in one place:
- password hashing (bcrypt via passlib)
- JWT creation
- the get_current_user dependency that turns a Bearer token into a User
- ensure_owner: a small authorization check

Good-practice note on the route design:
Your blueprint passes user_id in the URL (e.g. /profile/{user_id}). On its
own that's insecure — anyone could pass someone else's id. So every protected
route also requires a valid JWT, and `ensure_owner` checks that the id in the
URL actually matches the logged-in user from the token. The token is the
source of truth; the URL id is just convenience.
"""
import re
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=True)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# Password policy: >=8 chars, upper, lower, number, special. Returned as a list
# of human-readable problems so the same rules power the API error AND (mirrored)
# the frontend hints. Enforcing here means the browser can never be bypassed.
def password_problems(password: str) -> list[str]:
    p = password or ""
    problems = []
    if len(p) < 8:
        problems.append("at least 8 characters")
    if not re.search(r"[A-Z]", p):
        problems.append("one uppercase letter")
    if not re.search(r"[a-z]", p):
        problems.append("one lowercase letter")
    if not re.search(r"[0-9]", p):
        problems.append("one number")
    if not re.search(r"[^A-Za-z0-9]", p):
        problems.append("one special character")
    return problems


def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            creds.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exc
    except jwt.PyJWTError:
        raise credentials_exc

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exc
    return user


def ensure_owner(path_user_id: uuid.UUID, current_user: models.User) -> None:
    if str(path_user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this resource",
        )
