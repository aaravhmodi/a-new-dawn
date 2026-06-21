from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PlayerClass(str, enum.Enum):
    smuggler = "smuggler"
    jedi = "jedi"
    bounty_hunter = "bounty_hunter"


class CampaignStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    abandoned = "abandoned"


class EpisodeStatus(str, enum.Enum):
    locked = "locked"
    available = "available"
    in_progress = "in_progress"
    completed = "completed"


class SceneStatus(str, enum.Enum):
    pending = "pending"
    rendered = "rendered"
    resolved = "resolved"


class RelationshipKind(str, enum.Enum):
    ally = "ally"
    rival = "rival"
    canon = "canon"
    faction = "faction"


class ItemKind(str, enum.Enum):
    weapon = "weapon"
    gear = "gear"
    artifact = "artifact"
    quest = "quest"
    consumable = "consumable"
    currency = "currency"


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    handle: Mapped[str] = mapped_column(Text, unique=True)
    display_name: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(Text, default="STAR WARS: A NEW DAWN")
    campaign_seed: Mapped[int] = mapped_column()
    player_class: Mapped[PlayerClass] = mapped_column(Enum(PlayerClass, name="player_class"))
    era_key: Mapped[str] = mapped_column(Text)
    starting_planet_key: Mapped[str] = mapped_column(Text)
    main_villain_key: Mapped[str] = mapped_column(Text)
    central_objective_key: Mapped[str] = mapped_column(Text)
    faction_anchor_key: Mapped[str | None] = mapped_column(Text)
    current_episode: Mapped[int] = mapped_column(Integer, default=1)
    current_scene_key: Mapped[str | None] = mapped_column(Text)
    status: Mapped[CampaignStatus] = mapped_column(Enum(CampaignStatus, name="campaign_status"), default=CampaignStatus.active)
    story_arc: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlayerState(Base):
    __tablename__ = "player_state"

    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True)
    health: Mapped[int] = mapped_column(Integer, default=100)
    max_health: Mapped[int] = mapped_column(Integer, default=100)
    credits: Mapped[int] = mapped_column(Integer, default=0)
    light_score: Mapped[int] = mapped_column(Integer, default=0)
    dark_score: Mapped[int] = mapped_column(Integer, default=0)
    independent_score: Mapped[int] = mapped_column(Integer, default=0)
    current_planet_key: Mapped[str | None] = mapped_column(Text)
    last_recap: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EpisodePlan(Base):
    __tablename__ = "episode_plans"
    __table_args__ = (UniqueConstraint("campaign_id", "episode_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"))
    episode_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text)
    theme: Mapped[str | None] = mapped_column(Text)
    status: Mapped[EpisodeStatus] = mapped_column(Enum(EpisodeStatus, name="episode_status"), default=EpisodeStatus.locked)
    plan_json: Mapped[dict] = mapped_column(JSONB)
    summary_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SceneInstance(Base):
    __tablename__ = "scene_instances"
    __table_args__ = (UniqueConstraint("campaign_id", "episode_number", "scene_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"))
    episode_number: Mapped[int] = mapped_column(Integer)
    scene_key: Mapped[str] = mapped_column(Text)
    status: Mapped[SceneStatus] = mapped_column(Enum(SceneStatus, name="scene_status"), default=SceneStatus.pending)
    scene_index: Mapped[int] = mapped_column(Integer)
    prompt_context: Mapped[dict] = mapped_column(JSONB, default=dict)
    resolution_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SceneHistory(Base):
    __tablename__ = "scene_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"))
    episode_number: Mapped[int] = mapped_column(Integer)
    scene_key: Mapped[str] = mapped_column(Text)
    narration_text: Mapped[str] = mapped_column(Text)
    selected_choice_key: Mapped[str | None] = mapped_column(Text)
    consequence_text: Mapped[str | None] = mapped_column(Text)
    llm_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (UniqueConstraint("campaign_id", "item_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"))
    item_key: Mapped[str] = mapped_column(Text)
    item_name: Mapped[str] = mapped_column(Text)
    kind: Mapped[ItemKind] = mapped_column(Enum(ItemKind, name="item_kind"), default=ItemKind.gear)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StoryFlag(Base):
    __tablename__ = "story_flags"

    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True)
    flag_key: Mapped[str] = mapped_column(Text, primary_key=True)
    flag_value: Mapped[object] = mapped_column(JSONB, default=True)
    source_episode: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Relationship(Base):
    __tablename__ = "relationships"
    __table_args__ = (UniqueConstraint("campaign_id", "character_key"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"))
    character_key: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(Text)
    relationship_type: Mapped[RelationshipKind] = mapped_column(Enum(RelationshipKind, name="relationship_kind"))
    score: Mapped[int] = mapped_column(Integer, default=0)
    metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FactionReputation(Base):
    __tablename__ = "faction_reputation"

    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True)
    faction_key: Mapped[str] = mapped_column(Text, primary_key=True)
    score: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChoiceHistory(Base):
    __tablename__ = "choice_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"))
    episode_number: Mapped[int] = mapped_column(Integer)
    scene_key: Mapped[str] = mapped_column(Text)
    choice_key: Mapped[str] = mapped_column(Text)
    choice_label: Mapped[str] = mapped_column(Text)
    effects_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CanonCameoLog(Base):
    __tablename__ = "canon_cameo_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"))
    character_key: Mapped[str] = mapped_column(Text)
    episode_number: Mapped[int] = mapped_column(Integer)
    role_key: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
