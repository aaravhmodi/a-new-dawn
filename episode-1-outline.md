# Episode I Outline

## Title

**Episode I: The False Name**

## Design Goals

This episode should:

- introduce Rylos Cesti clearly
- introduce the Empire's intelligence world in simple language
- establish the James Bond spy tone
- explain the core factions without assuming lore knowledge
- end with Rylos discovering he is Force-sensitive
- use mostly predetermined scenes and outcomes

AI should only be used for:

- phrasing scene narration
- polishing dialogue
- writing recap flavor

AI should not invent the structure of this episode.

## Episode Summary

Rylos Cesti, a covert field operative working for an Imperial intelligence branch, is sent to Dromund Kaas under a false identity. His mission is to trace a leak tied to a shadow network called Directorate Null, a hidden group that wants to break the power of both Sith and Jedi. To do that, he must enter a criminal social circle, secure stolen archive data, survive a lockdown, and decide what to do with the truth. At the end of the mission, under pressure and fear, he uses the Force for the first time without understanding how.

### Canon Cameos

This episode should include brief, purposeful encounters or presences from familiar canon characters:

- **Boba Fett** as the hired hunter who appears during the archive lockdown
- **Darth Vader** as the silent, terrifying Imperial power who receives the report at the end

These should support the story, not take it over.

## Plain-Language Setup

These concepts must be explained naturally:

- **The Empire**:
  A powerful authoritarian galactic government ruled through fear, military force, and political control.

- **Imperial Intelligence**:
  The Empire's spy service. They gather secrets, run covert missions, and eliminate threats before they become public.

- **Sith**:
  Dark-side rulers inside the Empire who use fear, anger, and supernatural power to control others.

- **Jedi**:
  A rival order of Force users, usually seen as protectors or guardians, though many in the Empire view them as enemies.

- **The Force**:
  A mysterious power that lets certain people sense, influence, or move things beyond normal human ability.

- **Directorate Null**:
  A secret network that believes both Sith and Jedi have poisoned the galaxy by dragging entire worlds into endless wars.

## Core Characters Introduced in Episode I

### Rylos Cesti

- player character
- field operative
- sharp, observant, composed under pressure
- does not yet know he is Force-sensitive

### Watcher Nine

- Rylos's handler
- calm voice in the earpiece
- senior intelligence coordinator
- explains the mission clearly and professionally

### Veska Tal

- undercover field observer
- practical and dangerous
- first ally Rylos can actually see on the ground

### Warden Karn

- security official
- suspicious, relentless, and ambitious
- visible human pressure inside the episode

### Directorate Null

- not a person yet, but a hidden organization
- should feel disciplined, ideological, and dangerous

## Three-Act Shape

### Act I: Escape

Prompts 1 to 3

Rylos arrives under false identity and must get through the first layer of danger.

### Act II: Infiltration

Prompts 4 to 7

Rylos enters the social and intelligence world beneath the capital and hunts the archive lead.

### Act III: Confrontation

Prompts 8 to 10

Rylos survives the fallout, learns what Directorate Null is trying to do, and awakens to the Force.

## 10-Prompt Episode Structure

## Prompt 1: Cold Open

### Title

**Rain Over Kaas**

### Purpose

- establish atmosphere immediately
- introduce Rylos and Watcher Nine
- start with pressure

### Scene

Rylos lands in a rain-soaked dock district on Dromund Kaas, the storm-wrapped capital world of the Sith-controlled Empire. Watcher Nine briefs him through a hidden comms channel: he is entering under a false identity to track a leak tied to an unknown sabotage network.

### Exposition Notes

Explain Dromund Kaas simply:

- capital of the Empire
- dark, industrial, heavily controlled

### Choices

1. Adopt the forged identity immediately.
2. Study the checkpoint first and look for weaknesses.
3. Follow Watcher Nine's instructions exactly.

### Branch Logic

- mostly flavor branch
- all roads lead to prompt 2
- effects:
  - option 1: gains `cover_confident`
  - option 2: gains `observant_entry`
  - option 3: gains `trusted_handler_start`

## Prompt 2: Mission Briefing

### Title

**The Assignment**

### Purpose

- explain the mission clearly
- define Imperial Intelligence
- define the target problem

### Scene

Watcher Nine explains that Imperial Intelligence believes someone inside state networks is feeding sensitive data into criminal channels. Rylos's job is to find the transfer point and identify the group behind it before the leak creates political damage.

### Exposition Notes

Explain Imperial Intelligence in one clean sentence:

- the Empire's covert spy service

### Choices

1. Ask who the buyer is.
2. Ask why normal security cannot handle it.
3. Ask what happens if he fails.

### Branch Logic

- dialogue branch only
- all roads lead to prompt 3
- choice determines which explanatory line the player sees

## Prompt 3: Entry Choice

### Title

**Checkpoint Blue**

### Purpose

- close Act I
- give first active choice with risk

### Scene

Rylos reaches the checkpoint controlling access to the lower district, where smugglers, brokers, and informants mix with state officials. Warden Karn's security teams are already increasing searches.

### Choices

1. Use the forged identity.
2. Bribe the checkpoint officer.
3. Slip through a maintenance access lane.

### Branch Logic

- option 1: safest social path
- option 2: costs credits, adds corruption tone
- option 3: more independent, slight risk tone
- all lead to prompt 4

## Prompt 4: Social Infiltration

### Title

**The Broken Cantina**

### Purpose

- begin Act II
- deliver Bond-style social infiltration
- introduce Veska Tal

### Scene

Rylos enters a lower-city cantina used by brokers, smugglers, and minor officials who prefer to trade in places where records disappear. His contact is late. Veska Tal is already in the room, watching from the shadows and pretending not to know him.

### Exposition Notes

Make it clear this is not just a bar:

- this is where information is bought and sold

### Choices

1. Sit with the broker and play the role.
2. Pressure the room by exposing a weak liar.
3. Use a coded phrase to identify Veska Tal.

### Branch Logic

- option 1: more professional
- option 2: more aggressive
- option 3: ally-trust path
- all lead to prompt 5

## Prompt 5: First Complication

### Title

**Someone Is Listening**

### Purpose

- raise tension
- show the plan slipping

### Scene

The broker reveals that archive access codes changed unexpectedly. At the same time, a local informant hints that a hidden group has been buying names, records, and movement schedules for both Imperial and anti-Imperial figures.

Warden Karn's people begin moving through the district.

### Choices

1. Buy the archive codes quietly.
2. Break the informant and force a name.
3. Leave the broker and shadow Karn's officers.

### Branch Logic

- option 1: gain `code_cylinder`
- option 2: gain `directorate_name_hint`
- option 3: gain `karn_pattern`
- all lead to prompt 6

## Prompt 6: Investigation Reveal

### Title

**Directorate Null**

### Purpose

- define the episode's true threat
- explain the anti-Force conspiracy clearly

### Scene

Rylos and Veska confirm that the leak feeds a network called Directorate Null. This group is not simply anti-Imperial or pro-Republic. It believes both Sith and Jedi drive endless conflict because powerful Force users always turn ordinary people into collateral.

### Exposition Notes

This explanation must be extremely clear and compact.

### Choices

1. Report the name to Watcher Nine immediately.
2. Hold the information back until there is proof.
3. Ask Veska what she knows about groups like this.

### Branch Logic

- changes trust and tone
- all lead to prompt 7

## Prompt 7: Action Sequence

### Title

**Archive Lockdown**

### Purpose

- physical set piece
- climax of Act II

### Scene

Rylos breaches the intelligence annex to recover the stolen archive fragment. But the district locks down before extraction. Security shutters slam shut, alarms cut through the rain, and Warden Karn's teams move in.

### Action Set Piece

- stealth into sprint
- archive breach under security scan
- close-quarters escape through machinery and collapsing access lanes

## Special Mechanics For This Scene

This scene should use a different interaction model from the rest of the episode.

Normal scenes use:

- one prompt
- three choices
- immediate consequence

The set piece should use:

- **three consecutive action beats**
- **stateful pressure**
- **no long exposition between beats**

This makes the action feel like a sequence instead of a normal menu.

### Mechanic Name

**Pressure Track**

During the set piece, the game tracks:

- `heat`
- `cover`
- `intel`

### Definitions

- `heat`:
  how close security is to catching Rylos

- `cover`:
  how intact the false identity remains

- `intel`:
  how much useful archive data Rylos escapes with

### Starting Values

- `heat = 0`
- `cover = 2`
- `intel = 0`

### Three Action Beats

#### Beat 1: Entry

Rylos gets through the first layer of archive security.

Choices:

1. Cut power to a side corridor.
2. Use the code cylinder.
3. Follow a maintenance shaft.

Effects:

- `cut power`
  - `heat +1`
  - `intel +1`
- `use code cylinder`
  - `cover +1`
  - `intel +1`
- `maintenance shaft`
  - `cover -1`
  - `heat 0`

#### Beat 2: Extraction

Rylos locates the archive fragment while patrols converge.

Choices:

1. Copy everything quickly.
2. Take only the critical file cluster.
3. Plant a false trace before downloading.

Effects:

- `copy everything`
  - `intel +2`
  - `heat +2`
- `critical cluster`
  - `intel +1`
  - `heat +1`
- `false trace`
  - `cover +1`
  - `intel +1`

#### Beat 3: Escape

The lockdown seals the annex and Karn's teams close in.

Choices:

1. Fight through the nearest exit.
2. Trigger a machinery collapse behind you.
3. Disappear into a service lift.

Effects:

- `fight through`
  - `heat +1`
  - `cover -1`
- `machinery collapse`
  - `heat -1`
  - `dark tone`
- `service lift`
  - `cover +1`
  - `intel 0`

## Set Piece Resolution Rules

After Beat 3, resolve the scene based on totals.

### Clean Success

Condition:

- `intel >= 2`
- `heat <= 2`

Result:

- Rylos escapes with strong evidence
- cover mostly holds
- Watcher Nine is impressed

### Messy Success

Condition:

- `intel >= 1`
- `heat <= 4`

Result:

- Rylos gets usable evidence
- security knows someone breached the annex
- Karn becomes more dangerous next episode

### Compromised Escape

Condition:

- `heat >= 5`
  or
- `cover <= 0`

Result:

- Rylos escapes, but his alias is partially blown
- one later scene in Episode II should reflect this
- Veska or Watcher Nine must help contain the damage

## Why This Mechanic Works

- it creates motion without requiring reflex gameplay
- it feels more cinematic than a single choice
- it stays CLI-friendly
- it gives the action set piece a memorable structure
- it preserves deterministic branching

## UI Recommendation

For this scene, show:

- a short action description
- current `heat`, `cover`, and `intel`
- the next three options

Example:

```text
ARCHIVE LOCKDOWN
Heat: 2   Cover: 2   Intel: 1

Security shutters slam down across the annex as red warning lights cut
through the blue archive glow. Karn's teams are closing fast.

1. Fight through the nearest exit
2. Trigger a machinery collapse behind you
3. Disappear into a service lift
```

## Writing Rule For This Scene

Keep each beat short and urgent.

Do not return to long lore exposition here.

The set piece should read like:

- pressure
- movement
- split-second tradeoffs
- immediate consequence

### Choices

1. Slice the archive and run.
2. Erase the watcher logs and preserve cover.
3. Plant evidence against Warden Karn.

### Branch Logic

- option 1: gains the strongest data
- option 2: best cover protection
- option 3: most morally dangerous
- all lead to prompt 8

## Prompt 8: Fallout and Character Beat

### Title

**After the Lockdown**

### Purpose

- start Act III
- slow down
- let the episode breathe

### Scene

Rylos regroups in a safe compartment while stormwater runs through metal grates under the floor. Watcher Nine demands clarity. Veska wants to know whether they can trust command with what they found.

This is the first quiet scene where the player feels the moral line forming.

### Choices

1. Trust Watcher Nine.
2. Trust Veska Tal.
3. Trust no one fully.

### Branch Logic

- sets emotional alignment
- leads to prompt 9

## Prompt 9: Confrontation

### Title

**The Silent Broadcast**

### Purpose

- direct confrontation with the ideology
- make the stakes bigger than one mission

### Scene

A hijacked pirate broadcast cuts through secure channels. A masked speaker claims the galaxy has been trapped for generations between priest-warriors and tyrants with supernatural power. The message frames Directorate Null as a liberating force that intends to break the cycle.

Darth Vader listens in on a secure Imperial line as the signal resolves. He does not speak, but his presence makes the danger feel bigger.

Rylos now understands the enemy is ideological, not merely criminal.

### Choices

1. Transmit everything to Watcher Nine.
2. Keep a private copy of the data.
3. Destroy the most dangerous parts of the archive.

### Branch Logic

- leads to different end-of-episode moral flavors
- all lead to prompt 10

## Prompt 10: Cliffhanger / Transformation

### Title

**What Woke Up**

### Purpose

- deliver the Force-sensitive reveal
- end Episode I with a transformation

### Scene

As the extraction goes bad, metal tools, cables, and loose cargo shift around Rylos without him touching them. Under fear and pressure, he unconsciously uses the Force for the first time.

This must feel shocking, not triumphant.

The key emotion is:

- confusion
- fear
- awe

### Ending Variants

#### If player trusted command

Rylos transmits the data and then sees the world around him move in answer to panic. He realizes the mission is no longer the only secret he is carrying.

#### If player kept leverage

Rylos hides part of the truth, then instinctively stops or redirects a falling object. His need for control now extends beyond politics.

#### If player destroyed the worst files

Rylos chooses restraint, and the Force answers him in a moment of survival. He leaves knowing he may have become the very kind of person Directorate Null fears.

### Required Flag

- `force_sensitive_awakened = true`

## Predetermined Branching Model

This episode should not explode into large branches.

Use:

- shared main spine
- small state changes
- different trust outcomes
- different data outcomes
- one common ending scene with 3 emotional variants

### Things that can vary

- credits
- trust with Watcher Nine
- trust with Veska
- suspicion from Karn
- whether Rylos keeps private leverage
- whether cover is preserved

### Things that should not vary yet

- Directorate Null is discovered
- the archive breach happens
- the broadcast happens
- Rylos awakens to the Force

## Episode I Action Scene Rule

There should be only one major action sequence:

- the archive lockdown and escape

Everything else should feel like:

- espionage
- pressure
- social maneuvering
- conspiracy discovery

## Writing Style Notes

### Keep prose readable

- 1 to 2 paragraphs per prompt
- avoid giant lore blocks
- define unfamiliar terms in context

### Keep choices understandable

Each choice should sound like:

- a tactical approach
- not a vague roleplay mood

### Keep introductions clean

When introducing a person or concept, answer:

- who are they
- why do they matter right now

## Implementation Recommendation

Use this exact episode structure as the source of truth for the deterministic game engine.

Do not let AI replace:

- prompt order
- reveals
- mission logic
- ending transformation

Let AI rewrite only the surface layer of wording if needed.
