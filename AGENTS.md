# Vault Governance & Conventions: {{CAMPAIGN_NAME}}

> **Governance Template:** Replace `{{CAMPAIGN_NAME}}`, the vault folder (`Vault/` or `template-vault/`), the Atlas collection name (`Campaign`), and your party roster below and in `campaign.config.json` to tailor **Demiurge Core** to your campaign.

This file defines the foundational rules every AI agent (and Dungeon Master) must follow when operating inside the **{{CAMPAIGN_NAME}}** vault with **Obsidian** and **Atlas VTT `0.16.0`**.

---

## 1. Directory Structure & Naming
*(Replace `template-vault/` with `Vault/` when starting your real campaign and update `vault_dir` in `campaign.config.json`.)*

- **`<Vault>/DM Screen.md`**: Central live-play reference dashboard for the DM.
- **`<Vault>/Lore/`, `<Vault>/Locations/`, `<Vault>/NPCs/`**: Canonical world compendium notes. NPC portraits live in `<Vault>/NPCs/Portraits/`.
- **`<Vault>/Campaign/`**: World state, story arcs, factions (`Factions/`), player character notes (`Players/`), quests (`Quests/`), and `Improv Log.md`.
- **`<Vault>/Sessions/`**: Modular session prep notes, session recaps, and `Campaign Log.md`.
- **`<Vault>/Items/`**: Magic items, gear, artifacts, and loot databases (`.base`). Item art lives in `<Vault>/Items/Images/`.
- **`<Vault>/Monsters/`**: Creature notes containing YAML statblocks for Obsidian Fantasy Statblocks. Monster portraits live in `<Vault>/Monsters/Portraits/`.
- **`<Vault>/Encounters/`**: Balanced encounter plans and treasure breakdowns.
- **`<Vault>/Tables/`**: Rollable Markdown tables compatible with Obsidian Dice Roller, Atlas `randomTables`, and `roll_tables.py`.
- **`<Vault>/Handouts/`**: Player-safe handouts free of DM secrets.
- **`<Vault>/atlas-vtt/`**: Maps, scenes (`.atlasmap`), tokens, dashboards, and encounters managed by **Atlas VTT `0.16.0`**.
- **`Sources/`** *(optional, local-only, gitignored)*: Personal copyrighted rulebooks or PDFs (read-only, **NEVER** commit to Git).
- **Filenames:** Clear, human-readable titles (spaces allowed). Avoid reserved characters (`< > : " / \ | ? *`).

---

## 2. YAML Frontmatter Standard
Every Markdown note must include valid YAML frontmatter. Relationship properties must be formatted as quoted wikilink lists (e.g., `location: ["[[Oakhaven Village]]"]`).

**Base schema:**
```yaml
title: "Note Title"
icon: "🗺️" # Coherent emoji for Iconize
tags: [entity_type] # e.g., location, npc, lore, item
type: "Subtype" # e.g., Tavern, Dungeon, Wondrous Item
status: "draft" # draft, ready, played. New agent notes start as draft.
```

---

## 3. Writing & Formatting Style
- **Language:** Clean, concise English (or your campaign's chosen language). Avoid cluttering narrative prose with emojis; reserve emojis for headers and operational DM callouts.
- **Wikilinks:** Always link proper nouns to existing notes using `[[Note Name]]` or `[[Note Name|Alias]]`. Verify link integrity with `python scripts/lint_vault.py`.
- **DM Secrets:** Anything hidden from players MUST be isolated inside a callout (e.g., `> [!danger] DM Secret`) or flagged in frontmatter with `visibility: "dm-only"`.

---

## 4. Workflow & Autonomy
1. Always read active campaign context first (`Campaign/World State.md` and related notes).
2. Create or edit files in strict compliance with all rules in `.agents/rules/`.
3. New notes authored by an agent default to `status: "draft"` unless the DM explicitly instructs otherwise.
4. Never write to or modify read-only reference folders (such as `Sources/`).

---

## 5. Narrative Authority & DM-as-Reviewer (Absolute Rule)
- **The Dungeon Master is the sole canonical authority:** An agent NEVER invents or treats unapproved narrative elements as canon (NPC names, contacts, faction ties, new dungeons with lore, or exact handout/letter text).
- **No Unilateral Invention of Locations, Temples, or Institutions:** Never assume or fabricate buildings, temples, guilds, or shrines that are not documented in the vault or approved by the DM. Always search the vault first before naming any entity.
- **Distinguish Meta-Intent from Canon:** When the DM shares an open idea (e.g., *"I'd like them to investigate in town, maybe at a temple"*), do NOT arbitrarily turn it into a specific canonical temple. Ask which existing institution to hook into, or propose 2–3 options for approval.
- **Always Propose Before Writing Canon:** Whenever a narrative element is missing, present 2–3 concise options or a bounded draft and wait for DM approval before writing it into canonical notes.
- **Technical Autonomy Only:** Agents may act autonomously only on rules/technical tasks (XP budgets, 5e statblock formatting, Atlas VTT scene assembly/validation, YAML/wikilink linting) and on lore explicitly approved by the DM.

---

## 6. Pre-Calculated Passive Scores in Dashboards & Prep
To eliminate mental math at the table, every **DM Dashboard** (`<Vault>/atlas-vtt/collections/{{ATLAS_COLLECTION}}/notes/*.md`) and **Session Prep** note must annotate checks against the party's passive scores:

- **Example Party Passives (Level 3 — customize in `campaign.config.json`):**
  - **[[Mira the Cleric|Mira]]:** Passive Perception **13** | Passive Investigation **10** | Passive Insight **15**
  - **[[Kael the Rogue|Kael]]:** Passive Perception **11** | Passive Investigation **14** | Passive Insight **10**
  - **[[Bram the Fighter|Bram]]:** Passive Perception **10** | Passive Investigation **9** | Passive Insight **12**
- **Inline Annotation Standard:**
  - When a Perception, Investigation, or Insight DC is **less than or equal to** a PC's passive score (and requires no active physical search of a closed container), mark it inline with **`⚡ [Automatic Passive — PC Name]`** stating what the DM can tell that player immediately without a roll.
  - When a check exceeds all party passives or requires a declared physical action (rummaging, lockpicking, forcing), mark it with **`🎲 [Active Roll — Skill DC X]`**.

---

## 7. Fidelity to Standard / SRD 5e Statblocks
- **Standard Creatures (`SRD 5.1` / Core Bestiary):** Standard creatures keep their exact official parameters (AC, HP, ability scores, actions, and traits — no arbitrary *Multiattack* additions or unapproved stat tweaks), including when embedded inline in Dashboards.
- **Custom / Boss Creatures:** Dedicated custom statblocks are permitted for roles or CRs not covered by standard entries; always label them clearly as *Homebrew*.
- **Player Characters (PCs):** Never create monster statblocks for PCs; Atlas VTT `0.16.0` tracks PC Hit Points natively via `playerCharacter: true` on tokens and `<Vault>/atlas-vtt/campaigns/{{ATLAS_CAMPAIGN_SLUG}}/characters.json`.

---

## 8. Atlas VTT `0.16.0` Conventions (Quests, Encounters & 32 KB Limit)
- **Hard 32 KB Technical Limit:** Atlas VTT ignores linked notes, dashboards, statblocks, or loot files larger than **32 KB** (`32768` bytes). Keep every DM Dashboard lean and strictly under **30 KB**.
- **Native Quest Integration (`<Vault>/Campaign/Quests/*.md`):** Quest notes include the YAML properties read by Atlas VTT's *Quests* panel:
  ```yaml
  atlas-type: "quest"
  campaign: "00000000-0000-4000-8000-000000000001"
  kind: "main" # "main" or "side"
  status: "open" # "open", "active", "done", "failed"
  experience: 300 # optional
  rewards:
    - "Reward 1"
  ```
- **Pre-Configured Encounters (`<Vault>/atlas-vtt/collections/{{ATLAS_COLLECTION}}/encounters/`):** Planned tactical fights can have dedicated Encounter `.json` files in the Atlas collection for 1-click placement, Note Pin linking, and Initiative Tracker integration (*"In this fight"* filter).
- **Automatic Vault Watcher (`reconcileWithVault`):** In Atlas VTT `0.16.0`, never hand-edit `.atlas-data/assets-metadata.json` while Obsidian is running; write canonical records under `maps/`, `scenes/`, `tokens/` and let Atlas reconcile automatically. Before editing an existing `.atlasmap` via script, always **close that scene's tab in Obsidian first**.
