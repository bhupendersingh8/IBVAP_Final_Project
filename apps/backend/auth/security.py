"""
IBVAP Security Utilities
========================
Password hashing, JWT creation/verification, and FastAPI dependency for
extracting the authenticated user from an incoming request.

Security notes
--------------
* All JWT validation errors are collapsed to a single generic 401 response
  to avoid leaking information about *why* a token was rejected.
* Secrets are never written to logs.  Structlog ``bind_contextvars`` is
  intentionally not called with any token material.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel

from config import get_settings

# ---------------------------------------------------------------------------
# Module-level logger — no token/secret data must ever be passed here.
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*.

    Args:
        password: Plain-text password supplied by the user.

    Returns:
        A bcrypt hash string safe for database storage.
    """
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return ``True`` when *plain_password* matches *hashed_password*.

    Args:
        plain_password:  Password candidate from the login form.
        hashed_password: Stored bcrypt hash retrieved from the database.

    Returns:
        Boolean indicating whether the password is correct.
    """
    return _pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# Token model
# ---------------------------------------------------------------------------


class UserInToken(BaseModel):
    """Payload extracted from a decoded JWT access token.

    Attributes:
        user_id:  Database PK of the authenticated user (UUID string).
        username: Display / login username.
        role:     RBAC role string (``ADMIN`` | ``OPERATOR`` | ``READ_ONLY``).
    """

    user_id: str
    username: str
    role: str


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

_GENERIC_AUTH_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials.",
    headers={"WWW-Authenticate": "Bearer"},
)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Encode *data* as a signed JWT access token.

    Args:
        data:          Arbitrary claims to embed in the token.  A ``sub``
                       (subject) key is recommended per RFC 7519.
        expires_delta: Token lifetime.  Defaults to the value of
                       ``JWT_ACCESS_TOKEN_EXPIRE_MINUTES`` in settings.

    Returns:
        A compact serialised JWT string.

    Note:
        The ``exp`` claim is always set; the raw secret is never logged.
    """
    settings = get_settings()
    to_encode = data.copy()

    if expires_delta is not None:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "iat": datetime.now(UTC)})

    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT access token.

    Args:
        token: Compact serialised JWT string from the ``Authorization`` header.

    Returns:
        The decoded claims dictionary.

    Raises:
        :class:`fastapi.HTTPException` 401: If the token is invalid, expired,
            or has an unrecognised signature — **always** the same generic
            message so callers cannot distinguish the failure reason.
    """
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        # Log at DEBUG so the CI/monitoring pipeline can see token churn
        # without exposing the token itself.
        logger.debug("JWT validation failed: token expired")
        raise _GENERIC_AUTH_ERROR
    except jwt.InvalidTokenError:
        logger.debug("JWT validation failed: invalid token")
        raise _GENERIC_AUTH_ERROR


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInToken:
    """FastAPI dependency that returns the authenticated user from the JWT.

    Inject this dependency into any route that requires authentication::

        @router.get("/protected")
        async def protected_route(user: UserInToken = Depends(get_current_user)):
            return {"hello": user.username}

    Args:
        token: Bearer token extracted automatically by
               :class:`fastapi.security.OAuth2PasswordBearer`.

    Returns:
        :class:`UserInToken` populated from the JWT claims.

    Raises:
        :class:`fastapi.HTTPException` 401: If the token cannot be validated
            or required claims (``sub``, ``username``, ``role``) are missing.
    """
    payload = decode_token(token)

    user_id: str | None = payload.get("sub")
    username: str | None = payload.get("username")
    role: str | None = payload.get("role")

    if not user_id or not username or not role:
        logger.debug("JWT validation failed: missing required claims")
        raise _GENERIC_AUTH_ERROR

    return UserInToken(user_id=user_id, username=username, role=role)
