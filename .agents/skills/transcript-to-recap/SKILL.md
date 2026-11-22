---
name: transcript-to-recap
description: >-
  Preprocesses raw audio or Discord session transcripts (.srt, .vtt, .txt) via
  scripts/prep_transcript.py, extracts candidate events, loot, quest updates,
  improvised NPCs, and faction clock triggers against the auto-extracted Vault
  Proper-Noun Glossary, presents an Extraction Review Sheet for DM-as-Reviewer
  approval, and hands off approved changes to session-recap and living-world.
---

# Transcript to Recap (`transcript-to-recap`)

Converts raw audio transcriptions (Whisper, Zoom, YouTube, Discord Craig `.srt` / `.vtt` / `.txt`) into verified, canon-safe campaign updates without burning context tokens on timestamps or letting speech-to-text errors drift campaign lore.

> [!IMPORTANT] DM-as-Reviewer Gate (`dm-reviewer-narrative-authority.md`)
> Raw transcripts contain out-of-character banter, misheard proper nouns, and throwaway table improvisation. **NEVER** write directly into canonical notes (`Sessions/`, `NPCs/`, `Locations/`, `Campaign/World State.md`, `Campaign/Factions/`) before presenting the **Extraction Review Sheet** and receiving explicit DM approval.

---

## 1. Anchor Live Canon & Preprocess Transcript

Before reading the transcript, anchor current vault canon and compress the raw file:

1. **Compile live context (optional but recommended for long campaigns):**
   ```bash
   python scripts/build_context_pack.py --out .tmp_context_pack.md
   ```
   Read the snapshot so active quests, current party location, and existing faction clocks are top of mind.

2. **Clean and chunk the transcript with the Vault Proper-Noun Glossary:**
   ```bash
   python scripts/prep_transcript.py path/to/session_audio.srt --out-dir .tmp_transcript_chunks
   ```
   - Supported inputs: `.srt` (SubRip), `.vtt` (WebVTT with `<v Speaker>` tags), and `.txt` (Discord / raw `Speaker: text`).
   - Automatically strips timestamps, cue IDs, empty noise cues, and duplicate lines, merging consecutive lines by the same speaker for 40–60% token savings.
   - Prefixes every chunk (`chunk_01.md`, `chunk_02.md`, ...) with the **Vault Proper-Noun Glossary** (Players, NPCs, Locations, Factions, Quests, Monsters + frontmatter aliases) and overlapping continuity windows (`--chunk-words 2500`, `--overlap-words 150`).
   - To inspect only the extracted proper-noun reference list, run:
     ```bash
     python scripts/prep_transcript.py --glossary-only
     ```

---

## 2. Chunk-by-Chunk Candidate Extraction

Read `chunk_01.md`, `chunk_02.md`, ... sequentially and accumulate structured **candidates** in working memory (ignoring duplicate events inside `*[Overlap from previous chunk]*` sections):

1. **Proper-Noun Disambiguation:**
   - Map likely speech-to-text errors (e.g., *"Oak Haven"* -> `[[Oakhaven Village]]`, *"Myra"* -> `[[Mira the Cleric]]`) strictly against the injected **Vault Proper-Noun Glossary**.
   - List every unrecognized proper noun separately for DM verification — never guess or fabricate canonical ties.
2. **Chronological Events (Player-Safe vs. DM-Only):**
   - **Player-Safe beats:** What the PCs witnessed, decided, or learned in-character.
   - **DM-Only beats:** Behind-the-screen rolls, missed clues, unrevealed motives, or meta reminders (isolated later in `> [!danger] DM Secret` callouts).
3. **Loot, Gold & Resource Deltas:**
   - Treasury changes, claimed items, spent consumables, and physical clues gained.
4. **Quest Progress Candidates:**
   - New hooks accepted, objectives checked off, or status transitions (`open`, `active`, `done`, `failed`) for `<Vault>/Campaign/Quests/*.md`.
5. **Improvised Elements (`live-improv-and-boundaries.md`):**
   - Newly improvised NPCs, shops, venues, or side-encounters that entered play. Stage these as **candidates for `<Vault>/Campaign/Improv Log.md`** (or ask whether any standout element deserves promotion to `<Vault>/NPCs/` or `<Vault>/Locations/`).
6. **Faction Clock & Downtime Triggers (`living-world`):**
   - In-game days elapsed, faction plans disrupted or ignored, and visible fallout witnessed at the table.

---

## 3. Mandatory DM-as-Reviewer Approval Gate

Stop and present a concise **Extraction Review Sheet** to the DM containing:

- **Proposed Player-Safe Recap Bullets** (5–10 crisp chronological points)
- **Proposed DM-Only Notes / Missed Clues**
- **Unrecognized Proper Nouns & Ambiguities** *(Ask explicitly: "Is Name X a misspelling of an existing vault entity, a new ephemeral bystander for `Improv Log.md`, or OOC table banter to discard?")*
- **Loot, Gold & In-Game Date Delta** (for `Campaign/World State.md`)
- **Quest Updates** (proposed edits to `Campaign/Quests/*.md`)
- **Improvised Elements Triage** (log in `Improv Log.md` as `ephemeral` / `recurring`, promote to canon, or drop)
- **Proposed Faction Clock Adjustments** (for `living-world`)

Wait for the DM to edit, reject, or approve every item before modifying any vault file.

---

## 4. Canonical Handoff (`session-recap` & `living-world`)

Once the DM approves the Extraction Review Sheet:

1. **Hand off to `session-recap`:**
   - Author `<Vault>/Sessions/Session NN.md` with separate **Player-Safe Recap** and **DM Log** (`> [!danger] DM Secret`) sections.
   - Append a chronological row to `<Vault>/Sessions/Campaign Log.md`.
   - Update `<Vault>/Campaign/World State.md` (session counter, in-game date, party location, shared resources).
   - Sync quest `status` values in `<Vault>/Campaign/Quests/*.md` for Atlas VTT `0.16.0`.
   - Apply approved triage decisions to `<Vault>/Campaign/Improv Log.md` (and create canonical notes in `NPCs/` or `Locations/` only if the DM explicitly approved promotion).
2. **Hand off to `living-world` (if days passed or factions reacted):**
   - Commit approved clock segment shifts to `<Vault>/Campaign/World State.md` and `<Vault>/Campaign/Factions/*.md`.
   - Record observable fallout hooks for the next `session-prep`.
3. **Clean up & Verify:**
   - Delete temporary working folders (`.tmp_transcript_chunks/`, `.tmp_context_pack.md`) so raw transcripts are never accidentally committed.
   - Run `python scripts/lint_vault.py` to verify YAML frontmatter, wikilinks, and Atlas VTT's 32 KB limit.
   - *(Optional)* Export an updated spoiler-free player recap/portal via:
     ```bash
     python scripts/export_player_view.py --out <player-export-dir> --verify
     ```

---

## Rules & Verification Checklist

- **Never invent** events, NPCs, or secrets absent from the transcript and DM confirmation.
- **Discard OOC table banter** (rules debates, snack breaks, scheduling talk) cleanly.
- [ ] Preprocessed raw transcript with `scripts/prep_transcript.py` and resolved proper nouns against the Vault Glossary?
- [ ] Presented the Extraction Review Sheet and received explicit **DM-as-Reviewer** approval?
- [ ] Completed `session-recap` updates (`Session NN.md`, `Campaign Log.md`, `World State.md`, `Quests/`, `Improv Log.md`)?
- [ ] Handed off elapsed-time / faction reactions to `living-world`?
- [ ] Removed temporary chunk files and passed `python scripts/lint_vault.py`?
