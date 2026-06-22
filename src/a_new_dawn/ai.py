from __future__ import annotations

import json
import random
from typing import Any

import httpx
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

from a_new_dawn.content import DEFAULT_CRAWL
from a_new_dawn.settings import get_settings


class RecurringCharacter(BaseModel):
    key: str
    name: str


class CampaignArcModel(BaseModel):
    title: str
    opening_crawl: str
    main_villain_key: str
    main_villain_name: str
    central_objective_key: str
    central_objective_name: str
    faction_anchor_key: str
    recurring_allies: list[RecurringCharacter]
    recurring_rivals: list[RecurringCharacter]


class ChoiceEffectsModel(BaseModel):
    credits_delta: int = 0
    health_delta: int = 0
    light_delta: int = 0
    dark_delta: int = 0
    independent_delta: int = 0
    set_flags: list[str] = Field(default_factory=list)
    add_items: list[dict[str, str]] = Field(default_factory=list)
    relationship_deltas: dict[str, int] = Field(default_factory=dict)
    faction_deltas: dict[str, int] = Field(default_factory=dict)


class EpisodeChoiceModel(BaseModel):
    choice_key: str
    label: str
    description: str
    outcome: str
    next_scene_key: str
    effects: ChoiceEffectsModel


class EpisodeSceneModel(BaseModel):
    scene_key: str
    title: str
    prompt: str
    choices: list[EpisodeChoiceModel]


class EpisodePlanModel(BaseModel):
    episode_number: int
    title: str
    theme: str
    summary: str
    scenes: list[EpisodeSceneModel]


class SceneNarrationModel(BaseModel):
    title: str
    narration: str


class AIService:
    def __init__(self) -> None:
        settings = get_settings()
        self.provider = settings.llm_provider.lower()
        self.model = settings.llm_model
        api_key = settings.llm_api_key
        base_url = settings.llm_base_url
        self.client = None if self.provider in {"ollama", "gemini"} else (OpenAI(api_key=api_key, base_url=base_url) if api_key else None)
        self.ollama_base_url = settings.ollama_base_url
        self.gemini_base_url = settings.gemini_base_url
        self.gemini_api_key = settings.gemini_api_key

    def generate_campaign_arc(self, *, player_class: str, era: str, planet: str, seed: int) -> dict[str, Any]:
        prompt = f"""
You are designing a 9-episode Star Wars campaign for a choice-driven RPG.
Return strict JSON with keys:
title, opening_crawl, main_villain_key, main_villain_name, central_objective_key,
central_objective_name, faction_anchor_key, recurring_allies, recurring_rivals.

Constraints:
- player_class: {player_class}
- era: {era}
- starting_planet: {planet}
- seed: {seed}
- Keep it cinematic and concise.
"""
        fallback = CampaignArcModel.model_validate({
            "title": "STAR WARS: A NEW DAWN",
            "opening_crawl": DEFAULT_CRAWL,
            "main_villain_key": "imperial_inquisitor_vael",
            "main_villain_name": "Imperial Inquisitor Vael",
            "central_objective_key": "lost_holocron",
            "central_objective_name": "Lost Holocron",
            "faction_anchor_key": "outer_rim_rebels",
            "recurring_allies": [{"key": "kira_veen", "name": "Kira Veen"}],
            "recurring_rivals": [{"key": "captain_drex", "name": "Captain Drex"}],
        })
        return self._validated_json_response(prompt, CampaignArcModel, fallback).model_dump()

    def generate_episode_plan(self, *, campaign_arc: dict[str, Any], episode_number: int, player_class: str) -> dict[str, Any]:
        prompt = f"""
Generate strict JSON for one episode plan of a choice-driven Star Wars RPG.
Return keys:
episode_number, title, theme, summary, scenes.

Each scene must have:
scene_key, title, prompt, choices.

Each choice must have:
choice_key, label, description, outcome, next_scene_key, effects.

Effects can include:
credits_delta, health_delta, light_delta, dark_delta, independent_delta,
set_flags (array), add_items (array of objects with item_key and item_name),
relationship_deltas (object), faction_deltas (object).

Rules:
- 4 scenes per episode.
- 3 choices per scene.
- The final scene should set next_scene_key to END.
- Episode number: {episode_number}
- Player class: {player_class}
- Campaign arc: {json.dumps(campaign_arc)}
"""
        fallback = EpisodePlanModel.model_validate(self._fallback_episode_plan(campaign_arc, episode_number, player_class))
        return self._validated_json_response(prompt, EpisodePlanModel, fallback).model_dump()

    def narrate_scene(self, *, opening_crawl: str, campaign_arc: dict[str, Any], scene: dict[str, Any], stats: dict[str, Any]) -> dict[str, str]:
        prompt = f"""
Write compact cinematic text for a Star Wars CLI RPG scene.
Return strict JSON with keys:
title, narration.

Campaign arc:
{json.dumps(campaign_arc)}

Opening crawl:
{opening_crawl}

Scene:
{json.dumps(scene)}

Player stats:
{json.dumps(stats)}
"""
        fallback = SceneNarrationModel(title=scene["title"], narration=scene["prompt"])
        return self._validated_json_response(prompt, SceneNarrationModel, fallback).model_dump()

    def narrate_resolution(self, *, scene_title: str, choice_label: str, outcome: str) -> str:
        if self.provider == "ollama":
            prompt = f"""
Write one short cinematic paragraph for a Star Wars game resolution.
Scene: {scene_title}
Choice: {choice_label}
Outcome: {outcome}
"""
            return self._ollama_text_response(prompt) or outcome
        if self.provider == "gemini":
            prompt = f"""
Write one short cinematic paragraph for a Star Wars game resolution.
Scene: {scene_title}
Choice: {choice_label}
Outcome: {outcome}
"""
            return self._gemini_text_response(prompt) or outcome

        if not self.client:
            return outcome

        prompt = f"""
Write one short cinematic paragraph for a Star Wars game resolution.
Scene: {scene_title}
Choice: {choice_label}
Outcome: {outcome}
"""
        response = self.client.responses.create(model=self.model, input=prompt)
        return response.output_text.strip() or outcome

    def _validated_json_response(self, prompt: str, model_type: type[BaseModel], fallback: BaseModel) -> BaseModel:
        if self.provider == "ollama":
            last_error: Exception | None = None
            for _ in range(3):
                text = self._ollama_text_response(
                    prompt + f"\nReturn valid JSON only. Use this schema shape: {json.dumps(model_type.model_json_schema())}"
                )
                if not text:
                    continue
                try:
                    return model_type.model_validate(json.loads(text))
                except (json.JSONDecodeError, ValidationError) as exc:
                    last_error = exc
                    continue
            return fallback

        if self.provider == "gemini":
            last_error: Exception | None = None
            for _ in range(3):
                text = self._gemini_text_response(
                    prompt + f"\nReturn valid JSON only. Use this schema shape: {json.dumps(model_type.model_json_schema())}"
                )
                if not text:
                    continue
                try:
                    return model_type.model_validate(json.loads(text))
                except (json.JSONDecodeError, ValidationError) as exc:
                    last_error = exc
                    continue
            return fallback

        if not self.client:
            return fallback

        last_error: Exception | None = None
        for _ in range(3):
            response = self.client.responses.create(
                model=self.model,
                input=prompt + f"\nReturn valid JSON only. Use this schema shape: {json.dumps(model_type.model_json_schema())}",
            )
            text = response.output_text.strip()
            try:
                return model_type.model_validate(json.loads(text))
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                continue

        if last_error:
            return fallback
        return fallback

    def _ollama_text_response(self, prompt: str) -> str:
        response = httpx.post(
            f"{self.ollama_base_url}/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        return (data.get("response") or "").strip()

    def _gemini_text_response(self, prompt: str) -> str:
        if not self.gemini_api_key:
            return ""
        response = httpx.post(
            f"{self.gemini_base_url}/models/{self.model}:generateContent",
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": self.gemini_api_key,
            },
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt,
                            }
                        ]
                    }
                ]
            },
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        text_parts = [part.get("text", "") for part in parts if part.get("text")]
        return "\n".join(text_parts).strip()

    def _fallback_episode_plan(self, campaign_arc: dict[str, Any], episode_number: int, player_class: str) -> dict[str, Any]:
        prefix = f"ep{episode_number}"
        ally = campaign_arc["recurring_allies"][0]["name"]
        rival = campaign_arc["recurring_rivals"][0]["name"]
        return {
            "episode_number": episode_number,
            "title": f"Episode {episode_number}: Embers Over Corellia",
            "theme": "survival and rising resistance",
            "summary": f"The player is pulled deeper into conflict while crossing paths with {ally} and {rival}.",
            "scenes": [
                {
                    "scene_key": f"{prefix}_dockside",
                    "title": "Dockside Shadows",
                    "prompt": "Rain hisses over the Corellian docks as Imperial patrols sweep the loading lanes.",
                    "choices": [
                        {
                            "choice_key": "scan_crates",
                            "label": "Scan the cargo crates",
                            "description": "Look for contraband or a hidden route.",
                            "outcome": "A hidden rebel transponder flickers beneath a crate seal.",
                            "next_scene_key": f"{prefix}_cantina",
                            "effects": {"credits_delta": 25, "set_flags": ["found_rebel_transponder"]},
                        },
                        {
                            "choice_key": "follow_patrol",
                            "label": "Shadow the Imperial patrol",
                            "description": "Tail the stormtroopers through the dockyard.",
                            "outcome": "You learn the patrol route but attract unwanted attention.",
                            "next_scene_key": f"{prefix}_cantina",
                            "effects": {"health_delta": -5, "independent_delta": 1},
                        },
                        {
                            "choice_key": "call_ally",
                            "label": f"Contact {ally}",
                            "description": "Ask your ally for a quiet extraction path.",
                            "outcome": f"{ally} sends coordinates to a cantina safehouse.",
                            "next_scene_key": f"{prefix}_cantina",
                            "effects": {"relationship_deltas": {"kira_veen": 5}},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_cantina",
                    "title": "The Split Sabacc",
                    "prompt": f"The cantina hums with low voices as rumors spread about {campaign_arc['central_objective_name']}.",
                    "choices": [
                        {
                            "choice_key": "buy_info",
                            "label": "Buy information from a broker",
                            "description": "Spend credits for a lead.",
                            "outcome": "The broker whispers that the holocron passed through an Imperial relay.",
                            "next_scene_key": f"{prefix}_relay",
                            "effects": {"credits_delta": -20, "light_delta": 1},
                        },
                        {
                            "choice_key": "bluff_guard",
                            "label": "Bluff an off-duty officer",
                            "description": "Use charm and timing to pry loose details.",
                            "outcome": "The officer reveals a relay checkpoint schedule.",
                            "next_scene_key": f"{prefix}_relay",
                            "effects": {"independent_delta": 2},
                        },
                        {
                            "choice_key": "start_brawl",
                            "label": "Start a distraction",
                            "description": "Trigger chaos and search in the confusion.",
                            "outcome": "The cantina erupts and you slip away with a stolen data chit.",
                            "next_scene_key": f"{prefix}_relay",
                            "effects": {"dark_delta": 2, "add_items": [{"item_key": "stolen_data_chit", "item_name": "Stolen Data Chit"}]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_relay",
                    "title": "Relay Station Veil",
                    "prompt": f"At the edge of the city, a relay tower pulses against the night while {rival}'s enforcers close in.",
                    "choices": [
                        {
                            "choice_key": "slice_terminal",
                            "label": "Slice the relay terminal",
                            "description": "Pull the shipment records directly.",
                            "outcome": "The terminal reveals a route tied to the holocron transfer.",
                            "next_scene_key": f"{prefix}_escape",
                            "effects": {"set_flags": ["sliced_relay_terminal"], "light_delta": 1},
                        },
                        {
                            "choice_key": "ambush_enforcers",
                            "label": "Ambush the enforcers",
                            "description": "Strike first before they box you in.",
                            "outcome": "The enforcers scatter, leaving behind a coded badge.",
                            "next_scene_key": f"{prefix}_escape",
                            "effects": {"health_delta": -10, "add_items": [{"item_key": "coded_badge", "item_name": "Coded Badge"}]},
                        },
                        {
                            "choice_key": "send_false_signal",
                            "label": "Send a false distress signal",
                            "description": "Pull security away from your real objective.",
                            "outcome": "Security diverts long enough for you to slip into the access lane.",
                            "next_scene_key": f"{prefix}_escape",
                            "effects": {"independent_delta": 2, "faction_deltas": {"outer_rim_rebels": 1}},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_escape",
                    "title": "Engines at Dawn",
                    "prompt": "Sirens cut through the morning haze as your route out of Corellia narrows to a single desperate choice.",
                    "choices": [
                        {
                            "choice_key": "trust_ally",
                            "label": f"Trust {ally}'s route",
                            "description": "Bet on your ally's escape corridor.",
                            "outcome": "You punch through a maintenance lane and glimpse the road ahead.",
                            "next_scene_key": "END",
                            "effects": {"relationship_deltas": {"kira_veen": 3}, "set_flags": [f"episode_{episode_number}_cleared"]},
                        },
                        {
                            "choice_key": "face_rival",
                            "label": f"Confront {rival}",
                            "description": "Turn and force the issue before fleeing.",
                            "outcome": "Your enemy retreats, but only after marking you as a target.",
                            "next_scene_key": "END",
                            "effects": {"dark_delta": 1, "set_flags": ["captain_drex_marked_you", f"episode_{episode_number}_cleared"]},
                        },
                        {
                            "choice_key": "jump_blind",
                            "label": "Take the blind jump",
                            "description": "Escape without knowing where the hyperspace lane ends.",
                            "outcome": "The stars twist and the campaign widens into uncertainty.",
                            "next_scene_key": "END",
                            "effects": {"independent_delta": 3, "set_flags": [f"episode_{episode_number}_cleared"]},
                        },
                    ],
                },
            ],
        }
