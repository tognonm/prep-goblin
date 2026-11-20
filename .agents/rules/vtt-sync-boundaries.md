# Synchronization Boundaries: Obsidian ↔ Atlas VTT `0.16.0`

This document establishes clear boundaries between what stays purely as Markdown prose in Obsidian and what MUST have a visual or mechanical asset inside **Atlas VTT `0.16.0`**.

---

## 1. The "Active Scene" Principle
The golden rule is the **Active Scene**. Everything belonging to the background world (history, distant NPCs, off-screen faction plots) lives solely in Obsidian. Everything the players can **see, fight, or tactically explore right now** needs a ready asset in Atlas VTT.

---

## 2. What Lives ONLY in Obsidian (No VTT Asset Required)
- **Lore & History:** Creation myths, historical wars, pantheon notes, setting background.
- **Off-Screen NPCs:** Distant rulers, mentioned contacts who are not present, PC relatives off-screen.
- **Factions & Progress Clocks:** Secret faction advances (until a clock trigger physically manifests in front of the party).
- **Macro Locations:** Nations, regions, or whole-city overview notes (unless using an interactive overland map in Atlas).
- **Routine Gear & Text-Only Inventory:** Standard equipment, coins, and purely textual handouts.

---

## 3. What MUST Be Synced to Atlas VTT (Asset Required)
When preparing a session or tactical encounter, ensure these items have matching VTT assets:

### A. Combat Monsters & On-Screen NPCs
If a creature (e.g., a *Skeleton Sentry* in a crypt) or key NPC is physically present on the map:
- **In Obsidian:** A note with a ```` ```statblock ```` block exists in `<Vault>/Monsters/` (or an NPC sheet in `<Vault>/NPCs/`).
- **Portraits / Tokens:** Generate or assign square token art (`<Vault>/Monsters/Portraits/` or `<Vault>/NPCs/Portraits/`) and link it inside the note (`image: "[[...]]"`).
- **In Atlas VTT:** Register the token in the configured collection (`atlas-token-art/scripts/register_token.py`) with `statblockPath` set, or create it from Atlas VTT's Token Creator.
- **Player Characters (PCs):** PC tokens use `"playerCharacter": true` and sync HP across scenes via `<Vault>/atlas-vtt/campaigns/<campaign_slug>/characters.json`.

### B. Battlemaps & Dungeons
If players explore a tactical space turn-by-turn (dungeon, tavern, ambush site):
- **In Obsidian:** Compendium Location Note (`<Vault>/Locations/`) + compact DM Dashboard (`< 30 KB`) in the Atlas collection.
- **In Atlas VTT:** Validated `.atlasmap` scene (schema `v4`) with calibrated grid, walls, doors, dynamic lights, tokens, and Note Pins verified via `atlas_scene_tools.py`.

### C. Visual Handouts & Puzzles
If players inspect a physical visual prop (ciphered letter, sigil, mural):
- **In Obsidian:** Transcription and DM solution (isolated in a `> [!danger] DM Secret` callout).
- **In Atlas VTT / `<Vault>/Handouts/`:** Clean player-safe image or handout free of spoilers.

---

## 4. Disk Integrity Rules for Atlas VTT `0.16.0`
- **Close Scene Tab Before Scripted Edits:** Never overwrite an `.atlasmap` file while that scene is open in an Obsidian tab, or Atlas may flush stale RAM state over your disk changes.
- **Never Hand-Edit Internal Metadata:** Avoid manually editing `.atlas-data/assets-metadata.json` while Obsidian is running; write canonical records under `collections/<Collection>/{maps,scenes,tokens,encounters}` and let `reconcileWithVault` index them automatically.
- **Controlled Exception for `quick-battlemap`:** See `live-improv-and-boundaries.md` for throwaway improvised scenes.
