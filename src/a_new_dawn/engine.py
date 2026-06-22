from __future__ import annotations

import random
from concurrent.futures import ThreadPoolExecutor
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
        arc = self.ai.basic_campaign_arc(
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

        plan = self.ai.basic_episode_plan(
            campaign_arc=arc,
            episode_number=1,
            player_class=request.player_class.value,
        )
        self.store.insert(
            "episode_plans",
            {
                "campaign_id": campaign["id"],
                "episode_number": 1,
                "title": plan["title"],
                "theme": plan.get("theme"),
                "status": "available",
                "plan_json": plan,
                "summary_json": {"summary": plan.get("summary", "")},
            },
        )

        return self._summary_from_campaign(campaign)

    def get_campaign_summary(self, *, campaign_id: UUID, user_id: UUID) -> CampaignSummary:
        campaign = self._require_campaign(campaign_id, user_id)
        return self._summary_from_campaign(campaign)

    def get_current_scene(self, *, campaign_id: UUID, user_id: UUID) -> SceneResponse:
        campaign = self._require_campaign(campaign_id, user_id)
        state = self._require_player_state(campaign_id)
        episode = self._require_episode_plan(campaign_id, campaign["current_episode"])
        current_scene_key = self._canonical_scene_key(campaign.get("current_scene_key"))
        scene = self._resolve_scene_from_plan(episode["plan_json"], current_scene_key)
        if current_scene_key and scene["scene_key"] != current_scene_key:
            self.store.update(
                "campaigns",
                filters={"id": campaign_id},
                payload={"current_scene_key": scene["scene_key"], "updated_at": self._utc_now()},
            )

        instance = self.store.select_one(
            "scene_instances",
            filters={
                "campaign_id": campaign_id,
                "episode_number": campaign["current_episode"],
                "scene_key": scene["scene_key"],
            },
        )
        if instance is None:
            resolution_json = {}
            if scene.get("set_piece"):
                resolution_json = {"action_state": {"beat": 1, "heat": 0, "cover": 2, "intel": 0}}
            instance = self.store.insert(
                "scene_instances",
                {
                    "campaign_id": str(campaign_id),
                    "episode_number": campaign["current_episode"],
                    "scene_key": scene["scene_key"],
                    "status": "pending",
                    "scene_index": self._scene_index(episode["plan_json"], scene["scene_key"]),
                    "prompt_context": {"episode_title": episode["title"], "scene_title": scene["title"]},
                    "resolution_json": resolution_json,
                },
            )

        scene_response = self._build_scene_response(campaign=campaign, state=state, scene=scene, instance=instance)

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
                "narration_text": scene_response.narration,
                "llm_metadata": {"title": scene_response.title},
            },
        )

        return scene_response

    def choose(self, *, campaign_id: UUID, user_id: UUID, choice_key: str) -> ChoiceResult:
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
        if scene.get("set_piece"):
            return self._choose_set_piece(
                campaign=campaign,
                state=state,
                episode=episode,
                scene=scene,
                instance=instance,
                user_id=user_id,
                campaign_id=campaign_id,
                choice_key=choice_key,
            )

        forced_ending_key = scene.get("forced_ending_key")
        if forced_ending_key:
            ending = self._ending_from_key(forced_ending_key)
            self._finalize_campaign(
                campaign=campaign,
                campaign_id=campaign_id,
                episode=episode,
                ending=ending,
            )
            return ChoiceResult(
                resolution_text=ending["ending_summary"],
                next_scene=None,
                ending_key=ending["ending_key"],
                ending_title=ending["ending_title"],
                ending_summary=ending["ending_summary"],
            )

        choice = next((item for item in scene["choices"] if item["choice_key"] == choice_key), None)
        if choice is None:
            raise ValueError(f"Choice '{choice_key}' is not valid for scene '{scene['scene_key']}'.")

        self._apply_effects(campaign_id=campaign_id, episode_number=campaign["current_episode"], state=state, effects=choice.get("effects", {}))

        next_scene_key = choice["next_scene_key"]
        is_ending = next_scene_key == "END"

        if not is_ending:
            next_scene_key = self._canonical_scene_key(next_scene_key)
            if not self._scene_key_exists(episode["plan_json"], next_scene_key):
                raise ValueError(
                    f"Choice '{choice_key}' points to missing scene '{next_scene_key}' in episode {campaign['current_episode']}."
                )
            self.store.update(
                "campaigns",
                filters={"id": campaign_id},
                payload={"current_scene_key": next_scene_key, "updated_at": self._utc_now()},
            )

        # Run AI narration and next-scene load concurrently to cut wait time in half.
        with ThreadPoolExecutor(max_workers=2) as pool:
            resolution_future = pool.submit(
                self.ai.narrate_resolution,
                scene_title=scene["title"],
                choice_label=choice["label"],
                outcome=choice.get("outcome", ""),
            )
            if is_ending:
                next_scene_future = None
            else:
                next_scene_future = pool.submit(
                    self.get_current_scene,
                    campaign_id=campaign_id,
                    user_id=user_id,
                )

        resolution_text = resolution_future.result()
        next_scene = next_scene_future.result() if next_scene_future else None

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

        if is_ending:
            ending = self._resolve_ending(
                campaign=campaign,
                state=state,
                final_choice=choice,
            )
            self._finalize_campaign(
                campaign=campaign,
                campaign_id=campaign_id,
                episode=episode,
                ending=ending,
            )
            next_scene = None

        return ChoiceResult(
            resolution_text=resolution_text,
            next_scene=next_scene,
            ending_key=ending["ending_key"] if is_ending else None,
            ending_title=ending["ending_title"] if is_ending else None,
            ending_summary=ending["ending_summary"] if is_ending else None,
        )

    def _choose_set_piece(
        self,
        *,
        campaign: dict,
        state: dict,
        episode: dict,
        scene: dict,
        instance: dict | None,
        user_id: UUID,
        campaign_id: UUID,
        choice_key: str,
    ) -> ChoiceResult:
        if instance is None:
            raise ValueError("Set piece state not initialized.")

        action_state = instance.get("resolution_json", {}).get("action_state", {"beat": 1, "heat": 0, "cover": 2, "intel": 0})
        beat_number = int(action_state.get("beat", 1))
        beats = scene["set_piece"]["beats"]
        beat = beats[beat_number - 1]
        choice = next((item for item in beat["choices"] if item["choice_key"] == choice_key), None)
        if choice is None:
            raise ValueError(f"Choice '{choice_key}' is not valid for set piece beat {beat_number}.")

        effects = choice.get("effects", {})
        action_state["heat"] = action_state.get("heat", 0) + effects.get("heat_delta", 0)
        action_state["cover"] = action_state.get("cover", 0) + effects.get("cover_delta", 0)
        action_state["intel"] = action_state.get("intel", 0) + effects.get("intel_delta", 0)

        gameplay_effects = {k: v for k, v in effects.items() if not k.endswith("_delta") or k in {"credits_delta", "health_delta", "light_delta", "dark_delta", "independent_delta"}}
        self._apply_effects(campaign_id=campaign_id, episode_number=campaign["current_episode"], state=state, effects=gameplay_effects)

        resolution_text = choice.get("outcome", "")
        next_scene: SceneResponse | None

        if beat_number < len(beats):
            action_state["beat"] = beat_number + 1
            self.store.update(
                "scene_instances",
                filters={"id": instance["id"]},
                payload={"resolution_json": {"action_state": action_state}},
            )
            refreshed_instance = self.store.select_one("scene_instances", filters={"id": instance["id"]})
            next_scene = self._build_scene_response(campaign=campaign, state=self._require_player_state(campaign_id), scene=scene, instance=refreshed_instance)
        else:
            resolution_text = f"{resolution_text}\n\n{self._resolve_set_piece_outcome(action_state)}"
            story_arc = dict(campaign.get("story_arc", {}))
            episode_state = dict(story_arc.get("episode_state", {}))
            episode_state["archive_lockdown"] = {
                "heat": action_state.get("heat", 0),
                "cover": action_state.get("cover", 0),
                "intel": action_state.get("intel", 0),
            }
            story_arc["episode_state"] = episode_state
            self.store.update(
                "scene_instances",
                filters={"id": instance["id"]},
                payload={"status": "resolved", "resolution_json": {"action_state": action_state, "choice_key": choice_key, "outcome": resolution_text}},
            )
            self.store.insert(
                "choice_history",
                {
                    "campaign_id": str(campaign_id),
                    "episode_number": campaign["current_episode"],
                    "scene_key": scene["scene_key"],
                    "choice_key": choice["choice_key"],
                    "choice_label": choice["label"],
                    "effects_json": effects,
                },
            )
            self.store.insert(
                "scene_history",
                {
                    "campaign_id": str(campaign_id),
                    "episode_number": campaign["current_episode"],
                    "scene_key": scene["scene_key"],
                    "narration_text": beat["prompt"],
                    "selected_choice_key": choice["choice_key"],
                    "consequence_text": resolution_text,
                    "llm_metadata": {"set_piece": True},
                },
            )
            bad_outcome_key = scene["set_piece"].get("bad_outcome_scene_key")
            if bad_outcome_key and (action_state.get("cover", 0) <= 0 or action_state.get("heat", 0) >= 5):
                next_scene_key = bad_outcome_key
            else:
                next_scene_key = scene["set_piece"]["next_scene_key"]
            if not self._scene_key_exists(episode["plan_json"], next_scene_key):
                raise ValueError(
                    f"Set piece on scene '{scene['scene_key']}' points to missing scene '{next_scene_key}'."
                )
            self.store.update(
                "campaigns",
                filters={"id": campaign_id},
                payload={"current_scene_key": next_scene_key, "story_arc": story_arc, "updated_at": self._utc_now()},
            )
            next_scene = self.get_current_scene(campaign_id=campaign_id, user_id=user_id)

        return ChoiceResult(resolution_text=resolution_text, next_scene=next_scene)

    def _finalize_campaign(self, *, campaign: dict, campaign_id: UUID, episode: dict, ending: dict[str, str]) -> None:
        story_arc = dict(campaign.get("story_arc", {}))
        story_arc["ending"] = ending
        self.store.update("episode_plans", filters={"id": episode["id"]}, payload={"status": "completed"})
        self.store.update(
            "campaigns",
            filters={"id": campaign_id},
            payload={
                "status": "completed",
                "current_scene_key": None,
                "story_arc": story_arc,
                "updated_at": self._utc_now(),
            },
        )

    def _resolve_ending(
        self,
        *,
        campaign: dict,
        state: dict,
        final_choice: dict,
    ) -> dict[str, str]:
        # Check story_flags for an ending_ flag set by the final choice
        campaign_id = UUID(campaign["id"])
        flags = self.store.select(
            "story_flags",
            filters={"campaign_id": campaign_id},
        )
        for flag in flags or []:
            flag_key = flag.get("flag_key", "")
            if flag_key.startswith("ending_"):
                ending_key = flag_key[len("ending_"):]
                return self._ending_from_key(ending_key)

        # Fallback: derive from final choice key and dominant path (legacy behaviour)
        final_choice_key = final_choice["choice_key"]
        dominant_path = self._dominant_path(state)

        if dominant_path == "light":
            if final_choice_key == "accept_deeper_mission":
                return self._ending_from_key("emperors_blade")
            if final_choice_key == "refuse_request_extraction":
                return self._ending_from_key("quiet_defector")
        if dominant_path == "dark":
            if final_choice_key == "pretend_join_double_agent":
                return self._ending_from_key("the_infiltrator")
        return self._ending_from_key("silent_wanderer")

    def _ending_from_key(self, ending_key: str) -> dict[str, str]:
        endings: dict[str, dict[str, str]] = {
            "burned_cover": {
                "ending_key": "burned_cover",
                "ending_title": "Burned",
                "ending_summary": "Rylos escapes barely alive but his identity is gone. Warden Karn has his real name. Every faction now knows a Force-sensitive ghost walked through the annex. He runs.",
            },
            "emperors_blade": {
                "ending_key": "emperors_blade",
                "ending_title": "The Emperor's Blade",
                "ending_summary": "The Empire gives Rylos rank, resources, and a leash. Vader knows he exists. Command calls it an asset. Rylos calls it a cage with better lighting.",
            },
            "quiet_defector": {
                "ending_key": "quiet_defector",
                "ending_title": "The Quiet Defector",
                "ending_summary": "Rylos takes the extraction, burns his handler file, and surfaces three weeks later on a backwater moon with a new name. The Force stays quiet — for now.",
            },
            "ghost_who_knew": {
                "ending_key": "ghost_who_knew",
                "ending_title": "The Ghost Who Knew",
                "ending_summary": "Watcher Nine's trust becomes the key that unlocks the door out. Rylos vanishes from Imperial records while holding information that could destroy careers. A shadow with a conscience.",
            },
            "paid_instrument": {
                "ending_key": "paid_instrument",
                "ending_title": "The Paid Instrument",
                "ending_summary": "The Empire pays well for confirmed intelligence. Rylos becomes a line item in a classified budget. He is useful, compensated, and never quite free.",
            },
            "the_believer": {
                "ending_key": "the_believer",
                "ending_title": "The Believer",
                "ending_summary": "Directorate Null's ideology is not without logic. Rylos sells them the files and stays to hear the argument. He does not fully agree. He is not sure he disagrees.",
            },
            "ghost_broker": {
                "ending_key": "ghost_broker",
                "ending_title": "The Ghost Broker",
                "ending_summary": "The files burn. The credits from the pre-sale do not. Rylos becomes a name passed in whispers — someone who knows things and cannot be found. The Force hums quietly in his chest like a secret he hasn't told anyone.",
            },
            "the_convert": {
                "ending_key": "the_convert",
                "ending_title": "The Convert",
                "ending_summary": "Directorate Null welcomes him. Their cause is cold and rational and possibly right. Rylos trades one uniform for another — this one has no insignia.",
            },
            "the_infiltrator": {
                "ending_key": "the_infiltrator",
                "ending_title": "The Infiltrator",
                "ending_summary": "He says yes. He means no. The deep game begins, and Rylos is now running an operation inside an operation, Force-sensitive and pretending not to be, trusted by people he intends to destroy.",
            },
            "silent_wanderer": {
                "ending_key": "silent_wanderer",
                "ending_title": "The Silent Wanderer",
                "ending_summary": "No masters. No network. No name. The Force woke up in him and he walked away from everyone who would use it. Somewhere in the galaxy's margins, Rylos Cesti does not exist — and that is exactly the point.",
            },
        }
        return endings.get(
            ending_key,
            {
                "ending_key": ending_key,
                "ending_title": ending_key.replace("_", " ").title(),
                "ending_summary": "The mission ends. Rylos disappears.",
            },
        )

    def _dominant_path(self, state: dict) -> str:
        light_score = int(state.get("light_score", 0))
        dark_score = int(state.get("dark_score", 0))
        independent_score = int(state.get("independent_score", 0))
        if light_score >= dark_score and light_score >= independent_score:
            return "light"
        if dark_score >= light_score and dark_score >= independent_score:
            return "dark"
        return "independent"

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
        episode = self._patch_plan_if_stale(episode, campaign_id)
        return episode

    def _patch_plan_if_stale(self, episode: dict, campaign_id: UUID) -> dict:
        plan = episode.get("plan_json", {})
        scenes = plan.get("scenes", [])
        patched = False
        for scene in scenes:
            if "_archive_lockdown" in scene.get("scene_key", "") and not scene.get("set_piece"):
                rival = plan.get("rival", "Warden Karn")
                next_key = scene["scene_key"].replace("_archive_lockdown", "_intercept")
                escape_key = scene["scene_key"].replace("_archive_lockdown", "_escape_fallout")
                burned_key = scene["scene_key"].replace("_archive_lockdown", "_burned_cover")
                scene["set_piece"] = {
                    "next_scene_key": escape_key,
                    "bad_outcome_scene_key": burned_key,
                    "beats": [
                        {
                            "title": "Beat 1: Entry",
                            "prompt": "Security fields hum over the archive threshold. Rylos has seconds to get inside before the next patrol sweep crosses the corridor.",
                            "choices": [
                                {"choice_key": "cut_power", "label": "Cut power to a side corridor", "description": "Create confusion and slip through during the flicker.", "outcome": "The lights die for a breath and the annex hesitates just long enough for Rylos to cross the threshold.", "effects": {"heat_delta": 1, "intel_delta": 1}},
                                {"choice_key": "use_code_cylinder", "label": "Use the code cylinder", "description": "Open the first lock under an authorized identity.", "outcome": "The cylinder authenticates the fake credentials and the first gate unlocks without alarm.", "effects": {"cover_delta": 1, "intel_delta": 1}},
                                {"choice_key": "maintenance_shaft", "label": "Follow a maintenance shaft", "description": "Bypass the formal entry entirely.", "outcome": "Rylos squeezes through the service channel, but the route leaves traces a trained investigator might notice.", "effects": {"cover_delta": -1}},
                            ],
                        },
                        {
                            "title": "Beat 2: Extraction",
                            "prompt": "Rows of sealed data cylinders glow inside the vault. Patrol routes converge on the annex while Rylos races to pull the right files.",
                            "choices": [
                                {"choice_key": "copy_everything", "label": "Copy everything quickly", "description": "Take as much as possible and sort it out later.", "outcome": "Data floods into the cylinder in a messy burst, but the system notices the strain immediately.", "effects": {"intel_delta": 2, "heat_delta": 2}},
                                {"choice_key": "critical_cluster", "label": "Take only the critical file cluster", "description": "Prioritize the cleanest, most important target.", "outcome": "Rylos extracts the most relevant archive chain before the deeper systems can fully react.", "effects": {"intel_delta": 1, "heat_delta": 1, "set_flags": ["black_codex_fragment_found"]}},
                                {"choice_key": "plant_false_trace", "label": "Plant a false trace before downloading", "description": "Protect the mission by misdirecting the investigation.", "outcome": "A false access trail begins pointing security toward a different breach team while the files transfer.", "effects": {"cover_delta": 1, "intel_delta": 1}},
                            ],
                        },
                        {
                            "title": "Beat 3: Escape",
                            "prompt": f"Red lockdown lights flood the annex. {rival}'s officers are closing fast. At the far end of the corridor, a helmeted bounty hunter appears through the smoke — Boba Fett, hired to retrieve the same data.",
                            "choices": [
                                {"choice_key": "fight_through_exit", "label": "Fight through the nearest exit", "description": "Push hard before security can tighten the kill box.", "outcome": "Rylos smashes through the first response line and forces open a narrow path into the rain while Boba Fett raises his weapon.", "effects": {"heat_delta": 1, "cover_delta": -1}},
                                {"choice_key": "machinery_collapse", "label": "Trigger a machinery collapse behind you", "description": "Delay pursuit by bringing part of the annex down.", "outcome": "A shower of sparks and steel crashes into the corridor, burying the pursuit team while the bounty hunter vanishes into the smoke.", "effects": {"heat_delta": -1, "dark_delta": 1}},
                                {"choice_key": "service_lift", "label": "Disappear into a service lift", "description": "Trust stealth over violence for the final escape.", "outcome": "Rylos slips into a grimy service lift and vanishes between levels while Boba Fett is forced to choose between the chase and the collapsing corridor.", "effects": {"cover_delta": 1}},
                            ],
                        },
                    ],
                }
                scene["choices"] = []
                patched = True
        if patched:
            self.store.update("episode_plans", filters={"id": episode["id"]}, payload={"plan_json": plan})
            episode = dict(episode)
            episode["plan_json"] = plan
        return episode

    def _create_episode_plan(self, *, campaign_id: UUID, episode_number: int, campaign_arc: dict, player_class: str) -> dict:
        plan = self.ai.basic_episode_plan(
            campaign_arc=campaign_arc,
            episode_number=episode_number,
            player_class=player_class,
        )
        return self.store.insert(
            "episode_plans",
            {
                "campaign_id": str(campaign_id),
                "episode_number": episode_number,
                "title": plan["title"],
                "theme": plan.get("theme"),
                "status": "locked",
                "plan_json": plan,
                "summary_json": {"summary": plan.get("summary", "")},
            },
        )

    def _resolve_scene_from_plan(self, plan: dict, current_scene_key: str | None) -> dict:
        scenes = plan["scenes"]
        if current_scene_key is None:
            return scenes[0]
        for scene in scenes:
            if scene["scene_key"] == current_scene_key:
                return scene
        return scenes[0]

    def _scene_key_exists(self, plan: dict, scene_key: str) -> bool:
        return any(scene["scene_key"] == scene_key for scene in plan["scenes"])

    def _canonical_scene_key(self, scene_key: str | None) -> str | None:
        if scene_key is None:
            return None
        if scene_key.endswith("_archive_entry"):
            return scene_key.replace("_archive_entry", "_archive_lockdown")
        if scene_key == "archive_entry":
            return "archive_lockdown"
        return scene_key

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

    def _build_scene_response(self, *, campaign: dict, state: dict, scene: dict, instance: dict) -> SceneResponse:
        if scene.get("set_piece"):
            action_state = instance.get("resolution_json", {}).get("action_state", {"beat": 1, "heat": 0, "cover": 2, "intel": 0})
            beat_number = int(action_state.get("beat", 1))
            beat = scene["set_piece"]["beats"][beat_number - 1]
            narration = beat["prompt"]
            title = scene["title"]
            choices = [
                ChoiceOption(choice_key=choice["choice_key"], label=choice["label"], description=choice.get("description"))
                for choice in beat["choices"]
            ]
            scene_state = {
                "mode": "set_piece",
                "beat_title": beat["title"],
                "heat": action_state.get("heat", 0),
                "cover": action_state.get("cover", 0),
                "intel": action_state.get("intel", 0),
            }
        else:
            rendered = self.ai.narrate_scene(
                opening_crawl=campaign["story_arc"].get("opening_crawl", ""),
                campaign_arc=campaign["story_arc"],
                scene=scene,
                stats=self._stats_dict(state),
            )
            title = rendered["title"]
            narration = rendered["narration"]
            choices = [
                ChoiceOption(choice_key=choice["choice_key"], label=choice["label"], description=choice.get("description"))
                for choice in scene["choices"]
            ]
            scene_state = None

        return SceneResponse(
            campaign_id=UUID(campaign["id"]),
            episode_number=campaign["current_episode"],
            scene_key=scene["scene_key"],
            title=title,
            narration=narration,
            choices=choices,
            stats=self._stats_dict(state),
            scene_state=scene_state,
        )

    def _resolve_set_piece_outcome(self, action_state: dict) -> str:
        heat = action_state.get("heat", 0)
        cover = action_state.get("cover", 0)
        intel = action_state.get("intel", 0)
        if intel >= 2 and heat <= 2:
            return "Rylos escapes the annex with strong evidence and a clean enough trail that Watcher Nine can still work from the shadows."
        if heat >= 5 or cover <= 0:
            return "Rylos gets out alive, but the operation turns messy. Security now knows a ghost moved through the annex, and Warden Karn will not let it go."
        return "Rylos escapes with usable evidence, but the annex is fully alerted. The mission is still alive, only now the hunters know they are being hunted."
