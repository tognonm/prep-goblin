#!/usr/bin/env python3
"""Spoiler Firewall & Player Portal Exporter for Prep Goblin.

Exports a clean, player-safe subset of an Obsidian + Atlas VTT 0.16.0 vault
for Quartz static sites, shared player vaults, or single-file Discord/PDF
handouts.

Security guarantees (fail-closed):
- Excludes private DM directories (atlas-vtt/, Encounters/, Monsters/, etc.)
  and known DM-only files (DM Screen.md, World State.md, Improv Log.md,
  Story Arcs.md).
- Excludes any note with malformed YAML frontmatter (fail-closed),
  `visibility: dm-only` / `master`, DM-only tags (`dm-only`, `dm-secret`,
  `secret`, `private`, `master`), or `publish: false` (and optionally
  requires `publish: true` via `--publish-only`).
- Physically strips secret Obsidian callouts (including lazy continuation
  lines), ALL HTML comments (`<!--...-->`), paired/unclosed spoiler blocks,
  and ALL Obsidian native comments (`%%...%%`) outside fenced/inline code,
  airtight on both LF and CRLF.
- Sanitizes [[wikilinks]] and Markdown links (including angle-bracket
  CommonMark destinations, spaces, escaped pipes `\\|`, and YAML frontmatter
  values) while rejecting explicit excluded paths before basename fallback.
- Independent `--verify` audit pass fails with exit code 1 if any DM secret,
  comment marker, malformed YAML, or excluded link leaked into the output.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import yaml

EXCLUDED_DIRS = {
    "atlas-vtt",
    "encounters",
    "monsters",
    ".obsidian",
    ".trash",
    "_templates",
    ".git",
    ".agents",
    "sources",
    "manuals",
    "reference",
    "archive",
}

EXCLUDED_REL_FILES = {
    "dm screen.md",
    "campaign/world state.md",
    "campaign/improv log.md",
    "campaign/story arcs.md",
}

DM_VISIBILITY_VALUES = {
    "dm-only",
    "dm_only",
    "dm",
    "master",
    "private",
    "secret",
}

DM_ONLY_TAGS = {
    "dm-only",
    "dm_only",
    "dm-secret",
    "dm_secret",
    "secret",
    "private",
    "master",
}

SECRET_CALLOUT_TYPES = {
    "danger",
    "spoiler",
    "secret",
    "dm",
    "dm-only",
    "dm_only",
    "dm-secret",
    "dm_secret",
}

IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".svg",
    ".avif",
}

FM_RE = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)
EMPTY_FM_RE = re.compile(r"\A---[ \t]*\n---[ \t]*(?:\n|\Z)")
FM_OPEN_ONLY_RE = re.compile(r"\A---[ \t]*(?:\n|\Z)")

RAW_FM_DM_VIS_RE = re.compile(
    r"^[ \t]*visibility[ \t]*:[ \t]*['\"]?(?:dm-only|dm_only|dm|master|private|secret)['\"]?(?:[ \t#].*|$)",
    re.IGNORECASE | re.MULTILINE,
)
RAW_FM_PUBLISH_FALSE_RE = re.compile(
    r"^[ \t]*publish[ \t]*:[ \t]*['\"]?false['\"]?(?:[ \t#].*|$)",
    re.IGNORECASE | re.MULTILINE,
)
RAW_FM_DM_TAG_INLINE_RE = re.compile(
    r"^[ \t]*tags[ \t]*:[^\n]*(?:^|[\s,\[#\"'/])(?:dm-only|dm_only|dm-secret|dm_secret|secret|private|master)(?=$|[\s,\]\"'/])",
    re.IGNORECASE | re.MULTILINE,
)
RAW_FM_DM_TAG_ITEM_RE = re.compile(
    r"^[ \t]*-[ \t]*['\"]?#?(?:dm-only|dm_only|dm-secret|dm_secret|secret|private|master)(?:/[^\s'\"]*)?['\"]?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)

HTML_SPOILER_OPEN_RE = re.compile(
    r"<!--\s*(dm-only|dm_only|dm-secret|dm_secret|secret)\s*-->",
    re.IGNORECASE,
)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
OBSIDIAN_COMMENT_RE = re.compile(r"%%.*?%%", re.DOTALL)

BQ_PREFIX_RE = re.compile(r"^[ \t]*((?:>[ \t]*)+)")
CALLOUT_HEADER_RE = re.compile(
    r"^([ \t]*(?:>[ \t]*)+)\[\!([A-Za-z0-9_-]+)\]([+-])?(?:[ \t]+(.*))?$"
)
SECRET_TITLE_RE = re.compile(
    r"(?:dm[\s_-]*(?:secret|only)|spoiler)",
    re.IGNORECASE,
)
NEW_MD_BLOCK_RE = re.compile(
    r"^[ \t]*(?:"
    r"#{1,6}(?:[ \t]|$)"
    r"|[-*+][ \t]+"
    r"|\d+[.)][ \t]+"
    r"|(?:-[ \t]*){3,}$"
    r"|(?:\*[ \t]*){3,}$"
    r"|(?:_[ \t]*){3,}$"
    r"|`{3,}"
    r"|~{3,}"
    r"|\|"
    r")"
)

FENCE_OPEN_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
INLINE_CODE_SPAN_RE = re.compile(r"(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.DOTALL)
WIKILINK_RE = re.compile(r"(?P<bang>!?)\[\[(?P<inner>[^\[\]\n]+)\]\]")
MD_LINK_RE = re.compile(r"(?P<bang>!?)\[(?P<alt>[^\]\n]*)\]\((?P<dest>[^)\n]+)\)")
MD_DEST_ANGLE_RE = re.compile(r"^<([^>\n]+)>")
MD_DEST_TITLE_SUFFIX_RE = re.compile(r'\s+(?:"[^"]*"|\'[^\']*\'|\([^)]*\))\s*$')
PIPE_SPLIT_RE = re.compile(r"\\?\|")


@dataclass
class NoteRecord:
    src_path: Path
    rel_path: Path
    rel_posix: str
    frontmatter: dict[str, Any]
    has_frontmatter: bool
    raw_frontmatter: str
    body: str
    title: str
    slug: str


@dataclass
class ExportStats:
    scanned_notes: int = 0
    exported_notes: int = 0
    excluded_notes: int = 0
    excluded_reasons: dict[str, int] = field(default_factory=dict)
    stripped_callouts: int = 0
    stripped_comments: int = 0
    unclosed_comment_warnings: int = 0
    sanitized_links: int = 0
    copied_assets: int = 0

    def record_exclusion(self, reason: str) -> None:
        self.excluded_notes += 1
        self.excluded_reasons[reason] = self.excluded_reasons.get(reason, 0) + 1


def resolve_default_vault(repo_root: Path) -> Path:
    cfg_path = repo_root / "campaign.config.json"
    if cfg_path.is_file():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
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
            return cand.resolve()
    return (repo_root / "template-vault").resolve()


def load_campaign_name(repo_root: Path) -> str:
    cfg_path = repo_root / "campaign.config.json"
    if cfg_path.is_file():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8-sig"))
            name = str(cfg.get("campaign_name", "")).strip()
            if name and name != "{{CAMPAIGN_NAME}}":
                return name
        except Exception:
            pass
    return "Campaign"


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_text_normalized(path: Path) -> str:
    return normalize_newlines(path.read_text(encoding="utf-8-sig"))


def parse_frontmatter(text: str) -> tuple[dict[str, Any], bool, str, str, bool]:
    """Return (frontmatter_dict, has_frontmatter, raw_yaml, body, yaml_error)."""
    m_empty = EMPTY_FM_RE.match(text)
    if m_empty:
        return {}, True, "", text[m_empty.end():], False
    m = FM_RE.match(text)
    if not m:
        if FM_OPEN_ONLY_RE.match(text):
            # Opening '---' with no closing '---': treat as malformed YAML (fail-closed)
            return {}, True, text, "", True
        return {}, False, "", text, False
    raw_yaml = m.group(1)
    body = text[m.end():]
    try:
        loaded = yaml.safe_load(raw_yaml)
    except yaml.YAMLError:
        return {}, True, raw_yaml, body, True
    if loaded is None:
        return {}, True, raw_yaml, body, False
    if not isinstance(loaded, dict):
        return {}, True, raw_yaml, body, True
    return loaded, True, raw_yaml, body, False


def is_false_flag(val: Any) -> bool:
    if val is False:
        return True
    if isinstance(val, str) and val.strip().lower() == "false":
        return True
    return False


def is_true_flag(val: Any) -> bool:
    if val is True:
        return True
    if isinstance(val, str) and val.strip().lower() == "true":
        return True
    return False


def normalize_tag(tag: Any) -> str:
    return str(tag).strip().lstrip("#").lower()


def is_dm_only_frontmatter(fm: dict[str, Any]) -> bool:
    vis = fm.get("visibility")
    if isinstance(vis, str) and vis.strip().lower() in DM_VISIBILITY_VALUES:
        return True
    tags = fm.get("tags")
    if isinstance(tags, str):
        tags_list = [normalize_tag(t) for t in re.split(r"[,\s]+", tags) if t.strip()]
    elif isinstance(tags, list):
        tags_list = [normalize_tag(t) for t in tags if str(t).strip()]
    else:
        tags_list = []
    for t in tags_list:
        if t in DM_ONLY_TAGS or t.split("/", 1)[0] in DM_ONLY_TAGS:
            return True
    return False


def has_raw_dm_only_frontmatter(raw_yaml: str) -> bool:
    """Regex defense-in-depth over raw YAML frontmatter."""
    if not raw_yaml:
        return False
    if RAW_FM_DM_VIS_RE.search(raw_yaml):
        return True
    if RAW_FM_PUBLISH_FALSE_RE.search(raw_yaml):
        return True
    if RAW_FM_DM_TAG_INLINE_RE.search(raw_yaml):
        return True
    if RAW_FM_DM_TAG_ITEM_RE.search(raw_yaml):
        return True
    return False


def has_excluded_dir(rel_path: Path) -> bool:
    return any(part.lower() in EXCLUDED_DIRS for part in rel_path.parts[:-1])


def is_explicitly_excluded_target(raw_path: str, note_rel: Path | None = None) -> bool:
    """Return True if an explicit relative/vault path targets EXCLUDED_DIRS or EXCLUDED_REL_FILES."""
    norm = raw_path.replace("\\", "/").strip()
    if not norm or norm.startswith(("http://", "https://", "mailto:", "data:", "#")):
        return False

    candidates: list[str] = [norm.lstrip("./").strip("/").lower()]
    if note_rel is not None:
        rel_joined = os.path.normpath((note_rel.parent / norm).as_posix()).replace("\\", "/")
        candidates.append(rel_joined.lstrip("./").strip("/").lower())

    for cand in candidates:
        if not cand:
            continue
        parts = [p for p in cand.split("/") if p and p != "."]
        if any(p in EXCLUDED_DIRS for p in parts):
            return True
        if cand in EXCLUDED_REL_FILES:
            return True
        if not cand.endswith(".md") and f"{cand}.md" in EXCLUDED_REL_FILES:
            return True
    return False


def make_slug(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug or "section"


def bq_depth(line: str) -> int:
    m = BQ_PREFIX_RE.match(line)
    return m.group(1).count(">") if m else 0


def is_secret_callout_header(line: str) -> bool:
    m = CALLOUT_HEADER_RE.match(line)
    if not m:
        return False
    ctype = m.group(2).strip().lower()
    title = (m.group(4) or "").strip()
    if ctype in SECRET_CALLOUT_TYPES:
        return True
    if title and SECRET_TITLE_RE.search(title):
        return True
    return False


def split_by_fenced_code(text: str) -> list[tuple[bool, str]]:
    """Split text into [(is_code_block, chunk_text), ...] preserving exact text."""
    lines = text.split("\n")
    segments: list[tuple[bool, str]] = []
    buf: list[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0

    for line in lines:
        if not in_fence:
            m = FENCE_OPEN_RE.match(line)
            if m:
                if buf:
                    segments.append((False, "\n".join(buf)))
                    buf = []
                in_fence = True
                fence_char = m.group(1)[0]
                fence_len = len(m.group(1))
                buf.append(line)
            else:
                buf.append(line)
        else:
            buf.append(line)
            close_re = re.compile(rf"^[ \t]*{re.escape(fence_char)}{{{fence_len},}}[ \t]*$")
            if close_re.match(line):
                segments.append((True, "\n".join(buf)))
                buf = []
                in_fence = False
                fence_char = ""
                fence_len = 0

    if buf:
        segments.append((in_fence, "\n".join(buf)))

    return segments


def split_by_inline_code(text: str) -> list[tuple[bool, str]]:
    """Split a non-fenced fragment into [(is_inline_code, chunk), ...]."""
    out: list[tuple[bool, str]] = []
    pos = 0
    for m in INLINE_CODE_SPAN_RE.finditer(text):
        if m.start() > pos:
            out.append((False, text[pos:m.start()]))
        out.append((True, m.group(0)))
        pos = m.end()
    if pos < len(text):
        out.append((False, text[pos:]))
    return out


def tokenize_markdown_code(text: str) -> list[tuple[bool, str]]:
    """Split Markdown into [(is_code, text), ...] protecting fenced blocks and inline backticks."""
    tokens: list[tuple[bool, str]] = []
    fenced = split_by_fenced_code(text)
    for idx, (is_fence, chunk) in enumerate(fenced):
        if idx > 0:
            tokens.append((False, "\n"))
        if is_fence:
            tokens.append((True, chunk))
        else:
            tokens.extend(split_by_inline_code(chunk))
    return tokens


def strip_comments_outside_code(text: str, note_label: str = "") -> tuple[str, int, int]:
    """Strip paired/unclosed HTML spoiler blocks, all HTML comments, and all Obsidian %% comments.

    Operates outside fenced code blocks and inline code spans. Paired spoiler blocks
    (`<!-- dm-only -->...<!-- /dm-only -->`) also strip any fenced code wrapped inside them.
    Unclosed spoiler/comment markers fail-closed by stripping to EOF.

    Returns (cleaned_text, stripped_comment_count, unclosed_marker_warnings).
    """
    tokens = tokenize_markdown_code(text)
    stripped_count = 0
    unclosed_warnings = 0

    # Pass 1: paired and unpaired <!-- dm-only --> / <!-- secret --> spoiler blocks
    out_tokens: list[tuple[bool, str]] = []
    i = 0
    while i < len(tokens):
        is_code, chunk = tokens[i]
        if is_code:
            out_tokens.append((True, chunk))
            i += 1
            continue

        pos = 0
        while True:
            open_m = HTML_SPOILER_OPEN_RE.search(chunk, pos)
            if not open_m:
                if pos < len(chunk):
                    out_tokens.append((False, chunk[pos:]))
                break

            if open_m.start() > pos:
                out_tokens.append((False, chunk[pos:open_m.start()]))

            tag_name = open_m.group(1)
            close_re = re.compile(rf"<!--\s*/\s*{re.escape(tag_name)}\s*-->", re.IGNORECASE)

            # Check for closing tag in remainder of current token first
            close_m = close_re.search(chunk, open_m.end())
            if close_m:
                stripped_count += 1
                pos = close_m.end()
                continue

            # Search forward across subsequent non-code tokens (handles fenced code inside spoiler block)
            found_j: int | None = None
            found_close_end = 0
            for j in range(i + 1, len(tokens)):
                j_code, j_chunk = tokens[j]
                if j_code:
                    continue
                cm = close_re.search(j_chunk)
                if cm:
                    found_j = j
                    found_close_end = cm.end()
                    break

            if found_j is not None:
                stripped_count += 1
                i = found_j
                chunk = tokens[i][1]
                pos = found_close_end
                continue

            # Fail-closed: unpaired opening spoiler tag -> strip through EOF
            stripped_count += 1
            unclosed_warnings += 1
            if note_label:
                print(
                    f"WARNING: Unclosed <!-- {tag_name} --> spoiler block in {note_label}; "
                    "stripped fail-closed to end of file.",
                    file=sys.stderr,
                )
            return "".join(t for _, t in out_tokens), stripped_count, unclosed_warnings

        i += 1

    # Pass 2: strip all remaining closed HTML comments, Obsidian %% comments, and unclosed markers fail-closed
    final_tokens: list[tuple[bool, str]] = []
    for is_code, chunk in out_tokens:
        if is_code:
            final_tokens.append((True, chunk))
            continue

        def _html_repl(_m: re.Match[str]) -> str:
            nonlocal stripped_count
            stripped_count += 1
            return ""

        def _obs_repl(_m: re.Match[str]) -> str:
            nonlocal stripped_count
            stripped_count += 1
            return ""

        cleaned = HTML_COMMENT_RE.sub(_html_repl, chunk)
        cleaned = OBSIDIAN_COMMENT_RE.sub(_obs_repl, cleaned)

        # Fail-closed check for unclosed '<!--' or unclosed '%%'
        unclosed_html = cleaned.find("<!--")
        unclosed_obs = cleaned.find("%%")
        cut_positions = [p for p in (unclosed_html, unclosed_obs) if p != -1]
        if cut_positions:
            cut_at = min(cut_positions)
            marker = "<!--" if cut_at == unclosed_html else "%%"
            final_tokens.append((False, cleaned[:cut_at]))
            stripped_count += 1
            unclosed_warnings += 1
            if note_label:
                print(
                    f"WARNING: Unclosed `{marker}` comment in {note_label}; "
                    "stripped fail-closed to end of file.",
                    file=sys.stderr,
                )
            return "".join(t for _, t in final_tokens), stripped_count, unclosed_warnings

        final_tokens.append((False, cleaned))

    return "".join(t for _, t in final_tokens), stripped_count, unclosed_warnings


def strip_spoilers(body: str, note_label: str = "") -> tuple[str, int, int, int]:
    """Physically strip comments and secret Obsidian callouts (incl. lazy continuations).

    Returns (cleaned_body, stripped_callouts_count, stripped_comments_count, unclosed_warnings).
    """
    text = normalize_newlines(body)
    text, comment_count, unclosed_warnings = strip_comments_outside_code(text, note_label=note_label)

    lines = text.split("\n")
    out_lines: list[str] = []
    skip_depth = 0
    prev_was_nonempty_bq_or_lazy = False
    callout_count = 0

    in_fence = False
    fence_char = ""
    fence_len = 0

    i = 0
    while i < len(lines):
        line = lines[i]

        # Track fenced code blocks when not currently skipping a secret callout
        if skip_depth == 0:
            if not in_fence:
                fm = FENCE_OPEN_RE.match(line)
                if fm:
                    in_fence = True
                    fence_char = fm.group(1)[0]
                    fence_len = len(fm.group(1))
                    out_lines.append(line)
                    i += 1
                    continue
            else:
                out_lines.append(line)
                close_re = re.compile(rf"^[ \t]*{re.escape(fence_char)}{{{fence_len},}}[ \t]*$")
                if close_re.match(line):
                    in_fence = False
                    fence_char = ""
                    fence_len = 0
                i += 1
                continue

        depth = bq_depth(line)

        if skip_depth > 0:
            if depth >= skip_depth:
                prev_was_nonempty_bq_or_lazy = bool(line.lstrip(" \t>").strip())
                i += 1
                continue
            # CommonMark / Obsidian lazy continuation for top-level secret callouts
            if (
                skip_depth == 1
                and depth == 0
                and line.strip() != ""
                and prev_was_nonempty_bq_or_lazy
                and not NEW_MD_BLOCK_RE.match(line)
            ):
                prev_was_nonempty_bq_or_lazy = True
                i += 1
                continue
            skip_depth = 0
            prev_was_nonempty_bq_or_lazy = False
            # Re-evaluate this line without advancing i

        if is_secret_callout_header(line):
            skip_depth = max(1, depth)
            prev_was_nonempty_bq_or_lazy = True
            callout_count += 1
            i += 1
            continue

        out_lines.append(line)
        i += 1

    cleaned = "\n".join(out_lines)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned, callout_count, comment_count, unclosed_warnings


def index_allowed_assets(vault_dir: Path) -> dict[str, Path]:
    """Index local image assets outside excluded DM directories."""
    assets: dict[str, Path] = {}
    for root, dirs, files in os.walk(vault_dir):
        dirs[:] = sorted(d for d in dirs if d.lower() not in EXCLUDED_DIRS)
        for fname in sorted(files):
            fpath = Path(root) / fname
            if fpath.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            rel = fpath.relative_to(vault_dir)
            rel_posix = rel.as_posix().lower()
            assets[rel_posix] = rel
            assets.setdefault(fname.lower(), rel)
    return assets


def clean_display_name(note_part: str) -> str:
    norm = note_part.replace("\\", "/").strip("/")
    name = Path(norm).name if norm else note_part.strip()
    if name.lower().endswith(".md"):
        name = name[:-3]
    return name


def parse_md_link_dest(dest_raw: str) -> str:
    """Parse CommonMark link destination supporting <angle brackets>, spaces, and optional titles."""
    s = dest_raw.strip()
    if not s:
        return ""
    angle_m = MD_DEST_ANGLE_RE.match(s)
    if angle_m:
        path_raw = angle_m.group(1).strip()
    else:
        path_raw = MD_DEST_TITLE_SUFFIX_RE.sub("", s).strip()
    path_decoded = unquote(path_raw)
    return path_decoded.split("#", 1)[0].strip()


def sanitize_links_in_fragment(
    fragment: str,
    note_rel: Path,
    exported_targets: dict[str, NoteRecord],
    allowed_assets: dict[str, Path],
    referenced_assets: set[Path],
    output_format: str,
) -> tuple[str, int]:
    """Sanitize [[wikilinks]] and local Markdown links/images in a non-code fragment."""
    sanitized_count = 0

    def _resolve_asset(raw_target: str) -> Path | None:
        cleaned = unquote(raw_target.strip().strip("<>")).replace("\\", "/").strip()
        if not cleaned or cleaned.startswith(("http://", "https://", "mailto:", "data:", "#")):
            return None
        if is_explicitly_excluded_target(cleaned, note_rel=note_rel):
            return None
        rel_candidate = os.path.normpath((note_rel.parent / cleaned).as_posix()).replace("\\", "/").lower()
        if rel_candidate in allowed_assets:
            return allowed_assets[rel_candidate]
        norm_key = cleaned.lstrip("./").lower()
        if norm_key in allowed_assets:
            return allowed_assets[norm_key]
        # Only fall back to basename if target does not specify a directory path
        if "/" not in norm_key:
            base_key = Path(norm_key).name.lower()
            if base_key in allowed_assets:
                return allowed_assets[base_key]
        return None

    def _wikilink_repl(match: re.Match[str]) -> str:
        nonlocal sanitized_count
        bang = match.group("bang")
        inner = match.group("inner")

        pipe_m = PIPE_SPLIT_RE.search(inner)
        if pipe_m:
            target_part = inner[:pipe_m.start()].strip()
            alias_part = inner[pipe_m.end():].strip()
        else:
            target_part = inner.strip()
            alias_part = ""

        if "#" in target_part:
            note_part, anchor_part = target_part.split("#", 1)
            note_part = note_part.strip()
            anchor_part = anchor_part.strip()
        else:
            note_part = target_part.strip()
            anchor_part = ""

        # Same-file heading link (e.g., [[#Overview]])
        if not note_part:
            if output_format == "single-md" and anchor_part:
                display = alias_part or anchor_part
                return f"[{display}](#{make_slug(anchor_part)})"
            return match.group(0)

        norm = note_part.replace("\\", "/").strip("/")
        norm_lower = norm.lower()
        norm_no_md = norm_lower[:-3] if norm_lower.endswith(".md") else norm_lower

        # Reject explicit excluded paths BEFORE any lookup or basename fallback
        if is_explicitly_excluded_target(norm, note_rel=note_rel):
            sanitized_count += 1
            if bang == "!":
                return ""
            return alias_part if alias_part else clean_display_name(note_part)

        # Check image / asset embeds or links
        ext = Path(norm_lower).suffix
        if ext in IMAGE_EXTENSIONS:
            asset_rel = _resolve_asset(norm)
            if asset_rel is not None:
                referenced_assets.add(asset_rel)
                if output_format == "single-md":
                    alt = alias_part or asset_rel.stem
                    if bang == "!":
                        return f"![{alt}]({asset_rel.as_posix()})"
                    return f"[{alt}]({asset_rel.as_posix()})"
                return match.group(0)
            sanitized_count += 1
            if bang == "!":
                return ""
            return alias_part or clean_display_name(note_part)

        # Check exported notes (explicit path match first; basename fallback only when no directory specified)
        rec = exported_targets.get(norm_lower) or exported_targets.get(norm_no_md)
        if rec is None and "/" not in norm_lower:
            base_lower = Path(norm_lower).name
            base_no_md = base_lower[:-3] if base_lower.endswith(".md") else base_lower
            rec = exported_targets.get(base_lower) or exported_targets.get(base_no_md)

        if rec is not None:
            if output_format == "single-md":
                display = alias_part or rec.title
                return f"[{display}](#{rec.slug})"
            return match.group(0)

        # Target is excluded or unresolved -> strip embeds completely; rewrite links to plain text
        sanitized_count += 1
        if bang == "!":
            return ""
        return alias_part if alias_part else clean_display_name(note_part)

    def _md_link_repl(match: re.Match[str]) -> str:
        nonlocal sanitized_count
        bang = match.group("bang")
        alt = match.group("alt")
        dest_raw = match.group("dest").strip()
        if not dest_raw or dest_raw.startswith(("http://", "https://", "mailto:", "data:", "#")):
            return match.group(0)

        dest_path_part = parse_md_link_dest(dest_raw)
        if not dest_path_part or dest_path_part.startswith(("http://", "https://", "mailto:", "data:", "#")):
            return match.group(0)

        dest_norm = dest_path_part.replace("\\", "/")

        # Reject explicit excluded paths immediately
        if is_explicitly_excluded_target(dest_norm, note_rel=note_rel):
            sanitized_count += 1
            if bang == "!":
                return ""
            return alt or clean_display_name(dest_norm)

        ext = Path(dest_norm).suffix.lower()

        if ext in IMAGE_EXTENSIONS:
            asset_rel = _resolve_asset(dest_norm)
            if asset_rel is not None:
                referenced_assets.add(asset_rel)
                if output_format == "single-md":
                    return f"{bang}[{alt}]({asset_rel.as_posix()})"
                return match.group(0)
            sanitized_count += 1
            return "" if bang == "!" else alt

        if ext == ".md":
            rel_cand = os.path.normpath((note_rel.parent / dest_norm).as_posix()).replace("\\", "/").lower()
            rec = exported_targets.get(rel_cand) or exported_targets.get(dest_norm.lstrip("./").lower())
            if rec is not None:
                if output_format == "single-md":
                    display = alt or rec.title
                    return f"[{display}](#{rec.slug})"
                return match.group(0)
            sanitized_count += 1
            if bang == "!":
                return ""
            return alt or clean_display_name(dest_norm)

        return match.group(0)

    updated = WIKILINK_RE.sub(_wikilink_repl, fragment)
    updated = MD_LINK_RE.sub(_md_link_repl, updated)
    return updated, sanitized_count


def sanitize_body_links(
    body: str,
    note_rel: Path,
    exported_targets: dict[str, NoteRecord],
    allowed_assets: dict[str, Path],
    referenced_assets: set[Path],
    output_format: str,
) -> tuple[str, int]:
    """Sanitize wikilinks and local links outside fenced code blocks and inline backtick spans."""
    tokens = tokenize_markdown_code(body)
    rebuilt: list[str] = []
    total_sanitized = 0
    for is_code, chunk in tokens:
        if is_code:
            rebuilt.append(chunk)
        else:
            cleaned, count = sanitize_links_in_fragment(
                chunk,
                note_rel=note_rel,
                exported_targets=exported_targets,
                allowed_assets=allowed_assets,
                referenced_assets=referenced_assets,
                output_format=output_format,
            )
            rebuilt.append(cleaned)
            total_sanitized += count
    return "".join(rebuilt), total_sanitized


def sanitize_frontmatter_value(
    value: Any,
    note_rel: Path,
    exported_targets: dict[str, NoteRecord],
    allowed_assets: dict[str, Path],
    referenced_assets: set[Path],
) -> tuple[Any, int, bool]:
    """Recursively sanitize wikilinks, Markdown links, and excluded vault paths inside YAML frontmatter."""
    if isinstance(value, str):
        if "[[" in value or "](" in value:
            new_val, count = sanitize_links_in_fragment(
                value,
                note_rel=note_rel,
                exported_targets=exported_targets,
                allowed_assets=allowed_assets,
                referenced_assets=referenced_assets,
                output_format="vault",
            )
            return new_val, count, (new_val != value)

        norm = value.replace("\\", "/").strip()
        if not norm or norm.startswith(("http://", "https://", "mailto:", "data:")):
            return value, 0, False

        # Reject any raw excluded vault path (e.g., Monsters/..., atlas-vtt/..., Campaign/World State.md)
        if is_explicitly_excluded_target(norm, note_rel=note_rel):
            return "", 1, True

        ext = Path(norm).suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            norm_key = norm.lstrip("./").lower()
            if norm_key in allowed_assets:
                referenced_assets.add(allowed_assets[norm_key])
            elif "/" not in norm_key and Path(norm_key).name in allowed_assets:
                referenced_assets.add(allowed_assets[Path(norm_key).name])
        return value, 0, False

    if isinstance(value, list):
        new_list: list[Any] = []
        total = 0
        changed = False
        for item in value:
            ni, c, ch = sanitize_frontmatter_value(
                item, note_rel, exported_targets, allowed_assets, referenced_assets
            )
            total += c
            changed = changed or ch
            new_list.append(ni)
        return new_list, total, changed

    if isinstance(value, dict):
        new_dict: dict[Any, Any] = {}
        total = 0
        changed = False
        for k, v in value.items():
            nv, c, ch = sanitize_frontmatter_value(
                v, note_rel, exported_targets, allowed_assets, referenced_assets
            )
            total += c
            changed = changed or ch
            new_dict[k] = nv
        return new_dict, total, changed

    return value, 0, False


def render_note_vault(
    rec: NoteRecord,
    fm: dict[str, Any],
    fm_changed: bool,
    cleaned_body: str,
) -> str:
    if rec.has_frontmatter:
        if fm_changed:
            yaml_str = yaml.safe_dump(
                fm,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            ).strip()
        else:
            yaml_str = rec.raw_frontmatter
        body_clean = cleaned_body.lstrip("\n")
        return f"---\n{yaml_str}\n---\n\n{body_clean}".rstrip() + "\n"
    return cleaned_body.rstrip() + "\n"


def render_single_md(
    campaign_name: str,
    rendered_entries: list[tuple[NoteRecord, str]],
) -> str:
    lines: list[str] = [
        f"# Player Portal — {campaign_name}",
        "",
        "> Spoiler-filtered player compilation exported by **Prep Goblin**.",
        "",
        "## Table of Contents",
        "",
    ]
    for rec, _body in rendered_entries:
        folder = rec.rel_path.parent.as_posix()
        loc_tag = f" *({folder})*" if folder != "." else ""
        lines.append(f"- [{rec.title}](#{rec.slug}){loc_tag}")
    lines.append("")

    for rec, body in rendered_entries:
        lines.append("---")
        lines.append("")
        lines.append(f"## {rec.title}")
        meta_bits: list[str] = []
        note_type = rec.frontmatter.get("type")
        if note_type:
            meta_bits.append(f"**Type:** {note_type}")
        folder = rec.rel_path.parent.as_posix()
        if folder != ".":
            meta_bits.append(f"**Section:** `{folder}`")
        if meta_bits:
            lines.append(" | ".join(meta_bits))
            lines.append("")

        body_lines = body.strip().split("\n")
        if body_lines and re.match(r"^#\s+", body_lines[0]):
            body_lines = body_lines[1:]
            while body_lines and not body_lines[0].strip():
                body_lines = body_lines[1:]
        lines.append("\n".join(body_lines).strip())
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def audit_markdown_content(
    label: str,
    content: str,
    note_rel: Path | None = None,
    exported_targets: set[str] | None = None,
    exported_assets: set[str] | None = None,
    check_wikilinks: bool = False,
) -> list[str]:
    """Independent security audit of a single rendered Markdown document."""
    violations: list[str] = []
    text = normalize_newlines(content)
    fm, has_fm, raw_yaml, body, yaml_error = parse_frontmatter(text)

    if yaml_error:
        violations.append(f"{label}: malformed YAML frontmatter detected (fail-closed).")

    if has_fm:
        if is_dm_only_frontmatter(fm):
            violations.append(f"{label}: DM-only frontmatter detected (visibility/tags).")
        if is_false_flag(fm.get("publish")):
            violations.append(f"{label}: frontmatter has publish: false.")
        if has_raw_dm_only_frontmatter(raw_yaml):
            violations.append(f"{label}: raw DM-only or publish:false frontmatter pattern detected.")

    # Audit body outside fenced code blocks and inline code spans
    tokens = tokenize_markdown_code(body)
    non_code_text = "".join(chunk for is_code, chunk in tokens if not is_code)

    if "<!--" in non_code_text:
        violations.append(f"{label}: HTML comment marker (`<!--`) leaked outside code blocks.")
    if "%%" in non_code_text:
        violations.append(f"{label}: Obsidian comment marker (`%%`) leaked outside code blocks.")

    # Secret callout audit outside fenced code blocks
    in_fence = False
    fence_char = ""
    fence_len = 0
    for line_no, line in enumerate(body.split("\n"), start=1):
        if not in_fence:
            fm_open = FENCE_OPEN_RE.match(line)
            if fm_open:
                in_fence = True
                fence_char = fm_open.group(1)[0]
                fence_len = len(fm_open.group(1))
                continue
        else:
            close_re = re.compile(rf"^[ \t]*{re.escape(fence_char)}{{{fence_len},}}[ \t]*$")
            if close_re.match(line):
                in_fence = False
                fence_char = ""
                fence_len = 0
            continue

        if is_secret_callout_header(line):
            violations.append(f"{label}:{line_no}: secret callout header leaked: {line.strip()}")

    assets_set = exported_assets or set()

    def _check_links_in_fragment(fragment: str, context: str) -> None:
        # Check [[wikilinks]]
        if check_wikilinks and exported_targets is not None:
            for m in WIKILINK_RE.finditer(fragment):
                inner = m.group("inner")
                pipe_m = PIPE_SPLIT_RE.search(inner)
                target_part = inner[:pipe_m.start()].strip() if pipe_m else inner.strip()
                note_part = target_part.split("#", 1)[0].strip()
                if not note_part:
                    continue
                norm = note_part.replace("\\", "/").strip("/")
                if is_explicitly_excluded_target(norm, note_rel=note_rel):
                    violations.append(f"{label} ({context}): excluded path wikilink [[{inner}]]")
                    continue
                norm_l = norm.lower()
                norm_no_md = norm_l[:-3] if norm_l.endswith(".md") else norm_l
                resolved = (
                    norm_l in exported_targets
                    or norm_no_md in exported_targets
                    or norm_l in assets_set
                )
                if not resolved and "/" not in norm_l:
                    base = Path(norm_l).name
                    base_no_md = base[:-3] if base.endswith(".md") else base
                    resolved = (
                        base in exported_targets
                        or base_no_md in exported_targets
                        or base in assets_set
                    )
                if not resolved:
                    violations.append(f"{label} ({context}): unresolved or excluded wikilink [[{inner}]]")

        # Always check Markdown links [text](dest) for excluded directories/files (and unresolved .md in vault mode)
        for m in MD_LINK_RE.finditer(fragment):
            dest_raw = m.group("dest").strip()
            if not dest_raw or dest_raw.startswith(("http://", "https://", "mailto:", "data:", "#")):
                continue
            dest_path = parse_md_link_dest(dest_raw)
            if not dest_path or dest_path.startswith(("http://", "https://", "mailto:", "data:", "#")):
                continue
            dest_norm = dest_path.replace("\\", "/")
            if is_explicitly_excluded_target(dest_norm, note_rel=note_rel):
                violations.append(f"{label} ({context}): Markdown link points to excluded path ({dest_path})")
                continue
            ext = Path(dest_norm).suffix.lower()
            if check_wikilinks and exported_targets is not None and ext == ".md":
                rel_cand = (
                    os.path.normpath((note_rel.parent / dest_norm).as_posix()).replace("\\", "/").lower()
                    if note_rel is not None
                    else dest_norm.lstrip("./").lower()
                )
                if rel_cand not in exported_targets and dest_norm.lstrip("./").lower() not in exported_targets:
                    violations.append(f"{label} ({context}): unresolved Markdown link ({dest_path})")

    def _walk_fm(val: Any) -> None:
        if isinstance(val, str):
            if "[[" in val or "](" in val:
                _check_links_in_fragment(val, "frontmatter")
            elif is_explicitly_excluded_target(val, note_rel=note_rel):
                violations.append(f"{label} (frontmatter): excluded vault path leaked ({val})")
        elif isinstance(val, list):
            for item in val:
                _walk_fm(item)
        elif isinstance(val, dict):
            for v in val.values():
                _walk_fm(v)

    if has_fm and not yaml_error:
        _walk_fm(fm)

    for is_code, chunk in tokens:
        if is_code:
            continue
        _check_links_in_fragment(chunk, "body")

    return violations


def verify_output_on_disk(out_path: Path, output_format: str) -> list[str]:
    """Independent post-export audit reading directly from disk."""
    violations: list[str] = []
    if output_format == "single-md" and out_path.is_file():
        content = read_text_normalized(out_path)
        violations.extend(
            audit_markdown_content(out_path.name, content, note_rel=Path(out_path.name), check_wikilinks=False)
        )
        return violations

    if not out_path.is_dir():
        return [f"Output directory does not exist for verification: {out_path}"]

    exported_targets: set[str] = set()
    exported_assets: set[str] = set()
    md_files: list[Path] = []

    for root, dirs, files in os.walk(out_path):
        for d in dirs:
            if d.lower() in EXCLUDED_DIRS:
                rel_d = (Path(root) / d).relative_to(out_path).as_posix()
                violations.append(f"Excluded private directory present in output: {rel_d}/")
        for fname in files:
            fpath = Path(root) / fname
            rel = fpath.relative_to(out_path)
            rel_posix = rel.as_posix()
            rel_lower = rel_posix.lower()
            if rel_lower in EXCLUDED_REL_FILES:
                violations.append(f"Excluded DM-only file present in output: {rel_posix}")
            if fname.lower().endswith(".md"):
                md_files.append(fpath)
                exported_targets.add(rel_lower)
                exported_targets.add(rel_lower[:-3])
                exported_targets.add(fpath.name.lower())
                exported_targets.add(fpath.stem.lower())
            else:
                exported_assets.add(rel_lower)
                exported_assets.add(fname.lower())

    check_links = output_format == "vault"
    for md_file in sorted(md_files):
        rel = md_file.relative_to(out_path)
        content = read_text_normalized(md_file)
        violations.extend(
            audit_markdown_content(
                rel.as_posix(),
                content,
                note_rel=rel,
                exported_targets=exported_targets,
                exported_assets=exported_assets,
                check_wikilinks=check_links,
            )
        )
    return violations


def collect_exportable_notes(
    vault_dir: Path,
    publish_only: bool,
    stats: ExportStats,
) -> list[NoteRecord]:
    records: list[NoteRecord] = []
    used_slugs: set[str] = set()

    for root, dirs, files in os.walk(vault_dir):
        dirs[:] = sorted(d for d in dirs if d.lower() not in EXCLUDED_DIRS)
        for fname in sorted(files):
            if not fname.lower().endswith(".md"):
                continue
            src_path = Path(root) / fname
            rel_path = src_path.relative_to(vault_dir)
            rel_posix = rel_path.as_posix()
            stats.scanned_notes += 1

            if has_excluded_dir(rel_path):
                stats.record_exclusion("excluded-dir")
                continue

            if rel_posix.lower() in EXCLUDED_REL_FILES:
                stats.record_exclusion("dm-only-file")
                continue

            text = read_text_normalized(src_path)
            fm, has_fm, raw_yaml, body, yaml_error = parse_frontmatter(text)

            if yaml_error:
                print(
                    f"WARNING: Excluding {rel_posix} (fail-closed): malformed YAML frontmatter.",
                    file=sys.stderr,
                )
                stats.record_exclusion("malformed-yaml")
                continue

            if is_dm_only_frontmatter(fm) or has_raw_dm_only_frontmatter(raw_yaml):
                stats.record_exclusion("visibility:dm-only")
                continue

            if is_false_flag(fm.get("publish")):
                stats.record_exclusion("publish:false")
                continue

            if publish_only and not is_true_flag(fm.get("publish")):
                stats.record_exclusion("missing-publish:true")
                continue

            title = str(fm.get("title") or src_path.stem).strip()
            base_slug = make_slug(title)
            slug = base_slug
            suffix = 2
            while slug in used_slugs:
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            used_slugs.add(slug)

            records.append(
                NoteRecord(
                    src_path=src_path,
                    rel_path=rel_path,
                    rel_posix=rel_posix,
                    frontmatter=fm,
                    has_frontmatter=has_fm,
                    raw_frontmatter=raw_yaml,
                    body=body,
                    title=title,
                    slug=slug,
                )
            )

    records.sort(key=lambda r: r.rel_posix.lower())
    stats.exported_notes = len(records)
    return records


def safe_clean_output_dir(out_dir: Path, vault_dir: Path) -> bool:
    """Safely clear an output directory without risking wiping the vault or filesystem root."""
    resolved_out = out_dir.resolve()
    resolved_vault = vault_dir.resolve()
    if resolved_out == resolved_out.parent:
        print(f"ERROR: Refusing --clean on filesystem root: {resolved_out}", file=sys.stderr)
        return False
    if resolved_out == resolved_vault or resolved_out in resolved_vault.parents:
        print(
            f"ERROR: Refusing --clean because output directory contains or equals vault: {resolved_out}",
            file=sys.stderr,
        )
        return False
    if resolved_out.is_dir():
        for entry in list(resolved_out.iterdir()):
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry)
            else:
                entry.unlink()
    return True


def export_player_view(
    vault_dir: Path,
    out_path: Path | None,
    repo_root: Path,
    publish_only: bool = False,
    output_format: str = "vault",
    verify: bool = False,
    dry_run: bool = False,
    clean: bool = False,
) -> int:
    if not vault_dir.is_dir():
        print(f"ERROR: Vault directory not found: {vault_dir}", file=sys.stderr)
        return 1

    if not dry_run and out_path is None:
        print("ERROR: --out <dir> is required unless --dry-run is specified.", file=sys.stderr)
        return 1

    stats = ExportStats()
    records = collect_exportable_notes(vault_dir, publish_only=publish_only, stats=stats)
    allowed_assets = index_allowed_assets(vault_dir)

    exported_targets: dict[str, NoteRecord] = {}
    exported_target_keys: set[str] = set()
    for rec in records:
        rel_lower = rec.rel_posix.lower()
        keys = [
            rel_lower,
            rel_lower[:-3],
            rec.src_path.name.lower(),
            rec.src_path.stem.lower(),
        ]
        for k in keys:
            exported_targets.setdefault(k, rec)
            exported_target_keys.add(k)

    referenced_assets: set[Path] = set()
    rendered_vault_files: dict[Path, str] = {}
    rendered_single_entries: list[tuple[NoteRecord, str]] = []

    for rec in records:
        cleaned_body, callout_cnt, comment_cnt, unclosed_cnt = strip_spoilers(
            rec.body, note_label=rec.rel_posix
        )
        stats.stripped_callouts += callout_cnt
        stats.stripped_comments += comment_cnt
        stats.unclosed_comment_warnings += unclosed_cnt

        sanitized_body, body_link_cnt = sanitize_body_links(
            cleaned_body,
            note_rel=rec.rel_path,
            exported_targets=exported_targets,
            allowed_assets=allowed_assets,
            referenced_assets=referenced_assets,
            output_format=output_format,
        )
        stats.sanitized_links += body_link_cnt

        new_fm, fm_link_cnt, fm_changed = sanitize_frontmatter_value(
            rec.frontmatter,
            note_rel=rec.rel_path,
            exported_targets=exported_targets,
            allowed_assets=allowed_assets,
            referenced_assets=referenced_assets,
        )
        stats.sanitized_links += fm_link_cnt

        if output_format == "vault":
            rendered_vault_files[rec.rel_path] = render_note_vault(
                rec, new_fm, fm_changed, sanitized_body
            )
        else:
            rendered_single_entries.append((rec, sanitized_body))

    stats.copied_assets = len(referenced_assets)
    campaign_name = load_campaign_name(repo_root)
    single_md_text = (
        render_single_md(campaign_name, rendered_single_entries)
        if output_format == "single-md"
        else ""
    )

    written_target: Path | None = None
    if not dry_run and out_path is not None:
        if output_format == "vault":
            if clean and not safe_clean_output_dir(out_path, vault_dir):
                return 1
            out_path.mkdir(parents=True, exist_ok=True)
            for rel_path, content in rendered_vault_files.items():
                dest = out_path / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8", newline="\n")
            asset_root = out_path
            written_target = out_path
        else:
            if out_path.suffix.lower() == ".md":
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(single_md_text, encoding="utf-8", newline="\n")
                asset_root = out_path.parent
                written_target = out_path
            else:
                if clean and not safe_clean_output_dir(out_path, vault_dir):
                    return 1
                out_path.mkdir(parents=True, exist_ok=True)
                md_file = out_path / "player-view.md"
                md_file.write_text(single_md_text, encoding="utf-8", newline="\n")
                asset_root = out_path
                written_target = out_path

        for asset_rel in sorted(referenced_assets):
            src_asset = vault_dir / asset_rel
            dst_asset = asset_root / asset_rel
            if src_asset.is_file():
                dst_asset.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_asset, dst_asset)

    mode_tag = "[DRY-RUN] " if dry_run else ""
    print(f"{mode_tag}Player View Export ({output_format})")
    print(f"  Vault:             {vault_dir}")
    if out_path is not None:
        print(f"  Output:            {out_path}")
    print(f"  Notes scanned:     {stats.scanned_notes}")
    print(f"  Notes exported:    {stats.exported_notes}")
    print(f"  Notes excluded:    {stats.excluded_notes}")
    if stats.excluded_reasons:
        reasons_str = ", ".join(f"{k}={v}" for k, v in sorted(stats.excluded_reasons.items()))
        print(f"  Exclusion detail:  {reasons_str}")
    print(f"  Callouts stripped: {stats.stripped_callouts}")
    print(f"  Comments stripped: {stats.stripped_comments}")
    if stats.unclosed_comment_warnings:
        print(f"  Unclosed cuts:     {stats.unclosed_comment_warnings}")
    print(f"  Links sanitized:   {stats.sanitized_links}")
    print(f"  Assets copied:     {stats.copied_assets}")

    if dry_run and records:
        print("\nNotes queued for export:")
        for rec in records:
            print(f"  - {rec.rel_posix}")

    if verify:
        print("\nRunning independent security audit (--verify)...")
        if dry_run:
            violations: list[str] = []
            exported_asset_keys = {
                k
                for p in referenced_assets
                for k in (p.as_posix().lower(), p.name.lower())
            }
            if output_format == "vault":
                for rel_path, content in rendered_vault_files.items():
                    violations.extend(
                        audit_markdown_content(
                            rel_path.as_posix(),
                            content,
                            note_rel=rel_path,
                            exported_targets=exported_target_keys,
                            exported_assets=exported_asset_keys,
                            check_wikilinks=True,
                        )
                    )
            else:
                violations.extend(
                    audit_markdown_content(
                        "player-view.md",
                        single_md_text,
                        note_rel=Path("player-view.md"),
                        check_wikilinks=False,
                    )
                )
        else:
            assert written_target is not None
            violations = verify_output_on_disk(written_target, output_format=output_format)

        if violations:
            print("SECURITY AUDIT FAILED — Potential DM secrets or broken links detected:", file=sys.stderr)
            for v in violations:
                print(f"  [LEAK] {v}", file=sys.stderr)
            return 1
        print("SECURITY AUDIT PASSED: 0 DM-only files, 0 secret callouts, 0 HTML/Obsidian comments leaked.")

    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description="Spoiler Firewall & Player Portal Exporter for Obsidian / Quartz / Discord."
    )
    parser.add_argument(
        "--vault",
        type=Path,
        default=None,
        help="Path to the vault directory (auto-detected from campaign.config.json / Vault / template-vault).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory (or .md file for --format single-md). Required unless --dry-run is set.",
    )
    parser.add_argument(
        "--publish-only",
        action="store_true",
        help="Export only notes with `publish: true` in YAML frontmatter.",
    )
    parser.add_argument(
        "--format",
        choices=("vault", "single-md"),
        default="vault",
        help="Output format: `vault` (Quartz-ready folder tree) or `single-md` (single Markdown document).",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clear stale files from the output directory before exporting (recommended for recurring vault exports).",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run an independent post-export security audit; exits with code 1 if any DM secret leaked.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate export and print counts/file list without writing to disk.",
    )
    args = parser.parse_args(argv)

    vault_dir = args.vault.resolve() if args.vault else resolve_default_vault(repo_root)
    out_path = args.out.resolve() if args.out else None

    return export_player_view(
        vault_dir=vault_dir,
        out_path=out_path,
        repo_root=repo_root,
        publish_only=args.publish_only,
        output_format=args.format,
        verify=args.verify,
        dry_run=args.dry_run,
        clean=args.clean,
    )


if __name__ == "__main__":
    raise SystemExit(main())
