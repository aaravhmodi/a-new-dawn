from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from a_new_dawn.models import (
    Campaign,
    ChoiceHistory,
    EpisodePlan,
    FactionReputation,
    InventoryItem,
    PlayerState,
    Relationship,
    RelationshipKind,
    SceneHistory,
    SceneInstance,
    SceneStatus,
    StoryFlag,
)


def get_campaign(db: Session, campaign_id: UUID, user_id: UUID) -> Campaign | None:
    stmt = select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user_id)
    return db.scalar(stmt)


def get_player_state(db: Session, campaign_id: UUID) -> PlayerState | None:
    return db.get(PlayerState, campaign_id)


def get_episode_plan(db: Session, campaign_id: UUID, episode_number: int) -> EpisodePlan | None:
    stmt = select(EpisodePlan).where(
        EpisodePlan.campaign_id == campaign_id,
        EpisodePlan.episode_number == episode_number,
    )
    return db.scalar(stmt)


def get_scene_instance(db: Session, campaign_id: UUID, episode_number: int, scene_key: str) -> SceneInstance | None:
    stmt = select(SceneInstance).where(
        SceneInstance.campaign_id == campaign_id,
        SceneInstance.episode_number == episode_number,
        SceneInstance.scene_key == scene_key,
    )
    return db.scalar(stmt)


def create_scene_instance(db: Session, campaign_id: UUID, episode_number: int, scene_key: str, scene_index: int, prompt_context: dict) -> SceneInstance:
    instance = SceneInstance(
        campaign_id=campaign_id,
        episode_number=episode_number,
        scene_key=scene_key,
        scene_index=scene_index,
        prompt_context=prompt_context,
    )
    db.add(instance)
    return instance


def add_scene_history(
    db: Session,
    *,
    campaign_id: UUID,
    episode_number: int,
    scene_key: str,
    narration_text: str,
    selected_choice_key: str | None = None,
    consequence_text: str | None = None,
    llm_metadata: dict | None = None,
) -> SceneHistory:
    row = SceneHistory(
        campaign_id=campaign_id,
        episode_number=episode_number,
        scene_key=scene_key,
        narration_text=narration_text,
        selected_choice_key=selected_choice_key,
        consequence_text=consequence_text,
        llm_metadata=llm_metadata or {},
    )
    db.add(row)
    return row


def add_choice_history(db: Session, *, campaign_id: UUID, episode_number: int, scene_key: str, choice_key: str, choice_label: str, effects_json: dict) -> ChoiceHistory:
    row = ChoiceHistory(
        campaign_id=campaign_id,
        episode_number=episode_number,
        scene_key=scene_key,
        choice_key=choice_key,
        choice_label=choice_label,
        effects_json=effects_json,
    )
    db.add(row)
    return row


def upsert_inventory_item(db: Session, *, campaign_id: UUID, item_key: str, item_name: str) -> InventoryItem:
    stmt = select(InventoryItem).where(InventoryItem.campaign_id == campaign_id, InventoryItem.item_key == item_key)
    item = db.scalar(stmt)
    if item:
        item.quantity += 1
        return item

    item = InventoryItem(campaign_id=campaign_id, item_key=item_key, item_name=item_name)
    db.add(item)
    return item


def upsert_story_flag(db: Session, *, campaign_id: UUID, flag_key: str, episode_number: int) -> StoryFlag:
    stmt = select(StoryFlag).where(StoryFlag.campaign_id == campaign_id, StoryFlag.flag_key == flag_key)
    row = db.scalar(stmt)
    if row:
        row.flag_value = True
        row.source_episode = episode_number
        return row

    row = StoryFlag(campaign_id=campaign_id, flag_key=flag_key, flag_value=True, source_episode=episode_number)
    db.add(row)
    return row


def upsert_faction_reputation(db: Session, *, campaign_id: UUID, faction_key: str, delta: int) -> FactionReputation:
    stmt = select(FactionReputation).where(
        FactionReputation.campaign_id == campaign_id,
        FactionReputation.faction_key == faction_key,
    )
    row = db.scalar(stmt)
    if row:
        row.score += delta
        return row

    row = FactionReputation(campaign_id=campaign_id, faction_key=faction_key, score=delta)
    db.add(row)
    return row


def upsert_relationship(db: Session, *, campaign_id: UUID, character_key: str, delta: int) -> Relationship:
    stmt = select(Relationship).where(
        Relationship.campaign_id == campaign_id,
        Relationship.character_key == character_key,
    )
    row = db.scalar(stmt)
    if row:
        row.score += delta
        return row

    row = Relationship(
        campaign_id=campaign_id,
        character_key=character_key,
        display_name=character_key.replace("_", " ").title(),
        relationship_type=RelationshipKind.ally,
        score=delta,
    )
    db.add(row)
    return row


def mark_scene_rendered(instance: SceneInstance) -> None:
    instance.status = SceneStatus.rendered


def mark_scene_resolved(instance: SceneInstance, resolution_json: dict) -> None:
    instance.status = SceneStatus.resolved
    instance.resolution_json = resolution_json
