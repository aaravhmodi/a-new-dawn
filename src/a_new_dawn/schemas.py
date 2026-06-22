from __future__ import annotations

from typing import Any
from uuid import UUID

from enum import Enum

from pydantic import BaseModel, Field


class PlayerClass(str, Enum):
    smuggler = "smuggler"
    jedi = "jedi"
    bounty_hunter = "bounty_hunter"


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
    scene_state: dict[str, Any] | None = None


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
    ending_key: str | None = None
    ending_title: str | None = None
    ending_summary: str | None = None
