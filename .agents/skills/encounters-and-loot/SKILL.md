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

## 1. Encounter Balancing (XP Budget)
When building an encounter:
1. Check party size and level from `campaign.config.json` / `<Vault>/Campaign/Players/`.
2. Calculate the target XP budget (*Low*, *Moderate*, *High*) using your table's 5e guidelines.
3. Select creatures from `<Vault>/Monsters/` (or your reference bestiary) while watching action economy balance.
4. Output a clean summary table: **Creature | Qty | CR | XP Each | Total XP | Target Difficulty**, paired with at least 1 tactical terrain feature (cover, lighting, elevation, or secondary objective).

---

## 2. Treasure & Loot
- **Individual Treasure:** Coins, salvageable gear, and small pocket items matching enemy roles.
- **Hoard Treasure:** Reserved for bosses, vaults, or story milestones; confirm magic-item rarity fits party tier.
- Format loot as clean Markdown tables ready to paste into session logs or player handouts.

---

## 3. Atlas VTT `0.16.0` Integration
- **Prefer Standard / SRD Statblocks:** Keep standard monster stats unmodified (`AGENTS.md` Rule 7); use narrative reskinning for faction flavor without breaking math.
- **Encounter Builder (`<Vault>/atlas-vtt/collections/{{ATLAS_COLLECTION}}/encounters/`):** Save planned fights as `encounter-*.json` records inside the Atlas collection for 1-click placement previews and Note Pin linking.
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
