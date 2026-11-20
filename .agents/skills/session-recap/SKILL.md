---
name: session-recap
description: >-
  Turns rough DM session notes into a polished official session log separating player-safe
  narrative from DM secrets, updates World State.md and active Quests, triages Improv Log.md,
  and tees up hooks for the next session.
---

# Session Recap (`session-recap`)

Converts rough notes, bullet lists, or transcripts from the DM into a clean canonical session record while keeping the entire vault synchronized.

---

## Output File: `<Vault>/Sessions/Session NN.md`

Use valid YAML frontmatter:
```yaml
---
title: "Session NN - Title"
icon: "📜"
tags: [session, recap]
type: "Session"
real_date: "YYYY-MM-DD"
in_game_date: "Day X"
status: "played"
---
```

Required sections:
1. **Player-Safe Recap:** Engaging narrative summary containing zero DM secrets (strictly what the PCs witnessed or learned), ready to share before next session.
2. **DM Log:**
   - Crisp chronological bullet points of what actually occurred.
   - Secrets revealed, brushed past, or still hidden (isolated in `> [!danger] DM Secret` callouts).
3. **World Updates:**
   - Loot gained and XP / milestone progress.
   - Quest status updates (Opened, Advanced, Completed, Failed).
   - Newly encountered NPCs or locations (wikilinked if promoted to canon).
4. **Open Threads for Next Session:** Unresolved questions, looming threats, or cliffhangers.

---

## Mandatory Side Effects
After authoring `Session NN.md`, update:
1. `<Vault>/Sessions/Campaign Log.md`: Append a summary row to the chronological table.
2. `<Vault>/Campaign/World State.md`: Update in-game date, current party location, and shared resources.
3. `<Vault>/Campaign/Quests/*.md`: Sync `status` (`open`, `active`, `done`, `failed`) for Atlas VTT `0.16.0`.
4. `<Vault>/Campaign/Improv Log.md`: Run post-session triage with the DM to decide what to promote to canon (`Locations/` or `NPCs/`), keep as `recurring`/`ephemeral`, or clean up (`live-improv-and-boundaries.md`).
5. If in-game days passed or factions reacted, trigger `living-world`.

---

## Rules & Verification Checklist
- Cross-check misspelled proper nouns against existing vault notes.
- **Never invent** events absent from the DM's notes.
- [ ] Created `<Vault>/Sessions/Session NN.md` and updated `Campaign Log.md`?
- [ ] Updated `World State.md` and Quest statuses?
- [ ] Completed `Campaign/Improv Log.md` triage with the DM?
- [ ] Executed `python scripts/lint_vault.py`?
