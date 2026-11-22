# Live Improvisation, Skill Boundaries & Regional Evolution Rule

This rule complements `dm-reviewer-narrative-authority.md`, `vtt-sync-boundaries.md`, `scene-and-dashboard-standards.md`, and `session-lifecycle.md` to prevent skill overlap and ensure nothing improvised at the table gets lost.

---

## 1. Anti-Overlap Skill Matrix

Every skill in the framework owns a crisp perimeter; agents must never blur these boundaries:

| Skill | When to Use | Where It Writes | What It NEVER Does |
| :--- | :--- | :--- | :--- |
| **`live-improv`** | Live at the table for quick NPCs, shops, chases, weather, hazards, traps, quick loot, and random tables. | Chat output; on DM approval, 1 row in `<Vault>/Campaign/Improv Log.md`. | Never writes canonical notes into `<Vault>/Locations/`, `<Vault>/NPCs/`, or `<Vault>/Lore/`. |
| **`quick-battlemap`** | Unplanned combat or sudden detours (instant Wildcard scenes or 2–3s procedural generation). | `.atlasmap` scene + compact operational note inside `<Vault>/atlas-vtt/collections/{{ATLAS_COLLECTION}}/`. | Never creates compendium notes in `<Vault>/Locations/` or custom portrait art (reuses existing/fallback tokens). |
| **`dungeons-and-maps`** | Planned canonical dungeons and tactical locations. | Full two-level package (`<Vault>/Locations/...` + Dashboard `< 30 KB` + `.atlasmap` + Encounter). | Not triggered for throwaway improvised ambushes. |
| **`atlas-sound-moods`** | Atlas VTT `0.19.0+` Music & Ambience setup: registering local audio tracks, building reusable mood mixes, and binding `state.sound` (`mood` / `combatMood`) to `.atlasmap` scenes. | `<Vault>/atlas-vtt/sounds/records/*.json`, `sounds/moods/*.json`, and `state.sound` inside `.atlasmap` files. | Never commits binary audio files (`sounds/music/`, `sounds/ambience/`), never alters walls/tokens/narrative canon, and never writes while the target scene tab is open. |
| **`encounters-and-loot`** | Formal 5e XP balancing, hoard treasure, and persistent Atlas Encounter `.json` files. | `<Vault>/Encounters/`, `<Vault>/atlas-vtt/.../encounters/`. | Does not replace fast live table rolls from `live-improv`. |
| **Vault Compendium (`Locations/` / `NPCs/` / `Lore/`)** | Only pathway for promoting locations, NPCs, and lore into permanent canon (after DM OK). | `<Vault>/Locations/`, `<Vault>/NPCs/`, `<Vault>/Lore/`. | Never saves ephemeral bystanders before DM confirmation. |
| **`transcript-to-recap`** | Post-session audio or Discord transcript processing (`.srt`, `.vtt`, `.txt`) via `prep_transcript.py`. | Chat Extraction Review Sheet; after DM approval, stages candidate improvised entities in `<Vault>/Campaign/Improv Log.md` and hands off canon updates to `session-recap` & `living-world`. | Never writes canonical notes, updates `World State.md`, or advances clocks before explicit DM review. |
| **`session-recap` & `living-world`** | Post-session wrap-up: recap, clock updates, and triage of `Improv Log.md`. | `<Vault>/Sessions/`, `<Vault>/Campaign/World State.md`, `Factions/`, `Improv Log.md`. | Never invents events that did not happen at the table. |

---

## 2. Controlled Exception for `quick-battlemap` (VTT Sync & Dashboard)
As a scoped exception to `vtt-sync-boundaries.md` and `scene-and-dashboard-standards.md`, any scene created with `quick-battlemap` or a `Wildcard - *` scene:
- **Does NOT require** a Compendium Location Note in `<Vault>/Locations/` or custom portraits in `<Vault>/Monsters/Portraits/` or `<Vault>/NPCs/Portraits/`.
- Still enforces **every technical invariant of Atlas VTT `0.16.0`** (schema `v4`, `snapToGrid: true`, lights `>= 25 px` from walls, `fog: {}`, linked note `< 30 KB`, no manual edits to `assets-metadata.json`).
- If an improvised map location later becomes recurring, promote it cleanly via `dungeons-and-maps` after DM approval.

---

## 3. Master Staging Log & Mandatory Proactive Prompt
To keep campaign canon spotless without losing improvised table gold:
1. **Single DM Staging File:** Everything that actually enters play during improvisation is tracked in `<Vault>/Campaign/Improv Log.md` (`visibility: "dm-only"`), linked from `DM Screen.md`.
2. **Mandatory Proactive Prompt (Always):** After generating any substantial element via `live-improv` (NPC, venue, event, notable item) OR creating an on-demand battlemap via `quick-battlemap`, the agent **MUST ALWAYS** close by asking:
   > *"Would you like me to log this in `Campaign/Improv Log.md` so we don't lose track of it, or let it fade out?"*
3. **Write Only on Confirmation:** Never log before the DM confirms (allowing rerolls until the DM likes the result). On confirmation, append 1 clean row with an in-game date and location wikilink.
4. **Post-Session Triage:** During `session-recap` / `session-lifecycle.md`, review recent entries in `Improv Log.md` and ask the DM which to:
   - **Promote to canon** (dedicated note in `<Vault>/NPCs/` or `<Vault>/Locations/`),
   - **Keep in the log** as `recurring` or `ephemeral`,
   - **Archive / clean up** (e.g., temporary battlemaps no longer needed).

---

## 4. Setting Adaptation & Evolving Wildcard Scenes
- **Location-Aware Flavor:** Tables in `<Vault>/Tables/` and procedural battlemaps adapt to the party's **current location** read from `<Vault>/Campaign/World State.md` (or specified by the DM).
- **Evolving Wildcard Battlemap Pack:**
  - **Universal Starter Set:** `whiteboard` (dry-erase), `alley` (urban), `road` (country road & river), `hills` (rocky moorland), `interior` (tavern/shop/house), `camp` (woodland camp), `bridge` (stone river gorge bridge), `crypt` (forgotten subterranean crypt).
  - **Regional Expansion:** As the campaign enters new biomes (swamps, ships, arctic passes, underdark caverns, fortresses), propose adding tailored regional presets and `Wildcard - *` scenes.
