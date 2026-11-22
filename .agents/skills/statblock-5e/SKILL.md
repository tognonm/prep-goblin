---
name: statblock-5e
description: >-
  Compiles D&D 5e statblocks in Obsidian Fantasy Statblocks YAML format fully compatible
  with Atlas VTT 0.16.0 (auto-initiative, hover tooltips, bestiary indexing, and < 32 KB
  size compliance). Use when creating, importing, or scaling monsters and combat NPCs.
---

# 5e Statblocks for Fantasy Statblocks & Atlas VTT `0.16.0`

Atlas VTT `0.16.0` natively parses ```` ```statblock ```` blocks from **Fantasy Statblocks** (as well as its own native statblock templates in `<Vault>/atlas-vtt/statblock-templates`), powering hover tooltips, direct dice rolling, and automatic initiative bonuses whenever `statblockPath` is linked on a token.

---

## 1. Sources & Anti-Hallucination Rule
1. **SRD 5.1 / DM's Local Reference:** Verify exact numbers against SRD 5.1 (CC-BY-4.0) or any private local manuals kept in the gitignored `Sources/` directory (never committed).
2. **Custom / Homebrew Creatures:** If a creature does not exist in your reference material, state so explicitly, build it cleanly to CR targets, and label it `*Homebrew*`.
3. Never guess official values and present them as canon; flag any missing data clearly.

---

## 2. Standard Creatures vs. Custom Variants vs. PCs
- **Standard Creatures (`AGENTS.md` Rule 7):** Keep official AC, HP, stats, actions, and traits intact; handle faction flavor in room prose.
- **Custom / Boss Variants:** Permitted when filling an uncovered role or CR; list all adjustments explicitly.
- **Player Characters (PCs):** Do not create monster statblocks for PCs; use `"playerCharacter": true` on tokens and sync HP via `<Vault>/atlas-vtt/campaigns/<campaign_slug>/characters.json`.

---

## 3. Atlas VTT `0.16.0` Integration
- **Bestiary Frontmatter:** Always set `statblock: inline` in YAML frontmatter for notes under `<Vault>/Monsters/` so Fantasy Statblocks indexes the entry.
- **Token Linking (`statblockPath`):** Setting `statblockPath: "Monsters/<Name>.md"` in `tokens/*.json` enables automatic initiative calculation and the *"In this fight"* filter inside Atlas VTT.
- **Hard 32 KB Limit:** Every statblock note must stay under **32 KB** (`32768 bytes`), checked automatically by `python scripts/lint_vault.py`.
- **Dice Formulas & Art:** Supports dice expressions (`2d20kh1`, `1d8+3`) and linked portraits (`image: [[<portrait>.webp]]`).

---

## 4. Authoring Checklist
1. Start from `.agents/skills/statblock-5e/resources/statblock_template.md`.
2. Keep all YAML keys exact for Fantasy Statblocks (`name`, `ac`, `hp`, `stats`, `actions`, etc.).
3. Verify math consistency: average HP vs. Hit Dice, proficiency bonus for CR, save DC = `8 + prof + mod`.
4. Save to `<Vault>/Monsters/<Name>.md` (or `<Vault>/NPCs/` for named story NPCs) with valid YAML frontmatter.
5. Register matching token art via `atlas-token-art` + `register_token.py`.
6. Close with source attribution (e.g., `*Source: SRD 5.1 (CC-BY-4.0).*` or `*Homebrew — original variant.*`).
