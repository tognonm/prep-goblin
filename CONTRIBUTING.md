# Contributing to Prep Goblin

Thank you for your interest in improving **Prep Goblin**, an open-source, local-first agentic Dungeon Master framework for **Obsidian** and **Atlas VTT `0.16.0`**.

We welcome contributions ranging from new procedural battlemap presets and modular DM skills to vault linting checks, documentation improvements, and bug fixes.

---

## 1. Strict Copyright & Spoiler Policy (Non-Negotiable)

Before opening a pull request, verify that your changes uphold these safeguards:

- **Zero Copyrighted Rulebook Text:** Never paste text, tables, lore, or full statblocks copied from copyrighted D&D rulebooks, official adventures, or third-party commercial supplements.
- **SRD 5.1 Only for Mechanics Examples:** Any included monster statblock or mechanical example must be 100% original/fictional or strictly compatible with the open **Systems Reference Document 5.1 (CC-BY-4.0)**.
- **Zero Real Campaign Spoilers:** Keep `template-vault/` and all examples 100% fictional and free of private table lore, personal notes, or proprietary artwork.
- **Never Commit Private Reference Folders:** Folders listed in `.gitignore` (`Sources/`, `Manuals/`, `Reference/`, `Archive/`) are strictly local-only.
- **English Everywhere:** Code, docstrings, CLI flags, governance rules, skills, and starter vault notes must be written in clear, idiomatic English.

---

## 2. Development Setup

Requires **Python 3.10+**.

```bash
git clone https://github.com/tognonm/prep-goblin.git
cd prep-goblin
python -m pip install -r requirements.txt
python -m pip install pytest
```

Keep dependencies minimal: scripts should rely only on the Python standard library plus packages already listed in `requirements.txt` (`Pillow`, `numpy`, `PyYAML`).

---

## 3. Running Quality Checks Locally

Run all applicable checks before submitting a pull request:

```bash
# 1. Run the test suite
pytest

# 2. Lint the starter vault (YAML frontmatter, wikilinks, Atlas VTT 32 KB limit & full Atlas integrity)
python scripts/lint_vault.py --strict-links --full-atlas

# 3. Verify multi-agent adapter bridges match AGENTS.md and .agents/
python scripts/sync_agent_adapters.py --check

# 4. Validate the demo Atlas VTT 0.16.0 scene and linked DM Dashboard
python .agents/skills/dungeons-and-maps/scripts/atlas_scene_tools.py validate \
  "template-vault/atlas-vtt/collections/Campaign/scenes/Demo - Oakhaven Alley.atlasmap" \
  --dashboard "template-vault/atlas-vtt/collections/Campaign/notes/Demo - Oakhaven Alley.md"
```

When testing `scripts/init_campaign.py`, always pass `--target-root <temp_dir>` so you do not mutate `campaign.config.json` or `AGENTS.md` in the repository root.

---

## 4. How to Contribute

### Adding a New `quick-battlemap` Preset
1. Edit `.agents/skills/quick-battlemap/scripts/quick_battlemap.py`:
   - Add default dimensions, lighting, icon, and subtitle in `PRESET_DEFAULTS`.
   - Implement a deterministic `build_preset_<name>(...)` function using `random.Random(seed)` and `WallBuilder`, and register it in `PRESET_BUILDERS`.
2. Preserve every **Atlas VTT `0.16.0`** invariant:
   - Schema `v4`, `snapToGrid: true`, `offsetX: 0`, `offsetY: 0`.
   - Every dynamic light placed at least `25 px` away from all wall segments.
   - All token spawn cells on walkable integer grid cells (never inside walls or solid roofs).
   - No manual fog (`fog: {}`) fighting dynamic lighting.
   - Linked DM Dashboard strictly `< 30 KB` with exact 1:1 `### H3` Note Pin anchors.
   - Support both `feet` and `meters` via `fmt_dist(...)` and `unit_dist`.
3. Update `.agents/skills/quick-battlemap/SKILL.md` and run `--dry-run` plus `atlas_scene_tools.py validate` on generated output in a temporary directory.

### Adding or Updating a Skill or Governance Rule
1. **Respect Skill Boundaries:** Review the Anti-Overlap Skill Matrix in `.agents/rules/live-improv-and-boundaries.md` so each skill keeps a clear, non-overlapping scope.
2. **Skill Format (`.agents/skills/<skill-name>/SKILL.md`):**
   - Include valid YAML frontmatter with `name` and a concise, single-paragraph `description`.
   - Keep instructions concise, actionable, and compliant with DM-as-Reviewer governance (`AGENTS.md` Rule 5).
3. **Rule Format (`.agents/rules/<rule-name>.md`):**
   - Start with a clear `# H1` title describing the rule's scope.
4. **Regenerate Multi-Agent Adapters (Mandatory):**
   Whenever you add, rename, or update files in `.agents/rules/` or `.agents/skills/`, regenerate the adapter bridge files (`CLAUDE.md`, `.cursor/rules/prep-goblin.mdc`, `.github/copilot-instructions.md`) instead of editing them by hand:
   ```bash
   python scripts/sync_agent_adapters.py
   python scripts/sync_agent_adapters.py --check
   ```

### Improving `template-vault/`
- Follow the YAML frontmatter standard in `AGENTS.md` (including `title`, `icon`, `tags`, `type`, `status`).
- Keep Obsidian Bases (`.base`) files valid YAML and verify all `[[wikilinks]]` and Atlas assets pass `python scripts/lint_vault.py --strict-links --full-atlas`.
- Keep all Atlas linked notes and monster statblocks strictly under `32 KB` (target `< 30 KB`).

---

## 5. Code Style & Pull Request Checklist

- **Cross-Platform Paths:** Always use `pathlib.Path` rather than hardcoded OS path separators.
- **Windows UTF-8 Safety:** Reconfigure `sys.stdout` and `sys.stderr` with `encoding="utf-8", errors="replace"` in CLI entry points.
- **Clean PR Diff:** Remove temporary test artifacts and `__pycache__` directories before committing.

Before opening your PR, check:
- [ ] Zero copyrighted rulebook text and zero real campaign spoilers.
- [ ] `pytest` passes.
- [ ] `python scripts/lint_vault.py --strict-links --full-atlas` passes with 0 errors and 0 broken links.
- [ ] `python scripts/sync_agent_adapters.py --check` exits `0`.
- [ ] Any modified scripts were tested via `--dry-run` or an isolated temporary directory.
