#!/usr/bin/env python3
"""Anti-Canon-Drift Session Context Compiler for Prep Goblin.

Compiles a dense, structured, AI-ready Markdown snapshot from a live
Obsidian + Atlas VTT 0.16.0 campaign vault to prevent canon drift across
AI co-pilot sessions.

Compiled sections:
1. Campaign metadata & Party Passives table (campaign.config.json + Campaign/Players/*.md)
2. Campaign/World State.md (coordinates, resources, faction clocks)
3. Active / Open Quests (Campaign/Quests/*.md with status in open, active — incl. DM secrets)
4. Active Factions (Campaign/Factions/*.md)
5. Recent Sessions (latest N rows of Sessions/Campaign Log.md + latest Session *.md excerpt)
6. Pending Improv Log entries (non-placeholder review/recurring/active rows)
7. 1-Hop Location Context (wikilinked locations from World State's Party Location line)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

FM_RE = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)
EMPTY_FM_RE = re.compile(r"\A---[ \t]*\n---[ \t]*(?:\n|\Z)")
FENCE_OPEN_RE = re.compile(r"^[ \t]*(`{3,}|~{3,})")
HEADING_RE = re.compile(r"^(#{1,6})([ \t]+.*)$")
PARTY_LOCATION_RE = re.compile(r"party\s+location[*_`]*\s*:", re.IGNORECASE)
WIKILINK_RE = re.compile(r"\[\[([^\[\]\n]+)\]\]")
PIPE_SPLIT_RE = re.compile(r"\\?\|")
TABLE_SEP_RE = re.compile(r"^\|\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)+\|?$")
TRUNC_MARKER = "\n\n[truncated to fit budget]"

ACTIVE_QUEST_STATUSES = {"open", "active"}
INACTIVE_FACTION_STATUSES = {"archived", "inactive", "destroyed", "defeated", "done", "closed"}
CLOSED_IMPROV_STATUSES = {"archived", "promoted", "discarded", "deleted", "done"}


@dataclass
class Section:
    key: str
    heading: str
    content: str
    priority: int  # 1 = highest priority (trimmed last), 7 = lowest (trimmed first)


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_text_normalized(path: Path) -> str:
    return normalize_newlines(path.read_text(encoding="utf-8-sig"))


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    m_empty = EMPTY_FM_RE.match(text)
    if m_empty:
        return {}, text[m_empty.end():]
    m = FM_RE.match(text)
    if not m:
        return {}, text
    try:
        loaded = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        loaded = {}
    if not isinstance(loaded, dict):
        loaded = {}
    return loaded, text[m.end():]


def load_config(config_path: Path | None, repo_root: Path) -> tuple[dict[str, Any], Path | None]:
    cand = config_path.resolve() if config_path else (repo_root / "campaign.config.json")
    if cand.is_file():
        try:
            data = json.loads(cand.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                return data, cand
        except Exception as exc:
            print(f"WARNING: Could not parse config {cand}: {exc}", file=sys.stderr)
    return {}, None


def resolve_vault(
    explicit_vault: Path | None,
    cfg: dict[str, Any],
    cfg_path: Path | None,
    repo_root: Path,
) -> Path:
    if explicit_vault is not None:
        return explicit_vault.resolve()
    vault_dir = cfg.get("vault_dir")
    if isinstance(vault_dir, str) and vault_dir.strip():
        base = cfg_path.parent if cfg_path else repo_root
        cand = (base / vault_dir).resolve()
        if cand.is_dir():
            return cand
    for candidate_name in ("Vault", "template-vault"):
        cand = repo_root / candidate_name
        if cand.is_dir():
            return cand.resolve()
    return (repo_root / "template-vault").resolve()


def strip_leading_h1(body: str) -> str:
    lines = body.strip().split("\n")
    if lines and re.match(r"^#\s+", lines[0]):
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines = lines[1:]
    return "\n".join(lines).strip()


def demote_headings(text: str, levels: int) -> str:
    """Demote Markdown ATX headings by `levels` (capped at H6), preserving hierarchy and skipping fenced code."""
    if levels <= 0 or not text:
        return text
    out: list[str] = []
    in_fence = False
    fence_char = ""
    fence_len = 0

    for line in text.split("\n"):
        if not in_fence:
            fm = FENCE_OPEN_RE.match(line)
            if fm:
                in_fence = True
                fence_char = fm.group(1)[0]
                fence_len = len(fm.group(1))
                out.append(line)
                continue
        else:
            out.append(line)
            close_re = re.compile(rf"^[ \t]*{re.escape(fence_char)}{{{fence_len},}}[ \t]*$")
            if close_re.match(line):
                in_fence = False
                fence_char = ""
                fence_len = 0
            continue

        hm = HEADING_RE.match(line)
        if hm:
            new_level = min(6, len(hm.group(1)) + levels)
            out.append(f"{'#' * new_level}{hm.group(2)}")
        else:
            out.append(line)

    return "\n".join(out)


def strip_template_callout(body: str, pattern: re.Pattern[str]) -> str:
    """Remove a matching instructional blockquote callout from body."""
    lines = body.split("\n")
    out: list[str] = []
    skipping = False
    for line in lines:
        if skipping:
            if line.lstrip().startswith(">"):
                continue
            skipping = False
        if line.lstrip().startswith(">") and pattern.search(line):
            skipping = True
            continue
        out.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def extract_wikilink_targets(line: str) -> list[str]:
    targets: list[str] = []
    for raw in WIKILINK_RE.findall(line):
        pipe_m = PIPE_SPLIT_RE.search(raw)
        target_part = raw[:pipe_m.start()].strip() if pipe_m else raw.strip()
        note_part = target_part.split("#", 1)[0].strip()
        if note_part:
            targets.append(note_part)
    return targets


def format_list_value(val: Any) -> str:
    if isinstance(val, list):
        return ", ".join(str(x).strip() for x in val if str(x).strip())
    if val is None:
        return ""
    return str(val).strip()


def build_campaign_and_party_section(vault_dir: Path, cfg: dict[str, Any]) -> Section:
    campaign_name = str(cfg.get("campaign_name") or vault_dir.name).strip()
    atlas_collection = str(cfg.get("atlas_collection") or "Campaign").strip()
    party_level = cfg.get("party_level")

    # Collect party data from config first
    pc_map: dict[str, dict[str, Any]] = {}
    pc_order: list[str] = []

    raw_party = cfg.get("party")
    if isinstance(raw_party, list):
        for entry in raw_party:
            if not isinstance(entry, dict):
                continue
            note_name = str(entry.get("note") or entry.get("name") or "").strip()
            short_name = str(entry.get("name") or note_name).strip()
            if not note_name:
                continue
            key = note_name.lower()
            passives = entry.get("passives") if isinstance(entry.get("passives"), dict) else {}
            pc_map[key] = {
                "name": short_name,
                "note": note_name,
                "role": str(entry.get("role") or "").strip(),
                "level": party_level,
                "hp": entry.get("hp"),
                "torch": bool(entry.get("torch_in_dark", False)),
                "perc": passives.get("perception"),
                "inv": passives.get("investigation"),
                "ins": passives.get("insight"),
                "goal": "",
            }
            pc_order.append(key)

    # Merge / augment from Campaign/Players/*.md
    players_dir = vault_dir / "Campaign" / "Players"
    if players_dir.is_dir():
        for md in sorted(players_dir.glob("*.md"), key=lambda p: p.name.lower()):
            fm, body = parse_frontmatter(read_text_normalized(md))
            title = str(fm.get("title") or md.stem).strip()
            key = title.lower()
            stem_key = md.stem.lower()
            match_key = key if key in pc_map else (stem_key if stem_key in pc_map else None)
            if match_key is None:
                # Try matching by first token (e.g., "Mira" in "Mira the Cleric")
                for existing_k, existing_v in pc_map.items():
                    if existing_v["name"].lower() == title.split()[0].lower():
                        match_key = existing_k
                        break

            # Extract optional Goal and Max HP from body
            goal_m = re.search(r"\*\*Goal:\*\*\s*(.+)", body)
            goal_text = goal_m.group(1).strip() if goal_m else ""
            hp_m = re.search(r"\*\*Max HP:\*\*\s*`?(\d+)`?", body)
            body_hp = int(hp_m.group(1)) if hp_m else None

            if match_key is None:
                match_key = key
                pc_map[match_key] = {
                    "name": title,
                    "note": md.stem,
                    "role": str(fm.get("class") or fm.get("role") or "").strip(),
                    "level": fm.get("level", party_level),
                    "hp": fm.get("hp", body_hp),
                    "torch": False,
                    "perc": fm.get("passive_perception"),
                    "inv": fm.get("passive_investigation"),
                    "ins": fm.get("passive_insight"),
                    "goal": goal_text,
                }
                pc_order.append(match_key)
            else:
                rec = pc_map[match_key]
                rec["note"] = md.stem
                if fm.get("class"):
                    rec["role"] = str(fm["class"]).strip()
                if fm.get("level") is not None:
                    rec["level"] = fm["level"]
                if rec.get("hp") is None and body_hp is not None:
                    rec["hp"] = body_hp
                if fm.get("passive_perception") is not None:
                    rec["perc"] = fm["passive_perception"]
                if fm.get("passive_investigation") is not None:
                    rec["inv"] = fm["passive_investigation"]
                if fm.get("passive_insight") is not None:
                    rec["ins"] = fm["passive_insight"]
                if goal_text:
                    rec["goal"] = goal_text

    lines: list[str] = [
        f"- **Campaign:** {campaign_name} | **Vault:** `{vault_dir.name}` | **Atlas Collection:** `{atlas_collection}`"
        + (f" | **Party Level:** `{party_level}`" if party_level is not None else "")
    ]

    if pc_order:
        lines.extend([
            "",
            "| PC | Class / Role | Lv | Max HP | Pass. Perc | Pass. Inv | Pass. Ins | Notes |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |",
        ])
        max_perc: int | None = None
        max_inv: int | None = None
        max_ins: int | None = None

        for key in pc_order:
            pc = pc_map[key]
            note_ref = f"[[{pc['note']}|{pc['name']}]]" if pc["note"] != pc["name"] else f"[[{pc['note']}]]"
            note_ref_table = note_ref.replace("|", "\\|")
            role = pc["role"] or "—"
            lv = str(pc["level"]) if pc["level"] is not None else "—"
            hp = str(pc["hp"]) if pc["hp"] is not None else "—"
            perc = pc["perc"]
            inv = pc["inv"]
            ins = pc["ins"]
            if isinstance(perc, int):
                max_perc = perc if max_perc is None else max(max_perc, perc)
            if isinstance(inv, int):
                max_inv = inv if max_inv is None else max(max_inv, inv)
            if isinstance(ins, int):
                max_ins = ins if max_ins is None else max(max_ins, ins)
            notes_bits: list[str] = []
            if pc["torch"]:
                notes_bits.append("Torchbearer")
            if pc["goal"]:
                notes_bits.append(pc["goal"])
            notes_str = "; ".join(notes_bits).replace("|", "/") if notes_bits else "—"
            lines.append(
                f"| {note_ref_table} | {role} | {lv} | {hp} | "
                f"{perc if perc is not None else '—'} | "
                f"{inv if inv is not None else '—'} | "
                f"{ins if ins is not None else '—'} | {notes_str} |"
            )

        thresholds: list[str] = []
        if max_perc is not None:
            thresholds.append(f"Perception **DC {max_perc + 1}+**")
        if max_inv is not None:
            thresholds.append(f"Investigation **DC {max_inv + 1}+**")
        if max_ins is not None:
            thresholds.append(f"Insight **DC {max_ins + 1}+**")
        if thresholds:
            lines.append("")
            lines.append(f"- **Active Roll Thresholds (above highest passive):** {', '.join(thresholds)}")
    else:
        lines.append("- *(No player characters found in campaign.config.json or Campaign/Players/.)*")

    return Section(
        key="campaign_party",
        heading="## 1. Campaign Metadata & Party Passives",
        content="\n".join(lines).strip(),
        priority=1,
    )


def build_world_state_section(vault_dir: Path) -> tuple[Section, str]:
    ws_path = vault_dir / "Campaign" / "World State.md"
    if not ws_path.is_file():
        return (
            Section(
                key="world_state",
                heading="## 2. World State",
                content="*(Campaign/World State.md not found.)*",
                priority=2,
            ),
            "",
        )

    raw_text = read_text_normalized(ws_path)
    _fm, body = parse_frontmatter(raw_text)
    cleaned = strip_leading_h1(body)
    cleaned = strip_template_callout(
        cleaned,
        re.compile(r"Fill this out before Session 1", re.IGNORECASE),
    )
    # Demote headings inside World State by 1 level (preserving hierarchy, skipping fenced code)
    cleaned = demote_headings(cleaned, 1)
    return (
        Section(
            key="world_state",
            heading="## 2. World State",
            content=cleaned.strip(),
            priority=2,
        ),
        raw_text,
    )


def build_active_quests_section(vault_dir: Path) -> Section:
    quests_dir = vault_dir / "Campaign" / "Quests"
    if not quests_dir.is_dir():
        return Section(
            key="quests",
            heading="## 3. Active & Open Quests",
            content="*(Campaign/Quests/ directory not found.)*",
            priority=4,
        )

    quest_blocks: list[str] = []
    for md in sorted(quests_dir.rglob("*.md"), key=lambda p: p.as_posix().lower()):
        fm, body = parse_frontmatter(read_text_normalized(md))
        status = str(fm.get("status") or "").strip().lower()
        if status not in ACTIVE_QUEST_STATUSES:
            continue

        title = str(fm.get("title") or md.stem).strip()
        kind = str(fm.get("kind") or "quest").strip()
        meta_bits: list[str] = [f"kind: `{kind}`", f"status: `{status}`"]
        if fm.get("experience") is not None:
            meta_bits.append(f"XP: `{fm['experience']}`")
        loc_str = format_list_value(fm.get("location"))
        if loc_str:
            meta_bits.append(f"location: {loc_str}")
        rewards_str = format_list_value(fm.get("rewards"))
        if rewards_str:
            meta_bits.append(f"rewards: {rewards_str}")

        cleaned = strip_leading_h1(body)
        cleaned = strip_template_callout(
            cleaned,
            re.compile(r"Atlas VTT.*Native Quest Integration", re.IGNORECASE),
        )
        cleaned = demote_headings(cleaned, 2)

        block = [
            f"### [[{md.stem}|{title}]]" if title != md.stem else f"### [[{md.stem}]]",
            f"- {' | '.join(meta_bits)}",
        ]
        if cleaned:
            block.append("")
            block.append(cleaned)
        quest_blocks.append("\n".join(block).strip())

    content = (
        "\n\n".join(quest_blocks)
        if quest_blocks
        else "*(No active or open quests found in Campaign/Quests/.)*"
    )
    return Section(
        key="quests",
        heading="## 3. Active & Open Quests (incl. DM Secrets)",
        content=content,
        priority=4,
    )


def build_active_factions_section(vault_dir: Path) -> Section:
    factions_dir = vault_dir / "Campaign" / "Factions"
    if not factions_dir.is_dir():
        return Section(
            key="factions",
            heading="## 4. Active Factions",
            content="*(No faction notes in Campaign/Factions/ yet.)*",
            priority=5,
        )

    faction_blocks: list[str] = []
    for md in sorted(factions_dir.rglob("*.md"), key=lambda p: p.as_posix().lower()):
        fm, body = parse_frontmatter(read_text_normalized(md))
        status = str(fm.get("status") or "active").strip().lower()
        if status in INACTIVE_FACTION_STATUSES:
            continue

        title = str(fm.get("title") or md.stem).strip()
        meta_bits: list[str] = [f"status: `{status}`"]
        for key in ("type", "alignment", "clock", "leader", "influence"):
            val = format_list_value(fm.get(key))
            if val:
                meta_bits.append(f"{key}: {val}")

        cleaned = strip_leading_h1(body)
        cleaned = demote_headings(cleaned, 2)
        block = [
            f"### [[{md.stem}]] ({' | '.join(meta_bits)})",
        ]
        if cleaned:
            block.append(cleaned)
        faction_blocks.append("\n".join(block).strip())

    content = (
        "\n\n".join(faction_blocks)
        if faction_blocks
        else "*(No faction notes in Campaign/Factions/ yet.)*"
    )
    return Section(
        key="factions",
        heading="## 4. Active Factions",
        content=content,
        priority=5,
    )


def session_sort_key(path: Path) -> tuple[int, str]:
    m = re.search(r"(\d+)", path.stem)
    return (int(m.group(1)) if m else -1, path.stem.lower())


def build_recent_sessions_section(vault_dir: Path, recent_sessions: int) -> Section:
    sessions_dir = vault_dir / "Sessions"
    parts: list[str] = []

    log_path = sessions_dir / "Campaign Log.md"
    if log_path.is_file():
        _fm, body = parse_frontmatter(read_text_normalized(log_path))
        lines = body.split("\n")
        header_line: str | None = None
        sep_line: str | None = None
        data_rows: list[str] = []
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if TABLE_SEP_RE.match(stripped) and idx > 0 and lines[idx - 1].strip().startswith("|"):
                header_line = lines[idx - 1].strip()
                sep_line = stripped
                for row_line in lines[idx + 1:]:
                    r = row_line.strip()
                    if not r.startswith("|"):
                        break
                    data_rows.append(r)
                break
        if header_line and sep_line:
            kept_rows = data_rows[-recent_sessions:] if recent_sessions > 0 else []
            parts.append(f"### Campaign Log (Latest {len(kept_rows)} Row(s))")
            parts.append(header_line)
            parts.append(sep_line)
            parts.extend(kept_rows)

    # Latest Sessions/Session *.md condensed excerpt
    if sessions_dir.is_dir():
        session_files = [
            p
            for p in sessions_dir.glob("*.md")
            if re.match(r"^session\b", p.stem, re.IGNORECASE)
        ]
        if session_files:
            latest = sorted(session_files, key=session_sort_key)[-1]
            fm, body = parse_frontmatter(read_text_normalized(latest))
            title = str(fm.get("title") or latest.stem).strip()
            in_game = fm.get("in_game_date")
            real_date = fm.get("real_date")
            meta = []
            if in_game:
                meta.append(f"In-Game: `{in_game}`")
            if real_date:
                meta.append(f"Real Date: `{real_date}`")
            cleaned = strip_leading_h1(body)
            cleaned = demote_headings(cleaned, 2)
            # Keep condensed excerpt capped around 2500 chars before overall byte budget
            if len(cleaned) > 2500:
                cleaned = cleaned[:2500].rsplit("\n", 1)[0].rstrip() + "\n\n[session excerpt condensed]"
            header = f"### Latest Session Recap: [[{latest.stem}]]"
            if meta:
                header += f" ({' | '.join(meta)})"
            elif title != latest.stem:
                header += f" — {title}"
            if parts:
                parts.append("")
            parts.append(header)
            if cleaned:
                parts.append(cleaned)

    content = "\n".join(parts).strip() if parts else "*(No session logs found in Sessions/.)*"
    return Section(
        key="sessions",
        heading="## 5. Recent Sessions",
        content=content,
        priority=7,
    )


def parse_markdown_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    # Split on unescaped pipes
    cells = re.split(r"(?<!\\)\|", stripped)
    return [c.strip() for c in cells]


def is_placeholder_cell(cell: str) -> bool:
    clean = cell.strip(" `*_-—–")
    return clean == "" or clean.lower() in {"none", "n/a", "tbd"}


def build_improv_log_section(vault_dir: Path) -> Section:
    improv_path = vault_dir / "Campaign" / "Improv Log.md"
    if not improv_path.is_file():
        return Section(
            key="improv_log",
            heading="## 6. Pending Improv Log Entries",
            content="*(Campaign/Improv Log.md not found.)*",
            priority=6,
        )

    _fm, body = parse_frontmatter(read_text_normalized(improv_path))
    lines = body.split("\n")

    current_heading = "Entries"
    collected_blocks: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        h_m = re.match(r"^##+\s+(.+)$", line)
        if h_m:
            current_heading = h_m.group(1).strip()
            i += 1
            continue

        if (
            TABLE_SEP_RE.match(line)
            and i > 0
            and lines[i - 1].strip().startswith("|")
        ):
            header_raw = lines[i - 1].strip()
            header_cells = [c.lower() for c in parse_markdown_table_row(header_raw)]
            status_idx = next(
                (idx for idx, col in enumerate(header_cells) if "status" in col),
                len(header_cells) - 1,
            )
            sep_raw = line
            kept_rows: list[str] = []
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith("|"):
                row_raw = lines[j].strip()
                cells = parse_markdown_table_row(row_raw)
                status_val = (
                    cells[status_idx].strip(" `*_").lower()
                    if 0 <= status_idx < len(cells)
                    else ""
                )
                non_status_cells = [
                    c for idx, c in enumerate(cells) if idx != status_idx
                ]
                all_placeholder = all(is_placeholder_cell(c) for c in non_status_cells)
                if not all_placeholder and status_val not in CLOSED_IMPROV_STATUSES:
                    kept_rows.append(row_raw)
                j += 1

            if kept_rows:
                collected_blocks.append(
                    "\n".join([f"### {current_heading}", header_raw, sep_raw, *kept_rows])
                )
            i = j
            continue
        i += 1

    content = (
        "\n\n".join(collected_blocks)
        if collected_blocks
        else "*(No pending or non-placeholder entries in Campaign/Improv Log.md.)*"
    )
    return Section(
        key="improv_log",
        heading="## 6. Pending Improv Log Entries",
        content=content,
        priority=6,
    )


def build_location_context_section(vault_dir: Path, world_state_text: str) -> Section:
    locations_dir = vault_dir / "Locations"
    if not world_state_text:
        return Section(
            key="location_context",
            heading="## 7. Current Location Context (1-Hop)",
            content="*(No Party Location available — World State.md missing.)*",
            priority=3,
        )

    loc_targets: list[str] = []
    for line in world_state_text.split("\n"):
        if PARTY_LOCATION_RE.search(line):
            loc_targets.extend(extract_wikilink_targets(line))

    if not loc_targets:
        return Section(
            key="location_context",
            heading="## 7. Current Location Context (1-Hop)",
            content="*(No wikilinked location found on the `Party Location:` line in World State.md.)*",
            priority=3,
        )

    # Index Locations/*.md
    loc_index: dict[str, Path] = {}
    if locations_dir.is_dir():
        for md in sorted(locations_dir.rglob("*.md"), key=lambda p: p.as_posix().lower()):
            rel_from_vault = md.relative_to(vault_dir).as_posix().lower()
            loc_index[md.stem.lower()] = md
            loc_index[md.name.lower()] = md
            loc_index[rel_from_vault] = md
            loc_index[rel_from_vault[:-3]] = md
            fm, _ = parse_frontmatter(read_text_normalized(md))
            title = str(fm.get("title") or "").strip().lower()
            if title:
                loc_index.setdefault(title, md)

    seen_paths: set[Path] = set()
    loc_blocks: list[str] = []
    missing_targets: list[str] = []

    for raw_target in loc_targets:
        norm = raw_target.replace("\\", "/").strip("/").lower()
        norm_no_md = norm[:-3] if norm.endswith(".md") else norm
        base = Path(norm).name
        base_no_md = base[:-3] if base.endswith(".md") else base
        match_path = (
            loc_index.get(norm)
            or loc_index.get(norm_no_md)
            or loc_index.get(base)
            or loc_index.get(base_no_md)
        )
        if match_path is None:
            missing_targets.append(raw_target)
            continue
        if match_path in seen_paths:
            continue
        seen_paths.add(match_path)

        fm, body = parse_frontmatter(read_text_normalized(match_path))
        title = str(fm.get("title") or match_path.stem).strip()
        loc_type = str(fm.get("type") or "").strip()
        atlas_scene = str(fm.get("atlas_scene") or "").strip()
        atlas_dash = str(fm.get("atlas_dashboard") or "").strip()

        cleaned = strip_leading_h1(body)
        # Remove duplicate quick-link tip callout if we already have atlas_scene/atlas_dashboard
        if atlas_scene or atlas_dash:
            cleaned = strip_template_callout(
                cleaned,
                re.compile(r"Atlas VTT Quick Link", re.IGNORECASE),
            )
        # Strip mermaid blocks to keep AI context dense
        cleaned = re.sub(r"```mermaid.*?```", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        cleaned = demote_headings(cleaned, 2)

        meta_bits: list[str] = []
        if loc_type:
            meta_bits.append(f"**Type:** {loc_type}")
        if atlas_scene:
            meta_bits.append(f"**Atlas Scene:** `{atlas_scene}`")
        if atlas_dash:
            meta_bits.append(f"**DM Dashboard:** {atlas_dash}")

        block_lines = [f"### [[{match_path.stem}]]" + (f" ({title})" if title != match_path.stem else "")]
        if meta_bits:
            block_lines.append("- " + " | ".join(meta_bits))
        if cleaned:
            block_lines.append("")
            block_lines.append(cleaned)
        loc_blocks.append("\n".join(block_lines).strip())

    if missing_targets:
        loc_blocks.append(
            f"*(Unresolved location link(s) not found in `Locations/`: {', '.join(missing_targets)})*"
        )

    content = "\n\n".join(loc_blocks).strip()
    return Section(
        key="location_context",
        heading="## 7. Current Location Context (1-Hop)",
        content=content,
        priority=3,
    )


def utf8_len(text: str) -> int:
    return len(text.encode("utf-8"))


def truncate_utf8_clean(text: str, max_bytes: int, marker: str = TRUNC_MARKER) -> str:
    if max_bytes <= 0:
        return ""
    if utf8_len(text) <= max_bytes:
        return text

    marker_bytes = utf8_len(marker)
    if max_bytes <= marker_bytes:
        raw = marker.strip().encode("utf-8")[:max_bytes]
        return raw.decode("utf-8", errors="ignore")

    budget = max_bytes - marker_bytes
    kept_lines: list[str] = []
    used = 0
    for line in text.split("\n"):
        piece = ("\n" + line) if kept_lines else line
        piece_b = utf8_len(piece)
        if used + piece_b <= budget:
            kept_lines.append(line)
            used += piece_b
        else:
            break

    if kept_lines:
        return "\n".join(kept_lines).rstrip() + marker

    # Fallback: single first line longer than budget -> slice UTF-8 cleanly
    raw = text.encode("utf-8")[:budget]
    return raw.decode("utf-8", errors="ignore").rstrip() + marker


def render_pack(header: str, sections: list[Section]) -> str:
    blocks: list[str] = [header.strip()]
    for sec in sections:
        blocks.append(f"{sec.heading}\n\n{sec.content}".strip())
    return "\n\n---\n\n".join(blocks).rstrip() + "\n"


def enforce_byte_budget(header: str, sections: list[Section], max_bytes: int) -> tuple[str, bool]:
    """Enforce --max-bytes by trimming lower-priority sections cleanly."""
    rendered = render_pack(header, sections)
    if utf8_len(rendered) <= max_bytes:
        return rendered, False

    working = [Section(s.key, s.heading, s.content, s.priority) for s in sections]
    # Trim sections in order of lowest priority (largest number) to highest priority (1)
    indices_by_trim_order = sorted(
        range(len(working)),
        key=lambda idx: (-working[idx].priority, -idx),
    )

    for idx in indices_by_trim_order:
        current = render_pack(header, working)
        overflow = utf8_len(current) - max_bytes
        if overflow <= 0:
            break

        sec = working[idx]
        sec_bytes = utf8_len(sec.content)
        min_marker_bytes = utf8_len("[truncated to fit budget]")
        if sec_bytes <= min_marker_bytes:
            continue

        target_sec_bytes = max(min_marker_bytes, sec_bytes - overflow)
        if target_sec_bytes <= min_marker_bytes + 8:
            sec.content = "[truncated to fit budget]"
        else:
            sec.content = truncate_utf8_clean(sec.content, target_sec_bytes)

    final_text = render_pack(header, working)
    if utf8_len(final_text) > max_bytes:
        final_text = truncate_utf8_clean(final_text, max_bytes)
        if not final_text.endswith("\n") and utf8_len(final_text) < max_bytes:
            final_text += "\n"

    return final_text, True


def compile_context_pack(
    vault_dir: Path,
    cfg: dict[str, Any],
    max_bytes: int = 12000,
    recent_sessions: int = 3,
) -> tuple[str, bool]:
    campaign_name = str(cfg.get("campaign_name") or vault_dir.name).strip()
    header = (
        f"# Session Context Pack — {campaign_name}\n\n"
        "> Compiled automatically by `scripts/build_context_pack.py` from live vault canon. "
        "Treat this snapshot as the single source of truth; follow DM-as-Reviewer before introducing new lore."
    )

    sec_party = build_campaign_and_party_section(vault_dir, cfg)
    sec_world, world_raw = build_world_state_section(vault_dir)
    sec_quests = build_active_quests_section(vault_dir)
    sec_factions = build_active_factions_section(vault_dir)
    sec_sessions = build_recent_sessions_section(vault_dir, recent_sessions=recent_sessions)
    sec_improv = build_improv_log_section(vault_dir)
    sec_location = build_location_context_section(vault_dir, world_raw)

    sections = [
        sec_party,
        sec_world,
        sec_quests,
        sec_factions,
        sec_sessions,
        sec_improv,
        sec_location,
    ]
    return enforce_byte_budget(header, sections, max_bytes=max_bytes)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description="Compile an anti-canon-drift AI session context pack from an Obsidian vault."
    )
    parser.add_argument(
        "--vault",
        type=Path,
        default=None,
        help="Path to the vault directory (auto-detected from config / Vault / template-vault).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to campaign.config.json (defaults to repo root campaign.config.json).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional output Markdown file path. Prints compiled pack to stdout if omitted.",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=12000,
        help="Maximum UTF-8 byte budget for the compiled context pack (default: 12000).",
    )
    parser.add_argument(
        "--recent-sessions",
        type=int,
        default=3,
        help="Number of recent Campaign Log rows to include (default: 3).",
    )
    args = parser.parse_args(argv)

    if args.max_bytes < 100:
        print("ERROR: --max-bytes must be at least 100.", file=sys.stderr)
        return 1
    if args.recent_sessions < 0:
        print("ERROR: --recent-sessions cannot be negative.", file=sys.stderr)
        return 1

    cfg, cfg_path = load_config(args.config, repo_root)
    vault_dir = resolve_vault(args.vault, cfg, cfg_path, repo_root)
    if not vault_dir.is_dir():
        print(f"ERROR: Vault directory not found: {vault_dir}", file=sys.stderr)
        return 1

    pack_text, was_truncated = compile_context_pack(
        vault_dir=vault_dir,
        cfg=cfg,
        max_bytes=args.max_bytes,
        recent_sessions=args.recent_sessions,
    )
    byte_count = utf8_len(pack_text)
    approx_tokens = max(1, round(byte_count / 4))
    trunc_note = " (trimmed to fit budget)" if was_truncated else ""

    if args.out is not None:
        out_path = args.out.resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(pack_text, encoding="utf-8", newline="\n")
        print(
            f"Wrote context pack: {out_path} ({byte_count} bytes, ~{approx_tokens} tokens, "
            f"budget {args.max_bytes} bytes){trunc_note}"
        )
    else:
        sys.stdout.write(pack_text)
        print(
            f"[build_context_pack] {byte_count} bytes (~{approx_tokens} tokens, "
            f"budget {args.max_bytes} bytes){trunc_note}",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
