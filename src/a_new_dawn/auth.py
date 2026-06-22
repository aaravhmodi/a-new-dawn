from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import httpx
from fastapi import Header, HTTPException

from a_new_dawn.settings import get_settings


settings = get_settings()


@dataclass
class AuthenticatedUser:
    user_id: UUID
    email: str | None
    claims: dict


def verify_supabase_token(token: str) -> AuthenticatedUser:
    headers = {
        "apikey": settings.resolved_publishable_key,
        "Authorization": f"Bearer {token}",
    }
    response = httpx.get(f"{settings.supabase_url}/auth/v1/user", headers=headers, timeout=30.0)
    if response.status_code >= 400:
        detail = response.text or "Supabase token verification failed."
        raise HTTPException(status_code=401, detail=detail)

    data = response.json()
    user_id = data.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Supabase user payload missing id.")

    try:
        parsed_user_id = UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Supabase returned an invalid user id.") from exc

    return AuthenticatedUser(
        user_id=parsed_user_id,
        email=data.get("email"),
        claims=data,
    )


def get_current_user(authorization: str = Header(...)) -> AuthenticatedUser:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must be a Bearer token.")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    return verify_supabase_token(token)
