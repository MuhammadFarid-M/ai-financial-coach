"""
Pydantic schemas = the validated shapes of data crossing the API boundary.

Two jobs:
1. Request schemas reject malformed input before it ever reaches your logic.
2. Response schemas (with from_attributes=True) let us return an ORM object
   directly and have FastAPI serialise only the fields we declare here —
   so internal columns like hashed_password can never leak out.
"""
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ----------------------------- Auth -----------------------------
class SignupRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1)  # full strength rules enforced in the route


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    username: str


# --------------------------- Profile ----------------------------
class ProfileRequest(BaseModel):
    user_id: uuid.UUID
    monthly_income: float = 0
    monthly_expenses: float = 0
    current_savings: float = 0
    risk_tolerance: str = "Moderate"


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: uuid.UUID
    monthly_income: float
    monthly_expenses: float
    current_savings: float
    risk_tolerance: str


# --------------------------- Sessions ---------------------------
class SessionCreate(BaseModel):
    user_id: uuid.UUID
    title: Optional[str] = None  # auto-numbered if omitted


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    created_at: datetime


# ----------------------------- Chat -----------------------------
class ChatRequest(BaseModel):
    user_id: uuid.UUID
    session_id: Optional[uuid.UUID] = None  # omit to start a brand-new thread
    prompt: str = Field(min_length=1)
    # NOTE: no financial metrics here on purpose. The server reads the user's
    # profile from the database, so the AI context can't be spoofed by callers.


class InsightResponse(BaseModel):
    """The shape of a saved chat message returned to the frontend."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    session_id: uuid.UUID
    user_prompt: str
    conversational_response: str
    chart_bool: bool
    chart_data: Optional[Any] = None
    created_at: datetime
