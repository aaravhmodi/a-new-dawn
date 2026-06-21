-- STAR WARS: A NEW DAWN
-- Initial Supabase schema for a choice-driven single-player RPG.

create extension if not exists pgcrypto;

create type public.player_class as enum ('smuggler', 'jedi', 'bounty_hunter');
create type public.campaign_status as enum ('active', 'completed', 'abandoned');
create type public.episode_status as enum ('locked', 'available', 'in_progress', 'completed');
create type public.scene_status as enum ('pending', 'rendered', 'resolved');
create type public.relationship_kind as enum ('ally', 'rival', 'canon', 'faction');
create type public.item_kind as enum ('weapon', 'gear', 'artifact', 'quest', 'consumable', 'currency');

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, handle)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'handle', split_part(new.email, '@', 1))
  )
  on conflict (id) do nothing;

  return new;
end;
$$;

create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  handle text not null unique,
  display_name text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  check (char_length(handle) between 3 and 32)
);

create table if not exists public.campaigns (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  title text not null default 'STAR WARS: A NEW DAWN',
  campaign_seed bigint not null,
  player_class public.player_class not null,
  era_key text not null,
  starting_planet_key text not null,
  main_villain_key text not null,
  central_objective_key text not null,
  faction_anchor_key text,
  current_episode smallint not null default 1,
  current_scene_key text,
  status public.campaign_status not null default 'active',
  story_arc jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  check (current_episode between 1 and 9)
);

create table if not exists public.player_state (
  campaign_id uuid primary key references public.campaigns (id) on delete cascade,
  health integer not null default 100,
  max_health integer not null default 100,
  credits integer not null default 0,
  light_score integer not null default 0,
  dark_score integer not null default 0,
  independent_score integer not null default 0,
  current_planet_key text,
  last_recap text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  check (health >= 0),
  check (max_health > 0),
  check (credits >= 0)
);

create table if not exists public.episode_plans (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.campaigns (id) on delete cascade,
  episode_number smallint not null,
  title text not null,
  theme text,
  status public.episode_status not null default 'locked',
  plan_json jsonb not null,
  summary_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (campaign_id, episode_number),
  check (episode_number between 1 and 9)
);

create table if not exists public.scene_instances (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.campaigns (id) on delete cascade,
  episode_number smallint not null,
  scene_key text not null,
  status public.scene_status not null default 'pending',
  scene_index smallint not null,
  prompt_context jsonb not null default '{}'::jsonb,
  resolution_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (campaign_id, episode_number, scene_key),
  check (episode_number between 1 and 9),
  check (scene_index >= 1)
);

create table if not exists public.scene_history (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.campaigns (id) on delete cascade,
  episode_number smallint not null,
  scene_key text not null,
  narration_text text not null,
  selected_choice_key text,
  consequence_text text,
  llm_metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  check (episode_number between 1 and 9)
);

create table if not exists public.inventory_items (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.campaigns (id) on delete cascade,
  item_key text not null,
  item_name text not null,
  kind public.item_kind not null default 'gear',
  quantity integer not null default 1,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (campaign_id, item_key),
  check (quantity >= 0)
);

create table if not exists public.story_flags (
  campaign_id uuid not null references public.campaigns (id) on delete cascade,
  flag_key text not null,
  flag_value jsonb not null default 'true'::jsonb,
  source_episode smallint,
  updated_at timestamptz not null default timezone('utc', now()),
  primary key (campaign_id, flag_key),
  check (source_episode is null or source_episode between 1 and 9)
);

create table if not exists public.relationships (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.campaigns (id) on delete cascade,
  character_key text not null,
  display_name text not null,
  relationship_type public.relationship_kind not null,
  score integer not null default 0,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (campaign_id, character_key)
);

create table if not exists public.faction_reputation (
  campaign_id uuid not null references public.campaigns (id) on delete cascade,
  faction_key text not null,
  score integer not null default 0,
  updated_at timestamptz not null default timezone('utc', now()),
  primary key (campaign_id, faction_key)
);

create table if not exists public.choice_history (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.campaigns (id) on delete cascade,
  episode_number smallint not null,
  scene_key text not null,
  choice_key text not null,
  choice_label text not null,
  effects_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now()),
  check (episode_number between 1 and 9)
);

create table if not exists public.canon_cameo_log (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.campaigns (id) on delete cascade,
  character_key text not null,
  episode_number smallint not null,
  role_key text not null,
  created_at timestamptz not null default timezone('utc', now()),
  check (episode_number between 1 and 9)
);

create index if not exists campaigns_user_id_idx on public.campaigns (user_id);
create index if not exists campaigns_status_idx on public.campaigns (status);
create index if not exists episode_plans_campaign_episode_idx on public.episode_plans (campaign_id, episode_number);
create index if not exists scene_instances_campaign_episode_idx on public.scene_instances (campaign_id, episode_number);
create index if not exists scene_history_campaign_created_idx on public.scene_history (campaign_id, created_at desc);
create index if not exists choice_history_campaign_created_idx on public.choice_history (campaign_id, created_at desc);
create index if not exists inventory_items_campaign_idx on public.inventory_items (campaign_id);
create index if not exists relationships_campaign_idx on public.relationships (campaign_id);
create index if not exists story_flags_campaign_idx on public.story_flags (campaign_id);

create trigger set_profiles_updated_at
before update on public.profiles
for each row
execute function public.set_updated_at();

create trigger set_campaigns_updated_at
before update on public.campaigns
for each row
execute function public.set_updated_at();

create trigger set_player_state_updated_at
before update on public.player_state
for each row
execute function public.set_updated_at();

create trigger set_episode_plans_updated_at
before update on public.episode_plans
for each row
execute function public.set_updated_at();

create trigger set_scene_instances_updated_at
before update on public.scene_instances
for each row
execute function public.set_updated_at();

create trigger set_inventory_items_updated_at
before update on public.inventory_items
for each row
execute function public.set_updated_at();

create trigger set_relationships_updated_at
before update on public.relationships
for each row
execute function public.set_updated_at();

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row
execute function public.handle_new_user();

alter table public.profiles enable row level security;
alter table public.campaigns enable row level security;
alter table public.player_state enable row level security;
alter table public.episode_plans enable row level security;
alter table public.scene_instances enable row level security;
alter table public.scene_history enable row level security;
alter table public.inventory_items enable row level security;
alter table public.story_flags enable row level security;
alter table public.relationships enable row level security;
alter table public.faction_reputation enable row level security;
alter table public.choice_history enable row level security;
alter table public.canon_cameo_log enable row level security;

create policy "profiles_select_own"
on public.profiles
for select
using (auth.uid() = id);

create policy "profiles_update_own"
on public.profiles
for update
using (auth.uid() = id)
with check (auth.uid() = id);

create policy "profiles_insert_own"
on public.profiles
for insert
with check (auth.uid() = id);

create policy "campaigns_own_all"
on public.campaigns
for all
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "player_state_own_all"
on public.player_state
for all
using (
  exists (
    select 1
    from public.campaigns c
    where c.id = player_state.campaign_id
      and c.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from public.campaigns c
    where c.id = player_state.campaign_id
      and c.user_id = auth.uid()
  )
);

create policy "episode_plans_own_all"
on public.episode_plans
for all
using (
  exists (
    select 1
    from public.campaigns c
    where c.id = episode_plans.campaign_id
      and c.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from public.campaigns c
    where c.id = episode_plans.campaign_id
      and c.user_id = auth.uid()
  )
);

create policy "scene_instances_own_all"
on public.scene_instances
for all
using (
  exists (
    select 1
    from public.campaigns c
    where c.id = scene_instances.campaign_id
      and c.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from public.campaigns c
    where c.id = scene_instances.campaign_id
      and c.user_id = auth.uid()
  )
);

create policy "scene_history_own_all"
on public.scene_history
for all
using (
  exists (
    select 1
    from public.campaigns c
    where c.id = scene_history.campaign_id
      and c.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from public.campaigns c
    where c.id = scene_history.campaign_id
      and c.user_id = auth.uid()
  )
);

create policy "inventory_items_own_all"
on public.inventory_items
for all
using (
  exists (
    select 1
    from public.campaigns c
    where c.id = inventory_items.campaign_id
      and c.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from public.campaigns c
    where c.id = inventory_items.campaign_id
      and c.user_id = auth.uid()
  )
);

create policy "story_flags_own_all"
on public.story_flags
for all
using (
  exists (
    select 1
    from public.campaigns c
    where c.id = story_flags.campaign_id
      and c.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from public.campaigns c
    where c.id = story_flags.campaign_id
      and c.user_id = auth.uid()
  )
);

create policy "relationships_own_all"
on public.relationships
for all
using (
  exists (
    select 1
    from public.campaigns c
    where c.id = relationships.campaign_id
      and c.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from public.campaigns c
    where c.id = relationships.campaign_id
      and c.user_id = auth.uid()
  )
);

create policy "faction_reputation_own_all"
on public.faction_reputation
for all
using (
  exists (
    select 1
    from public.campaigns c
    where c.id = faction_reputation.campaign_id
      and c.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from public.campaigns c
    where c.id = faction_reputation.campaign_id
      and c.user_id = auth.uid()
  )
);

create policy "choice_history_own_all"
on public.choice_history
for all
using (
  exists (
    select 1
    from public.campaigns c
    where c.id = choice_history.campaign_id
      and c.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from public.campaigns c
    where c.id = choice_history.campaign_id
      and c.user_id = auth.uid()
  )
);

create policy "canon_cameo_log_own_all"
on public.canon_cameo_log
for all
using (
  exists (
    select 1
    from public.campaigns c
    where c.id = canon_cameo_log.campaign_id
      and c.user_id = auth.uid()
  )
)
with check (
  exists (
    select 1
    from public.campaigns c
    where c.id = canon_cameo_log.campaign_id
      and c.user_id = auth.uid()
  )
);
