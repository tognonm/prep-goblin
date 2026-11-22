# Obsidian Community Plugins Rule

This rule defines operational conventions for AI agents interacting with the recommended Obsidian plugins in the **{{CAMPAIGN_NAME}}** vault.

---

## 1. Fantasy Statblocks (`obsidian-5e-statblocks`)
- **Purpose:** Visual rendering of D&D 5e statblocks and bestiary indexing inside Obsidian.
- **Repository:** [Obsidian-TTRPG-Community/fantasy-statblocks](https://github.com/Obsidian-TTRPG-Community/fantasy-statblocks)
- **Agent Rule:** Use ```` ```statblock ```` YAML blocks following the `statblock-5e` skill. Always include `statblock: inline` in the frontmatter of `<Vault>/Monsters/*.md` notes so Fantasy Statblocks indexes the creature automatically.
- **Atlas VTT Integration:** Atlas reads these statblocks via `statblockPath` to auto-calculate initiative modifiers, show HP/AC, and power the *"In this fight"* filter. *(Atlas VTT also supports native statblock templates stored under `<Vault>/atlas-vtt/statblock-templates`.)*

## 2. Obsidian Dice Roller (`obsidian-dice-roller`)
- **Purpose:** Inline dice rolling and interactive random-table extraction directly inside Markdown notes.
- **Repository:** [Obsidian-TTRPG-Community/dice-roller](https://github.com/Obsidian-TTRPG-Community/dice-roller)
- **Agent Rule:** When authoring random tables in `<Vault>/Tables/` or `<Vault>/Encounters/`, attach Markdown block IDs (`^table-id`) and Dice Roller inline syntax:
  - Simple roll: `` `dice: 1d20+5` ``
  - Table lookup: `` `dice: [[Table Note Name#^table-id]]` ``

## 3. Atlas VTT (`atlas-vtt` `0.16.0`)
- **Purpose:** Local-first Virtual Tabletop inside Obsidian featuring tactical battlemaps, Dynamic Lighting, walls/doors, tokens, Note Pins, Encounter Builder, Quests, and Player View.
- **Repository & Docs:** [atlas-vtt/atlas-vtt](https://github.com/atlas-vtt/atlas-vtt) — [atlas-vtt.dev](https://atlas-vtt.dev/)
- **Agent Rule:**
  - Always follow `.atlasmap` schema `v4` and keep Dashboards/statblocks strictly under **32 KB**.
  - Use `atlas-token-art` for token registration, `dungeons-and-maps` for canonical dungeons, and `quick-battlemap` for improvised skirmishes.
  - Never hand-edit `.atlas-data/assets-metadata.json` while Obsidian is open; let `reconcileWithVault` index canonical collection records.

## 4. Iconize (`obsidian-icon-folder`) *(Recommended)*
- **Purpose:** Displays custom emoji/icons next to folders and notes in Obsidian's file explorer.
- **Agent Rule:** Include `icon: "<emoji>"` in every note's YAML frontmatter (see `AGENTS.md`).

## 5. Extended Graph (`extended-graph`) *(Optional)*
- **Purpose:** Enhanced semantic graph visualization across campaign notes.
- **Agent Rule:** Consistently use `[[Wikilinks]]` and structured YAML relationship lists (e.g., `location: ["[[Oakhaven Village]]"]`) to keep the knowledge graph rich and connected.
