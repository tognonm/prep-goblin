---
name: encounters-and-loot
description: >-
  Balances D&D 5e combat encounters using XP budgets for party level, generates tier-appropriate
  individual and hoard treasure, and configures Encounter JSONs, Random Tables, and native Quests
  for Atlas VTT 0.16.0.
---

# Encounters & Loot (`encounters-and-loot`)

Ensures planned encounters are mechanically balanced, tactically engaging, and cleanly integrated with **Atlas VTT `0.16.0`**.

---

## 1. Encounter Balancing (XP Budget) & Automated Builder
When building an encounter:
1. Check party size and level from `campaign.config.json` / `<Vault>/Campaign/Players/`.
2. Calculate the target XP budget using either the **2024 5e ruleset** (*Low*, *Moderate*, *High* — direct XP budgets, no size multiplier) or **2014 5e ruleset** (*Easy*, *Medium*, *Hard*, *Deadly* — with standard encounter-size multipliers).
3. Select creatures from `<Vault>/Monsters/` (or your reference bestiary) while watching action-economy balance.
4. Run **`scripts/build_encounter.py`** to compute the XP math, evaluate action-economy ratio, and generate both the Markdown encounter note and the Atlas VTT `0.16.0` Encounter JSON in one step:

```bash
# Default (2024 ruleset, party level/size from campaign.config.json)
python scripts/build_encounter.py --name "Oakhaven Alley Ambush" --enemies "Road Raider:2,Skeleton Sentry:1"

# Dry-run XP check under 2014 ruleset with custom party overrides
python scripts/build_encounter.py --name "Bridge Blockade" --enemies "Road Raider:4" --ruleset 2014 --party-level 3 --party-size 4 --dry-run

# Ad-hoc creatures with explicit HP (@11) and optional CR (#1/4)
python scripts/build_encounter.py --name "Night Wolf Pack" --enemies "Wolf:3@11#1/4" --dry-run
```

### CLI Options (`scripts/build_encounter.py`)
- `--name "<Encounter Name>"` *(required)*: Encounter display name and `<Vault>/Encounters/<Encounter Name>.md` filename.
- `--enemies "<Spec>"` *(required)*: Comma-separated creature spec matching `quick-battlemap` syntax (`"Road Raider:2,Skeleton Sentry:1"`, `"Wolf:3@11"`, or `"Wolf:3@11#1/4"` for explicit ad-hoc CR). Dynamically parses `<Vault>/Monsters/*.md` and `<Vault>/atlas-vtt/collections/<Col>/tokens/*.json`.
- `--ruleset {2024,2014}`: XP budget ruleset (`2024` default).
- `--party-level <int>` / `--party-size <int>`: Override `campaign.config.json` party settings (levels `1–20`).
- `--slug <str>`: Deterministic Encounter record ID (`encounter-<slug>.json`).
- `--collection <Name>` / `--vault <Path>` / `--config <File>` / `--out-dir <Path>`: Override collection, vault, or isolated output directory.
- `--dry-run`: Print full XP math, action-economy ratio, and resolved creatures without writing files.

### Generated Outputs
1. **`<Vault>/Encounters/<Encounter Name>.md`**: YAML frontmatter (`ruleset`, `difficulty`, `total_xp`, `atlas_encounter`), enemy summary table with escaped wikilinks (`[[Monsters/Road Raider\|Road Raider]]`), XP & action-economy breakdown, pre-calculated party passives from `campaign.config.json`, and a tactical terrain/morale checklist.
2. **`<Vault>/atlas-vtt/collections/{{ATLAS_COLLECTION}}/encounters/<encounter_id>.json`**: Atlas VTT `0.16.0` Encounter record (`atlasRecord` format 1, `type: "encounter"`, `entries` with `name`, `count`, `hp`, `imagePath`, `statblockPath`, `size`, `cr`, `xp`).

---

## 2. Treasure & Loot
- **Individual Treasure:** Coins, salvageable gear, and small pocket items matching enemy roles.
- **Hoard Treasure:** Reserved for bosses, vaults, or story milestones; confirm magic-item rarity fits party tier.
- Format loot as clean Markdown tables ready to paste into session logs or player handouts.

---

## 3. Atlas VTT `0.16.0` Integration
- **Prefer Standard / SRD Statblocks:** Keep standard monster stats unmodified (`AGENTS.md` Rule 7); use narrative reskinning for faction flavor without breaking math.
- **Encounter Builder (`<Vault>/atlas-vtt/collections/{{ATLAS_COLLECTION}}/encounters/`):** Use `scripts/build_encounter.py` to generate `encounter-*.json` records inside the Atlas collection for 1-click placement previews and Note Pin linking, and pair with `quick-battlemap` using the exact same `--enemies` spec when you also need a tactical map.
- **Random Tables (`collection.json`):** Register `<Vault>/Tables/*.md` files inside `settings.randomTables` (`{"path": "Tables/<Name>.md", "index": 0}`) in `collection.json` so they are directly rollable from Atlas VTT's UI.
- **Native Quests (`<Vault>/Campaign/Quests/*.md`):** Include standard YAML properties in every quest note:
  ```yaml
  atlas-type: "quest"
  campaign: "<atlas_campaign_id from campaign.config.json>"
  kind: "main" # or "side"
  status: "open" # open | active | done | failed
  experience: 300
  rewards:
    - "Reward 1"
  ```
