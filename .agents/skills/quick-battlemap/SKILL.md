---
name: quick-battlemap
description: >-
  Generates complete procedural battlemaps and Atlas VTT 0.16.0 (schema v4) scenes in 2-3 seconds
  for improvised combat, or points the DM to 8 pre-built Wildcard presets (whiteboard, alley, road,
  hills, interior, camp, bridge, crypt) complete with walls, openable doors, secret doors, dynamic
  lighting, party tokens from campaign.config.json, and enemies parsed from <Vault>/Monsters/.
---

# Instant Tactical Battlemap (`quick-battlemap` — Atlas VTT `0.16.0`)

This skill solves unplanned combat during live sessions on **Atlas VTT `0.16.0`** with two complementary modes: **0-second launch** using pre-generated Wildcard scenes, or **2–3 second on-demand generation** tailored to exact enemies, grid dimensions, and time of day.

---

## 1. Mode A (Zero-Wait Wildcards) vs. Mode B (On-Demand Generation)

### Mode A — Pre-Generated Wildcard Scenes
You can pre-generate **8 Wildcard scenes** in your Atlas collection (`campaign.config.json` → `atlas_collection`) with no fixed enemies, party tokens already snapped on the grid, walls/doors/lights pre-wired, and linked DM notes:

| Recommended Wildcard Scene | Preset | Grid | Default Light | Tabletop Use Case |
| :--- | :--- | :---: | :---: | :--- |
| **`Wildcard - Tactical Whiteboard`** | `whiteboard` | `16x12` | `day` | Clean dry-erase parchment canvas for live *Drawing* sketches |
| **`Wildcard - Urban Alley`** | `alley` | `16x12` | `dusk` | Street ambushes, T-junction alley, crate cover, 2-door side warehouse, 2 streetlamps |
| **`Wildcard - Country Road`** | `road` | `18x12` | `day` | Highway encounters, halted merchant wagon cover, 2 sight-blocking boulders, riverbank reeds |
| **`Wildcard - Rocky Hills`** | `hills` | `18x12` | `dusk` | Limestone moorland with 3 rock outcrops (broken LoS), ancient menhir, campfire |
| **`Wildcard - Building Interior`** | `interior` | `14x10` | `night` | Shop/tavern/house: main hall with counter, tables, 2 pillars, backroom, and **1 secret door** to rear alley |
| **`Wildcard - Forest Camp`** | `camp` | `16x12` | `night` | Woodland clearing with 3 angled canvas tents, central roaring campfire, fallen log cover, and 4 ancient tree sight-blockers |
| **`Wildcard - Stone Bridge`** | `bridge` | `18x12` | `day` | North–South rocky river gorge spanned by an arched stone bridge, parapet piers, cliffside boulders, and 2 bridge post lanterns |
| **`Wildcard - Forgotten Crypt`** | `crypt` | `16x12` | `night` | Subterranean flagstone crypt with 4 shadow-casting columns, sarcophagi, raised dais, west door, 2 braziers, and **1 hidden east reliquary secret door** |

- **How to run them live:** Open from Atlas VTT's *Scenes* library, drag enemy tokens from *Tokens*, and play immediately. Afterwards, run *Lighting settings → Forget explored areas* to reset.

### Mode B — On-Demand Generation (2–3 Seconds)
When the DM asks for a tailored skirmish map with enemies placed and custom lighting:

```bash
python .agents/skills/quick-battlemap/scripts/quick_battlemap.py --preset <preset> [options]
```

> [!IMPORTANT] Atlas VTT Automatic Vault Watcher & Overwrites
> - **New scenes:** Atlas VTT `0.16.0` automatically indexes every new `maps/map-*.json`, `scenes/scene-*.json`, and `scenes/*.atlasmap` via `reconcileWithVault` (**NEVER** hand-edit `assets-metadata.json` or `collection.json`).
> - **Overwriting existing scenes (`--slug`):** Always have the DM **close that scene's tab in Obsidian first** before overwriting an existing `.atlasmap`, then reopen it.

---

## 2. Example Chat Requests → CLI Commands

| DM Prompt in Chat | CLI Command |
| :--- | :--- |
| *"Night alley ambush with 2 road raiders"* | `python .agents/skills/quick-battlemap/scripts/quick_battlemap.py --preset alley --name "Alley Ambush" --lighting night --enemies "Road Raider:2"` |
| *"Quick 16x12 whiteboard"* | `python .agents/skills/quick-battlemap/scripts/quick_battlemap.py --preset whiteboard --name "Quick Whiteboard" --cols 16 --rows 12 --lighting day` |
| *"Rocky hills at dusk with 3 skeleton sentries"* | `python .agents/skills/quick-battlemap/scripts/quick_battlemap.py --preset hills --name "Hills Skirmish" --lighting dusk --enemies "Skeleton Sentry:3"` |
| *"Shop interior at night with 2 guards (11 HP)"* | `python .agents/skills/quick-battlemap/scripts/quick_battlemap.py --preset interior --name "Shop Skirmish" --lighting night --enemies "Guard:2@11"` |
| *"Night camp ambush with 3 wolves (11 HP)"* | `python .agents/skills/quick-battlemap/scripts/quick_battlemap.py --preset camp --name "Camp Ambush" --lighting night --enemies "Wolf:3@11"` |
| *"Daytime bridge toll blockade with 3 road raiders"* | `python .agents/skills/quick-battlemap/scripts/quick_battlemap.py --preset bridge --name "Bridge Blockade" --lighting day --enemies "Road Raider:3"` |
| *"Subterranean crypt with 4 skeleton sentries"* | `python .agents/skills/quick-battlemap/scripts/quick_battlemap.py --preset crypt --name "Crypt Skirmish" --lighting night --enemies "Skeleton Sentry:4"` |
| *"Dry-run country road at dusk with 3 wolves (11 HP), new seed"* | `python .agents/skills/quick-battlemap/scripts/quick_battlemap.py --preset road --name "Road Wolves" --lighting dusk --enemies "Wolf:3@11" --seed 77 --dry-run` |

---

## 3. CLI Reference (`scripts/quick_battlemap.py`)

- `--preset {whiteboard,alley,road,hills,interior,camp,bridge,crypt}` *(required)*: Procedural art, wall layout, doors, lights, and Note Pins.
- `--name "<Scene Name>"`: Display name in Atlas VTT and base filename for `.atlasmap`, `.thumb.jpg`, and `notes/<Name>.md`.
- `--cols <int>`, `--rows <int>`, `--cell <int>`: Grid size (min `10x8`, default `70` px per cell).
- `--lighting {day,dusk,night}`: Controls `ambient` (`1.0` / `0.35` / `0.0`), activates `dnd5e-torch` on the configured torchbearer PC, and toggles ambient lamps/campfires.
- `--enemies "<Spec>"`: Comma-separated list, e.g., `"Road Raider:2,Skeleton Sentry:1"` or `"Wolf:3@11"`. Dynamically parses `<Vault>/Monsters/*.md` and matches registered tokens (or falls back to `campaign.config.json` fallback art).
- `--collection <Name>` / `--vault <Path>` / `--config <File>`: Override `campaign.config.json` defaults.
- `--seed <int>`: Deterministic RNG seed for rocks, shrubs, cracks, and props.
- `--slug <str>`: Deterministic filenames and IDs (e.g., `--slug wildcard_alley`).
- `--no-pcs`: Omit party PC tokens.
- `--dry-run`: Simulate and self-validate without writing files.

---

## 4. Verification & Staging Rules

1. **Post-Generation Validation:** For persistent scenes, confirm zero errors and zero warnings:
   ```bash
   python .agents/skills/dungeons-and-maps/scripts/atlas_scene_tools.py validate "<Vault>/atlas-vtt/collections/<Collection>/scenes/<Name>.atlasmap" --dashboard "<Vault>/atlas-vtt/collections/<Collection>/notes/<Name>.md"
   ```
2. **Built-In Technical Guarantees:**
   - Atlas VTT `0.16.0` (`version: 4`), `snapToGrid: true`, `offsetX/Y: 0`, configured grid units (`feet` or `meters`).
   - All tokens centered on integer walkable cells, never inside walls or solid roofs.
   - All lights kept `>= 25 px` away from every wall segment.
   - No manual `fog` fighting Dynamic Lighting (`fog: {}`).
   - Linked DM Dashboard `< 5 KB` (well under Atlas's `32 KB` ceiling) with 1:1 `### H3` pin anchors and dynamic party passives.
3. **Mandatory Proactive Staging Prompt (`live-improv-and-boundaries.md`):**
   - After generating any on-demand battlemap, always ask the DM:
     > *"Would you like me to log this scene in `Campaign/Improv Log.md` so we can decide whether to keep or clean it up after the session?"*
