#!/usr/bin/env python3
"""Audio / Discord Session Transcript Preprocessor for Prep Goblin.

Cleans raw `.srt`, `.vtt`, and `.txt` session transcripts by stripping
timestamps, cue IDs, inline caption tags, empty/filler noise, and duplicate
lines, then merges consecutive utterances by the same speaker for 40-60%
token savings.

Auto-extracts a Vault Proper-Noun Glossary (Players, NPCs, Locations,
Factions, Quests, Monsters + frontmatter aliases + campaign.config.json
party aliases) and splits the cleaned transcript into overlapping,
word-bounded Markdown chunks prefixed with a DM-as-Reviewer extraction
checklist.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

FM_RE = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)
EMPTY_FM_RE = re.compile(r"\A---[ \t]*\n---[ \t]*(?:\n|\Z)")

SRT_TIME_RE = re.compile(
    r"^\d{1,2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{1,2}:\d{2}:\d{2}[,.]\d{3}.*$"
)
VTT_TIME_RE = re.compile(
    r"^(?:\d{1,2}:)?\d{2}:\d{2}\.\d{3}\s*-->\s*(?:\d{1,2}:)?\d{2}:\d{2}\.\d{3}.*$"
)
VTT_VOICE_OPEN_RE = re.compile(r"^<v(?:\.[^>\s]+)?\s+([^>]+)>(.*)$", re.IGNORECASE)
INLINE_TAG_RE = re.compile(
    r"</?(?:v|c|i|b|u|font|lang|ruby|rt)(?:[^>]*)>|<\d{1,2}:\d{2}(?::\d{2})?\.\d{3}>",
    re.IGNORECASE,
)
SSA_TAG_RE = re.compile(r"\{\\[^}]+\}")

LEADING_TS_RE = re.compile(
    r"^(?:[\[(]\s*(?:\d{1,2}:)?\d{2}:\d{2}(?:[,.]\d{1,3})?\s*[\])]\s*(?:-\s*)?|"
    r"(?:\d{1,2}:)?\d{2}:\d{2}(?:[,.]\d{1,3})?\s*(?:-\s*|\|\s*|\s+))"
)
# Unicode-aware speaker patterns (supports accented letters like Rene, Jose, etc.)
DISCORD_HEADER_RE = re.compile(
    r"^([^\W\d_][\w .'\-()]{0,35}?)\s+[—–-]\s+"
    r"(?:(?:Today|Yesterday)\s+at\s+\d{1,2}:\d{2}(?:\s*[AP]M)?|"
    r"\d{1,4}[/-]\d{1,2}[/-]\d{1,4}(?:,?\s+\d{1,2}:\d{2}(?:\s*[AP]M)?)?|"
    r"\d{1,2}:\d{2}(?:\s*[AP]M)?)$",
    re.IGNORECASE,
)
SPEAKER_COLON_RE = re.compile(
    r"^(?:-\s*)?([^\W\d_][\w .'\-()]{0,30}?):(?:\s+(.*)|\s*)$"
)
SPEAKER_BRACKET_RE = re.compile(
    r"^\[([^\W\d_][\w .'\-()]{0,30}?)\](?:\s+(.*)|\s*)$"
)

NOISE_TAG_RE = re.compile(
    r"[\[(]\s*(?:laughter|laughs?|applause|music|silence|inaudible|crosstalk|"
    r"sighs?|coughs?|clears?\s+throat|background\s+noise|unintelligible|pause|cheering)\s*[\])]",
    re.IGNORECASE,
)
HESITATION_ONLY_RE = re.compile(
    r"^(?:um+|uh+|uhh+|erm+|hmm+|mm+|mhm|mm-hmm|uh-huh|ah+|oh+|♪+)[.?!,…\s]*$",
    re.IGNORECASE,
)

NON_SPEAKER_WORDS = {
    "http",
    "https",
    "note",
    "warning",
    "tip",
    "cue",
    "style",
    "region",
    "summary",
    "recap",
    "context",
    "example",
    "update",
    "result",
    "roll",
    "check",
    "damage",
    "total",
    "question",
    "answer",
    "reminder",
    "step",
    "part",
    "scene",
    "chapter",
    "session",
    "loot",
    "quest",
    "goal",
    "plan",
    "status",
    "location",
    "date",
}

NON_SPEAKER_STARTERS = {
    "i",
    "we",
    "you",
    "they",
    "he",
    "she",
    "it",
    "this",
    "that",
    "these",
    "those",
    "there",
    "here",
    "one",
    "two",
    "three",
    "four",
    "five",
    "some",
    "all",
    "every",
    "no",
    "yes",
    "yeah",
    "yep",
    "nope",
    "well",
    "so",
    "but",
    "and",
    "or",
    "if",
    "when",
    "then",
    "just",
    "wait",
    "okay",
    "ok",
    "also",
    "next",
    "first",
    "second",
    "third",
    "finally",
    "actually",
    "basically",
    "literally",
    "maybe",
    "quick",
    "real",
    "sorry",
    "please",
    "thanks",
}

NAME_CONNECTORS = {"the", "of", "de", "da", "di", "la", "le", "van", "von", "el", "al", "del"}
NUMBERED_SPEAKER_PREFIXES = {"speaker", "player", "user", "dm", "gm", "pc", "host", "guest", "voice"}

GLOSSARY_CATEGORIES: list[tuple[str, str]] = [
    ("Campaign/Players", "Player Characters"),
    ("NPCs", "NPCs"),
    ("Locations", "Locations"),
    ("Campaign/Factions", "Factions"),
    ("Campaign/Quests", "Quests"),
    ("Monsters", "Monsters & Creatures"),
]

DM_REVIEWER_CHECKLIST = """## DM-as-Reviewer Extraction Checklist

When analyzing this transcript chunk, **do NOT edit canonical vault files directly**:
1. **Resolve Proper Nouns:** Cross-check possible Whisper/speech-to-text misspellings against the **Vault Proper-Noun Glossary** above. Flag any unrecognized name for DM verification instead of guessing.
2. **Chronological Events:** Separate **Player-Safe Recap** facts (what the PCs witnessed or learned) from **DM-Only Notes** (behind-the-screen mechanics, missed clues, or hidden motives).
3. **Loot, Gold & Resources:** List coin deltas, magic items, consumables, or key clues gained/spent (candidates for `Campaign/World State.md`).
4. **Quest Progress:** Note quests opened, objectives completed, or status shifts (`open` / `active` / `done` / `failed`) for `Campaign/Quests/*.md`.
5. **Improvised Elements (`Campaign/Improv Log.md`):** Capture newly improvised NPCs, shops, venues, or side-encounters as **staging candidates** — never write directly into canonical `NPCs/` or `Locations/` without DM approval.
6. **Faction Clock Triggers (`living-world`):** Flag elapsed in-game days, disrupted plots, or ignored threats that should advance or shift faction clocks.
7. **Gate Behind DM Sign-Off:** Present all extracted candidates in a concise review sheet for the DM before invoking `session-recap` and `living-world`."""


@dataclass
class Utterance:
    speaker: str | None
    text: str


@dataclass
class GlossaryEntry:
    canonical: str
    aliases: list[str]
    hint: str


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_transcript_text(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return normalize_newlines(path.read_text(encoding=enc))
        except UnicodeDecodeError:
            continue
    return normalize_newlines(path.read_text(encoding="utf-8", errors="replace"))


def parse_frontmatter(text: str) -> dict[str, Any]:
    if EMPTY_FM_RE.match(text):
        return {}
    m = FM_RE.match(text)
    if not m:
        return {}
    try:
        loaded = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def resolve_config_path(
    explicit_config: Path | None,
    explicit_vault: Path | None,
    repo_root: Path,
) -> Path | None:
    if explicit_config is not None:
        return explicit_config.resolve()
    if explicit_vault is not None:
        sibling_cfg = explicit_vault.resolve().parent / "campaign.config.json"
        if sibling_cfg.is_file():
            return sibling_cfg
    default_cfg = repo_root / "campaign.config.json"
    if default_cfg.is_file():
        return default_cfg
    return None


def resolve_default_vault(config_path: Path | None, repo_root: Path) -> Path:
    if config_path is not None and config_path.is_file():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8-sig"))
            vault_dir = cfg.get("vault_dir")
            if vault_dir:
                cand = (config_path.parent / vault_dir).resolve()
                if cand.is_dir():
                    return cand
        except Exception:
            pass
    for candidate_name in ("Vault", "template-vault"):
        cand = repo_root / candidate_name
        if cand.is_dir():
            return cand.resolve()
    return (repo_root / "template-vault").resolve()


def load_party_aliases(config_path: Path | None) -> dict[str, list[str]]:
    """Map lowercased PC note names to short aliases from campaign.config.json."""
    mapping: dict[str, list[str]] = {}
    if config_path is None or not config_path.is_file():
        return mapping
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return mapping
    party = cfg.get("party")
    if isinstance(party, list):
        for entry in party:
            if not isinstance(entry, dict):
                continue
            note = str(entry.get("note") or "").strip()
            short = str(entry.get("name") or "").strip()
            if note and short and short.lower() != note.lower():
                mapping.setdefault(note.lower(), []).append(short)
    return mapping


def extract_aliases_from_fm(fm: dict[str, Any]) -> list[str]:
    aliases: list[str] = []
    for key in ("aliases", "alias"):
        raw = fm.get(key)
        if isinstance(raw, list):
            for item in raw:
                val = str(item).strip()
                if val:
                    aliases.append(val)
        elif isinstance(raw, str) and raw.strip():
            for part in raw.split(","):
                val = part.strip()
                if val:
                    aliases.append(val)
    return aliases


def extract_vault_glossary(
    vault_dir: Path,
    config_path: Path | None,
) -> dict[str, list[GlossaryEntry]]:
    """Scan core vault entity directories and extract canonical names + aliases."""
    party_aliases = load_party_aliases(config_path)
    glossary: dict[str, list[GlossaryEntry]] = {}

    for rel_sub, label in GLOSSARY_CATEGORIES:
        folder = vault_dir / Path(rel_sub)
        entries: list[GlossaryEntry] = []
        if folder.is_dir():
            for md in sorted(folder.rglob("*.md"), key=lambda p: p.stem.lower()):
                if any(part.startswith(".") for part in md.relative_to(folder).parts):
                    continue
                raw = normalize_newlines(md.read_text(encoding="utf-8-sig"))
                fm = parse_frontmatter(raw)
                canonical = md.stem.strip()
                title = str(fm.get("title") or "").strip()
                raw_aliases = extract_aliases_from_fm(fm)
                if title and title.lower() != canonical.lower():
                    raw_aliases.insert(0, title)
                if rel_sub == "Campaign/Players":
                    raw_aliases.extend(party_aliases.get(canonical.lower(), []))

                seen = {canonical.lower()}
                clean_aliases: list[str] = []
                for a in raw_aliases:
                    al = a.lower()
                    if al not in seen:
                        seen.add(al)
                        clean_aliases.append(a)

                hint = str(fm.get("class") or fm.get("type") or "").strip()
                if hint.lower() in {"player character", "creature", "quest"}:
                    hint = ""
                entries.append(GlossaryEntry(canonical=canonical, aliases=clean_aliases, hint=hint))
        if entries:
            glossary[label] = entries

    return glossary


def render_glossary_markdown(glossary: dict[str, list[GlossaryEntry]]) -> str:
    lines: list[str] = ["## Vault Proper-Noun Glossary"]
    if not glossary:
        lines.append("")
        lines.append("*(No entity notes found in the target vault.)*")
        return "\n".join(lines)

    for label, entries in glossary.items():
        formatted: list[str] = []
        for e in entries:
            item = f"`{e.canonical}`"
            extras: list[str] = []
            if e.aliases:
                extras.append("aliases: " + ", ".join(e.aliases))
            if e.hint:
                extras.append(e.hint)
            if extras:
                item += f" ({'; '.join(extras)})"
            formatted.append(item)
        lines.append(f"- **{label}:** " + " | ".join(formatted))

    return "\n".join(lines)


def clean_formatting_tags(text: str) -> str:
    text = SSA_TAG_RE.sub("", text)
    text = INLINE_TAG_RE.sub("", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def clean_noise_and_ws(text: str) -> str:
    text = NOISE_TAG_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_plausible_speaker(name: str, strict_colon: bool = False) -> bool:
    """Validate whether `name` looks like a speaker label rather than ordinary prose."""
    cleaned = name.strip()
    if not cleaned or len(cleaned) > 32:
        return False
    if not any(ch.isalpha() for ch in cleaned):
        return False

    lower = cleaned.lower()
    if lower in NON_SPEAKER_WORDS:
        return False

    words = cleaned.split()
    if not words or len(words) > 3:
        return False

    first_bare = words[0].strip("().'\"-").lower()
    if first_bare in NON_SPEAKER_WORDS:
        return False

    if strict_colon:
        if first_bare in NON_SPEAKER_STARTERS:
            return False

        # Allow numbered generic labels like "Speaker 1", "Player 2", "DM 1"
        if len(words) == 2 and first_bare in NUMBERED_SPEAKER_PREFIXES and words[1].strip("()").isdigit():
            return True

        # Reject standalone digits inside multi-word prose (e.g., "I rolled a 19")
        if any(w.strip("()").isdigit() for w in words):
            return False

        # Single-token handle/name: allow capitalized name, acronym, or handle with _ / digits (e.g., dm, kael_99)
        if len(words) == 1:
            token = words[0].strip("()'\".-")
            if not token:
                return False
            if token[0].isupper() or token.lower() in {"dm", "gm", "pc"} or "_" in token or any(c.isdigit() for c in token):
                return True
            return False

        # Multi-word speaker label (2-3 words): require proper-noun capitalization on main tokens
        for idx, w in enumerate(words):
            core = w.strip("()'\".,-")
            if not core:
                continue
            if idx > 0 and core.lower() in NAME_CONNECTORS:
                continue
            if not core[0].isupper():
                return False

    return True


def split_speaker_prefix(line: str) -> tuple[str | None, str]:
    stripped = LEADING_TS_RE.sub("", line).strip()
    m_colon = SPEAKER_COLON_RE.match(stripped)
    if m_colon:
        cand = m_colon.group(1).strip()
        rest = (m_colon.group(2) or "").strip()
        if is_plausible_speaker(cand, strict_colon=True):
            return cand, rest
    m_br = SPEAKER_BRACKET_RE.match(stripped)
    if m_br:
        cand = m_br.group(1).strip()
        rest = (m_br.group(2) or "").strip()
        if is_plausible_speaker(cand, strict_colon=False):
            return cand, rest
    return None, stripped


def parse_srt(text: str) -> list[Utterance]:
    utterances: list[Utterance] = []
    blocks = re.split(r"\n{2,}", text.strip())
    for block in blocks:
        raw_lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not raw_lines:
            continue
        cue_lines: list[str] = []
        for idx, ln in enumerate(raw_lines):
            if idx == 0 and ln.isdigit():
                continue
            if SRT_TIME_RE.match(ln):
                continue
            cue_lines.append(ln)
        if not cue_lines:
            continue

        block_speaker: str | None = None
        for cl in cue_lines:
            tag_cleaned = clean_formatting_tags(cl)
            if not tag_cleaned:
                continue
            spk, raw_utt = split_speaker_prefix(tag_cleaned)
            if spk is not None:
                block_speaker = spk
                utt = clean_noise_and_ws(raw_utt)
                if utt:
                    utterances.append(Utterance(speaker=spk, text=utt))
            else:
                utt = clean_noise_and_ws(raw_utt)
                if utt:
                    utterances.append(Utterance(speaker=block_speaker, text=utt))
    return utterances


def parse_vtt(text: str) -> list[Utterance]:
    utterances: list[Utterance] = []
    blocks = re.split(r"\n{2,}", text.strip())
    for block in blocks:
        raw_lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
        if not raw_lines:
            continue
        first_upper = raw_lines[0].upper()
        if first_upper.startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
            continue

        ts_idx = next((i for i, ln in enumerate(raw_lines) if VTT_TIME_RE.match(ln)), None)
        cue_lines = raw_lines[ts_idx + 1:] if ts_idx is not None else raw_lines
        if not cue_lines:
            continue

        block_speaker: str | None = None
        for cl in cue_lines:
            voice_parts = [
                p.strip()
                for p in re.split(r"(?=<v(?:\.[^>\s]+)?\s+[^>]+>)", cl, flags=re.IGNORECASE)
                if p.strip()
            ]
            for part in voice_parts:
                v_m = VTT_VOICE_OPEN_RE.match(part)
                if v_m:
                    spk = v_m.group(1).strip()
                    rest = clean_noise_and_ws(clean_formatting_tags(v_m.group(2)))
                    block_speaker = spk if is_plausible_speaker(spk, strict_colon=False) else None
                    if rest:
                        utterances.append(Utterance(speaker=block_speaker, text=rest))
                    continue

                tag_cleaned = clean_formatting_tags(part)
                if not tag_cleaned:
                    continue
                spk, raw_utt = split_speaker_prefix(tag_cleaned)
                if spk is not None:
                    block_speaker = spk
                    utt = clean_noise_and_ws(raw_utt)
                    if utt:
                        utterances.append(Utterance(speaker=spk, text=utt))
                else:
                    utt = clean_noise_and_ws(raw_utt)
                    if utt:
                        utterances.append(Utterance(speaker=block_speaker, text=utt))
    return utterances


def parse_txt(text: str) -> list[Utterance]:
    head = text.lstrip()
    if head.upper().startswith("WEBVTT"):
        return parse_vtt(text)
    if re.search(r"^\d{1,2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{1,2}:\d{2}:\d{2},\d{3}", text, re.MULTILINE):
        return parse_srt(text)

    utterances: list[Utterance] = []
    active_speaker: str | None = None

    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if SRT_TIME_RE.match(line) or VTT_TIME_RE.match(line):
            continue

        disc_m = DISCORD_HEADER_RE.match(line)
        if disc_m and is_plausible_speaker(disc_m.group(1), strict_colon=False):
            active_speaker = disc_m.group(1).strip()
            continue

        tag_cleaned = clean_formatting_tags(line)
        if not tag_cleaned:
            continue

        spk, raw_utt = split_speaker_prefix(tag_cleaned)
        if spk is not None:
            if not raw_utt:
                # Standalone `Speaker:` header (Otter.ai / Zoom / Teams format)
                active_speaker = spk
                continue
            utt = clean_noise_and_ws(raw_utt)
            if utt:
                active_speaker = None
                utterances.append(Utterance(speaker=spk, text=utt))
            continue

        utt = clean_noise_and_ws(raw_utt)
        if utt:
            utterances.append(Utterance(speaker=active_speaker, text=utt))

    return utterances


def parse_transcript(path: Path, raw_text: str) -> tuple[str, list[Utterance]]:
    ext = path.suffix.lower()
    if ext == ".srt":
        return "srt", parse_srt(raw_text)
    if ext == ".vtt":
        return "vtt", parse_vtt(raw_text)
    return "txt", parse_txt(raw_text)


def norm_dedupe_key(text: str) -> str:
    return re.sub(r"[^\w]+", " ", text.lower()).strip()


def deduplicate_and_merge(utterances: list[Utterance]) -> list[Utterance]:
    """Filter noise/fillers, remove rolling/exact duplicates, merge consecutive same-speaker turns."""
    filtered: list[Utterance] = []
    for u in utterances:
        t = re.sub(r"\s+", " ", u.text).strip()
        if not t:
            continue
        if HESITATION_ONLY_RE.match(t):
            continue
        # Unicode-aware alphanumeric content check
        if not any(ch.isalnum() for ch in t):
            continue

        cur_key = norm_dedupe_key(t)
        if not cur_key:
            continue

        if filtered:
            prev = filtered[-1]
            prev_key = norm_dedupe_key(prev.text)
            same_speaker = (prev.speaker or "").lower() == (u.speaker or "").lower()
            if cur_key == prev_key:
                continue
            if same_speaker and cur_key.startswith(prev_key + " "):
                prev.text = t
                continue
            if same_speaker and (prev_key.endswith(" " + cur_key) or prev_key == cur_key):
                continue

        filtered.append(Utterance(speaker=u.speaker, text=t))

    merged: list[Utterance] = []
    for u in filtered:
        if merged:
            prev = merged[-1]
            if prev.speaker is not None and u.speaker is not None and prev.speaker.lower() == u.speaker.lower():
                prev.text = f"{prev.text} {u.text}"
                continue
            if prev.speaker is None and u.speaker is None:
                if len(prev.text.split()) < 80:
                    prev.text = f"{prev.text} {u.text}"
                    continue
        merged.append(Utterance(speaker=u.speaker, text=u.text))

    return merged


def format_utterance(u: Utterance) -> str:
    if u.speaker:
        return f"**{u.speaker}:** {u.text}"
    return u.text


def split_oversized_utterance(u: Utterance, max_words: int) -> list[str]:
    formatted = format_utterance(u)
    words = formatted.split()
    if len(words) <= max_words:
        return [formatted]

    prefix = f"**{u.speaker} (cont.):** " if u.speaker else ""
    first_prefix = f"**{u.speaker}:** " if u.speaker else ""
    body_words = u.text.split()
    pieces: list[str] = []
    idx = 0
    first = True
    while idx < len(body_words):
        p = first_prefix if first else prefix
        p_words = len(p.split())
        take = max(1, max_words - p_words)
        seg = " ".join(body_words[idx:idx + take])
        pieces.append(f"{p}{seg}")
        idx += take
        first = False
    return pieces


def build_overlap_lines(prev_turns: list[str], overlap_words: int) -> list[str]:
    if overlap_words <= 0 or not prev_turns:
        return []
    selected: list[str] = []
    total = 0
    for turn in reversed(prev_turns):
        w = len(turn.split())
        if not selected and w > overlap_words * 1.5:
            tail = " ".join(turn.split()[-overlap_words:])
            selected.append(f"...{tail}")
            break
        selected.append(turn)
        total += w
        if total >= overlap_words:
            break
    selected.reverse()
    return selected


def chunk_turns(
    utterances: list[Utterance],
    chunk_words: int,
    overlap_words: int,
) -> list[tuple[list[str], list[str]]]:
    """Return list of (overlap_turns, main_turns) for each chunk."""
    turns: list[str] = []
    for u in utterances:
        turns.extend(split_oversized_utterance(u, chunk_words))

    if not turns:
        return []

    chunks: list[tuple[list[str], list[str]]] = []
    idx = 0
    prev_main: list[str] = []

    while idx < len(turns):
        overlap = build_overlap_lines(prev_main, overlap_words) if chunks else []
        overlap_w = sum(len(t.split()) for t in overlap)
        budget = max(1, chunk_words - overlap_w)

        main: list[str] = []
        used = 0
        while idx < len(turns):
            w = len(turns[idx].split())
            if main and used + w > budget:
                break
            main.append(turns[idx])
            used += w
            idx += 1

        chunks.append((overlap, main))
        prev_main = main

    return chunks


def render_chunk_markdown(
    chunk_num: int,
    total_chunks: int,
    source_name: str,
    glossary_md: str,
    overlap_turns: list[str],
    main_turns: list[str],
) -> str:
    main_words = sum(len(t.split()) for t in main_turns)
    overlap_words = sum(len(t.split()) for t in overlap_turns)
    lines: list[str] = [
        f"# Session Transcript — Chunk {chunk_num:02d} / {total_chunks:02d}",
        "",
        f"- **Source:** `{source_name}` | **New Words:** `{main_words}`"
        + (f" | **Overlap Context Words:** `{overlap_words}`" if overlap_words else ""),
        "",
        glossary_md,
        "",
        DM_REVIEWER_CHECKLIST,
        "",
        "---",
        "",
        "## Cleaned Transcript",
        "",
    ]

    if overlap_turns:
        lines.append("*[Overlap from previous chunk — continuity context only; do not double-count events]*")
        lines.append("")
        lines.append("\n\n".join(overlap_turns))
        lines.append("")
        lines.append("*[End of overlap — new transcript content begins below]*")
        lines.append("")

    lines.append("\n\n".join(main_turns))
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(
        description="Preprocess audio/Discord session transcripts (.srt, .vtt, .txt) into AI-ready chunks with a Vault Proper-Noun Glossary."
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        type=Path,
        default=None,
        help="Path to raw transcript file (.srt, .vtt, or .txt). Optional when --glossary-only is set.",
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
        help="Optional path to campaign.config.json for resolving vault_dir and party short-name aliases.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Directory to write overlapping chunk_XX.md files. Prints summary if omitted.",
    )
    parser.add_argument(
        "--chunk-words",
        type=int,
        default=2500,
        help="Target word budget per transcript chunk (default: 2500).",
    )
    parser.add_argument(
        "--overlap-words",
        type=int,
        default=150,
        help="Word overlap carried between consecutive chunks (default: 150).",
    )
    parser.add_argument(
        "--glossary-only",
        action="store_true",
        help="Extract and print only the Vault Proper-Noun Glossary, then exit.",
    )
    args = parser.parse_args(argv)

    config_path = resolve_config_path(args.config, args.vault, repo_root)
    vault_dir = args.vault.resolve() if args.vault else resolve_default_vault(config_path, repo_root)
    if not vault_dir.is_dir():
        print(f"ERROR: Vault directory not found: {vault_dir}", file=sys.stderr)
        return 1

    glossary = extract_vault_glossary(vault_dir, config_path)
    glossary_md = render_glossary_markdown(glossary)

    if args.glossary_only:
        print(glossary_md)
        return 0

    if args.input_file is None:
        parser.error("input_file is required unless --glossary-only is specified.")

    input_path = args.input_file.resolve()
    if not input_path.is_file():
        print(f"ERROR: Transcript file not found: {input_path}", file=sys.stderr)
        return 1

    if args.chunk_words <= 0:
        print("ERROR: --chunk-words must be a positive integer.", file=sys.stderr)
        return 1
    if args.overlap_words < 0 or args.overlap_words >= args.chunk_words:
        print("ERROR: --overlap-words must be >= 0 and strictly less than --chunk-words.", file=sys.stderr)
        return 1

    raw_text = read_transcript_text(input_path)
    raw_bytes = len(raw_text.encode("utf-8"))
    raw_words = len(raw_text.split())

    detected_fmt, parsed = parse_transcript(input_path, raw_text)
    merged = deduplicate_and_merge(parsed)

    cleaned_plain = "\n\n".join(format_utterance(u) for u in merged)
    cleaned_bytes = len(cleaned_plain.encode("utf-8"))
    cleaned_words = len(cleaned_plain.split())

    byte_saved_pct = ((raw_bytes - cleaned_bytes) / raw_bytes * 100.0) if raw_bytes > 0 else 0.0
    raw_est_tokens = max(1, round(raw_bytes / 4)) if raw_bytes else 0
    clean_est_tokens = max(1, round(cleaned_bytes / 4)) if cleaned_bytes else 0

    chunks = chunk_turns(merged, chunk_words=args.chunk_words, overlap_words=args.overlap_words)
    total_chunks = len(chunks)
    pad_width = max(2, len(str(max(1, total_chunks))))

    written_files: list[Path] = []
    if args.out_dir is not None:
        out_dir = args.out_dir.resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        for idx, (overlap_turns, main_turns) in enumerate(chunks, start=1):
            chunk_md = render_chunk_markdown(
                chunk_num=idx,
                total_chunks=total_chunks,
                source_name=input_path.name,
                glossary_md=glossary_md,
                overlap_turns=overlap_turns,
                main_turns=main_turns,
            )
            chunk_path = out_dir / f"chunk_{idx:0{pad_width}d}.md"
            chunk_path.write_text(chunk_md, encoding="utf-8", newline="\n")
            written_files.append(chunk_path)

    glossary_count = sum(len(v) for v in glossary.values())
    print(f"Transcript Preprocessor ({detected_fmt.upper()})")
    print(f"  Source file:      {input_path}")
    print(f"  Vault:            {vault_dir} ({glossary_count} glossary entities)")
    print(f"  Raw size:         {raw_bytes} bytes | {raw_words} words (~{raw_est_tokens} tokens)")
    print(f"  Cleaned size:     {cleaned_bytes} bytes | {cleaned_words} words (~{clean_est_tokens} tokens)")
    print(f"  Size reduction:   {byte_saved_pct:.1f}% ({len(parsed)} raw cues -> {len(merged)} merged turns)")
    print(f"  Chunks planned:   {total_chunks} (target {args.chunk_words} words, overlap {args.overlap_words} words)")

    if written_files:
        print(f"\nWrote {len(written_files)} chunk(s) to {args.out_dir.resolve()}:")
        for f in written_files:
            print(f"  - {f.name} ({f.stat().st_size} bytes)")
    else:
        print("\n" + glossary_md)
        if chunks:
            print("\nChunk Breakdown (pass --out-dir <dir> to write chunk Markdown files):")
            for idx, (ov, main) in enumerate(chunks, start=1):
                mw = sum(len(t.split()) for t in main)
                ow = sum(len(t.split()) for t in ov)
                print(f"  - chunk_{idx:0{pad_width}d}.md: {mw} new words ({ow} overlap words, {len(main)} turns)")
        else:
            print("\nWARNING: No usable speech lines remained after cleaning.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
