from __future__ import annotations

import time
from dataclasses import dataclass
from uuid import UUID

import httpx
import jwt
from fastapi import Header, HTTPException
from jwt import InvalidTokenError

from a_new_dawn.settings import get_settings


settings = get_settings()


@dataclass
class AuthenticatedUser:
    user_id: UUID
    email: str | None
    claims: dict


class SupabaseJWTVerifier:
    def __init__(self) -> None:
        self._jwks: dict | None = None
        self._jwks_expiry = 0.0

    def verify(self, token: str) -> AuthenticatedUser:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise HTTPException(status_code=401, detail="JWT missing key id.")

        jwk = self._get_jwk(kid)
        if jwk is None:
            self._refresh_jwks(force=True)
            jwk = self._get_jwk(kid)
        if jwk is None:
            raise HTTPException(status_code=401, detail="Unable to resolve JWT signing key.")

        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
        try:
            claims = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=settings.supabase_jwt_audience,
                issuer=settings.resolved_supabase_jwt_issuer,
            )
        except InvalidTokenError as exc:
            raise HTTPException(status_code=401, detail=f"Invalid JWT: {exc}") from exc

        subject = claims.get("sub")
        if not subject:
            raise HTTPException(status_code=401, detail="JWT missing subject.")

        try:
            user_id = UUID(subject)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="JWT subject is not a valid user id.") from exc

        return AuthenticatedUser(user_id=user_id, email=claims.get("email"), claims=claims)

    def _get_jwk(self, kid: str) -> str | None:
        if self._jwks is None or time.time() > self._jwks_expiry:
            self._refresh_jwks()

        keys = self._jwks.get("keys", []) if self._jwks else []
        for key in keys:
            if key.get("kid") == kid:
                return key
        return None

    def _refresh_jwks(self, *, force: bool = False) -> None:
        if not force and self._jwks is not None and time.time() <= self._jwks_expiry:
            return
        response = httpx.get(settings.resolved_supabase_jwks_url, timeout=15.0)
        response.raise_for_status()
        self._jwks = response.json()
        self._jwks_expiry = time.time() + 300


verifier = SupabaseJWTVerifier()


def get_current_user(authorization: str = Header(...)) -> AuthenticatedUser:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must be a Bearer token.")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    return verifier.verify(token)
