from __future__ import annotations

import random
from uuid import UUID

from sqlalchemy.orm import Session

from a_new_dawn.ai import AIService
from a_new_dawn.models import Campaign, CampaignStatus, EpisodePlan, EpisodeStatus, PlayerState
from a_new_dawn.repository import (
    add_choice_history,
    add_scene_history,
    create_scene_instance,
    get_campaign,
    get_episode_plan,
    get_player_state,
    get_scene_instance,
    mark_scene_rendered,
    mark_scene_resolved,
    upsert_faction_reputation,
    upsert_inventory_item,
    upsert_relationship,
    upsert_story_flag,
)
from a_new_dawn.schemas import CampaignCreateRequest, CampaignSummary, ChoiceOption, ChoiceResult, SceneResponse


class GameEngine:
    def __init__(self) -> None:
        self.ai = AIService()

    def create_campaign(self, db: Session, *, user_id: UUID, request: CampaignCreateRequest) -> CampaignSummary:
        seed = random.randint(100_000, 999_999)
        arc = self.ai.generate_campaign_arc(
            player_class=request.player_class.value,
            era=request.era,
            planet=request.planet,
            seed=seed,
        )

        campaign = Campaign(
            user_id=user_id,
            title="STAR WARS: A NEW DAWN",
            campaign_seed=seed,
            player_class=request.player_class,
            era_key=request.era,
            starting_planet_key=request.planet,
            main_villain_key=arc["main_villain_key"],
            central_objective_key=arc["central_objective_key"],
            faction_anchor_key=arc.get("faction_anchor_key"),
            current_episode=1,
            current_scene_key=None,
            status=CampaignStatus.active,
            story_arc=arc,
        )
        db.add(campaign)
        db.flush()

        state = PlayerState(
            campaign_id=campaign.id,
            health=100,
            max_health=100,
            credits=150,
            light_score=0,
            dark_score=0,
            independent_score=0,
            current_planet_key=request.planet,
            last_recap=arc.get("opening_crawl"),
        )
        db.add(state)

        for episode_number in range(1, 10):
            plan = self.ai.generate_episode_plan(
                campaign_arc=arc,
                episode_number=episode_number,
                player_class=request.player_class.value,
            )
            episode = EpisodePlan(
                campaign_id=campaign.id,
                episode_number=episode_number,
                title=plan["title"],
                theme=plan.get("theme"),
                status=EpisodeStatus.available if episode_number == 1 else EpisodeStatus.locked,
                plan_json=plan,
                summary_json={"summary": plan.get("summary", "")},
            )
            db.add(episode)

        db.commit()
        return CampaignSummary(
            campaign_id=campaign.id,
            title=campaign.title,
            player_class=campaign.player_class.value,
            current_episode=campaign.current_episode,
            current_scene_key=campaign.current_scene_key,
            story_arc=campaign.story_arc,
        )

    def get_current_scene(self, db: Session, *, campaign_id: UUID, user_id: UUID) -> SceneResponse:
        campaign = self._require_campaign(db, campaign_id, user_id)
        state = self._require_player_state(db, campaign_id)
        episode = self._require_episode_plan(db, campaign_id, campaign.current_episode)
        scene = self._resolve_scene_from_plan(episode.plan_json, campaign.current_scene_key)

        instance = get_scene_instance(db, campaign_id, campaign.current_episode, scene["scene_key"])
        if instance is None:
            instance = create_scene_instance(
                db,
                campaign_id=campaign_id,
                episode_number=campaign.current_episode,
                scene_key=scene["scene_key"],
                scene_index=self._scene_index(episode.plan_json, scene["scene_key"]),
                prompt_context={"episode_title": episode.title, "scene_title": scene["title"]},
            )

        narration = self.ai.narrate_scene(
            opening_crawl=campaign.story_arc.get("opening_crawl", ""),
            campaign_arc=campaign.story_arc,
            scene=scene,
            stats=self._stats_dict(state),
        )

        mark_scene_rendered(instance)
        campaign.current_scene_key = scene["scene_key"]
        add_scene_history(
            db,
            campaign_id=campaign_id,
            episode_number=campaign.current_episode,
            scene_key=scene["scene_key"],
            narration_text=narration["narration"],
            llm_metadata={"title": narration["title"]},
        )
        db.commit()

        return SceneResponse(
            campaign_id=campaign.id,
            episode_number=campaign.current_episode,
            scene_key=scene["scene_key"],
            title=narration["title"],
            narration=narration["narration"],
            choices=[
                ChoiceOption(
                    choice_key=choice["choice_key"],
                    label=choice["label"],
                    description=choice.get("description"),
                )
                for choice in scene["choices"]
            ],
            stats=self._stats_dict(state),
        )

    def choose(self, db: Session, *, campaign_id: UUID, user_id: UUID, choice_key: str) -> ChoiceResult:
        campaign = self._require_campaign(db, campaign_id, user_id)
        state = self._require_player_state(db, campaign_id)
        episode = self._require_episode_plan(db, campaign_id, campaign.current_episode)
        scene = self._resolve_scene_from_plan(episode.plan_json, campaign.current_scene_key)
        choice = next((item for item in scene["choices"] if item["choice_key"] == choice_key), None)
        if choice is None:
            raise ValueError(f"Choice '{choice_key}' is not valid for scene '{scene['scene_key']}'.")

        effects = choice.get("effects", {})
        self._apply_effects(db, state=state, campaign_id=campaign_id, episode_number=campaign.current_episode, effects=effects)

        resolution_text = self.ai.narrate_resolution(
            scene_title=scene["title"],
            choice_label=choice["label"],
            outcome=choice.get("outcome", ""),
        )

        instance = get_scene_instance(db, campaign_id, campaign.current_episode, scene["scene_key"])
        if instance is not None:
            mark_scene_resolved(instance, {"choice_key": choice_key, "outcome": resolution_text})

        add_choice_history(
            db,
            campaign_id=campaign_id,
            episode_number=campaign.current_episode,
            scene_key=scene["scene_key"],
            choice_key=choice["choice_key"],
            choice_label=choice["label"],
            effects_json=effects,
        )
        add_scene_history(
            db,
            campaign_id=campaign_id,
            episode_number=campaign.current_episode,
            scene_key=scene["scene_key"],
            narration_text=scene["prompt"],
            selected_choice_key=choice["choice_key"],
            consequence_text=resolution_text,
        )

        next_scene_key = choice["next_scene_key"]
        if next_scene_key == "END":
            episode.status = EpisodeStatus.completed
            if campaign.current_episode < 9:
                campaign.current_episode += 1
                campaign.current_scene_key = None
                next_episode = self._require_episode_plan(db, campaign_id, campaign.current_episode)
                next_episode.status = EpisodeStatus.available
                db.commit()
                next_scene = self.get_current_scene(db, campaign_id=campaign_id, user_id=user_id)
            else:
                campaign.status = CampaignStatus.completed
                campaign.current_scene_key = None
                db.commit()
                next_scene = None
        else:
            campaign.current_scene_key = next_scene_key
            db.commit()
            next_scene = self.get_current_scene(db, campaign_id=campaign_id, user_id=user_id)

        return ChoiceResult(resolution_text=resolution_text, next_scene=next_scene)

    def _apply_effects(self, db: Session, *, state: PlayerState, campaign_id: UUID, episode_number: int, effects: dict) -> None:
        state.credits = max(0, state.credits + effects.get("credits_delta", 0))
        state.health = max(0, min(state.max_health, state.health + effects.get("health_delta", 0)))
        state.light_score += effects.get("light_delta", 0)
        state.dark_score += effects.get("dark_delta", 0)
        state.independent_score += effects.get("independent_delta", 0)

        for item in effects.get("add_items", []):
            upsert_inventory_item(
                db,
                campaign_id=campaign_id,
                item_key=item["item_key"],
                item_name=item["item_name"],
            )

        for flag_key in effects.get("set_flags", []):
            upsert_story_flag(db, campaign_id=campaign_id, flag_key=flag_key, episode_number=episode_number)

        for faction_key, delta in effects.get("faction_deltas", {}).items():
            upsert_faction_reputation(db, campaign_id=campaign_id, faction_key=faction_key, delta=delta)

        for character_key, delta in effects.get("relationship_deltas", {}).items():
            upsert_relationship(db, campaign_id=campaign_id, character_key=character_key, delta=delta)


    def _require_campaign(self, db: Session, campaign_id: UUID, user_id: UUID) -> Campaign:
        campaign = get_campaign(db, campaign_id, user_id)
        if campaign is None:
            raise ValueError("Campaign not found for this user.")
        return campaign

    def _require_player_state(self, db: Session, campaign_id: UUID) -> PlayerState:
        state = get_player_state(db, campaign_id)
        if state is None:
            raise ValueError("Player state not found.")
        return state

    def _require_episode_plan(self, db: Session, campaign_id: UUID, episode_number: int) -> EpisodePlan:
        episode = get_episode_plan(db, campaign_id, episode_number)
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

    def _stats_dict(self, state: PlayerState) -> dict[str, int]:
        return {
            "health": state.health,
            "max_health": state.max_health,
            "credits": state.credits,
            "light_score": state.light_score,
            "dark_score": state.dark_score,
            "independent_score": state.independent_score,
        }
