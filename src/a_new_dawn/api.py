from __future__ import annotations

import time
from collections import defaultdict
from uuid import UUID

import httpx
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request

from a_new_dawn.auth import AuthenticatedUser, get_current_user
from a_new_dawn.engine import GameEngine
from a_new_dawn.schemas import (
    CampaignCreateRequest,
    CampaignSummary,
    ChoiceResult,
    ChooseRequest,
    LoginRequest,
    SceneResponse,
    SessionResponse,
    SignupRequest,
)
from a_new_dawn.settings import get_settings
from a_new_dawn.supabase_store import SupabaseStore


settings = get_settings()
app = FastAPI(title="STAR WARS: A NEW DAWN API")
store = SupabaseStore()
engine = GameEngine(store=store)

# Simple in-memory rate limiter: max 10 requests per IP per 60 seconds
_rate_buckets: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 10
_RATE_WINDOW = 60.0


def _check_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    bucket = _rate_buckets[ip]
    _rate_buckets[ip] = [t for t in bucket if now - t < _RATE_WINDOW]
    if len(_rate_buckets[ip]) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many requests. Slow down.")
    _rate_buckets[ip].append(now)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/signup", response_model=SessionResponse)
def signup(request: SignupRequest, http_request: Request) -> SessionResponse:
    _check_rate_limit(http_request)
    try:
        data = store.signup(email=request.email, password=request.password, handle=request.handle)
        user = data["user"]
        session = data.get("session") or {}
        return SessionResponse(
            user_id=user["id"],
            access_token=session.get("access_token"),
            refresh_token=session.get("refresh_token"),
            email=user.get("email"),
        )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text or str(exc)
        raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/auth/login", response_model=SessionResponse)
def login(request: LoginRequest, http_request: Request) -> SessionResponse:
    _check_rate_limit(http_request)
    try:
        data = store.login(email=request.email, password=request.password)
        user = data["user"]
        return SessionResponse(
            user_id=user["id"],
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            email=user.get("email"),
        )
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text or str(exc)
        raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
def _game_error(exc: Exception, status: int = 400) -> HTTPException:
    msg = str(exc)
    # Safe user-facing messages only — never expose internals
    if "not found" in msg.lower() or "no campaign" in msg.lower():
        return HTTPException(status_code=404, detail="Campaign not found.")
    if "not valid" in msg.lower() or "invalid" in msg.lower() or "missing" in msg.lower():
        return HTTPException(status_code=400, detail="Invalid request.")
    if "permission" in msg.lower() or "access" in msg.lower():
        return HTTPException(status_code=403, detail="Access denied.")
    return HTTPException(status_code=status, detail="Something went wrong. Please try again.")


@app.post("/campaigns", response_model=CampaignSummary)
def create_campaign(
    request: CampaignCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> CampaignSummary:
    try:
        return engine.create_campaign(user_id=user.user_id, request=request)
    except Exception as exc:
        raise _game_error(exc) from exc


@app.get("/campaigns/{campaign_id}", response_model=CampaignSummary)
def get_campaign_summary(
    campaign_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
) -> CampaignSummary:
    try:
        return engine.get_campaign_summary(campaign_id=campaign_id, user_id=user.user_id)
    except Exception as exc:
        raise _game_error(exc, 404) from exc


@app.get("/campaigns/{campaign_id}/current-scene", response_model=SceneResponse)
def current_scene(
    campaign_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
) -> SceneResponse:
    try:
        return engine.get_current_scene(campaign_id=campaign_id, user_id=user.user_id)
    except Exception as exc:
        raise _game_error(exc) from exc


@app.post("/campaigns/{campaign_id}/choose", response_model=ChoiceResult)
def choose(
    campaign_id: UUID,
    request: ChooseRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> ChoiceResult:
    try:
        return engine.choose(campaign_id=campaign_id, user_id=user.user_id, choice_key=request.choice_key)
    except Exception as exc:
        raise _game_error(exc) from exc


def run() -> None:
    uvicorn.run("a_new_dawn.api:app", host=settings.api_host, port=settings.api_port, reload=False)
