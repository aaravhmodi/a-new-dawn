from __future__ import annotations

import random
from datetime import datetime, timezone
from uuid import UUID

from a_new_dawn.ai import AIService
from a_new_dawn.schemas import CampaignCreateRequest, CampaignSummary, ChoiceOption, ChoiceResult, SceneResponse
from a_new_dawn.supabase_store import SupabaseStore


class GameEngine:
    def __init__(self, store: SupabaseStore | None = None) -> None:
        self.ai = AIService()
        self.store = store or SupabaseStore()

    def create_campaign(self, *, user_id: UUID, request: CampaignCreateRequest) -> CampaignSummary:
        seed = random.randint(100_000, 999_999)
        arc = self.ai.generate_campaign_arc(
            player_class=request.player_class.value,
            era=request.era,
            planet=request.planet,
            seed=seed,
        )

        campaign = self.store.insert(
            "campaigns",
            {
                "user_id": str(user_id),
                "title": "STAR WARS: A NEW DAWN",
                "campaign_seed": seed,
                "player_class": request.player_class.value,
                "era_key": request.era,
                "starting_planet_key": request.planet,
                "main_villain_key": arc["main_villain_key"],
                "central_objective_key": arc["central_objective_key"],
                "faction_anchor_key": arc.get("faction_anchor_key"),
                "current_episode": 1,
                "current_scene_key": None,
                "status": "active",
                "story_arc": arc,
            },
        )

        self.store.insert(
            "player_state",
            {
                "campaign_id": campaign["id"],
                "health": 100,
                "max_health": 100,
                "credits": 150,
                "light_score": 0,
                "dark_score": 0,
                "independent_score": 0,
                "current_planet_key": request.planet,
                "last_recap": arc.get("opening_crawl"),
            },
        )

        episodes = []
        for episode_number in range(1, 10):
            plan = self.ai.generate_episode_plan(
                campaign_arc=arc,
                episode_number=episode_number,
                player_class=request.player_class.value,
            )
            episodes.append(
                {
                    "campaign_id": campaign["id"],
                    "episode_number": episode_number,
                    "title": plan["title"],
                    "theme": plan.get("theme"),
                    "status": "available" if episode_number == 1 else "locked",
                    "plan_json": plan,
                    "summary_json": {"summary": plan.get("summary", "")},
                }
            )
        self.store.bulk_insert("episode_plans", episodes)

        return self._summary_from_campaign(campaign)

    def get_campaign_summary(self, *, campaign_id: UUID, user_id: UUID) -> CampaignSummary:
        campaign = self._require_campaign(campaign_id, user_id)
        return self._summary_from_campaign(campaign)

    def get_current_scene(self, *, campaign_id: UUID, user_id: UUID) -> SceneResponse:
        campaign = self._require_campaign(campaign_id, user_id)
        state = self._require_player_state(campaign_id)
        episode = self._require_episode_plan(campaign_id, campaign["current_episode"])
        scene = self._resolve_scene_from_plan(episode["plan_json"], campaign.get("current_scene_key"))

        instance = self.store.select_one(
            "scene_instances",
            filters={
                "campaign_id": campaign_id,
                "episode_number": campaign["current_episode"],
                "scene_key": scene["scene_key"],
            },
        )
        if instance is None:
            instance = self.store.insert(
                "scene_instances",
                {
                    "campaign_id": str(campaign_id),
                    "episode_number": campaign["current_episode"],
                    "scene_key": scene["scene_key"],
                    "status": "pending",
                    "scene_index": self._scene_index(episode["plan_json"], scene["scene_key"]),
                    "prompt_context": {"episode_title": episode["title"], "scene_title": scene["title"]},
                    "resolution_json": {},
                },
            )

        narration = self.ai.narrate_scene(
            opening_crawl=campaign["story_arc"].get("opening_crawl", ""),
            campaign_arc=campaign["story_arc"],
            scene=scene,
            stats=self._stats_dict(state),
        )

        self.store.update(
            "scene_instances",
            filters={"id": instance["id"]},
            payload={"status": "rendered"},
        )
        self.store.update(
            "campaigns",
            filters={"id": campaign_id},
            payload={"current_scene_key": scene["scene_key"], "updated_at": self._utc_now()},
        )
        self.store.insert(
            "scene_history",
            {
                "campaign_id": str(campaign_id),
                "episode_number": campaign["current_episode"],
                "scene_key": scene["scene_key"],
                "narration_text": narration["narration"],
                "llm_metadata": {"title": narration["title"]},
            },
        )

        return SceneResponse(
            campaign_id=UUID(campaign["id"]),
            episode_number=campaign["current_episode"],
            scene_key=scene["scene_key"],
            title=narration["title"],
            narration=narration["narration"],
            choices=[
                ChoiceOption(choice_key=choice["choice_key"], label=choice["label"], description=choice.get("description"))
                for choice in scene["choices"]
            ],
            stats=self._stats_dict(state),
        )

    def choose(self, *, campaign_id: UUID, user_id: UUID, choice_key: str) -> ChoiceResult:
        campaign = self._require_campaign(campaign_id, user_id)
        state = self._require_player_state(campaign_id)
        episode = self._require_episode_plan(campaign_id, campaign["current_episode"])
        scene = self._resolve_scene_from_plan(episode["plan_json"], campaign.get("current_scene_key"))
        choice = next((item for item in scene["choices"] if item["choice_key"] == choice_key), None)
        if choice is None:
            raise ValueError(f"Choice '{choice_key}' is not valid for scene '{scene['scene_key']}'.")

        self._apply_effects(campaign_id=campaign_id, episode_number=campaign["current_episode"], state=state, effects=choice.get("effects", {}))

        resolution_text = self.ai.narrate_resolution(
            scene_title=scene["title"],
            choice_label=choice["label"],
            outcome=choice.get("outcome", ""),
        )

        instance = self.store.select_one(
            "scene_instances",
            filters={
                "campaign_id": campaign_id,
                "episode_number": campaign["current_episode"],
                "scene_key": scene["scene_key"],
            },
        )
        if instance:
            self.store.update(
                "scene_instances",
                filters={"id": instance["id"]},
                payload={"status": "resolved", "resolution_json": {"choice_key": choice_key, "outcome": resolution_text}},
            )

        self.store.insert(
            "choice_history",
            {
                "campaign_id": str(campaign_id),
                "episode_number": campaign["current_episode"],
                "scene_key": scene["scene_key"],
                "choice_key": choice["choice_key"],
                "choice_label": choice["label"],
                "effects_json": choice.get("effects", {}),
            },
        )
        self.store.insert(
            "scene_history",
            {
                "campaign_id": str(campaign_id),
                "episode_number": campaign["current_episode"],
                "scene_key": scene["scene_key"],
                "narration_text": scene["prompt"],
                "selected_choice_key": choice["choice_key"],
                "consequence_text": resolution_text,
                "llm_metadata": {},
            },
        )

        next_scene_key = choice["next_scene_key"]
        if next_scene_key == "END":
            self.store.update("episode_plans", filters={"id": episode["id"]}, payload={"status": "completed"})
            if campaign["current_episode"] < 9:
                next_episode_number = campaign["current_episode"] + 1
                next_episode = self._require_episode_plan(campaign_id, next_episode_number)
                self.store.update("episode_plans", filters={"id": next_episode["id"]}, payload={"status": "available"})
                self.store.update(
                    "campaigns",
                    filters={"id": campaign_id},
                    payload={"current_episode": next_episode_number, "current_scene_key": None, "updated_at": self._utc_now()},
                )
                next_scene = self.get_current_scene(campaign_id=campaign_id, user_id=user_id)
            else:
                self.store.update(
                    "campaigns",
                    filters={"id": campaign_id},
                    payload={"status": "completed", "current_scene_key": None, "updated_at": self._utc_now()},
                )
                next_scene = None
        else:
            self.store.update(
                "campaigns",
                filters={"id": campaign_id},
                payload={"current_scene_key": next_scene_key, "updated_at": self._utc_now()},
            )
            next_scene = self.get_current_scene(campaign_id=campaign_id, user_id=user_id)

        return ChoiceResult(resolution_text=resolution_text, next_scene=next_scene)

    def _apply_effects(self, *, campaign_id: UUID, episode_number: int, state: dict, effects: dict) -> None:
        updated_state = {
            "credits": max(0, state["credits"] + effects.get("credits_delta", 0)),
            "health": max(0, min(state["max_health"], state["health"] + effects.get("health_delta", 0))),
            "light_score": state["light_score"] + effects.get("light_delta", 0),
            "dark_score": state["dark_score"] + effects.get("dark_delta", 0),
            "independent_score": state["independent_score"] + effects.get("independent_delta", 0),
            "updated_at": self._utc_now(),
        }
        self.store.update("player_state", filters={"campaign_id": campaign_id}, payload=updated_state)

        for item in effects.get("add_items", []):
            existing = self.store.select_one("inventory_items", filters={"campaign_id": campaign_id, "item_key": item["item_key"]})
            if existing:
                self.store.update("inventory_items", filters={"id": existing["id"]}, payload={"quantity": existing["quantity"] + 1})
            else:
                self.store.insert(
                    "inventory_items",
                    {
                        "campaign_id": str(campaign_id),
                        "item_key": item["item_key"],
                        "item_name": item["item_name"],
                        "kind": "gear",
                        "quantity": 1,
                        "metadata": {},
                    },
                )

        for flag_key in effects.get("set_flags", []):
            self.store.upsert(
                "story_flags",
                payload={
                    "campaign_id": str(campaign_id),
                    "flag_key": flag_key,
                    "flag_value": True,
                    "source_episode": episode_number,
                    "updated_at": self._utc_now(),
                },
                on_conflict="campaign_id,flag_key",
            )

        for faction_key, delta in effects.get("faction_deltas", {}).items():
            existing = self.store.select_one("faction_reputation", filters={"campaign_id": campaign_id, "faction_key": faction_key})
            if existing:
                self.store.update("faction_reputation", filters={"campaign_id": campaign_id, "faction_key": faction_key}, payload={"score": existing["score"] + delta})
            else:
                self.store.insert("faction_reputation", {"campaign_id": str(campaign_id), "faction_key": faction_key, "score": delta})

        for character_key, delta in effects.get("relationship_deltas", {}).items():
            existing = self.store.select_one("relationships", filters={"campaign_id": campaign_id, "character_key": character_key})
            if existing:
                self.store.update("relationships", filters={"id": existing["id"]}, payload={"score": existing["score"] + delta})
            else:
                self.store.insert(
                    "relationships",
                    {
                        "campaign_id": str(campaign_id),
                        "character_key": character_key,
                        "display_name": character_key.replace("_", " ").title(),
                        "relationship_type": "ally",
                        "score": delta,
                        "metadata": {},
                    },
                )

    def _require_campaign(self, campaign_id: UUID, user_id: UUID) -> dict:
        campaign = self.store.select_one("campaigns", filters={"id": campaign_id, "user_id": user_id})
        if campaign is None:
            raise ValueError("Campaign not found for this user.")
        return campaign

    def _require_player_state(self, campaign_id: UUID) -> dict:
        state = self.store.select_one("player_state", filters={"campaign_id": campaign_id})
        if state is None:
            raise ValueError("Player state not found.")
        return state

    def _require_episode_plan(self, campaign_id: UUID, episode_number: int) -> dict:
        episode = self.store.select_one("episode_plans", filters={"campaign_id": campaign_id, "episode_number": episode_number})
        if episode is None:
            raise ValueError(f"Episode {episode_number} plan not found.")
        return episode

    def _resolve_scene_from_plan(self, plan: dict, current_scene_key: str | None) -> dict:
        scenes = plan["scenes"]
        if current_scene_key is None:
            return scenes[0]
        for scene in scenes:
            if scene["scene_key"] == current_scene_key:
                return scene
        return scenes[0]

    def _scene_index(self, plan: dict, scene_key: str) -> int:
        for index, scene in enumerate(plan["scenes"], start=1):
            if scene["scene_key"] == scene_key:
                return index
        return 1

    def _stats_dict(self, state: dict) -> dict[str, int]:
        return {
            "health": state["health"],
            "max_health": state["max_health"],
            "credits": state["credits"],
            "light_score": state["light_score"],
            "dark_score": state["dark_score"],
            "independent_score": state["independent_score"],
        }

    def _summary_from_campaign(self, campaign: dict) -> CampaignSummary:
        return CampaignSummary(
            campaign_id=UUID(campaign["id"]),
            title=campaign["title"],
            player_class=campaign["player_class"],
            current_episode=campaign["current_episode"],
            current_scene_key=campaign.get("current_scene_key"),
            story_arc=campaign["story_arc"],
        )

    def _utc_now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
