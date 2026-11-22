"""Tests for scripts/init_campaign.py and scripts/export_player_view.py."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from PIL import Image

from conftest import (
    SCRIPT_ATLAS_TOOLS,
    SCRIPT_EXPORT_PORTAL,
    SCRIPT_INIT_CAMPAIGN,
    SCRIPT_LINT,
    TEMPLATE_VAULT,
    run_cli,
)


# ---------------------------------------------------------------------------
# scripts/init_campaign.py
# ---------------------------------------------------------------------------


def test_init_campaign_non_interactive_meters_custom_party_and_validation(tmp_path: Path) -> None:
    target_root = tmp_path / "workspace"
    party_spec = (
        "Lyra:Cleric:14:15:11:16:torch,"
        "Theron:Rogue:12:12:15:10,"
        "Garrick:Fighter:16:10:9:11"
    )
    res = run_cli(
        SCRIPT_INIT_CAMPAIGN,
        "--non-interactive",
        "--name",
        "Ironvale Chronicles",
        "--vault-dir",
        "IronVault",
        "--collection",
        "Ironvale",
        "--units",
        "meters",
        "--party-level",
        "2",
        "--party",
        party_spec,
        "--target-root",
        target_root,
    )
    assert res.returncode == 0, res.stdout + res.stderr

    gen_vault = target_root / "IronVault"
    cfg_path = target_root / "campaign.config.json"
    agents_path = target_root / "AGENTS.md"
    assert gen_vault.is_dir()
    assert cfg_path.is_file()
    assert agents_path.is_file()

    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert cfg["campaign_name"] == "Ironvale Chronicles"
    assert cfg["atlas_collection"] == "Ironvale"
    assert cfg["grid_unit_type"] == "meters"
    assert cfg["grid_unit_distance"] == 1.5
    assert cfg["party_level"] == 2
    assert [pc["name"] for pc in cfg["party"]] == ["Lyra", "Theron", "Garrick"]
    assert cfg["atlas_campaign_id"] != "00000000-0000-4000-8000-000000000001"

    # Verify generated monogram WebP tokens and thumbnails
    for pc in cfg["party"]:
        tok_img = gen_vault / pc["imagePath"]
        assert tok_img.is_file()
        with Image.open(tok_img) as im:
            assert im.size == (400, 400)

    # Verify AGENTS.md replaced placeholders & updated passives
    agents_text = agents_path.read_text(encoding="utf-8")
    assert "Ironvale Chronicles" in agents_text
    assert "{{CAMPAIGN_NAME}}" not in agents_text
    assert "Lyra" in agents_text

    # Generated vault must pass full strict lint
    lint_res = run_cli(SCRIPT_LINT, "--vault", gen_vault, "--strict-links", "--full-atlas")
    assert lint_res.returncode == 0, lint_res.stdout + lint_res.stderr

    # Generated demo scene in custom collection must pass validate & audit-walls --strict
    scene_path = (
        gen_vault
        / "atlas-vtt"
        / "collections"
        / "Ironvale"
        / "scenes"
        / "Demo - Oakhaven Alley.atlasmap"
    )
    dash_path = (
        gen_vault
        / "atlas-vtt"
        / "collections"
        / "Ironvale"
        / "notes"
        / "Demo - Oakhaven Alley.md"
    )
    val_res = run_cli(
        SCRIPT_ATLAS_TOOLS,
        "--vault",
        gen_vault,
        "validate",
        scene_path,
        "--dashboard",
        dash_path,
    )
    assert val_res.returncode == 0, val_res.stdout + val_res.stderr

    aud_res = run_cli(
        SCRIPT_ATLAS_TOOLS,
        "--vault",
        gen_vault,
        "audit-walls",
        scene_path,
        "--strict",
    )
    assert aud_res.returncode == 0, aud_res.stdout + aud_res.stderr

    # Verify grid units converted to meters in the scene file
    scene_json = json.loads(scene_path.read_text(encoding="utf-8"))
    assert scene_json["state"]["grid"]["unitType"] == "meters"
    assert scene_json["state"]["grid"]["unitDistance"] == 1.5


def test_init_campaign_refuses_overwrite_without_force(tmp_path: Path) -> None:
    target_root = tmp_path / "overwrite_test"
    common = [
        "--non-interactive",
        "--name",
        "Test Realm",
        "--vault-dir",
        "Vault",
        "--target-root",
        target_root,
    ]
    first = run_cli(SCRIPT_INIT_CAMPAIGN, *common)
    assert first.returncode == 0, first.stdout + first.stderr

    second = run_cli(SCRIPT_INIT_CAMPAIGN, *common)
    assert second.returncode == 1
    assert "--force" in second.stderr

    forced = run_cli(SCRIPT_INIT_CAMPAIGN, *common, "--force")
    assert forced.returncode == 0, forced.stdout + forced.stderr


def test_init_campaign_case_only_collection_rename_and_meters_dashboard(tmp_path: Path) -> None:
    target_root = tmp_path / "case_rename"
    res = run_cli(
        SCRIPT_INIT_CAMPAIGN,
        "--non-interactive",
        "--name",
        "Lowercase Realm",
        "--vault-dir",
        "Vault",
        "--collection",
        "campaign",
        "--units",
        "meters",
        "--target-root",
        target_root,
    )
    assert res.returncode == 0, res.stdout + res.stderr

    gen_vault = target_root / "Vault"
    col_dir = gen_vault / "atlas-vtt" / "collections" / "campaign"
    assert col_dir.is_dir()

    col_json = json.loads((col_dir / "collection.json").read_text(encoding="utf-8"))
    assert col_json["id"] == "campaign"
    assert col_json["name"] == "campaign"

    # Demo dashboard body must convert imperial ft to meters
    dash_path = col_dir / "notes" / "Demo - Oakhaven Alley.md"
    assert dash_path.is_file()
    dash_text = dash_path.read_text(encoding="utf-8")
    assert re.search(r"\b\d+(?:\.\d+)?\s*ft\b", dash_text) is None
    assert "1.5m" in dash_text or "1.5 m" in dash_text

    # Generated vault must pass full strict lint
    lint_res = run_cli(SCRIPT_LINT, "--vault", gen_vault, "--strict-links", "--full-atlas")
    assert lint_res.returncode == 0, lint_res.stdout + lint_res.stderr


def test_init_campaign_with_wildcards_generates_all_8_valid_scenes(tmp_path: Path) -> None:
    target_root = tmp_path / "wildcards_test"
    res = run_cli(
        SCRIPT_INIT_CAMPAIGN,
        "--non-interactive",
        "--name",
        "Wildcard Frontier",
        "--vault-dir",
        "Vault",
        "--collection",
        "Frontier",
        "--with-wildcards",
        "--target-root",
        target_root,
    )
    assert res.returncode == 0, res.stdout + res.stderr

    gen_vault = target_root / "Vault"
    scenes_dir = gen_vault / "atlas-vtt" / "collections" / "Frontier" / "scenes"
    notes_dir = gen_vault / "atlas-vtt" / "collections" / "Frontier" / "notes"
    wildcard_scenes = sorted(scenes_dir.glob("Wildcard - *.atlasmap"))
    assert len(wildcard_scenes) == 8

    for scene_path in wildcard_scenes:
        dash_path = notes_dir / f"{scene_path.stem}.md"
        assert dash_path.is_file(), f"Missing wildcard dashboard: {dash_path}"
        val = run_cli(
            SCRIPT_ATLAS_TOOLS,
            "--vault",
            gen_vault,
            "validate",
            scene_path,
            "--dashboard",
            dash_path,
        )
        assert val.returncode == 0, f"{scene_path.name} failed validate:\n{val.stdout}\n{val.stderr}"


# ---------------------------------------------------------------------------
# scripts/export_player_view.py
# ---------------------------------------------------------------------------


def test_export_player_view_vault_and_single_md_on_template_vault(tmp_path: Path) -> None:
    out_vault = tmp_path / "player-vault"
    res_v = run_cli(
        SCRIPT_EXPORT_PORTAL,
        "--vault",
        TEMPLATE_VAULT,
        "--out",
        out_vault,
        "--format",
        "vault",
        "--verify",
    )
    assert res_v.returncode == 0, res_v.stdout + res_v.stderr
    assert "SECURITY AUDIT PASSED" in res_v.stdout

    # Private DM files and folders must not exist in player export
    assert not (out_vault / "DM Screen.md").exists()
    assert not (out_vault / "Campaign" / "World State.md").exists()
    assert not (out_vault / "Campaign" / "Improv Log.md").exists()
    assert not (out_vault / "Campaign" / "Story Arcs.md").exists()
    assert not (out_vault / "atlas-vtt").exists()
    assert not (out_vault / "Monsters").exists()
    assert not (out_vault / "Encounters").exists()

    # Exported vault must have zero broken wikilinks and valid YAML
    lint_res = run_cli(SCRIPT_LINT, "--vault", out_vault, "--strict-links")
    assert lint_res.returncode == 0, lint_res.stdout + lint_res.stderr

    # Single-MD export with --verify
    out_single = tmp_path / "player-handout.md"
    res_s = run_cli(
        SCRIPT_EXPORT_PORTAL,
        "--vault",
        TEMPLATE_VAULT,
        "--out",
        out_single,
        "--format",
        "single-md",
        "--verify",
    )
    assert res_s.returncode == 0, res_s.stdout + res_s.stderr
    assert out_single.is_file()
    single_txt = out_single.read_text(encoding="utf-8")
    assert "## Table of Contents" in single_txt
    assert "Oakhaven Village" in single_txt
    assert "[!danger]" not in single_txt.lower()


def test_export_player_view_stress_crlf_nested_callouts_conflicts_and_links(tmp_path: Path) -> None:
    vault = tmp_path / "stress_vault"
    (vault / "Lore").mkdir(parents=True)
    (vault / "NPCs").mkdir(parents=True)

    # Conflict note: visibility: dm-only + publish: true MUST remain excluded!
    secret_note = vault / "NPCs" / "Hidden Mastermind.md"
    secret_note.write_bytes(
        (
            "---\r\n"
            'title: "Hidden Mastermind"\r\n'
            'visibility: "dm-only"\r\n'
            "publish: true\r\n"
            "---\r\n\r\n"
            "# Hidden Mastermind\r\n\r\n"
            "TOP_SECRET_MASTERMIND_CODEWORD\r\n"
        ).encode("utf-8")
    )

    # Public note with CRLF, nested secret callouts, collapsible spoiler, HTML dm-only block,
    # and wikilinks (body + frontmatter) pointing to the excluded secret note.
    public_note = vault / "Lore" / "Market Rumors.md"
    public_content = (
        "---\r\n"
        'title: "Market Rumors"\r\n'
        "publish: true\r\n"
        'related: ["[[Hidden Mastermind]]"]\r\n'
        "---\r\n\r\n"
        "# Market Rumors\r\n\r\n"
        "Traders whisper about [[Hidden Mastermind|the Cloaked Broker]] and [[Hidden Mastermind]].\r\n\r\n"
        "> [!danger] DM Secret\r\n"
        "> Outer secret line SECRET_CALLOUT_ALPHA.\r\n"
        "> > Nested quote SECRET_NESTED_BETA.\r\n"
        ">\r\n"
        "> Trailing secret line SECRET_TRAIL_GAMMA.\r\n\r\n"
        "Visible paragraph after danger callout.\r\n\r\n"
        "> [!spoiler]- Hidden Twist\r\n"
        "> SECRET_SPOILER_DELTA.\r\n\r\n"
        "<!-- dm-only -->\r\n"
        "SECRET_HTML_EPSILON\r\n"
        "<!-- /dm-only -->\r\n\r\n"
        "Final public rumor line.\r\n"
    )
    public_note.write_bytes(public_content.encode("utf-8"))

    out_dir = tmp_path / "stress_out"
    res = run_cli(
        SCRIPT_EXPORT_PORTAL,
        "--vault",
        vault,
        "--out",
        out_dir,
        "--publish-only",
        "--format",
        "vault",
        "--verify",
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert not (out_dir / "NPCs" / "Hidden Mastermind.md").exists()

    exported = (out_dir / "Lore" / "Market Rumors.md").read_text(encoding="utf-8")
    for leaked_token in (
        "TOP_SECRET_MASTERMIND_CODEWORD",
        "SECRET_CALLOUT_ALPHA",
        "SECRET_NESTED_BETA",
        "SECRET_TRAIL_GAMMA",
        "SECRET_SPOILER_DELTA",
        "SECRET_HTML_EPSILON",
        "[[Hidden Mastermind",
    ):
        assert leaked_token not in exported

    assert "the Cloaked Broker" in exported
    assert "Visible paragraph after danger callout." in exported
    assert "Final public rumor line." in exported

    # Exported vault must also pass strict lint
    lint_res = run_cli(SCRIPT_LINT, "--vault", out_dir, "--strict-links")
    assert lint_res.returncode == 0, lint_res.stdout + lint_res.stderr


def test_export_player_view_verify_fails_when_secret_leaks(tmp_path: Path) -> None:
    # Case 1: Unclosed <!-- dm-only --> strips fail-closed to EOF with WARNING on stderr
    vault_a = tmp_path / "leak_vault_a"
    (vault_a / "Lore").mkdir(parents=True)
    (vault_a / "Lore" / "Unclosed.md").write_text(
        "---\ntitle: \"Unclosed\"\n---\n\nPublic text.\n<!-- dm-only -->\nUnclosed secret line.\n",
        encoding="utf-8",
    )
    out_a = tmp_path / "leak_out_a"
    res_a = run_cli(
        SCRIPT_EXPORT_PORTAL,
        "--vault",
        vault_a,
        "--out",
        out_a,
        "--format",
        "vault",
        "--verify",
    )
    assert res_a.returncode == 0, res_a.stdout + res_a.stderr
    assert "WARNING:" in res_a.stderr
    exported_a = (out_a / "Lore" / "Unclosed.md").read_text(encoding="utf-8")
    assert "Public text." in exported_a
    assert "Unclosed secret line." not in exported_a

    # Case 2: Injected secret artifacts sitting in output dir -> --verify catches each and exits 1
    leak_cases = [
        ("callout_leak", "---\ntitle: \"Leak\"\n---\n\n> [!danger] DM Secret\n> Leaked!\n"),
        ("html_comment_leak", "---\ntitle: \"Leak\"\n---\n\nPublic <!-- secret --> line.\n"),
        ("obsidian_comment_leak", "---\ntitle: \"Leak\"\n---\n\nPublic %% comment %% line.\n"),
        ("commonmark_link_leak", "---\ntitle: \"Leak\"\n---\n\nSee [Leak](<DM Screen.md>).\n"),
        ("dm_only_fm_leak", "---\ntitle: \"Leak\"\nvisibility: dm-only\n---\n\nSecret note.\n"),
    ]
    for case_name, leaked_md in leak_cases:
        vault_b = tmp_path / f"vault_{case_name}"
        (vault_b / "Lore").mkdir(parents=True)
        (vault_b / "Lore" / "Clean.md").write_text(
            "---\ntitle: \"Clean\"\n---\n\nSafe lore.\n",
            encoding="utf-8",
        )
        out_b = tmp_path / f"out_{case_name}"
        out_b.mkdir(parents=True)
        (out_b / "Injected Leak.md").write_text(leaked_md, encoding="utf-8")
        res_b = run_cli(
            SCRIPT_EXPORT_PORTAL,
            "--vault",
            vault_b,
            "--out",
            out_b,
            "--format",
            "vault",
            "--verify",
        )
        assert res_b.returncode == 1, f"{case_name} should fail --verify"
        assert "SECURITY AUDIT FAILED" in res_b.stderr


def test_export_player_view_wave3_hardening_regression(tmp_path: Path) -> None:
    vault = tmp_path / "hardened_vault"
    (vault / "Lore").mkdir(parents=True)
    (vault / "Locations").mkdir(parents=True)
    (vault / "Monsters").mkdir(parents=True)
    (vault / "Assets").mkdir(parents=True)

    # 1. Malformed YAML frontmatter MUST fail closed (excluded + stderr WARNING)
    (vault / "Lore" / "Broken Frontmatter.md").write_text(
        "---\ntitle: \"Unclosed Quote\nvisibility: dm-only\ntags: [bad, [yaml\n---\n\n"
        "MALFORMED_YAML_SECRET_TOKEN\n",
        encoding="utf-8",
    )

    # 2. Private note & Monster note with name collision against public Locations/Boss.md
    (vault / "Monsters" / "Boss.md").write_text(
        "---\ntitle: \"Boss\"\n---\n\nMONSTER_BOSS_SECRET\n",
        encoding="utf-8",
    )
    (vault / "Locations" / "Boss.md").write_text(
        "---\ntitle: \"Boss\"\npublish: true\n---\n\nPublic cliffside hamlet named Boss.\n",
        encoding="utf-8",
    )
    (vault / "Lore" / "Secret Note.md").write_text(
        "---\ntitle: \"Secret Note\"\nvisibility: dm-only\n---\n\nSECRET_EMBED_BODY\n",
        encoding="utf-8",
    )
    (vault / "DM Screen.md").write_text(
        "---\ntitle: \"DM Screen\"\n---\n\nDM_SCREEN_PRIVATE\n",
        encoding="utf-8",
    )

    # 3. Valid spaced public image asset
    pub_img = vault / "Assets" / "Oakhaven Map.png"
    Image.new("RGB", (64, 64), color=(30, 60, 90)).save(pub_img, "PNG")

    # 4. Public note exercising all Wave 3 stripping & link sanitization edge cases
    (vault / "Lore" / "Field Journal.md").write_text(
        "---\n"
        'title: "Field Journal"\n'
        "publish: true\n"
        "---\n\n"
        "# Field Journal\n\n"
        "Visible intro <!-- secret HTML comment --> after comment.\n\n"
        "Obsidian note %% secret obsidian comment %% still visible.\n\n"
        "> [!danger] DM Secret\n"
        "> Quoted secret line LAZY_SECRET_ONE.\n"
        "Lazy continuation secret line LAZY_SECRET_TWO.\n\n"
        "Paragraph after lazy callout.\n\n"
        "Spaced CommonMark link: [DM](<DM Screen.md>).\n\n"
        "Valid spaced image embed: ![[Oakhaven Map.png]]\n\n"
        "Name collision link: [[Monsters/Boss]] vs public [[Locations/Boss]].\n\n"
        "Excluded embed: ![[Secret Note]]\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "hardened_out"
    out_dir.mkdir(parents=True)
    stale_file = out_dir / "Stale Old Page.md"
    stale_file.write_text("Old stale content.\n", encoding="utf-8")

    res = run_cli(
        SCRIPT_EXPORT_PORTAL,
        "--vault",
        vault,
        "--out",
        out_dir,
        "--format",
        "vault",
        "--clean",
        "--verify",
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert "WARNING:" in res.stderr
    assert not stale_file.exists()
    assert not (out_dir / "Lore" / "Broken Frontmatter.md").exists()
    assert not (out_dir / "Lore" / "Secret Note.md").exists()
    assert not (out_dir / "Monsters").exists()

    # Valid spaced public image must be copied
    assert (out_dir / "Assets" / "Oakhaven Map.png").is_file()

    exported = (out_dir / "Lore" / "Field Journal.md").read_text(encoding="utf-8")
    for forbidden in (
        "MALFORMED_YAML_SECRET_TOKEN",
        "secret HTML comment",
        "<!--",
        "secret obsidian comment",
        "%%",
        "LAZY_SECRET_ONE",
        "LAZY_SECRET_TWO",
        "<DM Screen.md>",
        "[[Monsters/Boss]]",
        "![[Secret Note]]",
        "Secret Note",
    ):
        assert forbidden not in exported

    assert "Paragraph after lazy callout." in exported
    assert "Spaced CommonMark link: DM." in exported
    assert "![[Oakhaven Map.png]]" in exported
    assert "[[Locations/Boss]]" in exported

    # --clean must refuse --out == --vault (exit 1) and leave vault intact
    refuse = run_cli(
        SCRIPT_EXPORT_PORTAL,
        "--vault",
        vault,
        "--out",
        vault,
        "--format",
        "vault",
        "--clean",
    )
    assert refuse.returncode == 1
    assert "ERROR:" in refuse.stderr
    assert (vault / "DM Screen.md").is_file()
