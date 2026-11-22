---
name: dungeons-and-maps
description: >-
  Designs, builds, and validates end-to-end tactical dungeons, battlemaps, walls, doors,
  dynamic lights, tokens, and room dashboards for D&D 5e with Obsidian and Atlas VTT 0.16.0.
  Enforces the two-level vault model (Location Note + DM Dashboard < 30 KB), 1:1 Note Pin
  H3 anchors, pre-calculated party passives, and automated .atlasmap validation.
---

# Dungeons & Tactical Maps (`dungeons-and-maps` — Atlas VTT `0.16.0`)

This skill governs the complete preparation pipeline for canonical dungeons in **{{CAMPAIGN_NAME}}** with **Atlas VTT `0.16.0`**: from collaborative layout confirmation with the DM to full `.atlasmap` assembly (walls, doors, rubble drawings, dynamic lighting, tokens, and Note Pins) and visual verification.

---

## 1. Two-Level Architecture & Technical Invariants

```text
<Vault>/
├── Locations/
│   └── [Dungeon Name].md                                  <-- 1. COMPENDIUM NOTE (Lore, history, diagram, hooks)
└── atlas-vtt/collections/{{ATLAS_COLLECTION}}/
    ├── notes/[Dungeon Name] - Dashboard.md                <-- 2. DM DASHBOARD (< 30 KB, Linked Note, H3s, statblocks)
    ├── scenes/[Scene Name].atlasmap                       <-- 3. ATLAS SCENE (walls, doors, lights, tokens, pins)
    └── encounters/encounter-*.json                        <-- 4. PRE-CONFIGURED ENCOUNTERS
```

### Critical Constraints (`AGENTS.md` + Atlas `0.16.0`)
- **Hard 32 KB Limit:** Every DM Dashboard MUST stay under **30 KB** (Atlas VTT hard ceiling is `32768 bytes`).
- **Pre-Calculated Passives (`AGENTS.md` Rule 6):** Read party passives from `AGENTS.md` / `campaign.config.json`. Always mark DC ≤ passive with **`⚡ [Automatic Passive — PC Name]`** and anything above passives (or requiring active interaction) with **`🎲 [Active Roll — Skill DC X]`**.
- **Standard / SRD Statblocks (`AGENTS.md` Rule 7):** Standard creatures keep exact official stats with no arbitrary modifications.
- **Scene Name Consistency:** `atlas_scene:` in the Location Note must match `atlasRecord.name` in `scenes/scene-*.json`.
- **1:1 Indexable H3 Headings:** Every pinned room or POI must have an exact `### N. Room Name` heading (no `*italic*` or `**bold**` inside the heading) matching the `#Heading` anchor of its Note Pin.
- **Multi-Level Synchronization (Zero Canon Drift):** Whenever any room detail, DC, secret, treasure, or mechanic of a dungeon is modified, ALWAYS propagate the change in lockstep across all three layers: **(1)** the Compendium Location Note (`<Vault>/Locations/`), **(2)** the operational DM Dashboard (`<Vault>/atlas-vtt/collections/{{ATLAS_COLLECTION}}/notes/`), and **(3)** any linked Session Prep note (`<Vault>/Sessions/`). Never leave stale or contradictory details between layers.

---

## 2. End-to-End 4-Phase Workflow

Use the bundled CLI toolkit: `.agents/skills/dungeons-and-maps/scripts/atlas_scene_tools.py`.

### Phase 1 — Visual Analysis & Layout Sign-Off (DM-as-Reviewer)
**Never write final room lore before DM approval** (`AGENTS.md` Rule 5).
1. **Inspect the battlemap and verify grid alignment:**
   ```bash
   python .agents/skills/dungeons-and-maps/scripts/atlas_scene_tools.py grid-preview "<path.atlasmap or image>" --out "scratch/grid_check.png"
   ```
   - **Half-cell offset check:** Verify that 1-square corridors and 1×1 pillars fall **inside** grid cells rather than straddling grid lines. If misaligned by half a cell (`size / 2`), adjust `grid.offsetX` or `grid.offsetY` (within `[0, size)`) so `snapToGrid` never places tokens inside walls.
2. **Propose labeled room mapping (`A`, `B1`, `C`, ...):**
   Identify every drawn chamber, overlay clean letter badges in `scratch/`, and confirm with the DM:
   - **Map Letter ↔ Room / Encounter / Secret** mapping;
   - Any **blocked passages, cave-ins, or one-way shortcuts** to pace exploration.

### Phase 2 — Statblocks, Tokens & Encounters
1. Verify creature notes in `<Vault>/Monsters/` (compliant with `statblock-5e`).
2. For creatures lacking tokens, register art with `.agents/skills/atlas-token-art/scripts/register_token.py`.
3. Create or verify `encounters/encounter-*.json` under `<Vault>/atlas-vtt/collections/{{ATLAS_COLLECTION}}/encounters/`.

### Phase 3 — Compendium Location Note + DM Dashboard
1. Author the Compendium Location Note (`<Vault>/Locations/...`) with a Mermaid topology diagram, 5-second sensory read-aloud, and campaign hooks.
2. Author the DM Dashboard from `.agents/skills/dungeons-and-maps/resources/dashboard_template.md`, or bootstrap a `< 5 KB` starter Dashboard straight from an existing `.atlasmap` (matching every Note Pin 1:1 to an `### H3` heading and pulling party passives from `campaign.config.json`):
   ```bash
   python .agents/skills/dungeons-and-maps/scripts/atlas_scene_tools.py scaffold-dashboard "<path.atlasmap>" --out "<Vault>/atlas-vtt/collections/{{ATLAS_COLLECTION}}/notes/<Name> - Dashboard.md" --name "<Title>"
   ```
   Ensure every Note Pin matches a `### H3` heading 1:1 and total size stays strictly `< 30 KB`.

### Phase 4 — Scene `.atlasmap` Assembly, `.dd2vtt`/`.uvtt` Import & Visual Verification
> [!IMPORTANT] Before Writing to `.atlasmap`
> Always have the DM **close that scene's tab in Obsidian FIRST** before running scripts that modify an existing `.atlasmap` file (otherwise Atlas may flush stale RAM state over disk edits).

0. **Importing Dungeondraft / Dungeon Alchemist Maps (`.dd2vtt` / `.uvtt`):**
   - Atlas VTT `0.16.0` supports native `.dd2vtt` / `.uvtt` import (background image, grid, walls, doors/portals, and local lights come across automatically).
   - Immediately after importing or hand-walling a scene, run **`audit-walls`** to catch zero-length walls, duplicate overlapping segments, near-miss endpoint gaps (Dynamic Lighting leak cracks), and lights placed too close to walls (`< 20 px`):
     ```bash
     python .agents/skills/dungeons-and-maps/scripts/atlas_scene_tools.py audit-walls "<path.atlasmap>" --gap-threshold 18 --strict
     ```
   - Then run **`scaffold-dashboard`** (above) to generate a compact `< 5 KB` DM Dashboard pre-populated with scene metadata, placed tokens, and party passives.
1. **Auto-Detect Natural Light Clusters (crystals, braziers, torches, glowing pools):**
   ```bash
   python .agents/skills/dungeons-and-maps/scripts/atlas_scene_tools.py detect-lights "<image>" --color amber --out "scratch/lights_check.png" --json "scratch/lights.json"
   ```
   - Supported `--color` presets: `cyan` (crystals), `amber` (torches/braziers), `emerald` (acid/miasma), `purple` (arcane runes).
   - **Anti-occlusion clearance rule:** Place every light source at least **`≥ 20 px`** (ideally `≥ 25 px`) away from any wall or pillar segment so raycasting isn't clipped.
2. **Walls, Pillars, Doors & Visual Cave-Ins (`walls` + `drawings`):**
   - **`walls`:** Use `"type": "solid"`, `"door"`, `"secret-door"`, or `"window"`. Locked visible doors use `"type": "door", "locked": true`; **hidden secret doors** use `"type": "secret-door", "closed": true` (invisible in Player View until opened by the DM). Box in interior pillars with closed squares for crisp dynamic shadows.
   - **Visual Rubble (`drawings` on layer `"map"`):** When sealing off a corridor that looks open on the artwork, add closed boulder polygons (`points[0] == points[-1]`, `"type": "pen"`, `"fill": "solid"`, `"layer": "map"`, `"locked": true`) immediately in front of the solid wall.
3. **Dynamic Lighting vs. Manual Fog (`lighting` vs. `fog`):**
   - **Prefer a single visibility system:** When using walls, closed doors, and `"lighting": {"enabled": true, "ambient": 0, "tokenVision": true, "exploredMemory": true}`, **keep `fog: {}` empty** so opening a door reveals the room in one click.
4. **PC & Enemy Tokens (`tokens`):**
   - **Exact Grid Snapping:** With `snapToGrid: true`, center every size-1 token on integer grid cells: `x = offsetX + (col + 0.5) * size`, `y = offsetY + (row + 0.5) * size`.
   - **PCs:** Set `"assetId"`, `"playerCharacter": true`, `"vision": {"enabled": true}`, `"hp": {"current": ..., "max": ...}`, and attach a `dnd5e-torch` light to the party's torchbearer in dark dungeons.
5. **Note Pins (`pins`):**
   - Link each pin to `atlas-vtt/collections/{{ATLAS_COLLECTION}}/notes/<Name> - Dashboard.md#<Exact H3>`.
6. **Mandatory Visual & Automated Validation:**
   ```bash
   python .agents/skills/dungeons-and-maps/scripts/atlas_scene_tools.py audit-walls "<path.atlasmap>" --gap-threshold 18 --strict
   python .agents/skills/dungeons-and-maps/scripts/atlas_scene_tools.py verify-scene "<path.atlasmap>" --out "scratch/verify.png"
   python .agents/skills/dungeons-and-maps/scripts/atlas_scene_tools.py validate "<path.atlasmap>" --dashboard "<path Dashboard.md>"
   ```
   Inspect `scratch/verify.png`, confirm zero errors and zero warnings, and run `--reset-test` before session start to clear any `exploredMask` or `diceLog` test artifacts.

---

## 3. Quick Table Controls (Atlas VTT `0.16.0`)

- **Hold `H` (*Lighting Peek*):** Preview the exact player view through Dynamic Lighting.
- **Open Doors:** Click any door segment directly on the map — light and vision flow through instantly.
- **Toggle Torches:** Right-click token → *Carry light* → *None* / *Torch*.
- **Reset Exploration:** *Lighting settings → Forget explored areas* (or `--reset-test`).
- **Toggle Dashboard:** Press **`Tab`** (Linked Note) or click any **Note Pin**.
