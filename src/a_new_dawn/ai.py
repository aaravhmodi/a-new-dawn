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
    set_piece: dict | None = None
    forced_ending_key: str | None = None


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
        static = scene["prompt"]
        if self.provider in ("gemini", "ollama"):
            prompt = f"""You are narrating a scene in a Star Wars RPG with a James Bond espionage tone.
Expand the following scene description into two vivid cinematic paragraphs (max 120 words total).
Keep it tense, atmospheric, and immersive. Do not invent new plot points or characters beyond what is given.

Scene title: {scene["title"]}
Scene description: {static}
Player health: {stats.get("health", 100)}, Credits: {stats.get("credits", 0)}
"""
            try:
                if self.provider == "gemini":
                    narration = self._gemini_text_response(prompt)
                else:
                    narration = self._ollama_text_response(prompt)
                if narration:
                    return {"title": scene["title"], "narration": narration}
            except Exception:
                pass
        return {"title": scene["title"], "narration": static}

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
                timeout=8.0,
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
                timeout=8.0,
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
                            "outcome": "The forged identity clears the first checkpoint. Rylos walks into the cantina district looking like he belongs.",
                            "next_scene_key": f"{prefix}_cantina_confident",
                            "effects": {"independent_delta": 1, "set_flags": ["cover_identity_established"]},
                        },
                        {
                            "choice_key": "bribe_checkpoint",
                            "label": "Bribe the checkpoint officer",
                            "description": "Pay for a smoother entry and a name on the local roster.",
                            "outcome": "The officer looks away and slips Rylos a quiet warning: someone in the cantina is already watching for his alias.",
                            "next_scene_key": f"{prefix}_cantina_bribed",
                            "effects": {"credits_delta": -20, "set_flags": ["bribed_checkpoint"]},
                        },
                        {
                            "choice_key": "follow_handler",
                            "label": f"Follow {ally}'s instructions exactly",
                            "description": "Trust your handler's route and avoid improvisation.",
                            "outcome": f"{ally} guides Rylos through a maintenance corridor used by intelligence couriers, arriving behind the bar.",
                            "next_scene_key": f"{prefix}_cantina_guided",
                            "effects": {"relationship_deltas": {"watcher_nine": 4}, "light_delta": 1},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_cantina_confident",
                    "title": "The Cantina: Polished Entry",
                    "prompt": f"Rylos enters as a polished broker with forged credentials and moves like he owns the room. His contact is already seated, waiting — calm, professional, unalarmed. The cantina regulars barely register his arrival. Everything is exactly where {ally} said it would be.",
                    "choices": [
                        {
                            "choice_key": "trade_codes",
                            "label": "Trade for encryption codes",
                            "description": "Exchange credits and favors for network access.",
                            "outcome": "A code cylinder changes hands under the table. The contact confirms: someone inside the intelligence annex has been leaking data for months.",
                            "next_scene_key": f"{prefix}_karn_merchant",
                            "effects": {"credits_delta": -15, "add_items": [{"item_key": "imperial_code_cylinder", "item_name": "Imperial Code Cylinder"}]},
                        },
                        {
                            "choice_key": "bait_informant",
                            "label": "Bait the local informant",
                            "description": "Force the contact to reveal who else is listening.",
                            "outcome": "The informant cracks under quiet pressure and names a watcher at the bar. The smooth entry made it easier to push — and harder to walk back.",
                            "next_scene_key": f"{prefix}_karn_exposed",
                            "effects": {"dark_delta": 1, "set_flags": ["informant_broken"]},
                        },
                        {
                            "choice_key": "meet_observer",
                            "label": f"Signal {second_ally}",
                            "description": "Use a dead-drop phrase to surface your field contact.",
                            "outcome": f"{second_ally} slides into the booth. She confirms the annex records were accessed twice last week by someone who does not officially exist.",
                            "next_scene_key": f"{prefix}_karn_veska",
                            "effects": {"relationship_deltas": {"veska_tal": 4}, "set_flags": ["watcher_contacted"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_cantina_bribed",
                    "title": "The Cantina: Compromised Entry",
                    "prompt": f"The bribed checkpoint officer's tip was accurate: someone in the cantina is already watching for Rylos's alias. His contact is jumpy, the booth is compromised, and the background noise feels engineered. Rylos has to work twice as hard to extract the same intelligence from a meeting that was already half-burned before it started.",
                    "choices": [
                        {
                            "choice_key": "trade_codes",
                            "label": "Trade for encryption codes",
                            "description": "Push through the tension and complete the exchange anyway.",
                            "outcome": "The code cylinder transfers under the table in a hurried, graceless handoff. The contact is sweating. The data is good even if the meeting was not.",
                            "next_scene_key": f"{prefix}_karn_merchant",
                            "effects": {"credits_delta": -15, "add_items": [{"item_key": "imperial_code_cylinder", "item_name": "Imperial Code Cylinder"}]},
                        },
                        {
                            "choice_key": "bait_informant",
                            "label": "Bait the local informant",
                            "description": "Lean into the tension — use the contact's fear against them.",
                            "outcome": "The informant was already near breaking. A single hard question opens the fracture. The watcher at the bar is named, and the meeting burns behind Rylos as he walks out.",
                            "next_scene_key": f"{prefix}_karn_exposed",
                            "effects": {"dark_delta": 1, "set_flags": ["informant_broken"]},
                        },
                        {
                            "choice_key": "meet_observer",
                            "label": f"Signal {second_ally}",
                            "description": "Cut the compromised meeting short and route through your field contact instead.",
                            "outcome": f"{second_ally} reads the room the moment Rylos signals. She pulls the contact's intelligence herself and passes it clean. The booth is abandoned before the watcher moves.",
                            "next_scene_key": f"{prefix}_karn_veska",
                            "effects": {"relationship_deltas": {"veska_tal": 4}, "set_flags": ["watcher_contacted"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_cantina_guided",
                    "title": "The Cantina: Guided Entry",
                    "prompt": f"{ally}'s route brought Rylos through a maintenance corridor used by intelligence couriers — and deposited him behind the bar, unseen. He sees the full room before anyone sees him: the contact's table, the exits, the watchers, the angles. He chooses how to approach from a position of total clarity.",
                    "choices": [
                        {
                            "choice_key": "trade_codes",
                            "label": "Trade for encryption codes",
                            "description": "Approach the contact directly, using your positional advantage to keep the exchange clean.",
                            "outcome": "The trade is textbook. Rylos controls the approach, the pace, and the exit. The code cylinder is secured before the contact's nerves have time to show.",
                            "next_scene_key": f"{prefix}_karn_merchant",
                            "effects": {"credits_delta": -15, "add_items": [{"item_key": "imperial_code_cylinder", "item_name": "Imperial Code Cylinder"}]},
                        },
                        {
                            "choice_key": "bait_informant",
                            "label": "Bait the local informant",
                            "description": "Use your hidden vantage to identify which patron is the watcher before the contact can warn them.",
                            "outcome": "Rylos identifies the watcher first, isolates the contact, and applies pressure from a position the informant never saw coming. The fracture is clean and fast.",
                            "next_scene_key": f"{prefix}_karn_exposed",
                            "effects": {"dark_delta": 1, "set_flags": ["informant_broken"]},
                        },
                        {
                            "choice_key": "meet_observer",
                            "label": f"Signal {second_ally}",
                            "description": "From behind the bar, pass a dead-drop signal to your field contact already in the room.",
                            "outcome": f"{second_ally} catches the signal from across the room and adjusts her position. She reaches the contact two minutes before Rylos does and has the intelligence waiting when he arrives.",
                            "next_scene_key": f"{prefix}_karn_veska",
                            "effects": {"relationship_deltas": {"veska_tal": 4}, "set_flags": ["watcher_contacted"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_karn_merchant",
                    "title": "Warden Karn: The Merchant Sweep",
                    "prompt": f"{rival} arrived in the district specifically because black-market encryption traffic spiked this week. He knows someone just bought codes. His sweep teams are moving methodically through every vendor and broker in the quarter, and the net is tightening toward the table where Rylos is sitting.",
                    "choices": [
                        {
                            "choice_key": "blend_crowd",
                            "label": "Disappear into the crowd",
                            "description": "Stay calm, look like a regular, and let the sweep move past you.",
                            "outcome": f"Rylos nurses his drink and mirrors the locals. {rival}'s sweep team logs him as background and moves on.",
                            "next_scene_key": f"{prefix}_safehouse_debrief",
                            "effects": {"light_delta": 1, "set_flags": ["karn_unsuspicious"]},
                        },
                        {
                            "choice_key": "feed_false_tip",
                            "label": f"Feed {rival} a false lead",
                            "description": "Point the warden's team toward a different encryption buyer to redirect the sweep.",
                            "outcome": f"A whispered tip sends {rival}'s team toward the wrong end of the market. Rylos walks out while they are still logging the false lead.",
                            "next_scene_key": f"{prefix}_safehouse_debrief_burned",
                            "effects": {"dark_delta": 1, "independent_delta": 1, "set_flags": ["karn_misdirected"]},
                        },
                        {
                            "choice_key": "contact_veska",
                            "label": f"Signal {second_ally} for a diversion",
                            "description": "Have your field partner pull the sweep team away from the market.",
                            "outcome": f"{second_ally} triggers a minor disturbance two blocks over. {rival} moves to contain it, and Rylos slips out of the merchant quarter clean.",
                            "next_scene_key": f"{prefix}_safehouse_debrief_team",
                            "effects": {"relationship_deltas": {"veska_tal": 2}, "set_flags": ["karn_diverted"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_karn_exposed",
                    "title": "Warden Karn: The Description",
                    "prompt": f"Someone reported a coercive interrogation in the cantina district. {rival} is now hunting the operative who cracked an informant — and the description circulating through Imperial security channels matches Rylos closely enough to be dangerous. Karn does not have a name yet, but he has a face and a method.",
                    "choices": [
                        {
                            "choice_key": "blend_crowd",
                            "label": "Disappear into the crowd",
                            "description": "Change your silhouette and stay in motion to blur the description.",
                            "outcome": f"Rylos sheds his outer jacket, adjusts his gait, and becomes unremarkable. {rival}'s officers study the crowd and mark him as a non-match.",
                            "next_scene_key": f"{prefix}_safehouse_debrief",
                            "effects": {"light_delta": 1, "set_flags": ["karn_unsuspicious"]},
                        },
                        {
                            "choice_key": "feed_false_tip",
                            "label": f"Feed {rival} a false lead",
                            "description": "Point security toward a different operative who fits the description better.",
                            "outcome": f"A quiet word redirects {rival}'s attention toward a known freelancer three blocks away. Rylos is off the description before the report is even updated.",
                            "next_scene_key": f"{prefix}_safehouse_debrief_burned",
                            "effects": {"dark_delta": 1, "independent_delta": 1, "set_flags": ["karn_misdirected"]},
                        },
                        {
                            "choice_key": "contact_veska",
                            "label": f"Signal {second_ally} for a diversion",
                            "description": "Have your field partner create an incident that demands Karn's personal attention.",
                            "outcome": f"{second_ally} manufactures a security alert one district over. {rival} responds in person — the description ceases to be his priority for long enough to matter.",
                            "next_scene_key": f"{prefix}_safehouse_debrief_team",
                            "effects": {"relationship_deltas": {"veska_tal": 2}, "set_flags": ["karn_diverted"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_karn_veska",
                    "title": "Warden Karn: The Dead-Drop Signal",
                    "prompt": f"One of {rival}'s surveillance teams picked up a coded dead-drop signal matching known intelligence protocols. Karn does not yet know it was Rylos — but he is close enough to the meeting location that he could see the table from where he is standing. The distance between suspicion and certainty is narrowing fast.",
                    "choices": [
                        {
                            "choice_key": "blend_crowd",
                            "label": "Disappear into the crowd",
                            "description": "Stay still and unremarkable while Karn's team triangulates the signal source.",
                            "outcome": f"Rylos orders another drink and does nothing suspicious. {rival}'s team traces the signal to a public relay post and logs it as ambient chatter.",
                            "next_scene_key": f"{prefix}_safehouse_debrief",
                            "effects": {"light_delta": 1, "set_flags": ["karn_unsuspicious"]},
                        },
                        {
                            "choice_key": "feed_false_tip",
                            "label": f"Feed {rival} a false lead",
                            "description": "Introduce noise into the signal trail that points Karn in the wrong direction.",
                            "outcome": f"A second burst signal — false, planted — fires from a location two streets over. {rival}'s team pivots toward the louder signature and loses the original thread.",
                            "next_scene_key": f"{prefix}_safehouse_debrief_burned",
                            "effects": {"dark_delta": 1, "independent_delta": 1, "set_flags": ["karn_misdirected"]},
                        },
                        {
                            "choice_key": "contact_veska",
                            "label": f"Signal {second_ally} for a diversion",
                            "description": "Have your field partner pull the surveillance team away before they finish triangulating.",
                            "outcome": f"{second_ally} creates a scene loud enough to demand {rival}'s direct attention. The surveillance team abandons the signal trace before it resolves to Rylos.",
                            "next_scene_key": f"{prefix}_safehouse_debrief_team",
                            "effects": {"relationship_deltas": {"veska_tal": 2}, "set_flags": ["karn_diverted"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_safehouse_debrief",
                    "title": "The Safe House",
                    "prompt": f"Rylos slips into a rented room above a repair depot — the kind of place that doesn't log guests. {second_ally} is already there, spreading decrypted fragments across a portable display. On the wall, a public Imperial wanted screen cycles through faces. One stops Rylos cold: a Togruta woman, montrals swept back, twin lightsabers at her sides. The bounty is enormous. The name reads: AHSOKA TANO. ARMED. EXTREMELY DANGEROUS. DO NOT ENGAGE ALONE. The screen moves on before {second_ally} notices him looking.",
                    "choices": [
                        {
                            "choice_key": "review_data",
                            "label": "Review the decrypted fragments",
                            "description": "Study the archive data before moving — know exactly what you are after.",
                            "outcome": f"The fragments sketch the outline of a weapons codex older than the Empire itself. {second_ally} flags one entry: coordinates for a listening post no official record acknowledges.",
                            "next_scene_key": f"{prefix}_shadow_pursuit",
                            "effects": {"light_delta": 1, "set_flags": ["studied_codex_fragments"]},
                        },
                        {
                            "choice_key": "plan_exfil",
                            "label": "Plan the exfiltration route first",
                            "description": "Map the exit before the entry — if the archive goes loud, you need a clean way out.",
                            "outcome": f"Rylos identifies three exit corridors, two of which {rival} does not have covered yet. He marks them and commits the map to memory.",
                            "next_scene_key": f"{prefix}_shadow_pursuit_tactical",
                            "effects": {"independent_delta": 1, "set_flags": ["exfil_route_planned"]},
                        },
                        {
                            "choice_key": "rest_brief",
                            "label": "Take an hour and rest",
                            "description": "You have been running since the shuttle. A short rest sharpens the edge.",
                            "outcome": f"Rylos closes his eyes for an hour. When {second_ally} wakes him, something feels different — a low, persistent hum at the edge of his awareness. He does not mention it.",
                            "next_scene_key": f"{prefix}_shadow_pursuit_force",
                            "effects": {"health_delta": 10, "dark_delta": 1, "set_flags": ["force_hum_noticed"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_safehouse_debrief_burned",
                    "title": "The Safe House: Hot Exit",
                    "prompt": f"Rylos slips into the rented room above the repair depot to find {second_ally} already dismantling the safe house. A scanner on the table shows Karn's sweep teams two blocks out and closing. The false tip bought twenty minutes, and fifteen of them are gone. The Ahsoka Tano wanted poster on the wall cycles past unnoticed — there is no time to look at anything that isn't an exit. The debrief happens in fragments, between equipment checks and route confirmations, with one eye always on the scanner.",
                    "choices": [
                        {
                            "choice_key": "review_data",
                            "label": "Pull the critical data now",
                            "description": "Grab what matters from the fragments before the room burns.",
                            "outcome": f"Rylos extracts the key archive fragment with thirty seconds to spare. {second_ally} kills the scanner and moves. The data is secured. Karn will find a cold room.",
                            "next_scene_key": f"{prefix}_shadow_pursuit",
                            "effects": {"light_delta": 1, "set_flags": ["studied_codex_fragments"]},
                        },
                        {
                            "choice_key": "plan_exfil",
                            "label": "Map the exit while you still can",
                            "description": "Burn the hardware and memorize the route out before Karn tightens the net.",
                            "outcome": f"Rylos commits three alternative corridors to memory while {second_ally} strips the room. Karn's team reaches the building eight minutes later and finds nothing worth reporting.",
                            "next_scene_key": f"{prefix}_shadow_pursuit_tactical",
                            "effects": {"independent_delta": 1, "set_flags": ["exfil_route_planned"]},
                        },
                        {
                            "choice_key": "rest_brief",
                            "label": "Go still and feel the building",
                            "description": "There is something wrong with the room that you cannot name. You need a moment.",
                            "outcome": f"Rylos stops moving. {second_ally} stares at him. For three seconds the room is completely quiet — and then Rylos knows which exit Karn is not watching yet. He cannot explain how. He moves.",
                            "next_scene_key": f"{prefix}_shadow_pursuit_force",
                            "effects": {"health_delta": 10, "dark_delta": 1, "set_flags": ["force_hum_noticed"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_safehouse_debrief_team",
                    "title": "The Safe House: Veska's Debrief",
                    "prompt": f"{second_ally} already has the data spread across the portable display when Rylos arrives. She ran the debrief herself — extracted the key fragments, cross-referenced the access logs, and flagged three connections the original brief missed entirely. She does not look up when Rylos walks in. 'I've been waiting,' she says. 'The archive has been running a parallel intelligence operation that no one told us to find. Someone inside the annex wanted this to be discovered.' On the wall, Ahsoka Tano's wanted poster cycles past. {second_ally} does not react. Rylos files the image away.",
                    "choices": [
                        {
                            "choice_key": "review_data",
                            "label": "Review what Veska found",
                            "description": "Go through her analysis and add your own read.",
                            "outcome": f"Between them, they reconstruct an intelligence trail that goes back eighteen months. The archive fragment is a thread. {second_ally} found the rope.",
                            "next_scene_key": f"{prefix}_shadow_pursuit",
                            "effects": {"light_delta": 1, "set_flags": ["studied_codex_fragments"]},
                        },
                        {
                            "choice_key": "plan_exfil",
                            "label": "Plan the next approach while Veska reads",
                            "description": "Let her work the data while you map what comes after the annex.",
                            "outcome": f"{second_ally} nods without looking up. Rylos lays out the approach routes. By the time she finishes the analysis, he has three entry corridors and four exits committed to memory.",
                            "next_scene_key": f"{prefix}_shadow_pursuit_tactical",
                            "effects": {"independent_delta": 1, "set_flags": ["exfil_route_planned"]},
                        },
                        {
                            "choice_key": "rest_brief",
                            "label": "Ask her what she felt in there",
                            "description": "She was in the building before you. Ask her if anything seemed wrong in a way that has no name.",
                            "outcome": f"{second_ally} looks up for the first time. A long pause. 'The air changed near the vault,' she says carefully. 'Like static before a lightning strike, but inside your head.' She does not ask if Rylos felt it too. She does not have to.",
                            "next_scene_key": f"{prefix}_shadow_pursuit_force",
                            "effects": {"health_delta": 10, "dark_delta": 1, "set_flags": ["force_hum_noticed"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_shadow_pursuit",
                    "title": "The Shadow on Your Heels",
                    "prompt": f"Moving toward the archive annex, Rylos notices a tail — professional, patient, switching positions to avoid pattern recognition. One figure stands out: compact armour under a street coat, a rangefinder visor tilted down. This is not {rival}'s style and it is not Imperial. Someone has put a bounty hunter on him. That strange hum behind Rylos's eyes sharpens, like a warning he does not yet know how to read.",
                    "choices": [
                        {
                            "choice_key": "lose_the_tail",
                            "label": "Lose them in the transit hub",
                            "description": "Use the crowded station interchange to break the surveillance line.",
                            "outcome": "Three platform changes, a service corridor, a borrowed vendor coat. The armoured figure stops at the last junction and does not follow. For now.",
                            "next_scene_key": f"{prefix}_directorate_reveal",
                            "effects": {"independent_delta": 1, "set_flags": ["boba_fett_evaded"]},
                        },
                        {
                            "choice_key": "confront_tail",
                            "label": "Double back and face the hunter",
                            "description": "Step into an alcove and let him walk into you instead.",
                            "outcome": "The hunter stops one pace away. Mandalorian armour, green and battered. He does not draw. 'You have something people want,' Boba Fett says quietly. 'I'm not here for you. Yet.' He steps around Rylos and disappears into the crowd.",
                            "next_scene_key": f"{prefix}_directorate_reveal_warned",
                            "effects": {"dark_delta": 1, "independent_delta": 2, "set_flags": ["boba_fett_confronted", "boba_fett_warned"]},
                        },
                        {
                            "choice_key": "signal_veska",
                            "label": f"Signal {second_ally} to intercept",
                            "description": "Let your partner cut off the hunter while you stay on approach.",
                            "outcome": f"{second_ally} loops back. Four minutes of silence, then her voice: 'Mandalorian armour. He let me approach, then walked away. Rylos — someone hired Boba Fett.' A pause. 'Keep moving.'",
                            "next_scene_key": f"{prefix}_directorate_reveal_partnered",
                            "effects": {"relationship_deltas": {"veska_tal": 3}, "set_flags": ["boba_fett_identified", "veska_handled_tail"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_shadow_pursuit_tactical",
                    "title": "The Shadow on Your Heels: Planned Routes",
                    "prompt": f"Rylos is running his pre-mapped exit corridors when the tail appears — and the tail is already on his second-choice route. Someone anticipated the contingency. The figure is compact, armoured under a street coat, rangefinder visor scanning the crowd. This is not {rival}'s method. Rylos recognises the equipment before he recognises the problem: a bounty hunter was briefed on his fallback routes. That strange hum behind his eyes sharpens into something that feels like geometry — angles and distances arriving without calculation.",
                    "choices": [
                        {
                            "choice_key": "lose_the_tail",
                            "label": "Switch to the unmarked route",
                            "description": "Use the one corridor you kept off your original plan.",
                            "outcome": "The unmarked route is slower and dirtier, but the armoured figure never accounted for it. Rylos emerges four blocks east and watches the hunter double back on an empty street.",
                            "next_scene_key": f"{prefix}_directorate_reveal",
                            "effects": {"independent_delta": 1, "set_flags": ["boba_fett_evaded"]},
                        },
                        {
                            "choice_key": "confront_tail",
                            "label": "Double back and face the hunter",
                            "description": "Your map told you this alcove exists. Use it.",
                            "outcome": "The hunter walks into the position Rylos chose three corridors ago. Mandalorian armour, green and battered. 'You planned for this,' Boba Fett observes. It is not a question. 'Someone told me your exits,' he continues. 'I'm not here for you. But someone is.' He leaves Rylos alone with that.",
                            "next_scene_key": f"{prefix}_directorate_reveal_warned",
                            "effects": {"dark_delta": 1, "independent_delta": 2, "set_flags": ["boba_fett_confronted", "boba_fett_warned"]},
                        },
                        {
                            "choice_key": "signal_veska",
                            "label": f"Route {second_ally} through the cut-off point",
                            "description": "Your plan had a position for a second operative. Put her there.",
                            "outcome": f"{second_ally} takes the cut-off position before the hunter can double back. She lets him walk past, then follows him three blocks before he loses her deliberately. 'Mandalorian,' she reports. 'He knew I was there and let me watch him anyway. Rylos — Boba Fett doesn't do that unless he's sending a message.'",
                            "next_scene_key": f"{prefix}_directorate_reveal_partnered",
                            "effects": {"relationship_deltas": {"veska_tal": 3}, "set_flags": ["boba_fett_identified", "veska_handled_tail"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_shadow_pursuit_force",
                    "title": "The Shadow on Your Heels: The Hum Speaks",
                    "prompt": f"Rylos feels the tail before he sees it. That low persistent hum behind his eyes — the one he has been ignoring since the safe house — crests into something sharp and directional. He stops walking and the feeling resolves: someone is tracking him from the northeast corner of the interchange, compact and still under a street vendor's awning. When he finally looks, the rangefinder visor is already pointed at him. Mandalorian armour under a street coat. The hunter found him the same moment the hum did. Something about that symmetry is deeply unsettling.",
                    "choices": [
                        {
                            "choice_key": "lose_the_tail",
                            "label": "Follow the hum out",
                            "description": "Let whatever you're feeling guide the exit instead of your eyes.",
                            "outcome": "The feeling does not disappear, but it shifts — pulling Rylos toward a service corridor he would not have chosen on instinct. Three turns later the interchange is behind him and the signal is gone. He does not know what to make of any of it.",
                            "next_scene_key": f"{prefix}_directorate_reveal",
                            "effects": {"independent_delta": 1, "set_flags": ["boba_fett_evaded"]},
                        },
                        {
                            "choice_key": "confront_tail",
                            "label": "Walk toward him instead",
                            "description": "The hum is loudest in that direction. Step into it.",
                            "outcome": "Boba Fett does not reach for his weapon. He watches Rylos approach and something shifts in his posture — not threat recognition. Something closer to interest. 'You felt me before you saw me,' he says. Not a question. 'That's going to make you very hard to follow. And very easy to find.' He walks away. Rylos stands in the rain and understands that two very different things just happened simultaneously.",
                            "next_scene_key": f"{prefix}_directorate_reveal_warned",
                            "effects": {"dark_delta": 1, "independent_delta": 2, "set_flags": ["boba_fett_confronted", "boba_fett_warned"]},
                        },
                        {
                            "choice_key": "signal_veska",
                            "label": f"Send {second_ally} what the hum is telling you",
                            "description": "The feeling has coordinates. Pass them to your partner.",
                            "outcome": f"Rylos sends a position to {second_ally} without explanation. Thirty seconds of silence. Then: 'Mandalorian armour. He's gone now — he walked away the moment I confirmed visual. Rylos. How did you know exactly where he was?' Another silence. 'We should talk about that.'",
                            "next_scene_key": f"{prefix}_directorate_reveal_partnered",
                            "effects": {"relationship_deltas": {"veska_tal": 3}, "set_flags": ["boba_fett_identified", "veska_handled_tail"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_directorate_reveal",
                    "title": "Directorate Null",
                    "prompt": f"Rylos and {second_ally} regroup in a maintenance alcove while the sweep moves on. The contact's information and the archive access logs point to something larger than a simple data theft. There is a name at the centre of it: Directorate Null. Not a person. A philosophy. A network built on the belief that the galaxy's endless wars exist because Force users — Sith lords and Jedi knights alike — will always drag ordinary people into their conflicts.",
                    "choices": [
                        {
                            "choice_key": "report_immediately",
                            "label": f"Report the name to {ally} immediately",
                            "description": "Pass the intelligence up the chain before acting on it.",
                            "outcome": f"{ally}'s voice comes back steady and cold: proceed to the annex. Recover the archive fragment. The Empire wants the codex before Directorate Null can use it.",
                            "next_scene_key": f"{prefix}_archive_lockdown",
                            "effects": {"relationship_deltas": {"watcher_nine": 3}, "light_delta": 1},
                        },
                        {
                            "choice_key": "hold_the_name",
                            "label": "Hold the name back and investigate first",
                            "description": "Keep Directorate Null to yourself until you understand what they actually want.",
                            "outcome": "Rylos files a partial report and keeps the critical detail. If this network is ideological rather than criminal, the Empire may not be the right entity to hand it to.",
                            "next_scene_key": f"{prefix}_archive_lockdown",
                            "effects": {"independent_delta": 2, "set_flags": ["withheld_directorate_name"]},
                        },
                        {
                            "choice_key": "ask_veska_opinion",
                            "label": f"Ask {second_ally} what she thinks of them",
                            "description": "Trust your field partner's read before deciding who to tell.",
                            "outcome": f"{second_ally} is quiet for a long moment. 'They're not wrong about the Sith,' she says finally. 'That doesn't mean they're right about everything else.'",
                            "next_scene_key": f"{prefix}_archive_lockdown",
                            "effects": {"relationship_deltas": {"veska_tal": 3}, "set_flags": ["veska_questioned_null"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_directorate_reveal_warned",
                    "title": "Directorate Null: Already Known",
                    "prompt": f"Boba Fett's words sit between Rylos and {second_ally} like an unexploded charge. Someone hired him specifically — someone who knew about the archive operation and wanted leverage over it, not just the data. The Directorate Null connection clarifies something dangerous: this network did not surface in the archive logs because someone missed it. It surfaced because someone let it be found. The intelligence annex is not a target. It is an introduction. {second_ally} keeps her voice even when she says: 'We are walking into something that has been waiting for us.'",
                    "choices": [
                        {
                            "choice_key": "report_immediately",
                            "label": f"Report Null and the warning to {ally}",
                            "description": "Put everything on the table — Directorate Null, Boba Fett, the staged discovery. Let command react.",
                            "outcome": f"{ally}'s silence after the full report lasts four seconds. 'Proceed to the annex,' he says finally. 'Recover the fragment. Do not engage with any party attempting contact.' The order sounds like protection. It feels like a lid being placed over something.",
                            "next_scene_key": f"{prefix}_archive_lockdown",
                            "effects": {"relationship_deltas": {"watcher_nine": 3}, "light_delta": 1},
                        },
                        {
                            "choice_key": "hold_the_name",
                            "label": "Hold Null and the warning back",
                            "description": "If this was staged for you to find, telling command may be exactly what the setup requires.",
                            "outcome": "Rylos files a minimal report. The hunter's warning, the staged discovery, the Directorate Null connection — all of it stays in his head. He walks into the annex knowing something that no one on any side knows he knows.",
                            "next_scene_key": f"{prefix}_archive_lockdown",
                            "effects": {"independent_delta": 2, "set_flags": ["withheld_directorate_name"]},
                        },
                        {
                            "choice_key": "ask_veska_opinion",
                            "label": f"Ask {second_ally} what the warning was really for",
                            "description": "Boba Fett chose to speak. That was not an accident. She might read it differently.",
                            "outcome": f"'He told you someone is coming for you,' {second_ally} says. 'Not Null. Not {rival}. Someone above both of them.' She pauses. 'I think he was doing you a favor. I think he's not sure why.' She looks at the annex entrance. 'Go in anyway. We have to.'",
                            "next_scene_key": f"{prefix}_archive_lockdown",
                            "effects": {"relationship_deltas": {"veska_tal": 3}, "set_flags": ["veska_questioned_null"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_directorate_reveal_partnered",
                    "title": "Directorate Null: Veska's Read",
                    "prompt": f"{second_ally} is the one who makes the connection to Directorate Null. She lays out three access logs, a courier timestamp, and a name that appears in the archive records three months before the network was officially identified by Imperial Intelligence. She found it because she knew where to look — and when Rylos asks her how, she does not answer immediately. 'I've heard the name before,' she says finally. 'From someone I trusted once. That's all.' The weight of what she is not saying fills the maintenance alcove.",
                    "choices": [
                        {
                            "choice_key": "report_immediately",
                            "label": f"Report what {second_ally} found to {ally}",
                            "description": "Pass her intelligence up the chain, attribution included.",
                            "outcome": f"Rylos reports the connection with {second_ally}'s name attached. {ally}'s response is clipped: 'Proceed to the annex. We will discuss your field partner's sources when you return.' The word 'sources' lands wrong.",
                            "next_scene_key": f"{prefix}_archive_lockdown",
                            "effects": {"relationship_deltas": {"watcher_nine": 3}, "light_delta": 1},
                        },
                        {
                            "choice_key": "hold_the_name",
                            "label": "Keep Veska's connection private",
                            "description": "Whatever she knows about Directorate Null, it stays between you.",
                            "outcome": f"Rylos reports the Directorate Null connection without mentioning how it was found. {second_ally} gives him one careful look when the channel closes. Neither of them says anything. The trust is now running in both directions.",
                            "next_scene_key": f"{prefix}_archive_lockdown",
                            "effects": {"independent_delta": 2, "set_flags": ["withheld_directorate_name"]},
                        },
                        {
                            "choice_key": "ask_veska_opinion",
                            "label": "Ask her what she thinks you should do with it",
                            "description": "This is her intelligence. Her call on how it moves.",
                            "outcome": f"'Don't report it yet,' {second_ally} says. 'Not until we know what's in the annex. If I'm right about what Null wants, the order of information matters.' She is not explaining everything she knows. Rylos is choosing to be all right with that.",
                            "next_scene_key": f"{prefix}_archive_lockdown",
                            "effects": {"relationship_deltas": {"veska_tal": 3}, "set_flags": ["veska_questioned_null"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_archive_lockdown",
                    "title": "Archive Lockdown",
                    "prompt": f"The intelligence annex sits beneath layered security fields. Inside is a fragment of the {campaign_arc['central_objective_name']}, and outside, {rival} has begun to suspect a mole. Rylos feels a strange pressure behind his eyes as he approaches the vault. A rumor on the security channel says a hired bounty hunter, Boba Fett, may already be in the building.",
                    "set_piece": {
                        "next_scene_key": f"{prefix}_escape_fallout",
                        "bad_outcome_scene_key": f"{prefix}_burned_cover",
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
                    "scene_key": f"{prefix}_escape_fallout",
                    "title": "After the Annex",
                    "prompt": f"Rylos reaches a safe alcove two levels below the district surface. Rain hammers the grates above. His hands are steady but his mind is not. The archive data is secured, but the escape left marks. {second_ally} arrives through a side passage, and {ally}'s voice crackles in his ear demanding a status report. For a moment Rylos noticed something strange during the escape — objects that moved without reason, a pressure behind his eyes that wasn't fear. He pushes it aside. He has a report to make and a decision that will define what kind of operative he is.",
                    "choices": [
                        {
                            "choice_key": "full_debrief",
                            "label": f"Give {ally} a full debrief",
                            "description": "Report everything you found and let command decide what comes next.",
                            "outcome": f"{ally} processes the information without warmth. 'You have confirmed a network we suspected existed. Stay in position. The hunt continues.' Rylos feels the weight of being a tool that has just proven its usefulness.",
                            "next_scene_key": f"{prefix}_imperial_relay",
                            "effects": {"relationship_deltas": {"watcher_nine": 4}, "light_delta": 1},
                        },
                        {
                            "choice_key": "partial_debrief",
                            "label": "Hold the most dangerous parts back",
                            "description": "Give enough to satisfy command but keep leverage for yourself.",
                            "outcome": "The partial report satisfies protocol. What Rylos keeps — the deepest file cluster and the name of the network's contact — remains his alone. In this game, insurance is survival.",
                            "next_scene_key": f"{prefix}_shadow_market",
                            "effects": {"independent_delta": 2, "set_flags": ["held_leverage"]},
                        },
                        {
                            "choice_key": "trust_veska",
                            "label": f"Debrief {second_ally} instead of {ally}",
                            "description": "Trust your field partner with the truth before command gets a filtered version.",
                            "outcome": f"{second_ally} listens without judgment. 'There are things in those files that will get people killed if the wrong hands read them first,' she says. 'We decide who those hands are.' A partnership forms in the rain.",
                            "next_scene_key": f"{prefix}_veska_breakaway",
                            "effects": {"relationship_deltas": {"veska_tal": 5}, "independent_delta": 1, "set_flags": ["veska_trusted_first"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_imperial_relay",
                    "title": "Imperial Relay",
                    "prompt": f"Every secure channel in the district cuts to static, then a single pirate signal bleeds through. A masked voice, calm and measured, addresses not the Empire, not the Republic — but the galaxy itself. It claims the age of Jedi and Sith is a centuries-long catastrophe. It claims proof exists. It claims the proof is already in the wrong hands. Rylos knows the files in his pocket are exactly what the voice is describing. Then something happens that has no tactical explanation. The room around him goes quiet in a way that has nothing to do with sound. A loose hydrospanner lifts off the floor. A cracked viewport seals shut. Metal groans toward him like it recognizes him. In a secured Imperial relay somewhere beyond the stars, Darth Vader — the Emperor's enforcer, a man who was once a Jedi and chose a darker power — sits very still and listens to his analysts report a disturbance in the Force.",
                    "choices": [
                        {
                            "choice_key": "step_into_signal",
                            "label": "Step fully into the debrief",
                            "description": "Lean into the trust you built and let the Empire see all of it.",
                            "outcome": f"Rylos gives the relay everything. The analysts stop whispering and start obeying. {ally} does not congratulate him. He simply opens the next door.",
                            "next_scene_key": f"{prefix}_final_command",
                            "effects": {"relationship_deltas": {"watcher_nine": 3}, "light_delta": 1, "set_flags": [f"episode_{episode_number}_cleared", "swore_to_the_mission", "force_sensitive_awakened"]},
                        },
                        {
                            "choice_key": "sanitize_report",
                            "label": "Trim the debrief before it spreads",
                            "description": "Cooperate, but deny the relay the most dangerous details.",
                            "outcome": "Rylos cuts away the deepest fragments before the archive mirrors finish syncing. It is enough to stay useful, not enough to stay safe.",
                            "next_scene_key": f"{prefix}_final_command_independent",
                            "effects": {"independent_delta": 1, "set_flags": [f"episode_{episode_number}_cleared", "force_sensitive_awakened"]},
                        },
                        {
                            "choice_key": "ask_about_vader",
                            "label": "Ask who noticed the disturbance",
                            "description": "Push past protocol and find out who on the other end reacted to you.",
                            "outcome": f"{ally} answers with a silence too careful to be accidental. When he finally speaks, the name he avoids saying is more revealing than any confession. Rylos now understands the scale of what is hunting him.",
                            "next_scene_key": f"{prefix}_final_command_vader",
                            "effects": {"dark_delta": 1, "set_flags": [f"episode_{episode_number}_cleared", "force_sensitive_awakened"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_final_command",
                    "title": "Watcher's Orders",
                    "prompt": f"Watcher Nine's voice arrives without preamble. The files have been reviewed. Vader's analysts flagged the Force disturbance within the hour. This is no longer a reconnaissance assignment — the Empire wants Rylos for something deeper, and {ally} has been authorized to offer it. The mission just became a recruitment.",
                    "choices": [
                        {
                            "choice_key": "accept_deeper_mission",
                            "label": "Accept the Empire's deeper mission",
                            "description": "Step into the role the Empire is offering and see how far it goes.",
                            "outcome": f"Rylos agrees. {ally}'s voice carries something that might almost be satisfaction. The Empire gives rank, resources, and a leash. Vader knows he exists now. Command calls it an asset. Rylos calls it a cage with better lighting.",
                            "next_scene_key": "END",
                            "effects": {"relationship_deltas": {"watcher_nine": 4}, "set_flags": ["ending_emperors_blade"]},
                        },
                        {
                            "choice_key": "refuse_request_extraction",
                            "label": "Refuse the mission and request extraction",
                            "description": "Walk away from the Empire's offer and disappear clean.",
                            "outcome": f"Rylos declines. {ally} goes silent for three seconds — a long time on a secure channel. Extraction is arranged. Rylos surfaces three weeks later on a backwater moon with a new name. The Force stays quiet — for now.",
                            "next_scene_key": "END",
                            "effects": {"light_delta": 1, "independent_delta": 1, "set_flags": ["ending_quiet_defector"]},
                        },
                        {
                            "choice_key": "use_trust_to_disappear",
                            "label": f"Use {ally}'s trust to quietly disappear",
                            "description": "Exploit the handler relationship as cover to vanish from Imperial records entirely.",
                            "outcome": f"Rylos says yes on the channel and is gone before the extraction team arrives. {ally}'s trust becomes the key that unlocks the door out. He vanishes from Imperial records while holding information that could destroy careers. A shadow with a conscience.",
                            "next_scene_key": "END",
                            "effects": {"independent_delta": 2, "set_flags": ["ending_ghost_who_knew"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_final_command_independent",
                    "title": "Watcher's Orders: Incomplete Files",
                    "prompt": f"Watcher Nine does not accuse Rylos of sanitizing the debrief. He does not need to. The assignment he sends instead is designed as a test: an operation where the gaps in the report become the pressure points, where anyone running a private game will be forced to either show their hand or burn what they are hiding. {ally}'s voice is professionally warm and professionally empty. 'The mission continues,' he says. 'The specifics will reach you through the usual channel. I trust your judgment.' That last sentence is not a compliment.",
                    "choices": [
                        {
                            "choice_key": "accept_deeper_mission",
                            "label": "Accept and close the private game",
                            "description": "Give up the leverage, take the assignment, and go clean.",
                            "outcome": f"Rylos surrenders the hidden fragments and takes the mission on full terms. {ally}'s next message is warmer. The Empire gets what it paid for. Rylos gets a leash that fits properly.",
                            "next_scene_key": "END",
                            "effects": {"relationship_deltas": {"watcher_nine": 3}, "set_flags": ["ending_emperors_blade"]},
                        },
                        {
                            "choice_key": "refuse_request_extraction",
                            "label": "Refuse and take the hidden files out",
                            "description": "Walk away and keep what you know as insurance.",
                            "outcome": "Rylos declines the assignment and disappears with the sanitized fragments still in his possession. Command cannot move against him without confirming the files exist. He vanishes into a stalemate of his own construction.",
                            "next_scene_key": "END",
                            "effects": {"independent_delta": 2, "set_flags": ["ending_quiet_defector", "held_leverage"]},
                        },
                        {
                            "choice_key": "use_trust_to_disappear",
                            "label": f"Use {ally}'s test as cover to vanish",
                            "description": "Play along long enough to get extraction coordinates, then redirect them.",
                            "outcome": f"Rylos agrees to the assignment, requests extraction for operational security, and reroutes the extraction vessel before anyone realizes what happened. The hidden files go with him. {ally} will spend months deciding if this was a betrayal or a masterclass.",
                            "next_scene_key": "END",
                            "effects": {"independent_delta": 3, "set_flags": ["ending_ghost_who_knew", "held_leverage"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_final_command_vader",
                    "title": "Watcher's Orders: Vader's Notation",
                    "prompt": f"The assignment arrives in Watcher Nine's voice but carries a cipher notation Rylos was never briefed on — and {ally} explains it without being asked, which means he was told to. The notation is Vader's. Not relayed through an analyst or an Intelligence directorate. Direct. Personal. {ally} confirms what Rylos already understood: Vader registered the Force disturbance during the escape. He has not decided what to do about it yet. The assignment sitting in front of Rylos is not from the Empire. It is from the man inside the Empire who makes Emperors nervous.",
                    "choices": [
                        {
                            "choice_key": "accept_deeper_mission",
                            "label": "Accept the assignment and Vader's attention",
                            "description": "Step into whatever Vader has built around you and find out if it is a cage or a door.",
                            "outcome": f"Rylos accepts. {ally}'s relief is palpable — he did not want to explain a refusal. The assignment is unlike anything in the standard Intelligence portfolio. Vader's notation updates within the hour. Whatever Rylos is, the Empire's most dangerous man now knows he exists and has decided he is useful. For now.",
                            "next_scene_key": "END",
                            "effects": {"dark_delta": 2, "set_flags": ["ending_emperors_blade", "vader_noticed"]},
                        },
                        {
                            "choice_key": "refuse_request_extraction",
                            "label": "Refuse and run before Vader decides",
                            "description": "Whatever window exists before Vader commits to a course of action, use it now.",
                            "outcome": f"Rylos refuses before {ally} finishes the offer. The extraction is arranged with unusual speed — someone wants the liability resolved cleanly. Rylos surfaces weeks later with a new identity and the knowledge that Darth Vader once looked directly at him and let him go. He does not know why. He suspects the answer would be worse than not knowing.",
                            "next_scene_key": "END",
                            "effects": {"light_delta": 1, "independent_delta": 1, "set_flags": ["ending_quiet_defector", "vader_noticed"]},
                        },
                        {
                            "choice_key": "use_trust_to_disappear",
                            "label": "Use Vader's interest as your exit cover",
                            "description": "An Empire distracted by a Force-sensitive asset creates exactly the kind of blind spot a ghost needs.",
                            "outcome": f"Rylos agrees to report to the debriefing location and vanishes between the affirmation and the arrival. The gap in Vader's intelligence is now a Rylos-shaped hole. The Empire will spend years deciding whether a Force-sensitive operative walked away or was taken. Both explanations are true, depending on who is asking.",
                            "next_scene_key": "END",
                            "effects": {"independent_delta": 2, "dark_delta": 1, "set_flags": ["ending_ghost_who_knew", "vader_noticed"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_shadow_market",
                    "title": "The Hidden Ledger",
                    "prompt": f"Rylos and {second_ally} stash the unreported archive fragments in a dead vault beneath the tram lines. Within the hour, buyers start surfacing anyway. Someone inside Imperial Intelligence knows a copy survived. Directorate Null sends a phrase that proves they know exactly which fragments are missing. A third bidder never uses a name, only numbers. The market is not opening because Rylos advertised. It is opening because the galaxy can smell leverage.",
                    "choices": [
                        {
                            "choice_key": "test_imperial_buyer",
                            "label": "Probe the Imperial buyer first",
                            "description": "Measure how desperate command really is to recover the fragments.",
                            "outcome": "The Imperial channel answers too quickly and offers too much. Fear has entered the negotiation, which means the fragments matter more than the badge code admits.",
                            "next_scene_key": f"{prefix}_final_leverage",
                            "effects": {"light_delta": 1, "set_flags": [f"episode_{episode_number}_cleared", "kept_blackmail_copy", "force_sensitive_awakened"]},
                        },
                        {
                            "choice_key": "stir_bidding_war",
                            "label": "Stir the bidders against each other",
                            "description": "Escalate the price and keep every faction off balance.",
                            "outcome": "Conflicting offers start colliding within minutes. False escrow accounts bloom across the HoloNet. Everyone wants the files; nobody trusts the others to touch them first.",
                            "next_scene_key": f"{prefix}_final_leverage",
                            "effects": {"independent_delta": 2, "dark_delta": 1, "set_flags": [f"episode_{episode_number}_cleared", "kept_blackmail_copy", "force_sensitive_awakened"]},
                        },
                        {
                            "choice_key": "let_veska_screen",
                            "label": f"Let {second_ally} screen the buyers",
                            "description": "Use your field partner to separate the serious offers from the traps.",
                            "outcome": f"{second_ally} quietly kills three channels and keeps two. 'One is official, one is ideological, and one is bait pretending to be both,' she says. 'Now we choose what kind of trouble we prefer.'",
                            "next_scene_key": f"{prefix}_final_leverage",
                            "effects": {"relationship_deltas": {"veska_tal": 3}, "independent_delta": 1, "set_flags": [f"episode_{episode_number}_cleared", "kept_blackmail_copy", "force_sensitive_awakened"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_veska_breakaway",
                    "title": "Off the Grid",
                    "prompt": f"{second_ally} kills the comms, burns the rented room, and walks Rylos through maintenance tunnels no official map still admits exist. By the time {ally} realizes the report never came, they are already gone. Then the strange pressure behind Rylos's eyes crests into something sharper. A rack of tools rattles. A sealed door unlatches itself. Hours later, a single encoded message arrives on a relay only {second_ally} should know: Directorate Null is offering a meeting, and somehow they already know the files were not surrendered.",
                    "choices": [
                        {
                            "choice_key": "follow_veska_to_null",
                            "label": f"Follow {second_ally}'s lead",
                            "description": "Let Veska choose the meeting ground and control the first contact.",
                            "outcome": f"{second_ally} picks a meeting site designed for betrayal and then improves it. If Null wants a conversation, it will happen on terms she can collapse with one switch.",
                            "next_scene_key": f"{prefix}_final_null_contact",
                            "effects": {"relationship_deltas": {"veska_tal": 4}, "independent_delta": 1, "set_flags": [f"episode_{episode_number}_cleared", "veska_trusted_first", "force_sensitive_awakened"]},
                        },
                        {
                            "choice_key": "contact_null_alone",
                            "label": "Answer Directorate Null alone",
                            "description": "Keep even Veska one step back while you test the offer yourself.",
                            "outcome": "Rylos sends the acceptance himself. If this becomes a trap, at least it will be his trap to spring.",
                            "next_scene_key": f"{prefix}_final_null_contact",
                            "effects": {"dark_delta": 1, "independent_delta": 2, "set_flags": [f"episode_{episode_number}_cleared", "force_sensitive_awakened"]},
                        },
                        {
                            "choice_key": "burn_copy_before_meeting",
                            "label": "Destroy your copy before the meeting",
                            "description": "Arrive with knowledge, not inventory, and deny every side easy leverage.",
                            "outcome": "The archive fragments die in a controlled fire. The meeting will now be about conviction, not merchandise.",
                            "next_scene_key": f"{prefix}_final_null_contact",
                            "effects": {"light_delta": 1, "set_flags": [f"episode_{episode_number}_cleared", "burned_first_fragment", "force_sensitive_awakened"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_final_leverage",
                    "title": "The Market",
                    "prompt": "Three coded messages arrive within the hour of the private copy being secured. The Empire has triangulated a signal anomaly and wants to buy back the files quietly. Directorate Null sends a single encrypted phrase that means they already know what Rylos is holding. A third message has no sender ID at all — only a credit offer that makes both the others look modest. The market is open.",
                    "choices": [
                        {
                            "choice_key": "sell_to_empire",
                            "label": "Sell to the Empire",
                            "description": "Take the Imperial offer and close the transaction through official channels.",
                            "outcome": "The Empire pays well for confirmed intelligence. Rylos becomes a line item in a classified budget. He is useful, compensated, and never quite free.",
                            "next_scene_key": "END",
                            "effects": {"credits_delta": 50, "set_flags": ["ending_paid_instrument"]},
                        },
                        {
                            "choice_key": "sell_to_null",
                            "label": "Sell to Directorate Null",
                            "description": "Accept Directorate Null's offer and hear their argument.",
                            "outcome": "Directorate Null's ideology is not without logic. Rylos sells them the files and stays to hear the argument. He does not fully agree. He is not sure he disagrees.",
                            "next_scene_key": "END",
                            "effects": {"independent_delta": 2, "set_flags": ["ending_the_believer"]},
                        },
                        {
                            "choice_key": "destroy_and_disappear",
                            "label": "Destroy the files and disappear anyway",
                            "description": "Take the pre-sale credits already transferred and burn the evidence before any delivery.",
                            "outcome": "The files burn. The credits from the pre-sale do not. Rylos becomes a name passed in whispers — someone who knows things and cannot be found. The Force hums quietly in his chest like a secret he hasn't told anyone.",
                            "next_scene_key": "END",
                            "effects": {"credits_delta": 30, "light_delta": 1, "independent_delta": 1, "set_flags": ["ending_ghost_broker"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_final_null_contact",
                    "title": "The Null Contact",
                    "prompt": "Directorate Null reaches out within minutes of the files burning. They know exactly what Rylos did. Their message is brief: they respect it. A face-to-face contact is offered — not a threat, not a recruitment pitch, but a conversation the Empire would never allow. They offer a choice the Empire never would: the truth about what the files contained, and what it means.",
                    "choices": [
                        {
                            "choice_key": "join_null_openly",
                            "label": "Join Directorate Null openly",
                            "description": "Accept their offer and step across the line into their network.",
                            "outcome": "Directorate Null welcomes him. Their cause is cold and rational and possibly right. Rylos trades one uniform for another — this one has no insignia.",
                            "next_scene_key": "END",
                            "effects": {"independent_delta": 2, "dark_delta": 1, "set_flags": ["ending_the_convert"]},
                        },
                        {
                            "choice_key": "pretend_join_double_agent",
                            "label": "Pretend to join as a double agent",
                            "description": "Say yes while keeping your true allegiance to yourself.",
                            "outcome": "He says yes. He means no. The deep game begins, and Rylos is now running an operation inside an operation, Force-sensitive and pretending not to be, trusted by people he intends to destroy.",
                            "next_scene_key": "END",
                            "effects": {"dark_delta": 2, "independent_delta": 1, "set_flags": ["ending_the_infiltrator"]},
                        },
                        {
                            "choice_key": "reject_all_vanish",
                            "label": "Reject everyone and vanish alone",
                            "description": "Walk away from every offer and disappear into the galaxy's margins.",
                            "outcome": "No masters. No network. No name. The Force woke up in him and he walked away from everyone who would use it. Somewhere in the galaxy's margins, Rylos Cesti does not exist — and that is exactly the point.",
                            "next_scene_key": "END",
                            "effects": {"light_delta": 2, "independent_delta": 2, "set_flags": ["ending_silent_wanderer"]},
                        },
                    ],
                },
                {
                    "scene_key": f"{prefix}_burned_cover",
                    "title": "Burned",
                    "prompt": f"The annex operation unravels completely. Warden {rival} has Rylos's real name. Security footage has circulated to three Imperial departments. Every safe house on Dromund Kaas is flagged. The mission is not a failure — it is a catastrophe. Rylos runs with nothing but the clothes on his back and the strange pressure behind his eyes that he still cannot explain. The Empire is hunting him. Directorate Null is watching. And somewhere very far away, a masked enforcer in black armor has heard that a Force-sensitive ghost walked through the annex — and survived.",
                    "choices": [],
                    "forced_ending_key": "burned_cover",
                },
            ],
        }
