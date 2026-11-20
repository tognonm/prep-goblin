# Location Notes, Scene Standards & Atlas VTT Dashboards (`< 32 KB`)

This rule defines the mandatory structure for location notes and operational DM Dashboards to ensure fast table play and full compatibility with **Atlas VTT `0.16.0`**.

---

## 1. The Two-Level Model: Location Note vs. Scene Dashboard

The vault strictly separates two complementary layers:
1. **Compendium Location Note (`<Vault>/Locations/...`)**: Macro description, history, factions, diagrams, and campaign hooks. No strict byte limit.
2. **Scene DM Dashboard (`<Vault>/atlas-vtt/collections/{{ATLAS_COLLECTION}}/notes/<Name> - Dashboard.md`)**: The ultra-lean tactical card opened inside Atlas VTT by pressing **`Tab`** (Linked Note) or clicking **Note Pins**.

---

## 2. Hard Technical Constraint: Atlas VTT 32 KB Limit
> [!IMPORTANT] Hard 32 KB Limit (`32768 bytes`)
> Atlas VTT `0.16.0` silently ignores linked notes, dashboards, or statblocks larger than **32 KB** (`32768 bytes`).
> - **Recommended Target:** Keep every DM Dashboard strictly under **30 KB** (ideally `3 KB–24 KB`).
> - **Automated Verification:** Always check with `python .agents/skills/dungeons-and-maps/scripts/atlas_scene_tools.py validate <scene.atlasmap> --dashboard <dashboard.md>` and `python scripts/lint_vault.py`.

---

## 3. Mandatory Sections for Canonical Location Notes

Every canonical location note created or expanded in `<Vault>/Locations/` includes:

### A. YAML Frontmatter & Screen Visibility
```yaml
---
title: "Location Name"
icon: "🗺️"
tags: [location, settlement]
map_visibility: "player" # player (shareable), dm-only, theater_of_the_mind
atlas_scene: "Atlas Scene Name" # optional
atlas_dashboard: "[[Dashboard Note Name]]" # optional
status: "draft"
---
```

### B. Quick Link Banner (Top of Note)
```markdown
> [!TIP] **Atlas VTT Quick Link**
> 🗺️ **Atlas Scene:** `Scene Name` | 🛡️ **DM Dashboard:** [[Dashboard Note Name]]
```

### C. "5-Second Sensory Read-Aloud"
A concise evocative paragraph the DM can read verbatim when the party arrives:
- **Sight:** Lighting, architecture, shadows, and first focal point.
- **Sound:** Ambient noise, sudden sounds, echoes, or eerie silence.
- **Smell / Atmosphere:** Signature scents and temperature.

### D. 3 Improvised Quick Contacts
Three minor bystanders ready for spontaneous roleplay (approved by the DM or clearly flagged as optional prompts):
- Name/role, 1-sentence visual cue, what they want, and a signature quote.

### E. Quick `d6` Random Table (Obsidian Dice Roller)
A `d6` table of local happenings triggered with `` `dice: 1d6` ``.

---

## 4. Requirements for Atlas Scene Dashboards (`<Vault>/atlas-vtt/.../notes/`)
Linked Notes inside Atlas VTT must stay scannable at a glance and **strictly `< 30 KB`**:
1. **Quick Session Header:** Compact table with Party Level, **Pre-Calculated Party Passives** (`AGENTS.md` Rule 6), primary foes, key DCs, and core secret.
2. **Tactical Room Guide with Indexable `### H3` Headings:**
   - Every room or POI linked to a **Note Pin** must have an exact `### <Label>. <Room Name>` heading (no italic/bold formatting inside the heading text) matching the pin's `#...` anchor 1:1.
   - Tag every check with **`⚡ [Automatic Passive — PC Name]`** or **`🎲 [Active Roll — Skill DC X]`**.
3. **Compact Inline 5e Statblocks (or Direct Links):** Embed ```` ```statblock ```` blocks only for key foes (or link to `<Vault>/Monsters/`) to avoid bloating the file toward the 32 KB ceiling.
