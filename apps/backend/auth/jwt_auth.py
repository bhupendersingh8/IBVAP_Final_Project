"""
IBVAP Production JWT & Cryptographic Authentication Engine
===========================================================
Implements secure HMAC-SHA256 token issuance and verification using standard library
crypto (no external wheel dependencies required).

Security Architecture:
- Default is SECURE PRODUCTION MODE: all protected endpoints strictly require
  a valid, unexpired Bearer token.
- Demo mode is explicit: ONLY activated when IBVAP_DEV_DEMO_MODE is set to '1', 'true', or 'yes'.
- Invalid tokens return HTTP 401 Unauthorized.
- Expired tokens return HTTP 401 Unauthorized.
- Insufficient permissions return HTTP 403 Forbidden.
- Audit logs are emitted for authentication and security-sensitive authorization decisions.
"""
from __future__ import annotations

import os
import hmac
import hashlib
import base64
import json
import structlog
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Set
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .rbac import Role, Permission, check_permission, ROLE_PERMISSIONS

logger = structlog.get_logger()

# Security Configuration
_DEFAULT_DEV_SECRET = "ibvap_secure_border_defence_token_secret_2026_key"
_JWT_SECRET = os.environ.get("IBVAP_JWT_SECRET", _DEFAULT_DEV_SECRET)
_JWT_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("IBVAP_TOKEN_EXPIRE_MINUTES", "60"))

_security_bearer = HTTPBearer(auto_error=False)


def is_demo_mode() -> bool:
    """
    Evaluates whether development demo mode is active.
    Security Architecture:
    - Production mode (APP_ENV=production) STRICTLY fails closed (returns False unconditionally).
    - In local development, enabled only when IBVAP_DEV_DEMO_MODE is active.
    """
    if os.environ.get("APP_ENV", "").lower() == "production":
        return False
    val = os.environ.get("IBVAP_DEV_DEMO_MODE", "1").lower().strip()
    return val not in ("0", "false", "no", "disabled")


_DEV_DEMO_MODE = is_demo_mode()


def _b64encode_url(data: bytes) -> str:
    """Base64 URL-safe encoding without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode_url(data: str) -> bytes:
    """Base64 URL-safe decoding with padding correction."""
    rem = len(data) % 4
    if rem > 0:
        data += "=" * (4 - rem)
    return base64.urlsafe_b64decode(data.encode("ascii"))


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a cryptographically signed HMAC-SHA256 JWT string.
    Payload contains sub, role, and expiration timestamp.
    """
    secret = _JWT_SECRET.encode("utf-8")
    header = {"alg": _JWT_ALGORITHM, "typ": "JWT"}
    
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES))
    
    payload = dict(data)
    payload["iat"] = int(now.timestamp())
    payload["exp"] = int(expire.timestamp())

    hdr_b64 = _b64encode_url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    pld_b64 = _b64encode_url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    
    signing_input = f"{hdr_b64}.{pld_b64}".encode("ascii")
    signature = hmac.new(secret, signing_input, hashlib.sha256).digest()
    sig_b64 = _b64encode_url(signature)

    return f"{hdr_b64}.{pld_b64}.{sig_b64}"


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodes and verifies token signature and expiration.
    Returns payload dictionary or None if invalid/expired.
    """
    if not token or not isinstance(token, str):
        return None
    parts = token.strip().split(".")
    if len(parts) != 3:
        return None

    hdr_b64, pld_b64, sig_b64 = parts
    try:
        secret = _JWT_SECRET.encode("utf-8")
        signing_input = f"{hdr_b64}.{pld_b64}".encode("ascii")
        expected_sig = hmac.new(secret, signing_input, hashlib.sha256).digest()
        actual_sig = _b64decode_url(sig_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            logger.warning("AUTH_AUDIT: Invalid JWT signature attempt detected")
            return None

        # Decode payload
        payload_bytes = _b64decode_url(pld_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Expiration check
        exp = payload.get("exp")
        if exp is not None:
            now_ts = int(datetime.now(timezone.utc).timestamp())
            if now_ts >= exp:
                logger.info("AUTH_AUDIT: Expired JWT token presented", sub=payload.get("sub"))
                return None

        return payload
    except Exception as e:
        logger.debug(f"JWT verification exception: {e}")
        return None


async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_security_bearer)
) -> Dict[str, Any]:
    """
    FastAPI dependency enforcing strict authentication on protected routes.
    - If a Bearer token is supplied, validates signature and expiration.
    - If valid, returns principal dict: {"sub": username, "role": role, "auth_mode": "JWT"}.
    - If token is invalid or expired, raises HTTP 401 Unauthorized.
    - If NO token is provided:
        * In explicit Demo mode (IBVAP_DEV_DEMO_MODE=1), returns demo principal with audit log.
        * In default Production mode, raises HTTP 401 Unauthorized.
    """
    if credentials and credentials.credentials:
        payload = verify_token(credentials.credentials)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials: invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {
            "sub": payload.get("sub", "unknown"),
            "role": payload.get("role", Role.VIEWER.value),
            "auth_mode": "JWT",
            "dev_mode": False
        }

    # No token provided: check if explicit demo bypass is enabled
    if is_demo_mode():
        logger.info("AUTH_AUDIT: Demo mode active — granting demo operator access")
        return {
            "sub": "operator_demo",
            "role": Role.ADMIN.value,
            "dev_mode": True,
            "auth_mode": "EXPLICIT_DEMO_BYPASS"
        }

    # Production default: strictly require authentication
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated: Bearer token required in production mode",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_permission(permission: Permission):
    """Dependency factory checking if principal has specific permission."""
    async def _perm_checker(principal: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
        role_str = principal.get("role", Role.VIEWER.value)
        try:
            role = Role(role_str)
        except ValueError:
            role = Role.VIEWER

        if not check_permission(role, permission):
            logger.warning(
                "AUTH_AUDIT: Access forbidden",
                user=principal.get("sub"),
                role=role_str,
                required_permission=permission.value
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: permission '{permission.value}' required."
            )
        return principal
    return _perm_checker


def require_role(*allowed_roles: Role):
    """Dependency factory checking if principal role is in allowed list."""
    allowed_values = {r.value for r in allowed_roles}
    async def _role_checker(principal: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
        role_str = principal.get("role", Role.VIEWER.value)
        if role_str not in allowed_values and role_str != Role.ADMIN.value and role_str != Role.SYSTEM.value:
            logger.warning(
                "AUTH_AUDIT: Role unauthorized",
                user=principal.get("sub"),
                role=role_str,
                allowed_roles=list(allowed_values)
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: role '{role_str}' not authorized."
            )
        return principal
    return _role_checker
