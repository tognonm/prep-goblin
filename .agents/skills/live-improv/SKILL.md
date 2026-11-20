---
name: live-improv
description: >-
  Fast tabletop live-improvisation generator for D&D 5e powered by rollable Markdown tables
  in <Vault>/Tables/ (compatible with Obsidian Dice Roller and Atlas VTT randomTables). Use
  during live sessions whenever the DM needs instant NPCs, shops, chases, weather, hazards,
  traps, quick loot, or random encounters.
---

# Live Tabletop Improvisation (`live-improv`)

This skill turns chat into a lightning-fast DM co-pilot at the table: it rolls on real Markdown tables in `<Vault>/Tables/` via `scripts/roll_tables.py` and delivers ultra-compact, table-ready responses.

---

## Live Operating Rules

1. **Always roll via script before answering:** Do not invent results mentally; run:
   ```bash
   python .agents/skills/live-improv/scripts/roll_tables.py --list
   ```
   or `--preset <name>` / `--file "<name>" --table <index|all>`.
2. **Ultra-Compact Tabletop Format (max 6–8 lines):** The DM is actively running the session. Return:
   - **Scene / NPC / Object:** 1–2 crisp lines ready to read aloud.
   - **5e Mechanics:** DC, damage, suggested statblock, or social/chase rule in 1–2 lines.
   - **Pre-Calculated Party Passives:** Read from `AGENTS.md` / `campaign.config.json`, tagging **`⚡ [Automatic Passive — PC Name]`** for DC ≤ passive and **`🎲 [Active Roll]`** for higher DCs or active physical checks.
   - **Immediate Hook / Choice:** 1 line.
3. **Narrative Authority, Location Context & DM Staging (`AGENTS.md` Rule 5 & `live-improv-and-boundaries.md`):**
   - **Match Current Location:** Check `<Vault>/Campaign/World State.md` (or ask the DM) and flavor table results to the party's active region.
   - **Protect Canon:** Everything produced by `live-improv` is ephemeral table material. **NEVER** write directly into `<Vault>/NPCs/`, `<Vault>/Locations/`, or `World State.md` without explicit DM approval.
   - **Mandatory Proactive Prompt (ALWAYS close with this):** After every substantial live roll (NPC, venue, event, notable item), end by asking:
     > *"Would you like me to log this in `Campaign/Improv Log.md` so we don't lose track of it, or let it fade out?"*
   - If the DM says yes, append 1 clean row to the matching table in `<Vault>/Campaign/Improv Log.md` with in-game date, location wikilink, and status `ephemeral` (or `recurring`).
   - **Never fabricate canonical temples, factions, or lore:** Anchor details to existing vault notes or leave `[DM choice]` placeholders with 2 brief options.

---

## CLI Cheat Sheet (`scripts/roll_tables.py`)

| Goal | Command |
| :--- | :--- |
| List all indexed tables & presets | `python .agents/skills/live-improv/scripts/roll_tables.py --list` |
| Run a configured preset (e.g., demo) | `python .agents/skills/live-improv/scripts/roll_tables.py --preset demo-scene` |
| Roll a specific file & sub-table | `python .agents/skills/live-improv/scripts/roll_tables.py --file "Demo Table" --table 0` |
| Roll every sub-table in a file | `python .agents/skills/live-improv/scripts/roll_tables.py --file "Demo Table" --table all` |
| Repeat `N` times with a fixed seed | `python .agents/skills/live-improv/scripts/roll_tables.py --preset demo-npc --count 2 --seed 42` |

### Adding Your Own Tables & Presets
Drop any Markdown file with `| d6 |`, `| d8 |`, `| d10 |`, `| d12 |`, `| d20 |`, `| d100 |`, or `| d% |` tables into `<Vault>/Tables/` — `roll_tables.py` indexes them automatically. Define custom multi-table presets in `campaign.config.json` (`roll_table_presets`) or `<Vault>/Tables/presets.json`.

---

## Example Compact Tabletop Output (6–8 Lines)

> **Quick NPC — Corvus the Ferryman (River Docks)**
> - **Look & Tell:** Waxed oilskin cloak and an unlit brass lantern at his belt; taps his oar nervously whenever someone asks about last night's barge. *(Statblock: Commoner or unarmed `Road Raider`).*
> - **Attitude:** **Indifferent** — Charisma **DC 15** for confidential details (**Advantage** if the party offers discretion or coin).
> - **Passives:** `⚡ [Automatic Passive — Mira (Ins. 15)]` Immediately reads fear rather than hostility — he is watching the upper pier for someone.
> - **DM Staging:** Improvised bystander. *Would you like me to log him in `Campaign/Improv Log.md` so we don't lose track of him, or let him fade out?*
