#!/usr/bin/env python3
"""Vault linter for Obsidian + Atlas VTT 0.16.0 (Demiurge Core).

Checks:
1. Valid YAML frontmatter in all Markdown notes.
2. Broken [[wikilink]] references (ignoring links inside code blocks).
3. Atlas VTT 0.16.0 hard 32 KB (32768-byte) file size limit for linked notes,
   dashboards, and monster statblocks.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

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


def lint_vault(vault_dir: Path, strict_links: bool = False) -> int:
    if not vault_dir.is_dir():
        print(f"ERROR: Vault directory not found: {vault_dir}", file=sys.stderr)
        return 1

    print(f"Analyzing vault: {vault_dir}")
    all_files: set[str] = set()
    all_assets: set[str] = set()
    all_links: list[tuple[str, str]] = []
    errors: list[str] = []
    warnings: list[str] = []
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

    print(f"Scanned {checked_md} Markdown notes.")

    if warnings:
        print("\n--- WARNINGS ---")
        for w in warnings:
            print(f"- {w}")

    if errors:
        print("\n--- ERRORS FOUND ---")
        for e in errors:
            print(f"- {e}")
    else:
        print("\nNo YAML syntax or Atlas size limit errors found.")

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
    args = parser.parse_args(argv)
    vault_dir = args.vault.resolve() if args.vault else resolve_default_vault(repo_root)
    return lint_vault(vault_dir, strict_links=args.strict_links)


if __name__ == "__main__":
    raise SystemExit(main())
