-- STAR WARS: A NEW DAWN
-- Seed catalogs for eras, classes, factions, items, and canon cameo rules.

create table if not exists public.era_catalog (
  era_key text primary key,
  display_name text not null,
  description text not null
);

create table if not exists public.class_catalog (
  class_key text primary key,
  display_name text not null,
  description text not null,
  starting_health integer not null,
  starting_credits integer not null,
  starting_inventory jsonb not null default '[]'::jsonb
);

create table if not exists public.faction_catalog (
  faction_key text primary key,
  display_name text not null,
  description text not null,
  alignment_hint text
);

create table if not exists public.item_catalog (
  item_key text primary key,
  display_name text not null,
  item_kind public.item_kind not null,
  description text not null,
  rarity text not null default 'common',
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists public.canon_character_catalog (
  character_key text primary key,
  display_name text not null,
  rarity text not null,
  era_tags text[] not null default '{}',
  allowed_roles text[] not null default '{}',
  max_appearances integer not null default 1,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists public.cameo_rule_catalog (
  cameo_rule_key text primary key,
  character_key text not null references public.canon_character_catalog (character_key) on delete cascade,
  era_key text not null references public.era_catalog (era_key) on delete cascade,
  player_class_key text,
  min_light_score integer,
  max_dark_score integer,
  required_flags text[] not null default '{}',
  forbidden_flags text[] not null default '{}',
  notes text
);

insert into public.era_catalog (era_key, display_name, description) values
  ('galactic_civil_war', 'Galactic Civil War', 'The Empire dominates the galaxy while rebel cells gather strength.'),
  ('early_empire', 'Early Empire', 'The Republic has fallen and Imperial power is still consolidating.'),
  ('new_republic', 'New Republic', 'Imperial remnants, warlords, and independent factions fight over the future.')
on conflict (era_key) do update
set display_name = excluded.display_name,
    description = excluded.description;

insert into public.class_catalog (class_key, display_name, description, starting_health, starting_credits, starting_inventory) values
  ('smuggler', 'Smuggler', 'Fast-talking operators who survive on nerve, timing, and underworld connections.', 100, 150, '[{"item_key":"holdout_blaster","item_name":"Holdout Blaster"},{"item_key":"credit_chip","item_name":"Credit Chip"}]'::jsonb),
  ('jedi', 'Jedi Exile', 'Force-sensitive survivors balancing secrecy, discipline, and temptation.', 110, 80, '[{"item_key":"training_saber_hilt","item_name":"Training Saber Hilt"},{"item_key":"jedi_text_fragment","item_name":"Jedi Text Fragment"}]'::jsonb),
  ('bounty_hunter', 'Bounty Hunter', 'Trackers and mercenaries who rely on hardware, leverage, and intimidation.', 120, 120, '[{"item_key":"carbine_rifle","item_name":"Carbine Rifle"},{"item_key":"target_puck","item_name":"Targeting Puck"}]'::jsonb)
on conflict (class_key) do update
set display_name = excluded.display_name,
    description = excluded.description,
    starting_health = excluded.starting_health,
    starting_credits = excluded.starting_credits,
    starting_inventory = excluded.starting_inventory;

insert into public.faction_catalog (faction_key, display_name, description, alignment_hint) values
  ('outer_rim_rebels', 'Outer Rim Rebels', 'Scattered rebel cells trading supplies and intelligence beyond the Core.', 'light'),
  ('imperial_security_bureau', 'Imperial Security Bureau', 'The surveillance arm of the Empire focused on internal control.', 'dark'),
  ('smugglers_guild', 'Smugglers Guild', 'Independent operators loyal mostly to profit and survival.', 'independent'),
  ('hutt_cartel', 'Hutt Cartel', 'Criminal power brokers who turn wars into market opportunities.', 'dark')
on conflict (faction_key) do update
set display_name = excluded.display_name,
    description = excluded.description,
    alignment_hint = excluded.alignment_hint;

insert into public.item_catalog (item_key, display_name, item_kind, description, rarity, metadata) values
  ('holdout_blaster', 'Holdout Blaster', 'weapon', 'A compact blaster built for concealment and quick draws.', 'common', '{"damage": 1}'::jsonb),
  ('credit_chip', 'Credit Chip', 'currency', 'A small reserve of liquid funds hidden in an encoded chip.', 'common', '{}'::jsonb),
  ('training_saber_hilt', 'Training Saber Hilt', 'artifact', 'A damaged saber hilt tied to a forgotten Jedi past.', 'rare', '{"force_attuned": true}'::jsonb),
  ('jedi_text_fragment', 'Jedi Text Fragment', 'quest', 'A partial manuscript with warnings about an ancient holocron.', 'rare', '{}'::jsonb),
  ('carbine_rifle', 'Carbine Rifle', 'weapon', 'A durable rifle favored by bounty hunters in crowded ports.', 'common', '{"damage": 2}'::jsonb),
  ('target_puck', 'Targeting Puck', 'gear', 'A compact tracking puck keyed to one encrypted signature.', 'common', '{}'::jsonb),
  ('imperial_code_cylinder', 'Imperial Code Cylinder', 'quest', 'A stolen Imperial credential usable on secured terminals.', 'rare', '{}'::jsonb),
  ('stolen_data_chit', 'Stolen Data Chit', 'quest', 'Encrypted relay data ripped from an Imperial cache.', 'uncommon', '{}'::jsonb),
  ('coded_badge', 'Coded Badge', 'gear', 'A field badge carrying access tags for an enforcement detachment.', 'uncommon', '{}'::jsonb)
on conflict (item_key) do update
set display_name = excluded.display_name,
    item_kind = excluded.item_kind,
    description = excluded.description,
    rarity = excluded.rarity,
    metadata = excluded.metadata;

insert into public.canon_character_catalog (character_key, display_name, rarity, era_tags, allowed_roles, max_appearances, metadata) values
  ('obi_wan_kenobi', 'Obi-Wan Kenobi', 'legendary', '{"early_empire"}', '{"hologram","mentor_echo"}', 1, '{"alignment":"light"}'::jsonb),
  ('lando_calrissian', 'Lando Calrissian', 'rare', '{"galactic_civil_war","new_republic"}', '{"cantina_contact","smuggler_ally"}', 1, '{"alignment":"independent"}'::jsonb),
  ('hera_syndulla', 'Hera Syndulla', 'rare', '{"galactic_civil_war","new_republic"}', '{"brief_intervention","mission_brief"}', 1, '{"alignment":"light"}'::jsonb),
  ('cad_bane', 'Cad Bane', 'rare', '{"early_empire"}', '{"rival_presence","hunter_competition"}', 1, '{"alignment":"dark"}'::jsonb),
  ('bo_katan_kryze', 'Bo-Katan Kryze', 'rare', '{"new_republic"}', '{"brief_intervention","faction_contact"}', 1, '{"alignment":"independent"}'::jsonb),
  ('hondo_ohnaka', 'Hondo Ohnaka', 'common', '{"early_empire","galactic_civil_war","new_republic"}', '{"comic_relief","smuggler_contact","side_deal"}', 2, '{"alignment":"independent"}'::jsonb)
on conflict (character_key) do update
set display_name = excluded.display_name,
    rarity = excluded.rarity,
    era_tags = excluded.era_tags,
    allowed_roles = excluded.allowed_roles,
    max_appearances = excluded.max_appearances,
    metadata = excluded.metadata;

insert into public.cameo_rule_catalog (cameo_rule_key, character_key, era_key, player_class_key, min_light_score, max_dark_score, required_flags, forbidden_flags, notes) values
  ('obi_wan_mentor', 'obi_wan_kenobi', 'early_empire', 'jedi', 25, 30, '{"found_jedi_signal"}', '{}', 'Use only for a Force-aligned archive or memory sequence.'),
  ('lando_smuggler_meet', 'lando_calrissian', 'galactic_civil_war', 'smuggler', null, null, '{}', '{"angered_hutts"}', 'Best used in a high-stakes underworld negotiation scene.'),
  ('hera_rebel_brief', 'hera_syndulla', 'galactic_civil_war', null, 10, null, '{"found_rebel_transponder"}', '{}', 'Use for a rebel contact or mission handoff.'),
  ('hondo_side_deal', 'hondo_ohnaka', 'galactic_civil_war', null, null, null, '{}', '{}', 'Flexible comedic cameo tied to side deals or escapes.'),
  ('bo_katan_contact', 'bo_katan_kryze', 'new_republic', 'bounty_hunter', null, null, '{"tracked_imperial_remnant"}', '{}', 'Useful for remnant-era tactical encounters.')
on conflict (cameo_rule_key) do update
set character_key = excluded.character_key,
    era_key = excluded.era_key,
    player_class_key = excluded.player_class_key,
    min_light_score = excluded.min_light_score,
    max_dark_score = excluded.max_dark_score,
    required_flags = excluded.required_flags,
    forbidden_flags = excluded.forbidden_flags,
    notes = excluded.notes;
