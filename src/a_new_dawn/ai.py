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
        return self.basic_campaign_arc(player_class=player_class, era=era, planet=planet, seed=seed)

    def basic_campaign_arc(self, *, player_class: str, era: str, planet: str, seed: int) -> dict[str, Any]:
        fallback = CampaignArcModel.model_validate({
            "title": "STAR WARS: A NEW DAWN",
            "opening_crawl": DEFAULT_CRAWL,
            "main_villain_key": "directorate_null",
            "main_villain_name": "Directorate Null",
            "central_objective_key": "black_codex",
            "central_objective_name": "Black Codex",
            "faction_anchor_key": "imperial_intelligence_remnant",
            "protagonist_name": "Rylos Cesti",
            "recurring_allies": [
                {"key": "watcher_nine", "name": "Watcher Nine"},
                {"key": "veska_tal", "name": "Veska Tal"},
            ],
            "recurring_rivals": [
                {"key": "warden_karn", "name": "Warden Karn"},
            ],
        })
        return fallback.model_dump()

    def generate_episode_plan(self, *, campaign_arc: dict[str, Any], episode_number: int, player_class: str) -> dict[str, Any]:
        return self.basic_episode_plan(campaign_arc=campaign_arc, episode_number=episode_number, player_class=player_class)

    def basic_episode_plan(self, *, campaign_arc: dict[str, Any], episode_number: int, player_class: str) -> dict[str, Any]:
        return EpisodePlanModel.model_validate(self._fallback_episode_plan(campaign_arc, episode_number, player_class)).model_dump()

    def generate_scene_narration_enabled(self) -> bool:
        return True

    def ai_generate_campaign_arc(self, *, player_class: str, era: str, planet: str, seed: int) -> dict[str, Any]:
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
        fallback = CampaignArcModel.model_validate(self.basic_campaign_arc(player_class=player_class, era=era, planet=planet, seed=seed))
        return self._validated_json_response(prompt, CampaignArcModel, fallback).model_dump()

    def ai_generate_episode_plan(self, *, campaign_arc: dict[str, Any], episode_number: int, player_class: str) -> dict[str, Any]:
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
        fallback = EpisodePlanModel.model_validate(self.basic_episode_plan(campaign_arc=campaign_arc, episode_number=episode_number, player_class=player_class))
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
        try:
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
        except Exception:
            return ""

    def _gemini_text_response(self, prompt: str) -> str:
        if not self.gemini_api_key:
            return ""
        try:
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
        except Exception:
            return ""

    def _fallback_episode_plan(self, campaign_arc: dict[str, Any], episode_number: int, player_class: str) -> dict[str, Any]:
        prefix = f"ep{episode_number}"
        ally = campaign_arc["recurring_allies"][0]["name"]
        second_ally = campaign_arc["recurring_allies"][1]["name"] if len(campaign_arc["recurring_allies"]) > 1 else ally
        rival = campaign_arc["recurring_rivals"][0]["name"]
        return {
            "episode_number": episode_number,
            "title": f"Episode {episode_number}: Masks on Dromund",
            "theme": "covert infiltration and political sabotage",
            "summary": f"Rylos Cesti enters the field under false credentials, earning trust in a hostile network while receiving guidance from {ally} and drawing the suspicion of {rival}.",
            "scenes": [
                {
                    "scene_key": f"{prefix}_relay_arrival",
                    "title": "The Cover Identity",
                    "prompt": "Rylos Cesti's shuttle settles into a rain-soaked dockyard on Dromund Kaas. A false identity chip burns warm in his palm while a secure voice in his earpiece reminds him that tonight he is not himself.",
                    "choices": [
                        {
                            "choice_key": "adopt_cover",
                            "label": "Adopt the false identity",
                            "description": "Enter the district as a known broker with forged credentials.",
                            "outcome": "The forged identity clears the first checkpoint and buys you entry into the city's underworld.",
                            "next_scene_key": f"{prefix}_cantina_contact",
                            "effects": {"independent_delta": 1, "set_flags": ["cover_identity_established"]},
                        },
                        {
                            "choice_key": "bribe_checkpoint",
                            "label": "Bribe the checkpoint officer",
                            "description": "Pay for a smoother entry and a name on the local roster.",
                            "outcome": "The officer looks away and quietly adds your alias to the district access list.",
                            "next_scene_key": f"{prefix}_cantina_contact",
                            "effects": {"credits_delta": -20, "set_flags": ["bribed_checkpoint"]},
                        },
                        {
                            "choice_key": "follow_handler",
                            "label": f"Follow {ally}'s instructions exactly",
                            "description": "Trust your handler's route and avoid improvisation.",
                            "outcome": f"{ally} guides you through a maintenance corridor used by intelligence couriers.",
                            "next_scene_key": f"{prefix}_cantina_contact",
                            "effects": {"relationship_deltas": {"watcher_nine": 4}, "light_delta": 1},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_cantina_contact",
                    "title": "The Broken Cantina",
                    "prompt": f"In a cantina beneath the capital's industrial spires, Rylos Cesti's first contact waits at a cracked sabacc table. Somewhere in the crowd, {second_ally} is watching for signs that his cover is already blown.",
                    "choices": [
                        {
                            "choice_key": "trade_codes",
                            "label": "Trade for encryption codes",
                            "description": "Exchange credits and favors for network access.",
                            "outcome": "A code cylinder changes hands, along with a whisper about a hidden directorate shaping recent attacks.",
                            "next_scene_key": f"{prefix}_archive_entry",
                            "effects": {"credits_delta": -15, "add_items": [{"item_key": "imperial_code_cylinder", "item_name": "Imperial Code Cylinder"}]},
                        },
                        {
                            "choice_key": "bait_informant",
                            "label": "Bait the local informant",
                            "description": "Force the contact to reveal who else is listening.",
                            "outcome": "The informant cracks and names a surveillance team tied to a secret anti-Force network.",
                            "next_scene_key": f"{prefix}_archive_entry",
                            "effects": {"dark_delta": 1, "set_flags": ["informant_broken"]},
                        },
                        {
                            "choice_key": "meet_observer",
                            "label": f"Signal {second_ally}",
                            "description": "Use a dead-drop phrase to reveal your watcher in the room.",
                            "outcome": f"{second_ally} slides into the booth and confirms a theft in the intelligence archives.",
                            "next_scene_key": f"{prefix}_archive_entry",
                            "effects": {"relationship_deltas": {"veska_tal": 4}, "set_flags": ["watcher_contacted"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_archive_lockdown",
                    "title": "Archive Lockdown",
                    "prompt": f"The intelligence annex sits beneath layered security fields. Inside is a fragment of the {campaign_arc['central_objective_name']}, and outside, {rival} has begun to suspect a mole. Rylos feels a strange pressure behind his eyes as he approaches the vault. A rumor on the security channel says a hired bounty hunter, Boba Fett, may already be in the building.",
                    "set_piece": {
                        "next_scene_key": f"{prefix}_intercept",
                        "beats": [
                            {
                                "title": "Beat 1: Entry",
                                "prompt": "Security fields hum over the archive threshold. Rylos has seconds to get inside before the next patrol sweep crosses the corridor.",
                                "choices": [
                                    {
                                        "choice_key": "cut_power",
                                        "label": "Cut power to a side corridor",
                                        "description": "Create confusion and slip through during the flicker.",
                                        "outcome": "The lights die for a breath and the annex hesitates just long enough for Rylos to cross the threshold.",
                                        "effects": {"heat_delta": 1, "intel_delta": 1},
                                    },
                                    {
                                        "choice_key": "use_code_cylinder",
                                        "label": "Use the code cylinder",
                                        "description": "Open the first lock under an authorized identity.",
                                        "outcome": "The cylinder authenticates the fake credentials and the first gate unlocks without alarm.",
                                        "effects": {"cover_delta": 1, "intel_delta": 1},
                                    },
                                    {
                                        "choice_key": "maintenance_shaft",
                                        "label": "Follow a maintenance shaft",
                                        "description": "Bypass the formal entry entirely.",
                                        "outcome": "Rylos squeezes through the service channel, but the route leaves traces a trained investigator might notice.",
                                        "effects": {"cover_delta": -1},
                                    },
                                ],
                            },
                            {
                                "title": "Beat 2: Extraction",
                                "prompt": "Rows of sealed data cylinders glow inside the vault. Patrol routes converge on the annex while Rylos races to pull the right files before the lockdown seals everything.",
                                "choices": [
                                    {
                                        "choice_key": "copy_everything",
                                        "label": "Copy everything quickly",
                                        "description": "Take as much as possible and sort it out later.",
                                        "outcome": "Data floods into the cylinder in a messy burst, but the system notices the strain immediately.",
                                        "effects": {"intel_delta": 2, "heat_delta": 2},
                                    },
                                    {
                                        "choice_key": "critical_cluster",
                                        "label": "Take only the critical file cluster",
                                        "description": "Prioritize the cleanest, most important target.",
                                        "outcome": "Rylos extracts the most relevant archive chain before the deeper systems can fully react.",
                                        "effects": {"intel_delta": 1, "heat_delta": 1, "set_flags": ["black_codex_fragment_found"]},
                                    },
                                    {
                                        "choice_key": "plant_false_trace",
                                        "label": "Plant a false trace before downloading",
                                        "description": "Protect the mission by misdirecting the investigation.",
                                        "outcome": "A false access trail begins pointing security toward a different breach team while the files transfer in the background.",
                                        "effects": {"cover_delta": 1, "intel_delta": 1},
                                    },
                                ],
                            },
                            {
                                "title": "Beat 3: Escape",
                                "prompt": f"Red lockdown lights flood the annex. {rival}'s officers are closing fast, and Rylos has one move left before the whole district seals around him. At the far end of the corridor, a helmeted bounty hunter appears through the smoke - Boba Fett, hired to retrieve the same data.",
                                "choices": [
                                    {
                                        "choice_key": "fight_through_exit",
                                        "label": "Fight through the nearest exit",
                                        "description": "Push hard before security can tighten the kill box.",
                                        "outcome": "Rylos smashes through the first response line and forces open a narrow path into the rain while Boba Fett raises his weapon just long enough to make the escape feel impossible.",
                                        "effects": {"heat_delta": 1, "cover_delta": -1},
                                    },
                                    {
                                        "choice_key": "machinery_collapse",
                                        "label": "Trigger a machinery collapse behind you",
                                        "description": "Delay pursuit by bringing part of the annex down.",
                                        "outcome": "A shower of sparks and steel crashes into the corridor, burying the pursuit team under wreckage and panic while the bounty hunter vanishes into the smoke.",
                                        "effects": {"heat_delta": -1, "dark_delta": 1},
                                    },
                                    {
                                        "choice_key": "service_lift",
                                        "label": "Disappear into a service lift",
                                        "description": "Trust stealth over violence for the final escape.",
                                        "outcome": "Rylos slips into a grimy service lift and vanishes between levels while Boba Fett is forced to choose between the chase and the collapsing corridor.",
                                        "effects": {"cover_delta": 1},
                                    },
                                ],
                            },
                        ],
                    },
                    "choices": [],
                },
                {
                    "scene_key": f"{prefix}_intercept",
                    "title": "The Silent Broadcast",
                    "prompt": "A pirate signal cuts through every secure channel in the district. A masked voice claims the age of Jedi and Sith is ending, and Rylos's stolen files prove this is only the opening move. Then the room shudders, metal groans, and something impossible answers his fear. In a secure Imperial relay, Darth Vader listens in silence as the report reaches him.",
                    "choices": [
                        {
                            "choice_key": "report_keeper",
                            "label": f"Transmit everything to {ally}",
                            "description": "Hand the evidence to your handler and request extraction.",
                            "outcome": "The files go out over a secure burst just as loose equipment lifts and slams aside without Rylos touching it. Somewhere far away, Vader now knows a hidden asset is awakening, and command orders Rylos deeper into the hunt.",
                            "next_scene_key": "END",
                            "effects": {"relationship_deltas": {"watcher_nine": 3}, "light_delta": 1, "set_flags": [f"episode_{episode_number}_cleared", "swore_to_the_mission", "force_sensitive_awakened"]},
                        },
                        {
                            "choice_key": "keep_blackmail_copy",
                            "label": "Keep a private copy of the files",
                            "description": "Hold leverage back from your own command structure.",
                            "outcome": "Rylos sends a partial report and hides the rest, then instinctively reaches for a falling data core and stops it in midair. Vader's interest in the disturbance makes the galaxy feel smaller and far more dangerous.",
                            "next_scene_key": "END",
                            "effects": {"independent_delta": 3, "dark_delta": 1, "set_flags": [f"episode_{episode_number}_cleared", "kept_blackmail_copy", "force_sensitive_awakened"]},
                        },
                        {
                            "choice_key": "burn_the_files",
                            "label": "Burn the files and vanish",
                            "description": "Deny every faction the weaponized knowledge you just found.",
                            "outcome": "The data turns to ash, but when blaster fire tears through the archive, Rylos throws out a hand and the bolt deflects off a bent durasteel panel. Darth Vader receives only a partial signal, but it is enough to know the hunt has begun.",
                            "next_scene_key": "END",
                            "effects": {"light_delta": 2, "set_flags": [f"episode_{episode_number}_cleared", "burned_first_fragment", "force_sensitive_awakened"]},
                        },
                    ],
                },
            ],
        }
