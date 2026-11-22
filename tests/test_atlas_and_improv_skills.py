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
