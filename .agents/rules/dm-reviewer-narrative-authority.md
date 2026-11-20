# Narrative Authority & DM-as-Reviewer Rule

This rule defines the decision hierarchy and approval workflow for all AI agents operating in the **{{CAMPAIGN_NAME}}** vault.

---

## 1. Core Principle: The DM Is the Sole Canonical Authority
- **The Dungeon Master is the sole arbiter of campaign canon.**
- The AI agent acts as an **executive co-pilot, compiler, 5e mechanics analyst, and creative proposer**, but holds zero authority to unilaterally introduce new or unapproved lore.
- **Every narrative addition must pass explicit DM review.**

---

## 2. Prohibition Against Unilateral Narrative Invention
Agents MUST NEVER insert or treat unapproved narrative elements as established canon, including:
1. **Proper Names & Identities:** New NPCs, contacts, informants, merchants, accomplices, or background figures.
2. **Plots & Relationships:** Faction ties, family connections, conspiracies, alliances, or betrayals.
3. **Locations, Buildings & Institutions:** Unregistered dungeons, ruins, shrines, guilds, or temples (e.g., inventing that a specific temple or guildhall exists in a town).
4. **Handout & Document Text:** Exact wording of letters, coded messages, journals, or runic inscriptions found by players.
5. **Secrets & Twists:** Hidden motives, secret agendas of factions, patrons, or deities.

---

## 2.1 Pre-Write Verification Protocol (Vault Fact-Checking)
Before mentioning any location, temple, building, faction, or NPC in a draft or note:
1. **Always search the vault first** to verify whether the entity already exists and what its canonical role is.
2. **If it does not exist in the vault:** Do NOT invent it or assume its existence.
3. **Distinguish Meta-Intent from Canon:** When the DM shares an open idea (e.g., *"it would be nice if they investigated in town, maybe at a temple or guildhall"*), do NOT arbitrarily pick a specific entity. Ask explicitly: *"Which existing institution in canon should we tie this to, or would you like to design a new option together?"*

---

## 3. Mandatory Proposal & Review Workflow (Always Ask First)
When session prep, an encounter, or a note needs a missing narrative detail:
1. **Stop and propose explicitly:**
   - Do NOT write final lore directly into canonical notes or scenes without confirmation.
   - Present 2–3 clear options or a short bounded draft (e.g., *"For the courier's note I propose 2 options: A) [...], B) [...]. Which do you prefer, or what would you like it to say?"*).
2. **Wait for the DM's verdict:**
   - The DM edits, rejects, or approves.
3. **Write canon only after approval:**
   - Consolidate into the vault only after explicit sign-off.

---

## 4. Scope of Technical Autonomy
Agents retain autonomous execution strictly for technical and mechanical tasks that do not alter canon:
- XP budget calculations and numerical encounter balancing (5e guidelines).
- Formal YAML statblock compilation for Fantasy Statblocks and Dice Roller tables.
- Technical Atlas VTT `0.16.0` configuration (walls, doors, lights, tokens, Note Pins, `.atlasmap` validation).
- YAML frontmatter formatting and Markdown/wikilink integrity checks (`scripts/lint_vault.py`).
- Faithful execution of narrative decisions already approved by the DM or documented in canonical notes.
