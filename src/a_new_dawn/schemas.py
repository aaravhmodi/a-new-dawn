from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from a_new_dawn.models import PlayerClass


class SignupRequest(BaseModel):
    email: str
    password: str
    handle: str


class LoginRequest(BaseModel):
    email: str
    password: str


class SessionResponse(BaseModel):
    user_id: UUID
    access_token: str | None = None
    refresh_token: str | None = None
    email: str | None = None


class CampaignCreateRequest(BaseModel):
    player_class: PlayerClass
    era: str = "galactic_civil_war"
    planet: str = "corellia"


class ChoiceOption(BaseModel):
    choice_key: str
    label: str
    description: str | None = None


class SceneResponse(BaseModel):
    campaign_id: UUID
    episode_number: int
    scene_key: str
    title: str
    narration: str
    choices: list[ChoiceOption]
    stats: dict[str, Any]


class CampaignSummary(BaseModel):
    campaign_id: UUID
    title: str
    player_class: str
    current_episode: int
    current_scene_key: str | None
    story_arc: dict[str, Any]


class ChooseRequest(BaseModel):
    choice_key: str = Field(..., description="The selected choice key from the current scene")


class ChoiceResult(BaseModel):
    resolution_text: str
    next_scene: SceneResponse | None
