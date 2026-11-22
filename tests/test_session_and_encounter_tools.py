"""Tests for build_context_pack.py, prep_transcript.py, and build_encounter.py."""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from conftest import (
    SCRIPT_BUILD_ENCOUNTER,
    SCRIPT_CONTEXT_PACK,
    SCRIPT_LINT,
    SCRIPT_PREP_TRANSCRIPT,
    TEMPLATE_VAULT,
    run_cli,
)


# ---------------------------------------------------------------------------
# scripts/build_context_pack.py
# ---------------------------------------------------------------------------


def test_build_context_pack_full_template_vault(tmp_path: Path) -> None:
    out_file = tmp_path / "context-pack.md"
    res = run_cli(
        SCRIPT_CONTEXT_PACK,
        "--vault",
        TEMPLATE_VAULT,
        "--out",
        out_file,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert out_file.is_file()

    text = out_file.read_text(encoding="utf-8")
    assert "## 1. Campaign Metadata & Party Passives" in text
    assert "Mira" in text and "Kael" in text and "Bram" in text
    assert "Perception **DC 14+**" in text
    assert "Investigation **DC 15+**" in text
    assert "Insight **DC 16+**" in text
    assert "## 2. World State" in text
    assert "## 3. Active & Open Quests" in text
    assert "Demo Quest - The Missing Wagon" in text
    assert "## 7. Current Location Context (1-Hop)" in text
    assert "Oakhaven Village" in text


def test_build_context_pack_tight_max_bytes_truncation(tmp_path: Path) -> None:
    out_file = tmp_path / "tight-pack.md"
    res = run_cli(
        SCRIPT_CONTEXT_PACK,
        "--vault",
        TEMPLATE_VAULT,
        "--max-bytes",
        "800",
        "--out",
        out_file,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert out_file.is_file()

    raw_bytes = out_file.read_bytes()
    assert len(raw_bytes) <= 800
    text = raw_bytes.decode("utf-8")
    assert "[truncated to fit budget]" in text


def test_build_context_pack_party_location_bold_colon_and_heading_demotion(
    isolated_vault: Path, tmp_path: Path
) -> None:
    ws_path = isolated_vault / "Campaign" / "World State.md"
    ws_text = ws_path.read_text(encoding="utf-8")
    # Use bold label with colon OUTSIDE the asterisks: **Party Location**: [[Oakhaven Village]]
    ws_text = re.sub(
        r"\*\*Party Location:\*\*.*",
        "**Party Location**: [[Oakhaven Village]]",
        ws_text,
    )
    ws_path.write_text(ws_text, encoding="utf-8")

    # Add nested headings and a fenced code block with '#' comments into Oakhaven Village.md
    loc_path = isolated_vault / "Locations" / "Oakhaven Village.md"
    loc_path.write_text(
        loc_path.read_text(encoding="utf-8")
        + "\n## Market Square\n\n"
        + "### Blacksmith Stall\n\n"
        + "```bash\n"
        + "# Fenced comment must remain untouched\n"
        + "echo ready\n"
        + "```\n",
        encoding="utf-8",
    )

    out_file = tmp_path / "context-demote.md"
    res = run_cli(
        SCRIPT_CONTEXT_PACK,
        "--vault",
        isolated_vault,
        "--out",
        out_file,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    text = out_file.read_text(encoding="utf-8")

    assert "## 7. Current Location Context (1-Hop)" in text
    assert "### [[Oakhaven Village]]" in text
    # Hierarchy preserved: ## -> #### and ### -> #####
    assert "#### Market Square" in text
    assert "##### Blacksmith Stall" in text
    # Fenced code comment untouched
    assert "\n# Fenced comment must remain untouched\n" in text


# ---------------------------------------------------------------------------
# scripts/prep_transcript.py
# ---------------------------------------------------------------------------


def test_prep_transcript_glossary_only_on_template_vault() -> None:
    res = run_cli(SCRIPT_PREP_TRANSCRIPT, "--vault", TEMPLATE_VAULT, "--glossary-only")
    assert res.returncode == 0, res.stdout + res.stderr
    assert "## Vault Proper-Noun Glossary" in res.stdout
    assert "Mira the Cleric" in res.stdout
    assert "Oakhaven Village" in res.stdout
    assert "Road Raider" in res.stdout
    assert "Skeleton Sentry" in res.stdout
    assert "Demo Quest - The Missing Wagon" in res.stdout


def test_prep_transcript_srt_cleaning_merging_and_overlapping_chunks(tmp_path: Path) -> None:
    srt_file = tmp_path / "session_01.srt"
    srt_file.write_text(
        "\n".join(
            [
                "1",
                "00:00:01,000 --> 00:00:04,500",
                "DM: Rain lashes the cobblestones of Oakhaven Village [laughter] as dusk settles.",
                "",
                "2",
                "00:00:05,000 --> 00:00:08,200",
                "DM: A merchant wagon stands overturned near the north gate with splintered crates.",
                "",
                "3",
                "00:00:09,000 --> 00:00:10,000",
                "Kael: um...",
                "",
                "4",
                "00:00:11,000 --> 00:00:14,500",
                "Kael: I crouch behind the barrels and inspect the axle tracks for bootprints.",
                "",
                "5",
                "00:00:15,000 --> 00:00:19,000",
                "Kael: I crouch behind the barrels and inspect the axle tracks for bootprints and broken lanterns.",
                "",
                "6",
                "00:00:20,000 --> 00:00:24,000",
                "Mira: I raise my lantern to illuminate the alley and watch for Road Raiders hiding overhead.",
                "",
                "7",
                "00:00:25,000 --> 00:00:29,000",
                "Bram: I draw my longsword, step forward to shield Mira, and call out toward the warehouse doors.",
                "",
                "8",
                "00:00:30,000 --> 00:00:35,000",
                "DM: Two hooded scouts peer from the warehouse loft while a skeletal sentry rattles inside the shadows.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    out_dir = tmp_path / "srt_chunks"
    res = run_cli(
        SCRIPT_PREP_TRANSCRIPT,
        srt_file,
        "--vault",
        TEMPLATE_VAULT,
        "--out-dir",
        out_dir,
        "--chunk-words",
        "45",
        "--overlap-words",
        "12",
    )
    assert res.returncode == 0, res.stdout + res.stderr

    chunks = sorted(out_dir.glob("chunk_*.md"))
    assert len(chunks) >= 2

    c1 = chunks[0].read_text(encoding="utf-8")
    c2 = chunks[1].read_text(encoding="utf-8")

    # Vault Glossary & DM-as-Reviewer checklist prefixed to every chunk
    for txt in (c1, c2):
        assert "## Vault Proper-Noun Glossary" in txt
        assert "Oakhaven Village" in txt
        assert "## DM-as-Reviewer Extraction Checklist" in txt
        # Raw timestamps and noise tags must be stripped
        assert "-->" not in txt
        assert "[laughter]" not in txt

    # Consecutive DM utterances merged into one turn
    assert "**DM:** Rain lashes the cobblestones of Oakhaven Village as dusk settles. A merchant wagon stands overturned" in c1
    # Rolling caption deduplication preserved the extended Kael turn without doubling it
    assert "broken lanterns." in (c1 + c2)
    # Chunk 2 carries continuity overlap header
    assert "Overlap from previous chunk" in c2


def test_prep_transcript_vtt_voice_tags_and_chunks(tmp_path: Path) -> None:
    vtt_file = tmp_path / "session_02.vtt"
    vtt_file.write_text(
        "\n".join(
            [
                "WEBVTT",
                "",
                "NOTE Recording from Discord session",
                "",
                "00:00:01.000 --> 00:00:04.000",
                "<v Mira>We check the lantern of steady flame before entering the warehouse.</v>",
                "",
                "00:00:04.500 --> 00:00:08.000",
                "<v Mira>Keep your voices low <00:00:06.000>while Kael tests the side latch.</v>",
                "",
                "00:00:09.000 --> 00:00:12.000",
                "<v Kael>[coughs] The iron latch clicks open cleanly without triggering any alarm bell.</v>",
                "",
            ]
        ),
        encoding="utf-8",
    )

    out_dir = tmp_path / "vtt_chunks"
    res = run_cli(
        SCRIPT_PREP_TRANSCRIPT,
        vtt_file,
        "--vault",
        TEMPLATE_VAULT,
        "--out-dir",
        out_dir,
        "--chunk-words",
        "100",
        "--overlap-words",
        "10",
    )
    assert res.returncode == 0, res.stdout + res.stderr

    chunk1 = out_dir / "chunk_01.md"
    assert chunk1.is_file()
    txt = chunk1.read_text(encoding="utf-8")
    assert "## Vault Proper-Noun Glossary" in txt
    assert "WEBVTT" not in txt
    assert "<v " not in txt
    assert "[coughs]" not in txt
    assert "**Mira:** We check the lantern of steady flame before entering the warehouse. Keep your voices low while Kael tests the side latch." in txt
    assert "**Kael:** The iron latch clicks open cleanly without triggering any alarm bell." in txt


def test_prep_transcript_standalone_speaker_prose_colons_and_unicode(tmp_path: Path) -> None:
    unicode_speaker = "Ren\u00e9"
    txt_file = tmp_path / "session_03.txt"
    txt_file.write_text(
        "\n".join(
            [
                "DM:",
                "You enter the rain-slicked courtyard of Oakhaven Village.",
                "I rolled a 19: that hits!",
                f"{unicode_speaker}: I notch a silvered arrow and watch the rooftops.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "txt_chunks"
    res = run_cli(
        SCRIPT_PREP_TRANSCRIPT,
        txt_file,
        "--vault",
        TEMPLATE_VAULT,
        "--out-dir",
        out_dir,
        "--chunk-words",
        "200",
    )
    assert res.returncode == 0, res.stdout + res.stderr

    chunk1 = out_dir / "chunk_01.md"
    assert chunk1.is_file()
    out_txt = chunk1.read_text(encoding="utf-8")

    # Standalone "DM:\nYou enter..." keeps DM attribution and prose colon stays part of turn
    assert "**DM:** You enter the rain-slicked courtyard of Oakhaven Village. I rolled a 19: that hits!" in out_txt
    assert "**I rolled a 19:**" not in out_txt
    # Unicode speaker name works cleanly
    assert f"**{unicode_speaker}:** I notch a silvered arrow and watch the rooftops." in out_txt


# ---------------------------------------------------------------------------
# scripts/build_encounter.py
# ---------------------------------------------------------------------------


def test_build_encounter_dry_run_2024_and_2014() -> None:
    res_2024 = run_cli(
        SCRIPT_BUILD_ENCOUNTER,
        "--name",
        "Alley Ambush",
        "--enemies",
        "Road Raider:2,Skeleton Sentry:1",
        "--ruleset",
        "2024",
        "--dry-run",
    )
    assert res_2024.returncode == 0, res_2024.stdout + res_2024.stderr
    assert "ruleset=2024" in res_2024.stdout
    assert "Raw XP: 100 | Adjusted XP: 100 (x1.0)" in res_2024.stdout

    res_2014 = run_cli(
        SCRIPT_BUILD_ENCOUNTER,
        "--name",
        "Alley Ambush",
        "--enemies",
        "Road Raider:2,Skeleton Sentry:1",
        "--ruleset",
        "2014",
        "--dry-run",
    )
    assert res_2014.returncode == 0, res_2014.stdout + res_2014.stderr
    assert "ruleset=2014" in res_2014.stdout
    assert "Raw XP: 100 | Adjusted XP: 200 (x2.0)" in res_2014.stdout


def test_build_encounter_writes_valid_markdown_and_atlas_json(isolated_vault: Path) -> None:
    res = run_cli(
        SCRIPT_BUILD_ENCOUNTER,
        "--name",
        "Warehouse Watch",
        "--enemies",
        "Road Raider:2,Skeleton Sentry:1",
        "--ruleset",
        "2024",
        "--vault",
        isolated_vault,
        "--out-dir",
        isolated_vault,
    )
    assert res.returncode == 0, res.stdout + res.stderr

    md_path = isolated_vault / "Encounters" / "Warehouse Watch.md"
    json_path = (
        isolated_vault
        / "atlas-vtt"
        / "collections"
        / "Campaign"
        / "encounters"
        / "encounter-warehouse_watch.json"
    )
    assert md_path.is_file()
    assert json_path.is_file()

    # Validate Markdown YAML frontmatter and links
    md_text = md_path.read_text(encoding="utf-8")
    fm_match = re.match(r"^---\r?\n(.*?)\r?\n---", md_text, re.DOTALL)
    assert fm_match is not None
    fm = yaml.safe_load(fm_match.group(1))
    assert fm["title"] == "Warehouse Watch"
    assert fm["ruleset"] == "2024"
    assert fm["total_xp"] == 100
    assert fm["atlas_encounter"] == "encounter-warehouse_watch"
    assert "[[Monsters/Road Raider\\|Road Raider]]" in md_text
    assert "[[Monsters/Skeleton Sentry\\|Skeleton Sentry]]" in md_text

    # Validate Atlas VTT encounter JSON schema
    enc_data = json.loads(json_path.read_text(encoding="utf-8"))
    rec = enc_data["atlasRecord"]
    assert rec["format"] == 1
    assert rec["type"] == "encounter"
    assert rec["id"] == "encounter-warehouse_watch"
    assert rec["collection"] == "Campaign"
    assert rec["totalXp"] == 100
    assert len(rec["entries"]) == 2
    assert {e["name"]: e["count"] for e in rec["entries"]} == {
        "Road Raider": 2,
        "Skeleton Sentry": 1,
    }

    # Confirm the generated encounter note passes strict vault linting
    lint_res = run_cli(SCRIPT_LINT, "--vault", isolated_vault, "--strict-links", "--full-atlas")
    assert lint_res.returncode == 0, lint_res.stdout + lint_res.stderr


def test_build_encounter_wave3_unrated_dc_slug_and_external_config(
    isolated_vault: Path, tmp_path: Path
) -> None:
    # 1. Mixed known + unrated enemy -> Incomplete (Low+) + stderr warning
    mix_res = run_cli(
        SCRIPT_BUILD_ENCOUNTER,
        "--name",
        "Dragon Ambush",
        "--enemies",
        "Road Raider:1,Shadow Dragon",
        "--ruleset",
        "2024",
        "--vault",
        isolated_vault,
        "--dry-run",
    )
    assert mix_res.returncode == 0, mix_res.stdout + mix_res.stderr
    assert "Difficulty: Incomplete (Low+)" in mix_res.stdout
    assert "WARNING:" in mix_res.stderr
    assert "Shadow Dragon" in mix_res.stderr

    # 2. External --config resolves relative vault_dir against config parent;
    #    --slug "encounter-foo" produces encounter-foo.json; Active Roll DC is dynamically 15.
    ext_dir = tmp_path / "ext_campaign"
    ext_vault = ext_dir / "MyVault"
    (ext_vault / "Monsters").mkdir(parents=True)
    # Copy Road Raider statblock so relative vault_dir resolution is proven
    src_raider = isolated_vault / "Monsters" / "Road Raider.md"
    (ext_vault / "Monsters" / "Road Raider.md").write_text(
        src_raider.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    ext_cfg = ext_dir / "campaign.config.json"
    ext_cfg.write_text(
        json.dumps(
            {
                "campaign_name": "External Realm",
                "vault_dir": "MyVault",
                "atlas_collection": "ExternalCol",
                "party_level": 3,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    ext_res = run_cli(
        SCRIPT_BUILD_ENCOUNTER,
        "--name",
        "Bridge Toll",
        "--enemies",
        "Road Raider:2",
        "--slug",
        "encounter-foo",
        "--config",
        ext_cfg,
    )
    assert ext_res.returncode == 0, ext_res.stdout + ext_res.stderr

    md_path = ext_vault / "Encounters" / "Bridge Toll.md"
    json_path = (
        ext_vault
        / "atlas-vtt"
        / "collections"
        / "ExternalCol"
        / "encounters"
        / "encounter-foo.json"
    )
    assert md_path.is_file()
    assert json_path.is_file()

    md_text = md_path.read_text(encoding="utf-8")
    # Default party passives: Mira Perc 13, Kael Inv 14 -> dynamic Active Roll DC = max(13, 14) + 1 = 15
    assert "DC 15" in md_text
    assert "DC 14" not in md_text

    enc_data = json.loads(json_path.read_text(encoding="utf-8"))
    assert enc_data["id"] == "encounter-foo"
    assert enc_data["atlasRecord"]["id"] == "encounter-foo"
    assert enc_data["atlasRecord"]["collection"] == "ExternalCol"
    assert enc_data["atlasRecord"]["totalXp"] == 50
