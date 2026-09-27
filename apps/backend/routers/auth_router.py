"""
IBVAP Authentication & User Access Router
==========================================
Provides standard endpoints for user authentication, token generation,
and principal inspection.
"""
import os
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ..auth.jwt_auth import create_access_token, require_auth, _DEV_DEMO_MODE
from ..auth.rbac import Role

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# Credentials for border operator stations
# In production, backed by hashed passwords in PostgreSQL/SQLite User table or env secrets
DEMO_CREDENTIALS = {
    "admin": {
        "password": os.environ.get("IBVAP_ADMIN_PASSWORD", "adminpassword123"),
        "role": Role.ADMIN.value
    },
    "supervisor": {
        "password": os.environ.get("IBVAP_SUPERVISOR_PASSWORD", "supervisorpass123"),
        "role": Role.SUPERVISOR.value
    },
    "operator": {
        "password": os.environ.get("IBVAP_OPERATOR_PASSWORD", "operatorpass123"),
        "role": Role.OPERATOR.value
    },
    "viewer": {
        "password": os.environ.get("IBVAP_VIEWER_PASSWORD", "viewerpass123"),
        "role": Role.VIEWER.value
    },
}


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    expires_in_minutes: int = 120


class UserInfoResponse(BaseModel):
    username: str
    role: str
    auth_mode: str
    dev_mode: Optional[bool] = False


@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Authenticates user and returns a signed HMAC-SHA256 JWT access token.
    Enforces role-based permissions for Operator, Supervisor, and Admin.
    """
    user_record = DEMO_CREDENTIALS.get(credentials.username.lower())
    if not user_record or user_record["password"] != credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role = user_record["role"]
    token = create_access_token({
        "sub": credentials.username.lower(),
        "role": role
    })

    return LoginResponse(
        access_token=token,
        role=role,
        username=credentials.username.lower()
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(principal: Dict[str, Any] = Depends(require_auth)):
    """Inspects the currently active principal, role, and auth mode."""
    return UserInfoResponse(
        username=principal.get("sub", "unknown"),
        role=principal.get("role", Role.VIEWER.value),
        auth_mode=principal.get("auth_mode", "UNKNOWN"),
        dev_mode=principal.get("dev_mode", False)
    )
