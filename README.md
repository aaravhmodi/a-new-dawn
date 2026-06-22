# STAR WARS: A NEW DAWN

This repo now contains a working scaffold for a choice-driven CLI RPG with:

- a FastAPI backend
- a Typer CLI client
- an AI generation layer for campaign arcs, episode plans, and scene narration
- persistence through Supabase Auth + REST APIs
- verified Supabase JWT auth in the FastAPI layer
- seed catalogs for eras, classes, items, factions, and canon cameo rules
- a single ship-ready Episode I prototype with a special action set piece

## Quick Start

1. Create a Supabase project.
2. Run the SQL migrations in order:
   - [20260621112500_initial_schema.sql](C:\Users\upsid\documents\projects\star wars\supabase\migrations\20260621112500_initial_schema.sql)
   - [20260621120500_seed_content.sql](C:\Users\upsid\documents\projects\star wars\supabase\migrations\20260621120500_seed_content.sql)
3. Copy `.env.example` to `.env` and fill in your keys.
   For runtime, you only need `SUPABASE_URL`, a publishable key, and a server-side secret/service-role key.
   `SUPABASE_DB_URL` and `SUPABASE_DIRECT_URL` are optional and only useful if you want a separate migration toolchain.
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
a-new-dawn signup you@example.com "your-password" aarav
a-new-dawn new-campaign
```

## How To Play

If you only want the short version:

1. Run `a-new-dawn-api`
2. Run `a-new-dawn login`
3. Run `a-new-dawn new-campaign`
4. Read the scene
5. Type the number of the choice you want
6. Press Enter

If you want a reminder inside the CLI, run:

```bash
a-new-dawn guide
```

The game is designed to be choice-driven. You do not type freeform commands. You read the prompt, pick a number, and the story updates the stats and ending for you.

## Architecture

- The backend writes game state through Supabase REST endpoints.
- Supabase Auth creates `auth.users`; the trigger in the migration creates `public.profiles`.
- The CLI stores a local session file with `user_id` and Supabase access token.
- AI generation happens on the backend.
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
3. creates a fixed campaign arc for the one playable episode
4. stores Episode I in `episode_plans`
5. creates the first scene instance

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
- Expand into more episodes after Episode I is polished.
- Add item catalogs and cameo catalogs as seed tables.
- Add caching for AI-generated narration.
