from __future__ import annotations

from uuid import UUID

import httpx
import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from a_new_dawn.auth import AuthenticatedUser, get_current_user
from a_new_dawn.db import get_db
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


settings = get_settings()
app = FastAPI(title="STAR WARS: A NEW DAWN API")
engine = GameEngine()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/signup", response_model=SessionResponse)
def signup(request: SignupRequest) -> SessionResponse:
    payload = {
        "email": request.email,
        "password": request.password,
        "data": {"handle": request.handle},
    }
    headers = {
        "apikey": settings.resolved_publishable_key,
        "Authorization": f"Bearer {settings.resolved_publishable_key}",
    }
    response = httpx.post(f"{settings.supabase_url}/auth/v1/signup", json=payload, headers=headers, timeout=30.0)
    response.raise_for_status()
    data = response.json()
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
    headers = {
        "apikey": settings.resolved_publishable_key,
        "Authorization": f"Bearer {settings.resolved_publishable_key}",
    }
    payload = {"email": request.email, "password": request.password}
    response = httpx.post(
        f"{settings.supabase_url}/auth/v1/token?grant_type=password",
        json=payload,
        headers=headers,
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
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
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> CampaignSummary:
    try:
        return engine.create_campaign(db, user_id=user.user_id, request=request)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/campaigns/{campaign_id}", response_model=CampaignSummary)
def get_campaign_summary(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> CampaignSummary:
    from a_new_dawn.repository import get_campaign

    campaign = get_campaign(db, campaign_id, user.user_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return CampaignSummary(
        campaign_id=campaign.id,
        title=campaign.title,
        player_class=campaign.player_class.value,
        current_episode=campaign.current_episode,
        current_scene_key=campaign.current_scene_key,
        story_arc=campaign.story_arc,
    )


@app.get("/campaigns/{campaign_id}/current-scene", response_model=SceneResponse)
def current_scene(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> SceneResponse:
    try:
        return engine.get_current_scene(db, campaign_id=campaign_id, user_id=user.user_id)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/campaigns/{campaign_id}/choose", response_model=ChoiceResult)
def choose(
    campaign_id: UUID,
    request: ChooseRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> ChoiceResult:
    try:
        return engine.choose(db, campaign_id=campaign_id, user_id=user.user_id, choice_key=request.choice_key)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def run() -> None:
    uvicorn.run("a_new_dawn.api:app", host=settings.api_host, port=settings.api_port, reload=False)
