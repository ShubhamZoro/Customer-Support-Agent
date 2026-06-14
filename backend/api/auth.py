"""
api/auth.py — Login / Logout / Me endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from data.auth_db import login, logout, get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class LogoutRequest(BaseModel):
    session_id: str


@router.post("/login")
async def auth_login(body: LoginRequest):
    """Authenticate a user. Returns session_id on success."""
    session = login(body.email, body.password)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return {
        "session_id": session["session_id"],
        "user_id": session["user_id"],
        "email": session["email"],
        "login_at": session["login_at"],
    }


@router.post("/logout")
async def auth_logout(body: LogoutRequest):
    """Invalidate a session."""
    found = logout(body.session_id)
    if not found:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"message": "Logged out successfully."}


@router.get("/me")
async def auth_me(session_id: str):
    """Return the user associated with a session_id."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    return {
        "user_id": session["user_id"],
        "email": session["email"],
        "login_at": session["login_at"],
    }
