"""Tests for skill CLI scripts: quick_battlemap, atlas_scene_tools, roll_tables, register_token."""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from PIL import Image

from conftest import (
    DEMO_DASHBOARD,
    DEMO_SCENE,
    MOODS_TEMPLATE,
    SCRIPT_ATLAS_SOUND_TOOLS,
    SCRIPT_ATLAS_TOOLS,
    SCRIPT_QUICK_BATTLEMAP,
    SCRIPT_REGISTER_TOKEN,
    SCRIPT_ROLL_TABLES,
    TEMPLATE_VAULT,
    run_cli,
)


# ---------------------------------------------------------------------------
# .agents/skills/quick-battlemap/scripts/quick_battlemap.py
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "preset",
    ["whiteboard", "alley", "road", "hills", "interior", "camp", "bridge", "crypt"],
)
def test_quick_battlemap_dry_run_all_8_presets(preset: str) -> None:
    res = run_cli(
        SCRIPT_QUICK_BATTLEMAP,
        "--preset",
        preset,
        "--enemies",
        "Road Raider:2,Skeleton Sentry:1",
        "--dry-run",
    )
    assert res.returncode == 0, f"Preset '{preset}' failed:\n{res.stdout}\n{res.stderr}"
    assert "Self-validation PASSED (0 issues)." in res.stdout


@pytest.mark.parametrize("preset", ["camp", "bridge", "crypt"])
def test_quick_battlemap_full_generation_validated_by_atlas_tools(
    tmp_path: Path, preset: str
) -> None:
    out_vault = tmp_path / f"qb_{preset}"
    scene_name = f"Test Scene - {preset.title()}"
    gen = run_cli(
        SCRIPT_QUICK_BATTLEMAP,
        "--preset",
        preset,
        "--name",
        scene_name,
        "--enemies",
        "Road Raider:2,Skeleton Sentry:1",
        "--out-dir",
        out_vault,
    )
    assert gen.returncode == 0, gen.stdout + gen.stderr

    col_dir = out_vault / "atlas-vtt" / "collections" / "Campaign"
    atlasmap_path = col_dir / "scenes" / f"{scene_name}.atlasmap"
    dash_path = col_dir / "notes" / f"{scene_name}.md"
    assert atlasmap_path.is_file()
    assert dash_path.is_file()
    assert dash_path.stat().st_size < 5120

    scene_data = json.loads(atlasmap_path.read_text(encoding="utf-8"))
    assert scene_data["version"] == 4
    assert scene_data["state"]["objects"]["fog"] == {}
    assert (out_vault / scene_data["state"]["background"]).is_file()

    val = run_cli(
        SCRIPT_ATLAS_TOOLS,
        "--vault",
        out_vault,
        "validate",
        atlasmap_path,
        "--dashboard",
        dash_path,
    )
    assert val.returncode == 0, val.stdout + val.stderr
    assert "Validation PASSED." in val.stdout

    aud = run_cli(
        SCRIPT_ATLAS_TOOLS,
        "--vault",
        out_vault,
        "audit-walls",
        atlasmap_path,
        "--strict",
    )
    assert aud.returncode == 0, aud.stdout + aud.stderr
    assert "Wall audit CLEAN (0 issues)." in aud.stdout


def _point_to_seg_dist(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


@pytest.mark.parametrize("preset", ["interior", "hills", "camp"])
def test_quick_battlemap_min_size_10x8_cell50_and_camp_pin_b_outside_walls(
    tmp_path: Path, preset: str
) -> None:
    out_vault = tmp_path / f"qb_min_{preset}"
    scene_name = f"Min Scene - {preset.title()}"
    gen = run_cli(
        SCRIPT_QUICK_BATTLEMAP,
        "--preset",
        preset,
        "--name",
        scene_name,
        "--cols",
        "10",
        "--rows",
        "8",
        "--cell",
        "50",
        "--enemies",
        "Road Raider:2",
        "--out-dir",
        out_vault,
    )
    assert gen.returncode == 0, gen.stdout + gen.stderr

    col_dir = out_vault / "atlas-vtt" / "collections" / "Campaign"
    atlasmap_path = col_dir / "scenes" / f"{scene_name}.atlasmap"
    dash_path = col_dir / "notes" / f"{scene_name}.md"
    assert atlasmap_path.is_file()
    assert dash_path.is_file()

    val = run_cli(
        SCRIPT_ATLAS_TOOLS,
        "--vault",
        out_vault,
        "validate",
        atlasmap_path,
        "--dashboard",
        dash_path,
    )
    assert val.returncode == 0, val.stdout + val.stderr
    assert "Validation PASSED." in val.stdout

    aud = run_cli(
        SCRIPT_ATLAS_TOOLS,
        "--vault",
        out_vault,
        "audit-walls",
        atlasmap_path,
        "--strict",
    )
    assert aud.returncode == 0, aud.stdout + aud.stderr
    assert "Wall audit CLEAN (0 issues)." in aud.stdout

    if preset == "camp":
        scene_data = json.loads(atlasmap_path.read_text(encoding="utf-8"))
        objs = scene_data["state"]["objects"]
        pins = list((objs.get("pins") or {}).values())
        pin_b = next((p for p in pins if str(p.get("label")) == "B"), None)
        assert pin_b is not None, "Expected Pin B in camp scene"
        px, py = float(pin_b["x"]), float(pin_b["y"])

        solid_walls = [
            w for w in (objs.get("walls") or {}).values() if w.get("type", "solid") == "solid"
        ]
        assert solid_walls
        # Pin B must not sit on a solid wall segment
        min_dist = min(
            _point_to_seg_dist(
                px,
                py,
                float(w["p1"]["x"]),
                float(w["p1"]["y"]),
                float(w["p2"]["x"]),
                float(w["p2"]["y"]),
            )
            for w in solid_walls
        )
        assert min_dist >= 5.0, f"Camp Pin B too close to solid wall ({min_dist:.1f}px)"

        # Ray-casting check against interior solid-wall obstacles (excluding outer map perimeter)
        map_w, map_h = 10 * 50.0, 8 * 50.0
        interior_walls = [
            w
            for w in solid_walls
            if not (
                (float(w["p1"]["x"]) in (0.0, map_w) and float(w["p2"]["x"]) in (0.0, map_w))
                or (float(w["p1"]["y"]) in (0.0, map_h) and float(w["p2"]["y"]) in (0.0, map_h))
            )
        ]
        assert interior_walls
        crossings = 0
        for w in interior_walls:
            x1, y1 = float(w["p1"]["x"]), float(w["p1"]["y"])
            x2, y2 = float(w["p2"]["x"]), float(w["p2"]["y"])
            if (y1 > py) != (y2 > py):
                x_int = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
                if px < x_int:
                    crossings += 1
        assert crossings % 2 == 0, f"Camp Pin B ({px}, {py}) is trapped inside an interior solid wall box"


# ---------------------------------------------------------------------------
# .agents/skills/dungeons-and-maps/scripts/atlas_scene_tools.py
# ---------------------------------------------------------------------------


def test_atlas_scene_tools_validate_and_audit_walls_demo_scene() -> None:
    val = run_cli(
        SCRIPT_ATLAS_TOOLS,
        "validate",
        DEMO_SCENE,
        "--dashboard",
        DEMO_DASHBOARD,
    )
    assert val.returncode == 0, val.stdout + val.stderr
    assert "Validation PASSED." in val.stdout

    aud = run_cli(
        SCRIPT_ATLAS_TOOLS,
        "audit-walls",
        DEMO_SCENE,
        "--strict",
    )
    assert aud.returncode == 0, aud.stdout + aud.stderr
    assert "Wall audit CLEAN (0 issues)." in aud.stdout


def test_atlas_scene_tools_audit_walls_strict_catches_near_gap_and_tight_light(
    tmp_path: Path,
) -> None:
    synthetic_scene = tmp_path / "Leaky Room.atlasmap"
    payload = {
        "version": 4,
        "state": {
            "schema": "atlas-vtt",
            "version": 4,
            "objects": {
                "walls": {
                    "w1": {
                        "id": "w1",
                        "kind": "wall",
                        "type": "solid",
                        "p1": {"x": 100.0, "y": 100.0},
                        "p2": {"x": 300.0, "y": 100.0},
                    },
                    # Intentional 8px gap between (300, 100) and (308, 100)
                    "w2": {
                        "id": "w2",
                        "kind": "wall",
                        "type": "solid",
                        "p1": {"x": 308.0, "y": 100.0},
                        "p2": {"x": 308.0, "y": 300.0},
                    },
                },
                "lights": {
                    # Light placed only 6px below wall w1 (< 20px default clearance)
                    "l1": {
                        "id": "l1",
                        "kind": "light",
                        "x": 200.0,
                        "y": 106.0,
                        "emission": {"bright": 15, "dim": 30},
                    }
                },
            },
        },
    }
    synthetic_scene.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    res = run_cli(
        SCRIPT_ATLAS_TOOLS,
        "audit-walls",
        synthetic_scene,
        "--strict",
    )
    assert res.returncode == 1
    assert "near-gaps=1" in res.stdout
    assert "tight-lights=1" in res.stdout
    assert "gap of 8.0px" in res.stdout


def test_atlas_scene_tools_audit_walls_t_junction_curve_and_x_junction(tmp_path: Path) -> None:
    # 1. Near-miss 8px T-junction leak MUST fail --strict
    t_scene = tmp_path / "T Junction Leak.atlasmap"
    t_payload = {
        "version": 4,
        "state": {
            "schema": "atlas-vtt",
            "version": 4,
            "objects": {
                "walls": {
                    "w_bar": {
                        "id": "w_bar",
                        "kind": "wall",
                        "type": "solid",
                        "p1": {"x": 100.0, "y": 100.0},
                        "p2": {"x": 400.0, "y": 100.0},
                    },
                    # Stem stops 8px short of the horizontal bar midpoint (250, 100)
                    "w_stem": {
                        "id": "w_stem",
                        "kind": "wall",
                        "type": "solid",
                        "p1": {"x": 250.0, "y": 108.0},
                        "p2": {"x": 250.0, "y": 300.0},
                    },
                },
                "lights": {},
            },
        },
    }
    t_scene.write_text(json.dumps(t_payload, indent=2), encoding="utf-8")
    res_t = run_cli(SCRIPT_ATLAS_TOOLS, "audit-walls", t_scene, "--strict")
    assert res_t.returncode == 1
    assert "near-gaps=1" in res_t.stdout
    assert "T-junction" in res_t.stdout
    assert "gap of 8.0px" in res_t.stdout

    # 2. .dd2vtt-style 8-segment curve (12px segments) + crossing X-junction MUST be CLEAN (exit 0)
    walls_clean: dict[str, dict] = {}
    radius = 60.0
    cx, cy = 200.0, 200.0
    # 8 chained 12px-ish arc segments along a curve
    step_angle = 12.0 / radius  # ~0.2 rad -> chord ~12.0px
    pts = [
        (cx + radius * math.cos(i * step_angle), cy + radius * math.sin(i * step_angle))
        for i in range(9)
    ]
    for idx in range(8):
        wid = f"curve_{idx}"
        walls_clean[wid] = {
            "id": wid,
            "kind": "wall",
            "type": "solid",
            "p1": {"x": round(pts[idx][0], 2), "y": round(pts[idx][1], 2)},
            "p2": {"x": round(pts[idx + 1][0], 2), "y": round(pts[idx + 1][1], 2)},
        }

    # Crossing X-junction far from the curve
    walls_clean["x_diag1"] = {
        "id": "x_diag1",
        "kind": "wall",
        "type": "solid",
        "p1": {"x": 500.0, "y": 100.0},
        "p2": {"x": 700.0, "y": 300.0},
    }
    walls_clean["x_diag2"] = {
        "id": "x_diag2",
        "kind": "wall",
        "type": "solid",
        "p1": {"x": 700.0, "y": 100.0},
        "p2": {"x": 500.0, "y": 300.0},
    }

    clean_scene = tmp_path / "Curve And X.atlasmap"
    clean_payload = {
        "version": 4,
        "state": {
            "schema": "atlas-vtt",
            "version": 4,
            "objects": {"walls": walls_clean, "lights": {}},
        },
    }
    clean_scene.write_text(json.dumps(clean_payload, indent=2), encoding="utf-8")
    res_clean = run_cli(SCRIPT_ATLAS_TOOLS, "audit-walls", clean_scene, "--strict")
    assert res_clean.returncode == 0, res_clean.stdout + res_clean.stderr
    assert "Wall audit CLEAN (0 issues)." in res_clean.stdout


def test_atlas_scene_tools_scaffold_dashboard_dynamic_dc_and_collection_inference(
    tmp_path: Path,
) -> None:
    col_vault = tmp_path / "inferred_vault"
    scene_dir = col_vault / "atlas-vtt" / "collections" / "CustomRealm" / "scenes"
    scene_dir.mkdir(parents=True)
    custom_scene = scene_dir / "Sunken Gate.atlasmap"
    custom_scene.write_text(
        json.dumps(
            {
                "version": 4,
                "state": {
                    "schema": "atlas-vtt",
                    "version": 4,
                    "grid": {"size": 70, "unitDistance": 5, "unitType": "feet"},
                    "lighting": {"enabled": True, "ambient": 0.0},
                    "objects": {"walls": {}, "lights": {}, "pins": {}, "tokens": {}},
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    out_dash = col_vault / "atlas-vtt" / "collections" / "CustomRealm" / "notes" / "Sunken Gate.md"
    scaf = run_cli(
        SCRIPT_ATLAS_TOOLS,
        "--vault",
        col_vault,
        "scaffold-dashboard",
        custom_scene,
        "--out",
        out_dash,
    )
    assert scaf.returncode == 0, scaf.stdout + scaf.stderr
    dash_txt = out_dash.read_text(encoding="utf-8")
    assert 'collection: "CustomRealm"' in dash_txt
    assert "DC 15" in dash_txt
    assert "DC 14" not in dash_txt


def test_atlas_scene_tools_scaffold_dashboard_and_validate(tmp_path: Path) -> None:
    out_dash = tmp_path / "Scaffolded - Oakhaven Alley.md"
    scaf = run_cli(
        SCRIPT_ATLAS_TOOLS,
        "--vault",
        TEMPLATE_VAULT,
        "scaffold-dashboard",
        DEMO_SCENE,
        "--out",
        out_dash,
    )
    assert scaf.returncode == 0, scaf.stdout + scaf.stderr
    assert out_dash.is_file()
    assert out_dash.stat().st_size < 5120

    val = run_cli(
        SCRIPT_ATLAS_TOOLS,
        "--vault",
        TEMPLATE_VAULT,
        "validate",
        DEMO_SCENE,
        "--dashboard",
        out_dash,
    )
    assert val.returncode == 0, val.stdout + val.stderr
    assert "Validation PASSED." in val.stdout


def test_atlas_scene_tools_verify_scene_renders_image(tmp_path: Path) -> None:
    out_png = tmp_path / "verify.png"
    res = run_cli(
        SCRIPT_ATLAS_TOOLS,
        "--vault",
        TEMPLATE_VAULT,
        "verify-scene",
        DEMO_SCENE,
        "--out",
        out_png,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert out_png.is_file()
    with Image.open(out_png) as im:
        assert im.size == (1120, 840)


# ---------------------------------------------------------------------------
# .agents/skills/live-improv/scripts/roll_tables.py
# ---------------------------------------------------------------------------


def test_roll_tables_list_deterministic_preset_and_file_all() -> None:
    res_list = run_cli(SCRIPT_ROLL_TABLES, "--list")
    assert res_list.returncode == 0, res_list.stdout + res_list.stderr
    assert "Demo Table - Quick Prompts and Encounters.md" in res_list.stdout
    assert "demo-scene" in res_list.stdout

    run1 = run_cli(SCRIPT_ROLL_TABLES, "--preset", "demo-scene", "--seed", "42")
    run2 = run_cli(SCRIPT_ROLL_TABLES, "--preset", "demo-scene", "--seed", "42")
    assert run1.returncode == 0, run1.stdout + run1.stderr
    assert run2.returncode == 0, run2.stdout + run2.stderr
    assert run1.stdout == run2.stdout
    assert "[0]" in run1.stdout and "[1]" in run1.stdout and "[2]" in run1.stdout

    res_file = run_cli(SCRIPT_ROLL_TABLES, "--file", "Demo Table", "--table", "all", "--seed", "7")
    assert res_file.returncode == 0, res_file.stdout + res_file.stderr
    assert "[0]" in res_file.stdout and "[1]" in res_file.stdout and "[2]" in res_file.stdout


# ---------------------------------------------------------------------------
# .agents/skills/atlas-token-art/scripts/register_token.py
# ---------------------------------------------------------------------------


def test_register_token_dry_run_and_isolated_write(tmp_path: Path) -> None:
    src_img = tmp_path / "source_portrait.png"
    Image.new("RGB", (600, 480), color=(42, 72, 118)).save(src_img, "PNG")

    iso_vault = tmp_path / "token_vault"
    iso_vault.mkdir()

    dry = run_cli(
        SCRIPT_REGISTER_TOKEN,
        src_img,
        "--name",
        "Iron Warden",
        "--statblock",
        "Monsters/Road Raider.md",
        "--tags",
        "guard",
        "humanoid",
        "--vault",
        iso_vault,
        "--dry-run",
    )
    assert dry.returncode == 0, dry.stdout + dry.stderr
    assert "[dry-run]" in dry.stdout
    assert not (iso_vault / "atlas-vtt").exists()

    real = run_cli(
        SCRIPT_REGISTER_TOKEN,
        src_img,
        "--name",
        "Iron Warden",
        "--statblock",
        "Monsters/Road Raider.md",
        "--tags",
        "guard",
        "humanoid",
        "--vault",
        iso_vault,
    )
    assert real.returncode == 0, real.stdout + real.stderr

    tokens_dir = iso_vault / "atlas-vtt" / "collections" / "Campaign" / "tokens"
    token_files = list(tokens_dir.glob("token-*.json"))
    assert len(token_files) == 1

    tok_data = json.loads(token_files[0].read_text(encoding="utf-8"))
    rec = tok_data["atlasRecord"]
    assert rec["format"] == 1
    assert rec["type"] == "token"
    assert rec["name"] == "Iron Warden"
    assert rec["statblockPath"] == "Monsters/Road Raider.md"
    assert rec["tags"] == ["guard", "humanoid"]

    img_path = iso_vault / rec["imagePath"]
    thumb_path = iso_vault / rec["thumbnailPath"]
    assert img_path.is_file()
    assert thumb_path.is_file()

    with Image.open(img_path) as im:
        assert im.size == (400, 400)
        assert im.format == "WEBP"
    with Image.open(thumb_path) as th:
        assert th.size == (128, 128)
        assert th.format == "WEBP"


def test_register_token_normalizes_windows_backslashes_in_json(tmp_path: Path) -> None:
    src_img = tmp_path / "raider_portrait.png"
    Image.new("RGB", (500, 500), color=(90, 40, 40)).save(src_img, "PNG")

    iso_vault = tmp_path / "win_path_vault"
    iso_vault.mkdir()

    res = run_cli(
        SCRIPT_REGISTER_TOKEN,
        src_img,
        "--name",
        "Road Raider Win",
        "--statblock",
        r"Monsters\Road Raider.md",
        "--vault",
        iso_vault,
    )
    assert res.returncode == 0, res.stdout + res.stderr

    tokens_dir = iso_vault / "atlas-vtt" / "collections" / "Campaign" / "tokens"
    token_files = list(tokens_dir.glob("token-*.json"))
    assert len(token_files) == 1

    raw_json = token_files[0].read_text(encoding="utf-8")
    assert "\\\\" not in raw_json
    tok_data = json.loads(raw_json)
    rec = tok_data["atlasRecord"]
    assert rec["statblockPath"] == "Monsters/Road Raider.md"
    assert "\\" not in rec["imagePath"]
    assert "\\" not in rec["thumbnailPath"]


def test_build_wildcard_pack_generates_8_validated_party_agnostic_scenes_and_zip(
    tmp_path: Path,
) -> None:
    import zipfile

    pack_vault = tmp_path / "wildcard_pack_vault"
    zip_path = tmp_path / "prep-goblin-wildcards.zip"
    script_pack = Path(__file__).resolve().parent.parent / "scripts" / "build_wildcard_pack.py"

    res = run_cli(
        script_pack,
        "--out-vault",
        pack_vault,
        "--collection",
        "Prep Goblin Wildcards",
        "--units",
        "feet",
        "--zip",
        zip_path,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert "All 8 scenes PASSED validate + audit-walls --strict." in res.stdout
    assert zip_path.is_file() and zip_path.stat().st_size > 10_000

    scenes_dir = pack_vault / "atlas-vtt" / "collections" / "Prep Goblin Wildcards" / "scenes"
    scenes = sorted(scenes_dir.glob("Wildcard - *.atlasmap"))
    assert len(scenes) == 8
    for sc in scenes:
        data = json.loads(sc.read_text(encoding="utf-8"))
        # Party-agnostic pack must contain 0 PC tokens
        assert data["state"]["objects"]["tokens"] == {}

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert any(n.endswith("collection.json") for n in names)
        assert sum(1 for n in names if n.endswith(".atlasmap")) == 8


# ---------------------------------------------------------------------------
# .agents/skills/atlas-sound-moods/scripts/atlas_sound_tools.py
# ---------------------------------------------------------------------------


def test_atlas_sound_moods_template_is_valid_json_schema() -> None:
    cfg = json.loads(MOODS_TEMPLATE.read_text(encoding="utf-8"))
    assert cfg.get("collection") == "Campaign"
    moods = cfg.get("moods")
    assert isinstance(moods, list) and len(moods) >= 6
    valid_rooms = {"room", "hall", "cave", "cathedral"}
    for m in moods:
        assert m["id"].startswith("mood-")
        assert isinstance(m["name"], str) and m["name"]
        assert m["room"] in valid_rooms
        assert isinstance(m.get("tone"), str) and m["tone"]
        assert isinstance(m.get("music"), dict)
        assert isinstance(m.get("layers"), list)
    scene_links = cfg.get("sceneLinks")
    assert isinstance(scene_links, list) and len(scene_links) >= 1
    for link in scene_links:
        assert isinstance(link.get("scene"), str) and link["scene"].endswith(".atlasmap")
        assert isinstance(link.get("mood"), str) and link["mood"].startswith("mood-")


def test_atlas_sound_tools_inventory_build_link_and_validate_end_to_end(tmp_path: Path) -> None:
    vault = tmp_path / "sound_vault"
    sounds_dir = vault / "atlas-vtt" / "sounds"
    music_vocal = sounds_dir / "music" / "Tavern" / "Hearth Song.opus"
    music_inst = sounds_dir / "music" / "Tavern" / "Instrumental" / "Hearth Song.opus"
    music_combat = sounds_dir / "music" / "Combat" / "Skirmish.opus"
    amb_tavern = sounds_dir / "ambience" / "Tavern Chatter.opus"
    for p in (music_vocal, music_inst, music_combat, amb_tavern):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"OggS-dummy-audio-bytes")

    scenes_dir = vault / "atlas-vtt" / "collections" / "Campaign" / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)
    scene_file = scenes_dir / "Demo - Oakhaven Alley.atlasmap"
    scene_file.write_text(DEMO_SCENE.read_text(encoding="utf-8"), encoding="utf-8")

    # 1. inventory
    inv = run_cli(
        SCRIPT_ATLAS_SOUND_TOOLS,
        "--vault",
        vault,
        "inventory",
        "--list-ambience",
    )
    assert inv.returncode == 0, inv.stdout + inv.stderr
    assert "3 music file(s), 1 ambience file(s)" in inv.stdout
    assert "Tavern Chatter" in inv.stdout

    # 2. build-moods (prefers Instrumental on duplicate stem)
    cfg_path = tmp_path / "test_moods.json"
    cfg_payload = {
        "collection": "Campaign",
        "moods": [
            {
                "id": "mood-tavern",
                "name": "Tavern Hearth",
                "order": 0,
                "fadeSeconds": 3.0,
                "icon": "beer-stein",
                "tone": "amber",
                "room": "room",
                "music": {
                    "tracks": ["Hearth Song"],
                    "levelDb": -4,
                    "shuffle": True,
                    "reverb": 0.1,
                },
                "layers": [
                    {
                        "sound": "Tavern Chatter",
                        "levelDb": -8,
                        "reverb": 0.1,
                    }
                ],
            },
            {
                "id": "mood-skirmish",
                "name": "Alley Skirmish",
                "order": 1,
                "fadeSeconds": 1.5,
                "icon": "combat",
                "tone": "gules",
                "room": "hall",
                "music": {
                    "tracks": ["Skirmish"],
                    "levelDb": -2,
                    "shuffle": True,
                    "reverb": 0.15,
                },
                "layers": [],
            },
        ],
        "sceneLinks": [
            {
                "scene": "Demo - Oakhaven Alley.atlasmap",
                "mood": "mood-tavern",
                "combatMood": "mood-skirmish",
            }
        ],
    }
    cfg_path.write_text(json.dumps(cfg_payload, indent=2), encoding="utf-8")

    build1 = run_cli(
        SCRIPT_ATLAS_SOUND_TOOLS,
        "--vault",
        vault,
        "build-moods",
        cfg_path,
    )
    assert build1.returncode == 0, build1.stdout + build1.stderr

    records_dir = sounds_dir / "records"
    moods_dir = sounds_dir / "moods"
    rec_files = sorted(records_dir.glob("sound-*.json"))
    assert len(rec_files) == 3

    # Verify Instrumental track was preferred and all audioPaths use POSIX '/'
    hearth_rec = None
    for rf in rec_files:
        raw = rf.read_text(encoding="utf-8")
        assert "\\\\" not in raw
        data = json.loads(raw)
        assert "\\" not in data["audioPath"]
        if data["name"] == "Hearth Song":
            hearth_rec = data
    assert hearth_rec is not None
    assert "/Instrumental/" in hearth_rec["audioPath"]

    # 3. Re-running build-moods must be idempotent (reuses existing records)
    build2 = run_cli(
        SCRIPT_ATLAS_SOUND_TOOLS,
        "--vault",
        vault,
        "build-moods",
        cfg_path,
    )
    assert build2.returncode == 0, build2.stdout + build2.stderr
    assert len(list(records_dir.glob("sound-*.json"))) == 3
    assert len(list(moods_dir.glob("mood-*.json"))) == 2

    # 4. link-scene
    link_one = run_cli(
        SCRIPT_ATLAS_SOUND_TOOLS,
        "--vault",
        vault,
        "link-scene",
        scene_file,
        "--mood",
        "mood-tavern",
        "--combat-mood",
        "mood-skirmish",
    )
    assert link_one.returncode == 0, link_one.stdout + link_one.stderr
    linked_data = json.loads(scene_file.read_text(encoding="utf-8"))
    assert linked_data["state"]["sound"] == {
        "mood": "mood-tavern",
        "combatMood": "mood-skirmish",
    }

    # 5. link-all
    link_all = run_cli(
        SCRIPT_ATLAS_SOUND_TOOLS,
        "--vault",
        vault,
        "link-all",
        cfg_path,
    )
    assert link_all.returncode == 0, link_all.stdout + link_all.stderr

    # 6. validate (must pass cleanly)
    val = run_cli(
        SCRIPT_ATLAS_SOUND_TOOLS,
        "--vault",
        vault,
        "validate",
    )
    assert val.returncode == 0, val.stdout + val.stderr
    assert "0 errors" in val.stdout.lower() or "passed" in val.stdout.lower()


def test_atlas_sound_tools_validate_catches_missing_audio_backslashes_and_broken_links(
    tmp_path: Path,
) -> None:
    vault = tmp_path / "broken_sound_vault"
    records_dir = vault / "atlas-vtt" / "sounds" / "records"
    moods_dir = vault / "atlas-vtt" / "sounds" / "moods"
    scenes_dir = vault / "atlas-vtt" / "collections" / "Campaign" / "scenes"
    records_dir.mkdir(parents=True)
    moods_dir.mkdir(parents=True)
    scenes_dir.mkdir(parents=True)

    # Record with missing audio AND Windows backslash
    (records_dir / "sound-broken-1234567890.json").write_text(
        json.dumps(
            {
                "format": 1,
                "id": "sound-broken-1234567890",
                "name": "Broken Track",
                "tags": [],
                "createdAt": 1700000000000,
                "modifiedAt": 1700000000000,
                "audioPath": r"atlas-vtt\sounds\music\missing.opus",
                "audioSize": 100,
                "kind": "music",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # Mood referencing a nonexistent track ID + invalid tone
    (moods_dir / "mood-broken.json").write_text(
        json.dumps(
            {
                "format": 1,
                "id": "mood-broken",
                "name": "Broken Mood",
                "order": 0,
                "fadeSeconds": 2.0,
                "icon": "music",
                "tone": "neutral",
                "room": "room",
                "music": {"tracks": ["sound-does-not-exist"], "levelDb": -4},
                "layers": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # Scene referencing a nonexistent mood ID
    (scenes_dir / "Broken Scene.atlasmap").write_text(
        json.dumps(
            {
                "version": 4,
                "state": {
                    "schema": "atlas-vtt",
                    "version": 4,
                    "sound": {"mood": "mood-ghost", "combatMood": "mood-phantom"},
                    "objects": {},
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    res = run_cli(SCRIPT_ATLAS_SOUND_TOOLS, "--vault", vault, "validate")
    assert res.returncode == 1
    assert "Windows backslashes" in res.stdout
    assert "points to missing file" in res.stdout
    assert "invalid tone 'neutral'" in res.stdout
    assert "missing music track record 'sound-does-not-exist'" in res.stdout
    assert "mood='mood-ghost' does not exist" in res.stdout
    assert "combatMood='mood-phantom' does not exist" in res.stdout

