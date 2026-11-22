#!/usr/bin/env python3
"""Build a party-agnostic 8-scene Wildcard Battlemaps Atlas VTT 0.16.0 collection (Prep Goblin).

Generates all 8 procedural battlemap presets (whiteboard, alley, road, hills,
interior, camp, bridge, crypt) with zero PC tokens so any Game Master can import
or export the collection cleanly from Atlas VTT's Asset Manager (including for
sharing in the Atlas VTT Armarium at https://atlas-vtt.dev/armarium).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
QUICK_BATTLEMAP_SCRIPT = REPO_ROOT / ".agents" / "skills" / "quick-battlemap" / "scripts" / "quick_battlemap.py"
SCENE_TOOLS_SCRIPT = REPO_ROOT / ".agents" / "skills" / "dungeons-and-maps" / "scripts" / "atlas_scene_tools.py"

WILDCARD_PACK_SPECS: list[tuple[str, str, str, str]] = [
    ("whiteboard", "Wildcard - Tactical Whiteboard", "wildcard_whiteboard", "day"),
    ("alley", "Wildcard - Urban Alley", "wildcard_alley", "dusk"),
    ("road", "Wildcard - Country Road", "wildcard_road", "day"),
    ("hills", "Wildcard - Rocky Hills", "wildcard_hills", "dusk"),
    ("interior", "Wildcard - Building Interior", "wildcard_interior", "night"),
    ("camp", "Wildcard - Forest Camp", "wildcard_camp", "night"),
    ("bridge", "Wildcard - River Bridge", "wildcard_bridge", "day"),
    ("crypt", "Wildcard - Stone Crypt", "wildcard_crypt", "night"),
]


def run_step(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def build_pack(
    out_vault: Path,
    collection: str,
    units: str,
    seed: int,
    zip_out: Path | None,
    validate: bool,
) -> int:
    out_vault = out_vault.resolve()
    col_dir = out_vault / "atlas-vtt" / "collections" / collection
    col_dir.mkdir(parents=True, exist_ok=True)

    # Write a minimal temporary config inside a non-vault helper or pass overrides cleanly
    unit_dist = 1.5 if units == "meters" else 5
    tmp_cfg = out_vault / ".prep-goblin-pack.config.json"
    tmp_cfg.write_text(
        json.dumps(
            {
                "campaign_name": collection,
                "vault_dir": ".",
                "atlas_collection": collection,
                "grid_unit_type": units,
                "grid_unit_distance": unit_dist,
                "party_level": 3,
                "party": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    try:
        # Write clean Armarium-safe collection.json (no custom formulas/external paths)
        col_json = col_dir / "collection.json"
        col_json.write_text(
            json.dumps(
                {
                    "id": collection,
                    "name": collection,
                    "settings": {
                        "randomTables": [],
                        "lootBases": [],
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )

        generated_scenes: list[tuple[Path, Path]] = []
        for idx, (preset, scene_name, slug, lighting) in enumerate(WILDCARD_PACK_SPECS, start=1):
            cmd = [
                sys.executable,
                str(QUICK_BATTLEMAP_SCRIPT),
                "--preset",
                preset,
                "--name",
                scene_name,
                "--slug",
                slug,
                "--lighting",
                lighting,
                "--seed",
                str(seed + idx - 1),
                "--collection",
                collection,
                "--config",
                str(tmp_cfg),
                "--out-dir",
                str(out_vault),
                "--no-pcs",
            ]
            res = run_step(cmd)
            if res.returncode != 0:
                print(f"ERROR generating preset '{preset}':\n{res.stderr or res.stdout}", file=sys.stderr)
                return 1
            scene_path = col_dir / "scenes" / f"{scene_name}.atlasmap"
            note_path = col_dir / "notes" / f"{scene_name}.md"
            generated_scenes.append((scene_path, note_path))
            print(f"  [{idx}/8] Built {scene_name} ({preset}, {lighting})")

        if validate:
            print("\nValidating all 8 scenes (Atlas VTT v4 schema, < 32 KB Dashboards, zero wall leaks)...")
            for scene_path, note_path in generated_scenes:
                val = run_step(
                    [
                        sys.executable,
                        str(SCENE_TOOLS_SCRIPT),
                        "--vault",
                        str(out_vault),
                        "validate",
                        str(scene_path),
                        "--dashboard",
                        str(note_path),
                    ]
                )
                if val.returncode != 0:
                    print(f"VALIDATION FAILED for {scene_path.name}:\n{val.stdout}\n{val.stderr}", file=sys.stderr)
                    return 1
                aud = run_step(
                    [
                        sys.executable,
                        str(SCENE_TOOLS_SCRIPT),
                        "--vault",
                        str(out_vault),
                        "audit-walls",
                        str(scene_path),
                        "--strict",
                    ]
                )
                if aud.returncode != 0:
                    print(f"WALL AUDIT FAILED for {scene_path.name}:\n{aud.stdout}\n{aud.stderr}", file=sys.stderr)
                    return 1
            print("All 8 scenes PASSED validate + audit-walls --strict.")
    finally:
        if tmp_cfg.exists():
            tmp_cfg.unlink()

    if zip_out is not None:
        zip_out = zip_out.resolve()
        zip_out.parent.mkdir(parents=True, exist_ok=True)
        atlas_root = out_vault / "atlas-vtt"
        with zipfile.ZipFile(zip_out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for item in sorted(atlas_root.rglob("*")):
                if item.is_file():
                    arcname = item.relative_to(out_vault).as_posix()
                    zf.write(item, arcname)
        print(f"\nPackaged archive: {zip_out} ({zip_out.stat().st_size // 1024} KB)")

    print(
        f"\nReady! Open '{out_vault}' in Obsidian -> Atlas VTT -> Asset Manager -> "
        f"select '{collection}' -> Export collection to create an Armarium-ready .zip."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Build the Prep Goblin 8-scene party-agnostic Wildcard Battlemaps collection for Atlas VTT 0.16.0."
    )
    parser.add_argument(
        "--out-vault",
        type=Path,
        required=True,
        help="Target vault directory where atlas-vtt/collections/<collection>/ will be written.",
    )
    parser.add_argument(
        "--collection",
        default="Prep Goblin Wildcards",
        help="Atlas VTT collection name (default: 'Prep Goblin Wildcards').",
    )
    parser.add_argument(
        "--units",
        choices=["feet", "meters"],
        default="feet",
        help="Grid distance units (default: feet).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Base deterministic RNG seed (default: 42).",
    )
    parser.add_argument(
        "--zip",
        dest="zip_out",
        type=Path,
        default=None,
        help="Optional .zip archive path to bundle the generated atlas-vtt/ folder.",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip post-generation validate and audit-walls --strict checks.",
    )
    args = parser.parse_args(argv)
    return build_pack(
        out_vault=args.out_vault,
        collection=args.collection,
        units=args.units,
        seed=args.seed,
        zip_out=args.zip_out,
        validate=not args.no_validate,
    )


if __name__ == "__main__":
    raise SystemExit(main())
