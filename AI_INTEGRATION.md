# AI Integration

## What the AI should generate

The backend should use AI for three things only:

1. campaign arc generation
2. episode plan generation
3. scene narration and resolution text

The backend should not let the AI directly mutate game state.

## Current implementation

The generation entrypoints are in [src/a_new_dawn/ai.py](C:\Users\upsid\documents\projects\star wars\src\a_new_dawn\ai.py:1):

- `generate_campaign_arc(...)`
- `generate_episode_plan(...)`
- `narrate_scene(...)`
- `narrate_resolution(...)`

The orchestration is in [src/a_new_dawn/engine.py](C:\Users\upsid\documents\projects\star wars\src\a_new_dawn\engine.py:1).

## Storage model

### Campaign creation

When a new campaign is created:

- `campaigns.story_arc` stores the generated campaign arc
- `episode_plans.plan_json` stores each generated episode structure
- `player_state.last_recap` stores the opening crawl text

### Scene rendering

When the player requests the current scene:

- the backend loads `episode_plans.plan_json`
- the AI turns the structured scene template into narration
- the narration is written to `scene_history`
- the active scene instance is tracked in `scene_instances`

### Choice resolution

When the player selects a choice:

- deterministic effects update `player_state`
- flags are written to `story_flags`
- items are written to `inventory_items`
- faction changes are written to `faction_reputation`
- relationship changes are written to `relationships`
- the selected option is written to `choice_history`
- the consequence text is written to `scene_history`

## Required environment variables

Put these in `.env`:

```env
SUPABASE_DB_URL=postgresql+psycopg://...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4.1-mini
```

## How to make the AI better

The current prompts are intentionally compact. Improve them by:

- adding explicit JSON schemas to the prompt
- adding allowed era/canon character catalogs
- adding inventory/faction/class-specific guardrails
- adding retry logic when the model returns invalid JSON
- caching generated episode plans so retries do not duplicate content

## Recommended production flow

### Campaign generation

1. User creates campaign.
2. Backend writes a pending campaign row.
3. Backend generates arc and episode plans.
4. Backend stores the plans.
5. Backend marks episode 1 available.

### Scene generation

1. Backend finds the current scene template.
2. Backend sends only relevant state to the model.
3. Backend stores narration output separately from world state.

### Choice resolution

1. Backend validates the selected choice key against the stored plan.
2. Backend applies deterministic effects locally.
3. Backend generates consequence flavor text.
4. Backend advances the campaign pointer.

## What to replace before production

- Replace `X-User-Id` trust with Supabase JWT verification.
- Add idempotency keys for choice submissions.
- Add AI output validation before writing to the database.
- Add rate limiting around campaign generation.
