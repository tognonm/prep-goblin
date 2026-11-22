"""Tests for scripts/lint_vault.py and scripts/sync_agent_adapters.py."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from conftest import (
    REPO_ROOT,
    SCRIPT_LINT,
    SCRIPT_SYNC_ADAPTERS,
    TEMPLATE_VAULT,
    run_cli,
)


# ---------------------------------------------------------------------------
# scripts/lint_vault.py
# ---------------------------------------------------------------------------


def test_lint_vault_passes_template_vault_strict_and_full_atlas() -> None:
    res = run_cli(SCRIPT_LINT, "--vault", TEMPLATE_VAULT, "--strict-links", "--full-atlas")
    assert res.returncode == 0, res.stdout + res.stderr
    assert "No YAML syntax, Atlas integrity, or size limit errors found." in res.stdout
    assert "No broken wikilinks found." in res.stdout
    assert "Full Atlas audit:" in res.stdout


def test_lint_vault_catches_broken_wikilink(isolated_vault: Path) -> None:
    note = isolated_vault / "Locations" / "Oakhaven Village.md"
    note.write_text(
        note.read_text(encoding="utf-8") + "\nSee also [[Nonexistent Rumor Target]].\n",
        encoding="utf-8",
    )
    res = run_cli(SCRIPT_LINT, "--vault", isolated_vault, "--strict-links")
    assert res.returncode == 1
    assert "Nonexistent Rumor Target" in res.stdout


def test_lint_vault_catches_oversized_atlas_dashboard(isolated_vault: Path) -> None:
    dash = (
        isolated_vault
        / "atlas-vtt"
        / "collections"
        / "Campaign"
        / "notes"
        / "Demo - Oakhaven Alley.md"
    )
    oversized = dash.read_text(encoding="utf-8") + "\n" + ("A" * 33000) + "\n"
    dash.write_text(oversized, encoding="utf-8")
    res = run_cli(SCRIPT_LINT, "--vault", isolated_vault, "--strict-links", "--full-atlas")
    assert res.returncode == 1
    assert "32 KB limit exceeded" in res.stdout


def test_lint_vault_catches_missing_token_statblock_path(isolated_vault: Path) -> None:
    tok_path = (
        isolated_vault
        / "atlas-vtt"
        / "collections"
        / "Campaign"
        / "tokens"
        / "token-demo-raider.json"
    )
    data = json.loads(tok_path.read_text(encoding="utf-8"))
    data["atlasRecord"]["statblockPath"] = "Monsters/Missing Phantom.md"
    tok_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_cli(SCRIPT_LINT, "--vault", isolated_vault, "--strict-links", "--full-atlas")
    assert res.returncode == 1
    assert "missing statblockPath" in res.stdout
    assert "Monsters/Missing Phantom.md" in res.stdout


def test_lint_vault_catches_missing_pin_heading(isolated_vault: Path) -> None:
    scene_path = (
        isolated_vault
        / "atlas-vtt"
        / "collections"
        / "Campaign"
        / "scenes"
        / "Demo - Oakhaven Alley.atlasmap"
    )
    data = json.loads(scene_path.read_text(encoding="utf-8"))
    pins = data["state"]["objects"]["pins"]
    first_pin_id = next(iter(pins))
    pins[first_pin_id]["notePath"] = (
        "atlas-vtt/collections/Campaign/notes/Demo - Oakhaven Alley.md#Z. Missing Chamber Heading"
    )
    scene_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_cli(SCRIPT_LINT, "--vault", isolated_vault, "--strict-links", "--full-atlas")
    assert res.returncode == 1
    assert "Z. Missing Chamber Heading" in res.stdout


def test_lint_vault_catches_invalid_yaml_frontmatter(isolated_vault: Path) -> None:
    bad_note = isolated_vault / "Lore" / "Broken Note.md"
    bad_note.write_text(
        "---\ntitle: \"Unclosed Quote\ntags: [lore, [nested\n---\n\nBody text.\n",
        encoding="utf-8",
    )
    res = run_cli(SCRIPT_LINT, "--vault", isolated_vault, "--strict-links")
    assert res.returncode == 1
    assert "Invalid YAML frontmatter" in res.stdout


def test_lint_vault_warns_on_untriaged_improv_review_row(isolated_vault: Path) -> None:
    improv_path = isolated_vault / "Campaign" / "Improv Log.md"
    improv_path.write_text(
        improv_path.read_text(encoding="utf-8")
        + "| Day 4 | Barnaby the Cobbler | Oakhaven Village | Owes Kael a favor | `review` |\n",
        encoding="utf-8",
    )
    res = run_cli(SCRIPT_LINT, "--vault", isolated_vault, "--strict-links", "--full-atlas")
    assert res.returncode == 0, res.stdout + res.stderr
    assert "--- WARNINGS ---" in res.stdout
    assert "status: review" in res.stdout
    assert "Barnaby the Cobbler" in res.stdout


def test_lint_vault_catches_windows_backslashes_in_atlas_json_paths(isolated_vault: Path) -> None:
    tok_path = (
        isolated_vault
        / "atlas-vtt"
        / "collections"
        / "Campaign"
        / "tokens"
        / "token-demo-raider.json"
    )
    data = json.loads(tok_path.read_text(encoding="utf-8"))
    data["atlasRecord"]["statblockPath"] = r"Monsters\Road Raider.md"
    tok_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    res = run_cli(SCRIPT_LINT, "--vault", isolated_vault, "--strict-links", "--full-atlas")
    assert res.returncode == 1
    assert "Windows backslash" in res.stdout
    assert "statblockPath" in res.stdout


def test_lint_vault_warns_on_bold_review_improv_row_with_escaped_pipe(isolated_vault: Path) -> None:
    improv_path = isolated_vault / "Campaign" / "Improv Log.md"
    improv_path.write_text(
        improv_path.read_text(encoding="utf-8")
        + "| Day 5 | [[Locations/Oakhaven Village\\|Oakhaven Market]] | Oakhaven Village | "
        + "Improvised spice merchant | **review** |\n",
        encoding="utf-8",
    )
    res = run_cli(SCRIPT_LINT, "--vault", isolated_vault, "--strict-links", "--full-atlas")
    assert res.returncode == 0, res.stdout + res.stderr
    assert "--- WARNINGS ---" in res.stdout
    assert "status: review" in res.stdout
    assert "Oakhaven Market" in res.stdout


# ---------------------------------------------------------------------------
# scripts/sync_agent_adapters.py
# ---------------------------------------------------------------------------


def test_sync_agent_adapters_check_passes_on_repo() -> None:
    res = run_cli(SCRIPT_SYNC_ADAPTERS, "--check")
    assert res.returncode == 0, res.stdout + res.stderr
    assert "up to date" in res.stdout


def test_sync_agent_adapters_detects_drift_and_repairs_temp_copy(tmp_path: Path) -> None:
    temp_repo = tmp_path / "repo"
    temp_repo.mkdir()
    shutil.copy2(REPO_ROOT / "AGENTS.md", temp_repo / "AGENTS.md")
    shutil.copytree(REPO_ROOT / ".agents", temp_repo / ".agents")
    shutil.copy2(REPO_ROOT / "CLAUDE.md", temp_repo / "CLAUDE.md")
    shutil.copytree(REPO_ROOT / ".cursor", temp_repo / ".cursor")
    (temp_repo / ".github").mkdir()
    shutil.copy2(
        REPO_ROOT / ".github" / "copilot-instructions.md",
        temp_repo / ".github" / "copilot-instructions.md",
    )

    # Confirm baseline copy passes --check
    ok = run_cli(SCRIPT_SYNC_ADAPTERS, "--check", "--root", temp_repo)
    assert ok.returncode == 0, ok.stdout + ok.stderr

    # Introduce drift into CLAUDE.md
    claude_file = temp_repo / "CLAUDE.md"
    claude_file.write_text(claude_file.read_text(encoding="utf-8") + "\nDRIFT\n", encoding="utf-8")

    drift = run_cli(SCRIPT_SYNC_ADAPTERS, "--check", "--root", temp_repo)
    assert drift.returncode == 1
    assert "out of sync" in drift.stderr

    # Re-sync and confirm --check passes again
    regen = run_cli(SCRIPT_SYNC_ADAPTERS, "--root", temp_repo)
    assert regen.returncode == 0, regen.stdout + regen.stderr
    recheck = run_cli(SCRIPT_SYNC_ADAPTERS, "--check", "--root", temp_repo)
    assert recheck.returncode == 0, recheck.stdout + recheck.stderr
