```
     A long time ago in a galaxy far, far away....


  .d8888. d888888b  .d8b.  d8888b.      db   d8b   db  .d8b.  d8888b. .d8888.
  88'  YP `~~88~~' d8' `8b 88  `8D      88   I8I   88 d8' `8b 88  `8D 88'  YP
  `8bo.      88    88ooo88 88oobY'      88   I8I   88 88ooo88 88oobY' `8bo.
    `Y8b.    88    88~~~88 88`8b        Y8   I8I   88 88~~~88 88`8b     `Y8b.
  db   8D    88    88   88 88 `88.      `8b d8'8b d8' 88   88 88 `88. db   8D
  `8888Y'    YP    YP   YP 88   YD       `8b8' `8d8'  YP   YP 88   YD `8888Y'


           .d8b.       d8b   db d88888b db   d8b   db
          d8' `8b      888o  88 88'     88   I8I   88
          88ooo88      88V8o 88 88ooooo 88   I8I   88
          88~~~88      88 V8o88 88~~~~~ Y8   I8I   88
          88   88      88  V888 88.     `8b d8'8b d8'
          YP   YP      VP   V8P Y88888P  `8b8' `8d8'


                           d8888b.  .d8b.  db   d8b   db d8b   db
                           88  `8D d8' `8b 88   I8I   88 888o  88
                           88   88 88ooo88 88   I8I   88 88V8o 88
                           88   88 88~~~88 Y8   I8I   88 88 V8o88
                           88  .8D 88   88 `8b d8'8b d8' 88  V888
                           Y8888D' YP   YP  `8b8' `8d8'  VP   V8P
```

---

A choice-driven CLI RPG set in the Star Wars universe. You play as Rylos Cesti — a Force-sensitive operative working undercover for Imperial Intelligence on Dromund Kaas — navigating covert missions, moral compromises, and a growing power you cannot explain.

## Quick Start

```bash
# 1. Install
pip install -e .

# 2. Start the API (in one terminal)
a-new-dawn-api

# 3. Sign up and start a campaign (in another terminal)
a-new-dawn signup you@example.com "your-password" yourname
a-new-dawn new-campaign
```

Then read the scene, pick a number, press Enter.

## How To Play

- Run `a-new-dawn-api` to start the backend
- Run `a-new-dawn login` to authenticate
- Run `a-new-dawn new-campaign` to begin
- Read the scene, pick a numbered choice, press Enter
- Run `a-new-dawn guide` for a reminder of available commands

The game is choice-driven — no freeform input. Every decision affects your stats (HP, Credits, Light, Dark, Independent) and shapes which scenes you reach.

## Setup

1. Create a [Supabase](https://supabase.com) project
2. Run the SQL migrations in order from `supabase/migrations/`
3. Copy `.env.example` to `.env` and fill in your keys
4. Run `pip install -e .`

Required env vars: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`

## Stack

| Layer | Tech |
|---|---|
| Backend API | Python, FastAPI |
| CLI | Typer, Rich |
| Auth | Supabase Auth (JWT) |
| Database | Supabase (Postgres) |
| AI | OpenAI API — scene narration and campaign generation |
| Hosting | AWS EC2 |
| Packaging | PyPI (`pip install a-new-dawn`) |

Supabase handles auth and all game state (campaigns, episode plans, scene history, choice history). The FastAPI backend runs on EC2 and validates Supabase JWTs on every request. AI narrates scene resolutions and flavour text; the branching story structure itself is deterministic.
