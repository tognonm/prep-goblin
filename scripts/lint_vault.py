#!/usr/bin/env python3
"""Vault linter for Obsidian + Atlas VTT 0.16.0 (Demiurge Core).

Checks:
1. Valid YAML frontmatter in all Markdown notes.
2. Broken [[wikilink]] references (ignoring links inside code blocks).
3. Atlas VTT 0.16.0 hard 32 KB (32768-byte) file size limit for linked notes,
   dashboards, and monster statblocks.
4. Optional --full-atlas audit:
   - Token JSONs: verify every imagePath and statblockPath resolves in the vault.
   - Scene .atlasmap files: verify background, dmNotePath (< 32 KB), and 1:1
     pin.notePath#Heading anchors against ### H3 headings.
   - Locations/*.md: verify frontmatter atlas_scene references an existing scene.
   - Campaign/Improv Log.md: warn on any un-triaged post-session row with status
     `review` (ignoring empty template placeholder rows).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml

IGNORE_DIRS = {".git", ".obsidian", ".agents", "Sources", "Manuals", "Reference", "Archive", "scripts", "_templates"}
ATLAS_HARD_LIMIT_BYTES = 32768
ATLAS_WARN_LIMIT_BYTES = 30720
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
WIKILINK_RE = re.compile(r"\[\[([^\[\]\n]+)\]\]")


def resolve_default_vault(repo_root: Path) -> Path:
    cfg_path = repo_root / "campaign.config.json"
    if cfg_path.is_file():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            vault_dir = cfg.get("vault_dir")
            if vault_dir:
                cand = (repo_root / vault_dir).resolve()
                if cand.is_dir():
                    return cand
        except Exception:
            pass
    for candidate_name in ("Vault", "template-vault"):
        cand = repo_root / candidate_name
        if cand.is_dir():
            return cand
    return repo_root / "template-vault"


def is_atlas_size_checked(rel_path: Path) -> bool:
    parts = [p.lower() for p in rel_path.parts]
    if "atlas-vtt" in parts and "notes" in parts:
        return True
    if parts and parts[0] == "monsters":
        return True
    return False


def strip_code_blocks(content: str) -> str:
    no_fenced = FENCED_CODE_RE.sub("", content)
    return INLINE_CODE_RE.sub("", no_fenced)


def _resolve_vault_rel(vault_dir: Path, rel_str: str) -> Path:
    norm = rel_str.strip().replace("\\", "/").lstrip("/")
    return vault_dir / Path(*[part for part in norm.split("/") if part])


def _extract_h3_headings(md_path: Path, cache: dict[Path, set[str]]) -> set[str]:
    if md_path not in cache:
        try:
            text = md_path.read_text(encoding="utf-8", errors="ignore")
            cache[md_path] = set(re.findall(r"^###\s+(.+)$", text, flags=re.MULTILINE))
        except Exception:
            cache[md_path] = set()
    return cache[md_path]


def _check_posix_atlas_path(source_label: str, field_name: str, val: str, errors: list[str]) -> None:
    if "\\" in val:
        errors.append(
            f"{source_label} field '{field_name}' contains Windows backslash ('\\'): {val} "
            "(use forward slashes '/' for cross-platform Atlas VTT compatibility)"
        )


def _lint_full_atlas(
    vault_dir: Path,
    errors: list[str],
    warnings: list[str],
    already_size_checked: set[str],
) -> dict[str, int]:
    """Run deep Atlas VTT 0.16.0 cross-reference checks across the vault."""
    stats = {"tokens": 0, "scenes": 0, "locations": 0, "improv_review": 0}
    collections_root = vault_dir / "atlas-vtt" / "collections"
    heading_cache: dict[Path, set[str]] = {}
    available_scene_names: set[str] = set()

    if collections_root.is_dir():
        # 1. Verify token records: imagePath & statblockPath
        for tok_file in sorted(collections_root.glob("*/tokens/*.json")):
            stats["tokens"] += 1
            rel_tok = tok_file.relative_to(vault_dir).as_posix()
            try:
                data = json.loads(tok_file.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"Invalid JSON in token record {rel_tok}: {exc}")
                continue
            rec = data.get("atlasRecord") if isinstance(data.get("atlasRecord"), dict) else data
            if not isinstance(rec, dict):
                errors.append(f"Malformed token record in {rel_tok}")
                continue

            img_rel = str(rec.get("imagePath") or "").strip()
            if img_rel:
                _check_posix_atlas_path(f"Token {rel_tok}", "imagePath", img_rel, errors)
                if not _resolve_vault_rel(vault_dir, img_rel).is_file():
                    errors.append(f"Token {rel_tok} missing imagePath: {img_rel}")
            else:
                errors.append(f"Token {rel_tok} has empty imagePath")

            sb_rel = str(rec.get("statblockPath") or "").strip()
            if sb_rel:
                _check_posix_atlas_path(f"Token {rel_tok}", "statblockPath", sb_rel, errors)
                if not _resolve_vault_rel(vault_dir, sb_rel).is_file():
                    errors.append(f"Token {rel_tok} missing statblockPath: {sb_rel}")

        # Collect scene names from scene JSON records as well as .atlasmap stems
        for scene_json in sorted(collections_root.glob("*/scenes/*.json")):
            try:
                sdata = json.loads(scene_json.read_text(encoding="utf-8"))
            except Exception:
                continue
            rec = sdata.get("atlasRecord") if isinstance(sdata.get("atlasRecord"), dict) else {}
            sname = str(rec.get("name") or sdata.get("name") or "").strip()
            if sname:
                available_scene_names.add(sname)

        # 2. Verify .atlasmap scenes: background, dmNotePath (< 32 KB), and pin#Heading anchors
        for map_file in sorted(collections_root.glob("*/scenes/*.atlasmap")):
            stats["scenes"] += 1
            available_scene_names.add(map_file.stem)
            rel_map = map_file.relative_to(vault_dir).as_posix()
            try:
                data = json.loads(map_file.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"Invalid JSON in scene {rel_map}: {exc}")
                continue

            st = data.get("state") if isinstance(data.get("state"), dict) else {}
            objs = st.get("objects") if isinstance(st.get("objects"), dict) else {}

            bg_rel = str(st.get("background") or "").strip()
            if bg_rel:
                _check_posix_atlas_path(f"Scene {rel_map}", "background", bg_rel, errors)
                if not _resolve_vault_rel(vault_dir, bg_rel).is_file():
                    errors.append(f"Scene {rel_map} missing background asset: {bg_rel}")
            else:
                errors.append(f"Scene {rel_map} has no background asset defined")

            dm_note_rel = str(st.get("dmNotePath") or "").strip()
            if dm_note_rel:
                _check_posix_atlas_path(f"Scene {rel_map}", "dmNotePath", dm_note_rel, errors)
                dm_path = _resolve_vault_rel(vault_dir, dm_note_rel)
                if not dm_path.is_file():
                    errors.append(f"Scene {rel_map} missing dmNotePath: {dm_note_rel}")
                else:
                    dm_norm = dm_path.relative_to(vault_dir).as_posix()
                    if dm_norm not in already_size_checked:
                        bsize = dm_path.stat().st_size
                        if bsize >= ATLAS_HARD_LIMIT_BYTES:
                            errors.append(
                                f"Atlas VTT 32 KB limit exceeded in linked dmNotePath {dm_norm} "
                                f"({bsize} bytes >= {ATLAS_HARD_LIMIT_BYTES})"
                            )
                        elif bsize >= ATLAS_WARN_LIMIT_BYTES:
                            warnings.append(
                                f"Approaching Atlas VTT 32 KB limit in linked dmNotePath {dm_norm} ({bsize} bytes)"
                            )
                        already_size_checked.add(dm_norm)

            pins = objs.get("pins") if isinstance(objs.get("pins"), dict) else {}
            for pid, pin in pins.items():
                if not isinstance(pin, dict):
                    continue
                np_str = str(pin.get("notePath") or "").strip()
                if not np_str:
                    continue
                _check_posix_atlas_path(f"Scene {rel_map} pin {pid}", "notePath", np_str, errors)
                if "#" in np_str:
                    note_part, heading = np_str.split("#", 1)
                    note_path = _resolve_vault_rel(vault_dir, note_part)
                    if not note_path.is_file():
                        errors.append(f"Scene {rel_map} pin {pid} references missing note: {note_part}")
                    else:
                        headings = _extract_h3_headings(note_path, heading_cache)
                        if heading.strip() not in headings:
                            errors.append(
                                f"Scene {rel_map} pin {pid} heading not found as '### {heading.strip()}' in {note_part}"
                            )
                else:
                    if not _resolve_vault_rel(vault_dir, np_str).is_file():
                        errors.append(f"Scene {rel_map} pin {pid} references missing note: {np_str}")

    # 3. Verify Locations/*.md frontmatter atlas_scene references
    locations_dir = vault_dir / "Locations"
    if locations_dir.is_dir():
        for loc_md in sorted(locations_dir.rglob("*.md")):
            stats["locations"] += 1
            rel_loc = loc_md.relative_to(vault_dir).as_posix()
            try:
                content = loc_md.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            fm_match = re.match(r"^---\r?\n(.*?)\r?\n---", content, re.DOTALL)
            if not fm_match:
                continue
            try:
                fm: Any = yaml.safe_load(fm_match.group(1))
            except yaml.YAMLError:
                continue
            if isinstance(fm, dict):
                scene_ref = str(fm.get("atlas_scene") or "").strip()
                if scene_ref and scene_ref not in available_scene_names:
                    errors.append(
                        f"Location {rel_loc} references unknown atlas_scene '{scene_ref}' "
                        f"(not found in atlas-vtt/collections/*/scenes/)"
                    )

    # 4. Scan Campaign/Improv Log.md for un-triaged rows with status `review`
    improv_path = vault_dir / "Campaign" / "Improv Log.md"
    if improv_path.is_file():
        placeholder_vals = {"", "-", "—", "–", "n/a", "none"}
        try:
            improv_lines = improv_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            improv_lines = []
        for lineno, line in enumerate(improv_lines, 1):
            stripped = line.strip()
            if not (stripped.startswith("|") and stripped.endswith("|")):
                continue
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", stripped[1:-1])]
            if len(cells) < 2:
                continue
            # Skip table header separator rows (e.g. | :--- | :---: |)
            if all(re.fullmatch(r":?-+:?", c) for c in cells if c):
                continue
            status_cell = cells[-1].strip().strip("`*_").strip().lower()
            if status_cell != "review":
                continue
            data_cells = [c.strip().strip("`*_").strip() for c in cells[:-1]]
            if all(c.lower() in placeholder_vals for c in data_cells):
                continue
            stats["improv_review"] += 1
            summary = " | ".join(c for c in data_cells if c and c.lower() not in placeholder_vals)
            warnings.append(
                f"Un-triaged post-session item (status: review) in Campaign/Improv Log.md (line {lineno}): {summary}"
            )

    return stats


def lint_vault(vault_dir: Path, strict_links: bool = False, full_atlas: bool = False) -> int:
    if not vault_dir.is_dir():
        print(f"ERROR: Vault directory not found: {vault_dir}", file=sys.stderr)
        return 1

    print(f"Analyzing vault: {vault_dir}")
    all_files: set[str] = set()
    all_assets: set[str] = set()
    all_links: list[tuple[str, str]] = []
    errors: list[str] = []
    warnings: list[str] = []
    size_checked_paths: set[str] = set()
    checked_md = 0

    for root, dirs, files in os.walk(vault_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(vault_dir)
            rel_posix = rel_path.as_posix()
            all_assets.add(file)
            all_assets.add(rel_posix)

            if file.endswith(".md"):
                checked_md += 1
                all_files.add(file_path.stem)
                all_files.add(file)
                all_files.add(rel_posix)
                all_files.add(rel_posix[:-3])

                bsize = file_path.stat().st_size
                if is_atlas_size_checked(rel_path):
                    size_checked_paths.add(rel_posix)
                    if bsize >= ATLAS_HARD_LIMIT_BYTES:
                        errors.append(
                            f"Atlas VTT 32 KB limit exceeded in {rel_posix} ({bsize} bytes >= {ATLAS_HARD_LIMIT_BYTES})"
                        )
                    elif bsize >= ATLAS_WARN_LIMIT_BYTES:
                        warnings.append(
                            f"Approaching Atlas VTT 32 KB limit in {rel_posix} ({bsize} bytes)"
                        )

                try:
                    content = file_path.read_text(encoding="utf-8")
                except Exception as exc:
                    errors.append(f"Read error in {rel_posix}: {exc}")
                    continue

                fm_match = re.match(r"^---\r?\n(.*?)\r?\n---", content, re.DOTALL)
                if fm_match:
                    try:
                        yaml.safe_load(fm_match.group(1))
                    except yaml.YAMLError as exc:
                        errors.append(f"Invalid YAML frontmatter in {rel_posix}:\n{exc}")

                scan_body = strip_code_blocks(content)
                for raw_link in WIKILINK_RE.findall(scan_body):
                    clean_link = raw_link.replace("\\|", "|").split("|")[0].strip().split("#")[0].strip()
                    if clean_link:
                        all_links.append((clean_link, rel_posix))

    broken_links: list[tuple[str, str]] = []
    for link, src in all_links:
        if link.startswith(("http://", "https://")):
            continue
        link_norm = link.replace("\\", "/")
        link_path = Path(link_norm)
        if (
            link_norm not in all_files
            and link_norm not in all_assets
            and link_path.stem not in all_files
            and link_path.name not in all_assets
        ):
            broken_links.append((link, src))

    atlas_stats: dict[str, int] | None = None
    if full_atlas:
        atlas_stats = _lint_full_atlas(vault_dir, errors, warnings, size_checked_paths)

    print(f"Scanned {checked_md} Markdown notes.")
    if atlas_stats is not None:
        print(
            f"Full Atlas audit: {atlas_stats['tokens']} token record(s), "
            f"{atlas_stats['scenes']} scene(s), {atlas_stats['locations']} location note(s)."
        )

    if warnings:
        print("\n--- WARNINGS ---")
        for w in warnings:
            print(f"- {w}")

    if errors:
        print("\n--- ERRORS FOUND ---")
        for e in errors:
            print(f"- {e}")
    else:
        print("\nNo YAML syntax, Atlas integrity, or size limit errors found.")

    if broken_links:
        print("\n--- BROKEN WIKILINKS ---")
        for bl, src in sorted(set(broken_links)):
            print(f"- [[{bl}]] (in {src})")
    else:
        print("No broken wikilinks found.")

    if errors or (strict_links and broken_links):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Lint an Obsidian + Atlas VTT 0.16.0 vault.")
    parser.add_argument(
        "--vault",
        type=Path,
        default=None,
        help="Path to the vault directory (defaults to campaign.config.json vault_dir or Vault/ / template-vault/).",
    )
    parser.add_argument(
        "--strict-links",
        action="store_true",
        help="Exit with code 1 if any broken wikilinks are found.",
    )
    parser.add_argument(
        "--full-atlas",
        action="store_true",
        help="Verify Atlas VTT token assets, .atlasmap scenes/pins/dashboards, Location atlas_scene refs, and Improv Log triage status.",
    )
    args = parser.parse_args(argv)
    vault_dir = args.vault.resolve() if args.vault else resolve_default_vault(repo_root)
    return lint_vault(vault_dir, strict_links=args.strict_links, full_atlas=args.full_atlas)


if __name__ == "__main__":
    raise SystemExit(main())
