from __future__ import annotations

from uuid import UUID

import uvicorn
from fastapi import Depends, FastAPI, HTTPException

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


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/signup", response_model=SessionResponse)
def signup(request: SignupRequest) -> SessionResponse:
    data = store.signup(email=request.email, password=request.password, handle=request.handle)
    user = data["user"]
    session = data.get("session") or {}
    return SessionResponse(
        user_id=user["id"],
        access_token=session.get("access_token"),
        refresh_token=session.get("refresh_token"),
        email=user.get("email"),
    )


@app.post("/auth/login", response_model=SessionResponse)
def login(request: LoginRequest) -> SessionResponse:
    data = store.login(email=request.email, password=request.password)
    user = data["user"]
    return SessionResponse(
        user_id=user["id"],
        access_token=data.get("access_token"),
        refresh_token=data.get("refresh_token"),
        email=user.get("email"),
    )
@app.post("/campaigns", response_model=CampaignSummary)
def create_campaign(
    request: CampaignCreateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> CampaignSummary:
    try:
        return engine.create_campaign(user_id=user.user_id, request=request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/campaigns/{campaign_id}", response_model=CampaignSummary)
def get_campaign_summary(
    campaign_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
) -> CampaignSummary:
    try:
        return engine.get_campaign_summary(campaign_id=campaign_id, user_id=user.user_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/campaigns/{campaign_id}/current-scene", response_model=SceneResponse)
def current_scene(
    campaign_id: UUID,
    user: AuthenticatedUser = Depends(get_current_user),
) -> SceneResponse:
    try:
        return engine.get_current_scene(campaign_id=campaign_id, user_id=user.user_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/campaigns/{campaign_id}/choose", response_model=ChoiceResult)
def choose(
    campaign_id: UUID,
    request: ChooseRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> ChoiceResult:
    try:
        return engine.choose(campaign_id=campaign_id, user_id=user.user_id, choice_key=request.choice_key)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def run() -> None:
    uvicorn.run("a_new_dawn.api:app", host=settings.api_host, port=settings.api_port, reload=False)
