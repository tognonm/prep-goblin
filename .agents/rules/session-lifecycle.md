# Session Lifecycle & Living World Update Rule

This rule defines the mandatory check every agent must perform at the start of a conversation with the DM to keep the vault synchronized with table play.

---

## 1. Conversation Startup Check (Session Check)
At the beginning of a chat session or when the DM resumes campaign work:
1. **Verify session progress:**
   - Ask politely:
     > *"Since we last worked together, have you played one or more sessions? If so, how many sessions and how many in-game days have passed?"*
2. **If NO sessions were played:**
   - Proceed directly with the DM's request or prep.
3. **If ONE OR MORE sessions were played:**
   - Collect the DM's rough notes or summary of what happened.
   - Run the post-session update workflow (`session-recap` + `living-world`).

---

## 2. Post-Session Update Procedure
When sessions have been played or in-game time has elapsed:
1. **Update `<Vault>/Sessions/Campaign Log.md`:**
   - Append a new row to the summary table (Session #, real date, in-game date, location, key events, clocks).
   - Link the detailed recap note in `<Vault>/Sessions/Session NN.md`.
2. **Update `<Vault>/Campaign/World State.md`:**
   - Advance the in-game date according to your campaign calendar.
   - Update the party's current location and shared resources (gold, key items, clues).
3. **Advance Faction Clocks (`<Vault>/Campaign/Factions/`):**
   - Review all active factions listed in `World State.md` and `<Vault>/Campaign/Factions/`.
   - Propose clock updates based on party actions and elapsed time (`living-world`).
   - Surface visible consequences for the players (rumors, prices, patrols, NPC reactions).
4. **Update Player Character Arcs (`<Vault>/Campaign/Players/`):**
   - Update personal goals, bonds, debts, pacts, or milestones for each PC note.
5. **Triage `<Vault>/Campaign/Improv Log.md`:**
   - Review improvised NPCs, venues, events, and on-the-fly battlemaps with the DM (`live-improv-and-boundaries.md`).
   - Propose which entries to **promote to canon** (`<Vault>/NPCs/` or `<Vault>/Locations/`), which to keep as `recurring`/`ephemeral`, and which throwaway quick battlemaps to archive or delete.
   - If the party is entering a new region or biome, suggest adding regional `Wildcard - *` quick-battlemap presets (`quick-battlemap`).
6. **Final Integrity Lint:**
   - Run `python scripts/lint_vault.py` to check YAML frontmatter, wikilinks, and Atlas VTT's 32 KB limit.
