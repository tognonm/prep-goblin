---
name: atlas-token-art
description: >-
  Generates cohesive dark-fantasy portraits for monsters and NPCs by inferring weapons,
  armor, and visual traits from statblocks or lore, links the portrait in Obsidian, and
  registers the token cleanly for Atlas VTT 0.16.0.
---

# Token Art Generation & Registration (`atlas-token-art` — Atlas VTT `0.16.0`)

This skill governs portrait creation for creatures and NPCs, linking artwork in Obsidian notes, and registering ready-to-play tokens inside **Atlas VTT `0.16.0`**.

---

## 1. Standard Monsters vs. Named Story NPCs

### Case A: Standard Monsters & Creatures (`<Vault>/Monsters/<Name>.md`)
Used for generic enemies, guards, beasts, undead, and minions.
1. **Read the Statblock:** Inspect the monster note in `<Vault>/Monsters/`.
2. **Infer Iconic Gear & Form:**
   - Parse `actions:` and `traits:` for signature weapons (curved blade, halberd, shortbow).
   - *Natural weapons rule:* If the creature fights with claws, bite, horns, or tentacles, **do not** depict handheld weapons; emphasize anatomy and stance instead.
   - Match armor cues from `ac:` and scale from `size:`.
3. **Generate Artwork:** Square (`1:1`) aspect ratio following `.agents/rules/art-style.md` and `resources/prompt_template.md`.
4. **Save Portrait:** Save under `<Vault>/Monsters/Portraits/<filename>.webp` (or `.jpg`/`.png`).
5. **Link Inside the Note:**
   - Frontmatter: `image: "[[<filename>.webp]]"` and `statblock: inline` (required for Fantasy Statblocks bestiary indexing and interactive Atlas tooltips).
   - Inside the ```` ```statblock ```` block: `image: [[<filename>.webp]]`.
6. **Register Token for Atlas VTT `0.16.0`:**
   ```bash
   python .agents/skills/atlas-token-art/scripts/register_token.py "<image_path>" --name "<Name>" --statblock "Monsters/<Name>.md"
   ```
   The script center-crops to `400×400` WebP, generates a `128×128` thumbnail, and writes `tokens/token-*.json` in the configured Atlas collection (auto-indexed by Atlas `0.16.0` via `reconcileWithVault`).
   - **PC Tokens (`--player`):** Sets `"playerCharacter": true` so HP syncs across scenes via `<Vault>/atlas-vtt/campaigns/<campaign_slug>/characters.json`.

---

### Case B: Named Story NPCs (`<Vault>/NPCs/<Name>.md`)
Story NPCs have a distinct identity (and sometimes a disguise separate from their combat statblock).
1. **Read Narrative Lore:** Read the physical appearance section of the NPC note.
2. **Generate Portrait:** Depict their visible public appearance/disguise.
3. **Save Portrait:** Save under `<Vault>/NPCs/Portraits/<filename>.webp`.
4. **Link Inside the NPC Note:** Add `image: "[[<filename>.webp]]"` in frontmatter and `![[<filename>.webp]]` in the body.
5. **Register Token:** Run `register_token.py` (with optional `--statblock`) or create directly from Atlas VTT's *From vault* picker.

---

## 2. Prompt Guidelines
- Always append the style suffix defined in `.agents/rules/art-style.md`.
- **Framing:** Chest-up three-quarter portrait, centered and instantly legible at small grid sizes.
- **No Drawn Rings or Borders:** Never draw circular borders or frames (Atlas VTT renders dynamic token rings automatically).
- **Backdrop:** Clean dark atmospheric backdrop for crisp silhouette readability.
