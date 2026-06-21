# STAR WARS: A NEW DAWN System Design

`STAR WARS: A NEW DAWN` is the working title for this CLI RPG.

## 1. Goal

Build a single-player Star Wars-inspired CLI RPG where:

- each player has a unique campaign
- gameplay is choice-only, never free-text
- each campaign contains 9 episodes
- each episode takes about 15 minutes
- canon side characters and cameos can appear in controlled ways
- the LLM writes narration, but the game engine owns truth

This should feel closer to KOTOR + Mass Effect choices + AI-generated narration than to a chatbot.

## 2. Product Principles

### Hard rules

- The player only selects numbered choices.
- The game engine controls state, rules, gating, rewards, and outcomes.
- The LLM does not invent facts that override engine state.
- Major episode beats are structured before play starts.
- Choices must reflect inventory, relationships, class, alignment, and prior decisions.

### Design targets

- 9 episodes per campaign
- 12 to 18 minutes per episode
- 5 to 8 meaningful choices per episode
- 3 to 4 options per choice point
- strong callbacks in episodes 4 to 9
- at most 1 to 3 canon cameos per campaign

## 3. High-Level Architecture

```text
+-------------+       HTTPS        +------------------+
| CLI Client  |  <-------------->  | API / Game Server|
+-------------+                    +------------------+
                                          |
                                          v
                                 +-------------------+
                                 | Story/Game Engine |
                                 +-------------------+
                                   |       |       |
                                   |       |       |
                                   v       v       v
                              +--------+ +------+ +----------------+
                              | Postgres| |Redis | | LLM Narration |
                              +--------+ +------+ +----------------+
```

### Responsibilities

#### CLI client

- login/register
- start campaign
- fetch current scene
- render narrative and choices
- submit numbered choice
- show inventory, stats, and episode progress

#### API / game server

- authentication
- campaign/session loading
- choice submission endpoint
- validation and authorization
- orchestration of engine + LLM

#### Story/game engine

- generates campaign seed and episode plan
- enforces world rules
- decides valid choices
- resolves consequences
- updates player state
- triggers callbacks and cameo eligibility

#### Postgres

- persistent source of truth
- players, campaigns, episodes, choices, flags, inventory, NPC relationships

#### Redis

- optional cache for active sessions
- recent scene state
- rate limiting
- short-lived LLM prompt cache

#### LLM layer

- writes scene narration
- writes flavor text for options
- writes debriefs and cliffhangers
- never directly mutates world state

## 4. Core Design Choice: Engine First, LLM Second

The deterministic engine is truth.

The LLM is presentation.

### Correct flow

1. Engine loads current campaign state.
2. Engine selects the current scene template and valid branches.
3. Engine computes which choices are available.
4. LLM receives structured state and writes the narrative.
5. Player selects one numbered option.
6. Engine resolves the selected outcome.
7. Engine persists state changes.
8. LLM writes the result and next transition.

### Wrong flow

Player input -> LLM decides what is true -> database tries to catch up.

That version becomes inconsistent and hard to test.

## 5. Gameplay Structure

## Campaign structure

Each campaign has:

- a class or archetype
- a seed-generated main conflict
- a primary villain
- a key artifact/objective
- 2 to 4 recurring allies
- 1 to 3 recurring rivals
- 9 episodes
- one final ending path chosen by state totals and flags

### Example campaign frame

```json
{
  "campaign_seed": 812738,
  "player_class": "smuggler",
  "era": "galactic_civil_war",
  "starting_planet": "Corellia",
  "main_villain": "Imperial Inquisitor Vael",
  "central_objective": "recover a lost holocron",
  "faction_anchor": "Smugglers Guild"
}
```

## Episode structure

Each of the 9 episodes should fit this pacing:

1. Intro hook
2. Scene choice 1
3. Escalation
4. Scene choice 2
5. Complication
6. Scene choice 3
7. Mini-climax
8. Final choice
9. Cliffhanger or resolution

### Runtime target

- 6 scenes per episode
- 4 major choice points minimum
- 1 ending scene
- average scene read time: 45 to 90 seconds
- average decision time: 20 to 45 seconds

That keeps each episode near 15 minutes without dragging.

## 6. Episode Generation Strategy

Do not generate scene-by-scene from scratch during play.

Generate the whole episode plan up front, then narrate it dynamically.

### Pre-generated per episode

- title
- theme
- key scenes
- possible choices
- gating conditions
- rewards
- callback opportunities
- possible cameo slots
- ending states

### Dynamic at runtime

- narration wording
- character dialogue tone
- scene descriptions
- recap text
- cliffhanger flavor

### Why

- better pacing
- lower cost
- easier testing
- less LLM drift
- stronger callbacks

## 7. Choice System

Players always choose from numbered options.

### Choice format

```json
{
  "choice_id": "ep3_scene2_opt4",
  "label": "Use Imperial Code Cylinder",
  "requires": {
    "inventory": ["imperial_code_cylinder"]
  },
  "effects": {
    "flags_set": ["used_code_cylinder_corellia"],
    "reputation": {"rebels": 1},
    "next_scene": "ep3_scene3_secure_archive"
  }
}
```

### Choice categories

- diplomatic
- aggressive
- stealth
- tech/inventory
- ally-assisted
- class-specific
- alignment-specific

### Choice count

Default per scene:

- 3 visible options minimum
- 4 options ideal
- 1 hidden unlock if state supports it

## 8. Player Progression Model

### Persistent state

```json
{
  "health": 82,
  "credits": 450,
  "alignment_light": 61,
  "alignment_dark": 24,
  "alignment_independent": 37,
  "inventory": ["blaster", "imperial_code_cylinder"],
  "flags": {
    "saved_mechanic": true,
    "angered_hutts": false,
    "joined_rebels": true
  },
  "relationships": {
    "kira_mechanic": 72,
    "captain_drex": 41
  }
}
```

### Important systems

- health
- credits
- inventory
- faction reputation
- ally relationships
- alignment axes
- permanent story flags

## 9. Canon Cameo System

Canon characters should appear rarely and intentionally.

They should feel like rewards, not random fan service.

### Rules

- cameos must fit the selected era
- legendary characters should appear at most once per campaign
- cameos should not replace the player as the main actor
- cameos should usually appear through holograms, brief encounters, side rescues, or advisory moments

### Cameo rarity tiers

- Common canon side character: 2 to 3 possible appearances
- Rare canon figure: 1 possible appearance
- Legendary icon: 0 or 1 appearance

### Cameo entry example

```json
{
  "character_id": "obi_wan_kenobi",
  "era_tags": ["fall_of_republic", "early_empire"],
  "rarity": "legendary",
  "max_appearances": 1,
  "allowed_roles": ["hologram", "mentor_echo", "brief_intervention"],
  "requirements": {
    "alignment_light_min": 40,
    "jedi_path": true
  }
}
```

### Good cameo patterns

- hologram in an old archive
- cantina encounter with a known side character
- passing aid during a chase
- side quest involving a canon smuggler, droid, senator, or bounty hunter

## 10. Callback System

Callbacks are what make choices feel meaningful.

### Example

Episode 1:

- player saves a mechanic
- flag set: `saved_mechanic = true`

Episode 6:

- mechanic provides a new route into a blockade
- hidden option unlocked

Episode 8:

- mechanic sacrifices their ship to help the player escape

### Callback categories

- ally returns
- rival returns
- item reuse
- planet revisit
- faction consequence
- moral consequence

### Rule

Every episode after episode 3 should attempt at least one callback from earlier state.

## 11. Data Model

## Main tables

### `users`

- `id`
- `email`
- `password_hash` or OAuth identity
- `created_at`

### `campaigns`

- `id`
- `user_id`
- `campaign_seed`
- `player_class`
- `era`
- `starting_planet`
- `main_villain`
- `current_episode`
- `current_scene`
- `status`

### `player_state`

- `campaign_id`
- `health`
- `credits`
- `light_score`
- `dark_score`
- `independent_score`

### `inventory_items`

- `id`
- `campaign_id`
- `item_key`
- `quantity`

### `story_flags`

- `campaign_id`
- `flag_key`
- `flag_value`

### `relationships`

- `campaign_id`
- `character_key`
- `relationship_score`

### `episodes`

- `id`
- `campaign_id`
- `episode_number`
- `title`
- `plan_json`
- `status`

### `scene_history`

- `id`
- `campaign_id`
- `episode_number`
- `scene_id`
- `narration_text`
- `selected_choice_id`
- `created_at`

## 12. API Design

## Core endpoints

### `POST /auth/register`

Create account.

### `POST /auth/login`

Return auth token.

### `POST /campaigns`

Create a new campaign from chosen class/era.

### `GET /campaigns/{id}`

Return summary, episode progress, and player stats.

### `GET /campaigns/{id}/current-scene`

Return:

- scene narration
- available choices
- episode number
- key visible stats

### `POST /campaigns/{id}/choose`

Request:

```json
{
  "choice_id": "ep2_scene3_opt2"
}
```

Response:

```json
{
  "resolution_text": "The guard studies the forged cylinder, then steps aside.",
  "updated_stats": {
    "credits": 320,
    "health": 82
  },
  "next_scene": {
    "scene_id": "ep2_scene4_archive_entry",
    "narration": "Cold blue light spills into the archive vault...",
    "choices": [
      {"id": "a", "label": "Search the central console"},
      {"id": "b", "label": "Scan for security drones"},
      {"id": "c", "label": "Call Kira for remote support"}
    ]
  }
}
```

## 13. Tech Stack Recommendation

## MVP stack

- CLI: Python + Typer + Rich
- API: FastAPI
- DB: PostgreSQL
- Cache: Redis
- ORM: SQLAlchemy or SQLModel
- Migrations: Alembic
- Background jobs: Celery, RQ, or FastAPI background tasks for simple cases
- LLM provider: OpenAI API
- Deployment: Docker + Render/Fly.io/AWS

### Why this stack

- Python is strong for CLI + backend + LLM integration
- Typer gives clean command UX
- Rich gives polished terminal rendering
- FastAPI is straightforward for API-first single-player sessions

## 14. CLI UX

## Commands

```bash
starwars-rpg login
starwars-rpg new-campaign
starwars-rpg play
starwars-rpg resume
starwars-rpg stats
starwars-rpg inventory
starwars-rpg history
```

## Example game loop

```text
Episode IV: Embers of Corellia
Scene 3 of 6

The corridor opens into an abandoned Imperial relay chamber. A damaged
console blinks weakly while distant bootsteps echo through the steel hall.

1. Search the relay console
2. Use Imperial Code Cylinder
3. Contact Kira for remote support
4. Retreat into the maintenance shaft

Choose: 2
```

## 15. LLM Usage Design

The LLM should work from structured prompts only.

### LLM input

- campaign summary
- current episode summary
- current scene template
- available choices with intent tags
- relevant inventory
- relationship context
- callback candidates
- selected tone

### LLM output

- concise scene narration
- distinct option labels or flavor text
- result narration after choice resolution
- episode recap

### Do not let the LLM

- invent new items unless engine approved them
- override locked/unlocked choices
- change stats directly
- add canon characters outside cameo rules
- skip required episode beats

## 16. Episode and Ending Logic

## Episode arcs

Suggested trilogy rhythm:

### Episodes 1 to 3

- setup trilogy
- establish hero, allies, villain, and initial objective

### Episodes 4 to 6

- escalation trilogy
- faction pressure, setbacks, betrayals, deeper lore

### Episodes 7 to 9

- resolution trilogy
- major callbacks, final alignment tests, ending path

## Ending selection

Endings should be chosen by state, not by one final binary choice.

### Example endings

- Hero of the Rebellion
- Independent Wanderer
- Smuggler King
- Jedi Master
- Sith Acolyte
- Hidden Relic Keeper

### Inputs into ending selection

- light score
- dark score
- independent score
- faction reputation
- villain outcome
- ally survival
- key artifact disposition

## 17. Non-Functional Requirements

### Performance

- current-scene fetch under 300 ms without LLM call
- choice resolution under 2.5 s average with cached prompt context
- campaign save on every choice

### Reliability

- idempotent choice submission
- recoverable session resume
- full scene history audit trail

### Cost control

- pre-generate episode plans
- use shorter narration outputs
- cache recap/context summaries
- avoid calling the LLM for trivial menu views

## 18. MVP Scope

Build this first:

### Included

- one era
- 3 player classes
- 1 full 9-episode campaign framework
- 20 to 30 reusable scene templates
- inventory and relationship systems
- 5 to 10 canon cameo entries
- 4 to 6 ending variants

### Excluded for MVP

- multiplayer
- free-text input
- combat grid tactics
- voice features
- procedural planet maps

## 19. Build Plan

### Phase 1: foundation

- scaffold CLI and FastAPI backend
- add auth
- create database schema
- create campaign creation flow

### Phase 2: engine

- implement deterministic state engine
- implement choice gating
- implement episode plan generator
- implement persistence and resume

### Phase 3: narrative

- add LLM narration adapter
- add prompt contracts
- add recap generation
- add guardrails for canon and inventory consistency

### Phase 4: content

- write class definitions
- write episode templates
- write item catalog
- write canon cameo catalog
- write ending evaluator

### Phase 5: polish

- Rich terminal UI
- history log
- better pacing
- retry/idempotency
- analytics on choice paths

## 20. Recommended First Slice

If you want the strongest first demo, build this:

- one class: Smuggler
- one era: Galactic Civil War
- episodes 1 to 3 only
- one recurring ally
- one recurring rival
- one rare canon cameo
- one complete ending for the prototype

That is enough to prove:

- the engine-first architecture works
- 15-minute episode pacing works
- choice gating works
- callbacks work
- canon cameos feel earned

## 21. Bottom Line

This project is feasible if you treat it as a structured narrative game, not an open-ended chatbot.

The winning architecture is:

- choice-only CLI
- deterministic game engine
- pre-generated episode plans
- LLM for narration only
- strict state persistence
- controlled canon cameo system

That gives you a game that is actually testable, scalable, replayable, and polished enough to stand out.
