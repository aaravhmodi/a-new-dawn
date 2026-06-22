# STAR WARS: A NEW DAWN

This repo now contains a working scaffold for a choice-driven CLI RPG with:

- a FastAPI backend
- a Typer CLI client
- SQLAlchemy models mapped to the Supabase schema
- an AI generation layer for campaign arcs, episode plans, and scene narration
- persistence into Supabase Postgres
- verified Supabase JWT auth in the FastAPI layer
- seed catalogs for eras, classes, items, factions, and canon cameo rules

## Quick Start

1. Create a Supabase project.
2. Run the SQL migrations in order:
   - [20260621112500_initial_schema.sql](C:\Users\upsid\documents\projects\star wars\supabase\migrations\20260621112500_initial_schema.sql)
   - [20260621120500_seed_content.sql](C:\Users\upsid\documents\projects\star wars\supabase\migrations\20260621120500_seed_content.sql)
3. Copy `.env.example` to `.env` and fill in your keys.
   `SUPABASE_DB_URL` is still required and was left blank because it was not provided.
4. Install dependencies:

```bash
pip install -e .
```

5. Start the API:

```bash
a-new-dawn-api
```

6. In another terminal, sign up a user and start a campaign:

```bash
a-new-dawn signup --email you@example.com --password "your-password" --handle aarav
a-new-dawn new-campaign --player-class smuggler --era galactic_civil_war --planet corellia
```

## Architecture

- The backend writes game state to Supabase Postgres.
- Supabase Auth creates `auth.users`; the trigger in the migration creates `public.profiles`.
- The CLI stores a local session file with `user_id` and Supabase access token.
- AI generation happens on the backend through the OpenAI API.
- AI generation can also run through `modelrelay` or Ollama using the same OpenAI-compatible client shape.
- AI generation can also run through native Ollama or Gemini HTTP endpoints with no OpenAI compatibility layer.
- Episode plans are stored in `episode_plans.plan_json`.
- Rendered scenes and resolved choices are stored in `scene_history` and `choice_history`.

## Current Security Model

- Supabase Auth is used for signup/login.
- The CLI stores the Supabase access token locally in `.local/a-new-dawn-session.json`.
- The CLI sends `Authorization: Bearer <token>` to the backend.
- The backend validates the JWT against the Supabase JWKS endpoint and checks issuer/audience.

This is suitable for a serious prototype. For production, add token refresh handling and stricter request logging/rate limiting.

## AI Generation Flow

### New campaign

The backend:

1. creates a campaign row
2. creates base `player_state`
3. generates a campaign arc
4. generates 9 episode plans
5. stores each plan in `episode_plans`
6. creates the first scene instance

### Each turn

The backend:

1. loads the current campaign and active episode plan
2. determines the active scene
3. asks the AI for scene narration if needed
4. returns numbered choices to the CLI
5. on choice submit, applies deterministic effects
6. persists state changes and scene history
7. advances to the next scene

## Where To Extend

- Replace the simple engine with richer combat and relationship logic.
- Add item catalogs and cameo catalogs as seed tables.
- Add caching for AI-generated narration.
