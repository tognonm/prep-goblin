#!/usr/bin/env python3
"""5e XP Budget Calculator & Atlas VTT 0.16.0 Encounter JSON Builder (Demiurge Core).

Calculates combat encounter difficulty under D&D 5e 2024 (Low / Moderate / High,
no size multiplier) or 2014 (Easy / Medium / Hard / Deadly, with standard
encounter size multiplier), parses creature statblocks from <Vault>/Monsters/*.md
and token records from <Vault>/atlas-vtt/collections/<Col>/tokens/*.json, and
outputs:
  1. <Vault>/Encounters/<Encounter Name>.md
  2. <Vault>/atlas-vtt/collections/<Col>/encounters/<encounter_id>.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

DEFAULT_PARTY: list[dict[str, Any]] = [
    {
        "name": "Mira",
        "note": "Mira the Cleric",
        "role": "Cleric",
        "assetId": "token-demo-mira",
        "imagePath": "atlas-vtt/assets/token_mira.webp",
        "hp": 24,
        "torch_in_dark": True,
        "passives": {"perception": 13, "investigation": 10, "insight": 15},
    },
    {
        "name": "Kael",
        "note": "Kael the Rogue",
        "role": "Rogue",
        "assetId": "token-demo-kael",
        "imagePath": "atlas-vtt/assets/token_kael.webp",
        "hp": 21,
        "torch_in_dark": False,
        "passives": {"perception": 11, "investigation": 14, "insight": 10},
    },
    {
        "name": "Bram",
        "note": "Bram the Fighter",
        "role": "Fighter",
        "assetId": "token-demo-bram",
        "imagePath": "atlas-vtt/assets/token_bram.webp",
        "hp": 28,
        "torch_in_dark": False,
        "passives": {"perception": 10, "investigation": 9, "insight": 12},
    },
]

DEFAULT_FALLBACK_TOKENS: dict[str, str] = {
    "default": "atlas-vtt/assets/token_generic_fighter.webp",
    "scout": "atlas-vtt/assets/token_generic_scout.webp",
    "arcane": "atlas-vtt/assets/token_generic_arcane.webp",
}

MONSTER_ALIASES: dict[str, str] = {
    "bandit": "road raider",
    "bandits": "road raider",
    "raider": "road raider",
    "raiders": "road raider",
    "brigand": "road raider",
    "thug": "tough",
    "tough": "tough",
    "guard": "guard",
    "guards": "guard",
    "veteran": "veteran",
    "spy": "spy",
    "mage": "mage",
    "cultist": "cultist",
    "skeleton": "skeleton sentry",
    "skeletons": "skeleton sentry",
    "sentry": "skeleton sentry",
    "zombie": "zombie",
    "ghoul": "ghoul",
    "shadow": "shadow",
    "specter": "specter",
    "goblin": "goblin",
    "orc": "orc",
    "wolf": "wolf",
    "wolves": "wolf",
}

GENERIC_SCOUT_KEYWORDS = (
    "wolf", "wolves", "bear", "spider", "beast", "boar",
    "goblin", "hunter", "scout", "spy", "rogue", "archer", "ranger",
)
GENERIC_ARCANE_KEYWORDS = (
    "occult", "sorcer", "necrom", "mage", "wizard", "warlock",
    "cult", "demon", "devil", "ghost", "shadow", "specter", "undead", "skeleton",
)

# Standard 5e SRD Challenge Rating -> XP table (CR 0 through CR 30)
CR_TO_XP: dict[str, int] = {
    "0": 10,
    "1/8": 25,
    "1/4": 50,
    "1/2": 100,
    "1": 200,
    "2": 450,
    "3": 700,
    "4": 1100,
    "5": 1800,
    "6": 2300,
    "7": 2900,
    "8": 3900,
    "9": 5000,
    "10": 5900,
    "11": 7200,
    "12": 8400,
    "13": 10000,
    "14": 11500,
    "15": 13000,
    "16": 15000,
    "17": 18000,
    "18": 20000,
    "19": 22000,
    "20": 25000,
    "21": 33000,
    "22": 41000,
    "23": 50000,
    "24": 62000,
    "25": 75000,
    "26": 90000,
    "27": 105000,
    "28": 120000,
    "29": 135000,
    "30": 155000,
}

# 2024 ruleset: XP budget per character (Low, Moderate, High) — no multiplier
XP_BUDGET_2024: dict[int, tuple[int, int, int]] = {
    1: (50, 75, 100),
    2: (100, 150, 200),
    3: (150, 225, 400),
    4: (250, 375, 500),
    5: (500, 750, 1100),
    6: (600, 1000, 1400),
    7: (750, 1300, 1700),
    8: (1000, 1700, 2100),
    9: (1300, 2000, 2600),
    10: (1600, 2300, 3100),
    11: (1900, 2900, 4100),
    12: (2200, 3700, 4700),
    13: (2600, 4200, 5400),
    14: (2900, 4900, 6200),
    15: (3300, 5400, 7800),
    16: (3800, 6100, 9800),
    17: (4500, 7200, 11700),
    18: (5000, 8700, 14200),
    19: (5500, 10700, 17200),
    20: (6400, 13200, 22000),
}

# 2014 ruleset: XP thresholds per character (Easy, Medium, Hard, Deadly)
XP_THRESHOLDS_2014: dict[int, tuple[int, int, int, int]] = {
    1: (25, 50, 75, 100),
    2: (50, 100, 150, 200),
    3: (75, 150, 225, 400),
    4: (125, 250, 375, 500),
    5: (250, 500, 750, 1100),
    6: (300, 600, 900, 1400),
    7: (350, 750, 1100, 1700),
    8: (450, 900, 1400, 2100),
    9: (550, 1100, 1600, 2400),
    10: (600, 1200, 1900, 2800),
    11: (800, 1600, 2400, 3600),
    12: (1000, 2000, 3000, 4500),
    13: (1100, 2200, 3400, 5100),
    14: (1250, 2500, 3800, 5700),
    15: (1400, 2800, 4300, 6400),
    16: (1600, 3200, 4800, 7200),
    17: (2000, 3900, 5900, 8800),
    18: (2100, 4200, 6300, 9500),
    19: (2400, 4900, 7300, 10900),
    20: (2800, 5700, 8500, 12700),
}

MULTIPLIER_LADDER_2014: tuple[float, ...] = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0)


# ---------------------------------------------------------------------------
# Configuration & Catalog Loading (matching quick_battlemap.py conventions)
# ---------------------------------------------------------------------------

def load_runtime_config(config_path: pathlib.Path | None = None) -> dict[str, Any]:
    cfg_file = (config_path or (REPO_ROOT / "campaign.config.json")).resolve()
    raw: dict[str, Any] = {}
    if cfg_file.is_file():
        try:
            raw = json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception:
            raw = {}

    vault_dir_val = raw.get("vault_dir")
    if isinstance(vault_dir_val, str) and vault_dir_val.strip():
        v_raw = pathlib.Path(vault_dir_val)
        vault_path = v_raw.resolve() if v_raw.is_absolute() else (cfg_file.parent / v_raw).resolve()
    elif (cfg_file.parent / "Vault").is_dir():
        vault_path = (cfg_file.parent / "Vault").resolve()
    elif (REPO_ROOT / "Vault").is_dir():
        vault_path = (REPO_ROOT / "Vault").resolve()
    else:
        vault_path = (REPO_ROOT / "template-vault").resolve()

    collection = str(raw.get("atlas_collection") or "Campaign")
    party = raw.get("party") if isinstance(raw.get("party"), list) and raw.get("party") else DEFAULT_PARTY
    fallbacks = dict(DEFAULT_FALLBACK_TOKENS)
    if isinstance(raw.get("fallback_tokens"), dict):
        fallbacks.update({str(k): str(v) for k, v in raw["fallback_tokens"].items()})

    return {
        "vault_dir": vault_path,
        "collection": collection,
        "party_level": int(raw.get("party_level") or 3),
        "party": party,
        "fallback_tokens": fallbacks,
    }


def normalize_cr(raw_cr: str) -> str:
    if not raw_cr:
        return ""
    cleaned = raw_cr.strip().upper()
    if cleaned.startswith("CR"):
        cleaned = cleaned[2:].strip()
    cleaned = cleaned.split()[0] if cleaned else ""
    decimal_map = {"0.125": "1/8", "0.25": "1/4", "0.5": "1/2", "0.50": "1/2"}
    if cleaned in decimal_map:
        return decimal_map[cleaned]
    if cleaned in CR_TO_XP:
        return cleaned
    try:
        num = float(cleaned)
        if abs(num - round(num)) < 1e-6:
            as_int = str(int(round(num)))
            if as_int in CR_TO_XP:
                return as_int
    except ValueError:
        pass
    return cleaned


def cr_to_xp(cr_str: str) -> int | None:
    norm = normalize_cr(cr_str)
    if not norm:
        return None
    return CR_TO_XP.get(norm)


def load_token_catalog(col_dir: pathlib.Path) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    by_statblock: dict[str, dict[str, str]] = {}
    by_name: dict[str, dict[str, str]] = {}
    tokens_dir = col_dir / "tokens"
    if not tokens_dir.exists():
        return by_statblock, by_name
    for jf in sorted(tokens_dir.glob("*.json")):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue
        rec = data.get("atlasRecord") or {}
        img = rec.get("imagePath")
        if not img:
            continue
        info = {"imagePath": img, "assetId": rec.get("id", ""), "name": rec.get("name", "")}
        sb = (rec.get("statblockPath") or "").strip().lower()
        if sb:
            by_statblock[sb] = info
        nm = (rec.get("name") or "").strip().lower()
        if nm:
            by_name[nm] = info
    return by_statblock, by_name


def pick_fallback_art(name_key: str, fallbacks: dict[str, str]) -> str:
    if any(k in name_key for k in GENERIC_SCOUT_KEYWORDS):
        return fallbacks.get("scout", fallbacks["default"])
    if any(k in name_key for k in GENERIC_ARCANE_KEYWORDS):
        return fallbacks.get("arcane", fallbacks["default"])
    return fallbacks["default"]


def load_monster_catalog(
    vault_dir: pathlib.Path,
    collection: str,
    fallbacks: dict[str, str],
) -> dict[str, dict[str, Any]]:
    col_dir = vault_dir / "atlas-vtt" / "collections" / collection
    monsters_dir = vault_dir / "Monsters"
    by_statblock, by_token_name = load_token_catalog(col_dir)
    catalog: dict[str, dict[str, Any]] = {}
    if not monsters_dir.exists():
        return catalog

    for md in sorted(monsters_dir.glob("*.md")):
        txt = md.read_text(encoding="utf-8", errors="ignore")
        m_block = re.search(r"```statblock\s*(.*?)```", txt, flags=re.DOTALL)
        block = m_block.group(1) if m_block else txt

        def extract(key: str) -> str:
            m = re.search(rf"^{key}:\s*(.+)$", block, flags=re.MULTILINE)
            if not m:
                return ""
            return m.group(1).strip().strip('"').strip("'")

        disp_name = extract("name") or md.stem
        hp_m = re.search(r"\d+", extract("hp"))
        hp = int(hp_m.group(0)) if hp_m else 11
        ac_m = re.search(r"\d+", extract("ac"))
        ac = int(ac_m.group(0)) if ac_m else 12
        cr_norm = normalize_cr(extract("cr"))
        size_raw = extract("size").lower()
        tok_size = 2 if "large" in size_raw else (3 if "huge" in size_raw else (4 if "gargantuan" in size_raw else 1))

        sb_rel = f"Monsters/{md.name}"
        stem_key = md.stem.lower()
        name_key = disp_name.lower()

        token_info = (
            by_statblock.get(sb_rel.lower())
            or by_token_name.get(name_key)
            or by_token_name.get(stem_key)
        )
        image_path = token_info["imagePath"] if token_info else pick_fallback_art(name_key, fallbacks)
        asset_id = token_info["assetId"] if token_info else ""

        entry = {
            "name": disp_name,
            "stem": md.stem,
            "hp": hp,
            "ac": ac,
            "cr": cr_norm,
            "size": tok_size,
            "statblockPath": sb_rel,
            "imagePath": image_path,
            "assetId": asset_id,
        }
        catalog[stem_key] = entry
        catalog[name_key] = entry
    return catalog


def resolve_enemy(
    raw_name: str,
    hp_override: int | None,
    cr_override: str | None,
    catalog: dict[str, dict[str, Any]],
    fallbacks: dict[str, str],
) -> dict[str, Any]:
    cleaned = raw_name.strip()
    key = cleaned.lower()
    alias_key = MONSTER_ALIASES.get(key, key)
    found = catalog.get(key) or catalog.get(alias_key)
    if found:
        out = dict(found)
        if hp_override is not None:
            out["hp"] = hp_override
        if cr_override:
            out["cr"] = normalize_cr(cr_override)
        return out

    return {
        "name": cleaned,
        "stem": cleaned,
        "hp": hp_override if hp_override is not None else 11,
        "ac": 12,
        "cr": normalize_cr(cr_override) if cr_override else "",
        "size": 1,
        "statblockPath": "",
        "imagePath": pick_fallback_art(key, fallbacks),
        "assetId": "",
    }


def parse_enemy_groups(
    spec: str,
    catalog: dict[str, dict[str, Any]],
    fallbacks: dict[str, str],
) -> list[dict[str, Any]]:
    """Parse an enemy spec string into grouped encounter entries.

    Supported formats per comma/semicolon chunk:
      - 'Road Raider:2'
      - 'Wolf:3@11' (explicit HP override)
      - 'Wolf:3@11#1/4' (explicit HP and CR override for ad-hoc creatures)
    """
    if not spec or not spec.strip():
        return []

    groups: list[dict[str, Any]] = []
    for chunk in re.split(r"[,;]+", spec):
        item = chunk.strip()
        if not item:
            continue

        count = 1
        hp_override: int | None = None
        cr_override: str | None = None

        m_cr = re.search(r"#([0-9]+(?:/[0-9]+|\.[0-9]+)?)", item)
        if m_cr:
            cr_override = m_cr.group(1)
            item = item[: m_cr.start()] + item[m_cr.end() :]

        m_hp = re.search(r"@(\d+)", item)
        if m_hp:
            hp_override = int(m_hp.group(1))
            item = item[: m_hp.start()] + item[m_hp.end() :]

        if ":" in item:
            name_part, cnt_part = item.rsplit(":", 1)
            name_part = name_part.strip()
            try:
                count = max(1, int(cnt_part.strip()))
            except ValueError:
                name_part = item.strip()
                count = 1
        else:
            name_part = item.strip()

        if not name_part:
            continue

        proto = resolve_enemy(name_part, hp_override, cr_override, catalog, fallbacks)
        xp_each = cr_to_xp(proto["cr"])
        groups.append(
            {
                **proto,
                "count": count,
                "xp_each": xp_each,
                "xp_total": (xp_each * count) if xp_each is not None else 0,
            }
        )
    return groups


# ---------------------------------------------------------------------------
# 5e XP Budget & Difficulty Math (2024 & 2014 Rulesets)
# ---------------------------------------------------------------------------

def multiplier_2014(enemy_count: int, party_size: int) -> float:
    if enemy_count <= 1:
        idx = 1
    elif enemy_count == 2:
        idx = 2
    elif enemy_count <= 6:
        idx = 3
    elif enemy_count <= 10:
        idx = 4
    elif enemy_count <= 14:
        idx = 5
    else:
        idx = 6

    if party_size < 3:
        idx = min(len(MULTIPLIER_LADDER_2014) - 1, idx + 1)
    elif party_size >= 6:
        idx = max(0, idx - 1)
    return MULTIPLIER_LADDER_2014[idx]


def evaluate_encounter(
    groups: list[dict[str, Any]],
    party_level: int,
    party_size: int,
    ruleset: str,
) -> dict[str, Any]:
    total_enemies = sum(g["count"] for g in groups)
    known_cr_enemies = sum(g["count"] for g in groups if g["xp_each"] is not None)
    raw_xp = sum(g["xp_total"] for g in groups)
    unknown_cr_names = [g["name"] for g in groups if g["xp_each"] is None]

    if ruleset == "2024":
        low_pc, mod_pc, high_pc = XP_BUDGET_2024[party_level]
        budgets = {
            "Low": low_pc * party_size,
            "Moderate": mod_pc * party_size,
            "High": high_pc * party_size,
        }
        mult = 1.0
        adjusted_xp = raw_xp
        if adjusted_xp <= budgets["Low"]:
            base_difficulty = "Low"
        elif adjusted_xp <= budgets["Moderate"]:
            base_difficulty = "Moderate"
        elif adjusted_xp <= budgets["High"]:
            base_difficulty = "High"
        else:
            base_difficulty = "Over High"
    else:
        easy_pc, med_pc, hard_pc, dead_pc = XP_THRESHOLDS_2014[party_level]
        budgets = {
            "Easy": easy_pc * party_size,
            "Medium": med_pc * party_size,
            "Hard": hard_pc * party_size,
            "Deadly": dead_pc * party_size,
        }
        mult = multiplier_2014(total_enemies, party_size)
        adjusted_xp = int(round(raw_xp * mult))
        if adjusted_xp >= budgets["Deadly"]:
            base_difficulty = "Deadly"
        elif adjusted_xp >= budgets["Hard"]:
            base_difficulty = "Hard"
        elif adjusted_xp >= budgets["Medium"]:
            base_difficulty = "Medium"
        elif adjusted_xp >= budgets["Easy"]:
            base_difficulty = "Easy"
        else:
            base_difficulty = "Trivial"

    if unknown_cr_names:
        if known_cr_enemies == 0:
            difficulty = "Unrated"
        else:
            difficulty = f"Incomplete ({base_difficulty}+)"
    else:
        difficulty = base_difficulty

    ratio = total_enemies / max(1, party_size)
    if total_enemies == 1 and party_size >= 3:
        action_note = (
            "Solo foe against a full party: vulnerable to focus-fire and control spells. "
            "Pair with environmental hazards, cover, or staged reinforcements."
        )
    elif ratio < 0.75:
        action_note = (
            "Party holds an action-economy advantage: let foes leverage terrain bottlenecks, "
            "ranged cover, or defensive positioning."
        )
    elif ratio <= 1.5:
        action_note = (
            "Balanced action economy: positioning, cover, and target priority will swing momentum."
        )
    else:
        action_note = (
            "Foes outnumber the party significantly: spread attacks across targets, stagger "
            "reinforcements by 1-2 rounds, or tie enemy turns to a tactical objective."
        )

    return {
        "ruleset": ruleset,
        "party_level": party_level,
        "party_size": party_size,
        "total_enemies": total_enemies,
        "raw_xp": raw_xp,
        "multiplier": mult,
        "adjusted_xp": adjusted_xp,
        "budgets": budgets,
        "difficulty": difficulty,
        "ratio": ratio,
        "action_note": action_note,
        "unknown_cr_names": unknown_cr_names,
    }


# ---------------------------------------------------------------------------
# Output Formatting (Markdown Encounter Note + Atlas VTT Encounter JSON)
# ---------------------------------------------------------------------------

def sanitize_filename(name: str) -> str:
    clean = re.sub(r'[<>:"/\\|?*]+', "-", name).strip()
    return clean or "Encounter"


def sanitize_slug(slug: str) -> str:
    clean = re.sub(r"[^a-z0-9_-]+", "_", slug.lower())
    clean = re.sub(r"_{2,}", "_", clean).strip("_-")
    return clean or "encounter"


def yaml_escape(val: str) -> str:
    return val.replace("\\", "\\\\").replace('"', '\\"')


def format_party_passives_table(party: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| PC | Role | Passive Perception | Passive Investigation | Passive Insight |",
        "| :--- | :--- | :---: | :---: | :---: |",
    ]
    for pc in party:
        p = pc.get("passives") or {}
        note = pc.get("note") or pc["name"]
        if note == pc["name"]:
            pc_link = f"[[{note}]]"
        else:
            pc_link = f"[[{note}\\|{pc['name']}]]"
        lines.append(
            f"| {pc_link} | {pc.get('role', '-')} | `{p.get('perception', 10)}` | "
            f"`{p.get('investigation', 10)}` | `{p.get('insight', 10)}` |"
        )
    return lines


def best_passive(party: list[dict[str, Any]], stat: str) -> tuple[str, int]:
    best_name = "PC"
    best_val = 10
    for pc in party:
        val = int((pc.get("passives") or {}).get(stat, 10))
        if val > best_val or best_name == "PC":
            best_val = val
            best_name = str(pc.get("name", "PC"))
    return best_name, best_val


def render_encounter_md(
    encounter_name: str,
    encounter_id: str,
    collection: str,
    groups: list[dict[str, Any]],
    eval_data: dict[str, Any],
    party: list[dict[str, Any]],
) -> str:
    ruleset = eval_data["ruleset"]
    difficulty = eval_data["difficulty"]
    raw_xp = eval_data["raw_xp"]
    adjusted_xp = eval_data["adjusted_xp"]
    budgets = eval_data["budgets"]
    perc_name, perc_val = best_passive(party, "perception")
    inv_name, inv_val = best_passive(party, "investigation")
    ins_name, ins_val = best_passive(party, "insight")
    active_dc = max(perc_val, inv_val) + 1

    budget_summary = " | ".join(f"**{k}:** `{v:,} XP`" for k, v in budgets.items())

    lines: list[str] = [
        "---",
        f'title: "{yaml_escape(encounter_name)}"',
        'icon: "⚔️"',
        "tags: [encounter, combat]",
        'type: "Encounter"',
        f'ruleset: "{ruleset}"',
        f'difficulty: "{difficulty}"',
        f"total_xp: {raw_xp}",
        f'atlas_encounter: "{encounter_id}"',
        'status: "draft"',
        "---",
        "",
        f"# ⚔️ {encounter_name}",
        "",
        f"> [!SUMMARY] **Encounter Snapshot ({ruleset} 5e Ruleset)**",
        f"> **Difficulty:** `{difficulty}` | **Party:** `{eval_data['party_size']} PCs @ Level {eval_data['party_level']}` | **Total XP:** `{raw_xp:,} XP` | **Atlas Record:** `{encounter_id}` (`{collection}`)",
        "",
        "---",
        "",
        "## Enemy Roster",
        "",
        "| Creature | Qty | CR | AC | HP | XP Each | Total XP | Statblock |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]

    for g in groups:
        cr_disp = g["cr"] or "?"
        xp_each_disp = f"{g['xp_each']:,}" if g["xp_each"] is not None else "?"
        xp_tot_disp = f"{g['xp_total']:,}" if g["xp_each"] is not None else "?"
        sb = g["statblockPath"]
        if sb.endswith(".md"):
            sb_link = f"[[{sb[:-3]}\\|{g['name']}]]"
        else:
            sb_link = "Ad hoc"
        lines.append(
            f"| {g['name']} | {g['count']} | {cr_disp} | {g['ac']} | {g['hp']} | "
            f"{xp_each_disp} | {xp_tot_disp} | {sb_link} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## XP Math & Action Economy",
        "",
        f"- **Party XP Budgets ({ruleset}, {eval_data['party_size']} × Lv. {eval_data['party_level']}):** {budget_summary}.",
    ])

    if ruleset == "2024":
        lines.append(
            f"- **Encounter XP Total:** `{raw_xp:,} XP` (2024 ruleset uses direct XP budgets without a creature-count multiplier) → **`{difficulty}`**."
        )
    else:
        lines.append(
            f"- **Raw XP (Awarded):** `{raw_xp:,} XP` × `{eval_data['multiplier']}x` (2014 encounter-size multiplier for {eval_data['total_enemies']} foes) = **`{adjusted_xp:,} Adjusted XP`** → **`{difficulty}`**."
        )

    lines.append(
        f"- **Action-Economy Ratio:** `{eval_data['total_enemies']} foes` vs. `{eval_data['party_size']} PCs` (`{eval_data['ratio']:.2f}:1`). {eval_data['action_note']}"
    )

    if eval_data["unknown_cr_names"]:
        unknown_list = ", ".join(sorted(set(eval_data["unknown_cr_names"])))
        lines.append(
            f"- **Note (Missing CR):** Ad-hoc creature(s) without a statblock CR: `{unknown_list}`. Add a note under `Monsters/` or pass `#<CR>` (e.g. `Wolf:3@11#1/4`) to include their XP."
        )

    lines.extend([
        "",
        "---",
        "",
        "## Pre-Calculated Party Passives",
        "",
        *format_party_passives_table(party),
        "",
        f"- ⚡ **[Automatic Passive — {perc_name} (Perc. {perc_val})]:** Automatically spots obvious ambushes, cover positions, or hazards with DC ≤ `{perc_val}`.",
        f"- ⚡ **[Automatic Passive — {inv_name} (Inv. {inv_val})]:** Automatically catches structural tells, tracks, or tripwires with DC ≤ `{inv_val}`.",
        f"- ⚡ **[Automatic Passive — {ins_name} (Ins. {ins_val})]:** Immediately reads enemy morale or hesitation with DC ≤ `{ins_val}`.",
        f"- 🎲 **[Active Roll — Perception / Investigation DC {active_dc}]:** Required to notice concealed threats, hidden triggers, or stealthy flanking foes.",
        "",
        "---",
        "",
        "## Tactical Terrain & Morale Checklist",
        "",
        "- [ ] **Cover & Line of Sight:** Place at least 2 pieces of half cover (`+2 AC`) or 1 full sight-blocking obstacle.",
        "- [ ] **Lighting & Vision:** Confirm ambient brightness (`day` / `dusk` / `night`), torches, and darkvision sightlines in Atlas VTT.",
        "- [ ] **Terrain Feature / Secondary Objective:** Add elevation, difficult terrain, a hazard, or a non-combat goal (protecting cargo, stopping a runner, sealing a door).",
        "- [ ] **Morale & Retreat Trigger:** Define when foes parley, flee, or sound an alarm (e.g., once half are defeated or the leader falls).",
        "",
    ])

    return "\n".join(lines)


def build_atlas_encounter_json(
    encounter_id: str,
    encounter_name: str,
    collection: str,
    groups: list[dict[str, Any]],
    eval_data: dict[str, Any],
    ts: int,
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for g in groups:
        entry: dict[str, Any] = {
            "name": g["name"],
            "count": g["count"],
            "hp": g["hp"],
            "imagePath": g["imagePath"],
            "statblockPath": g["statblockPath"],
            "size": g["size"],
            "cr": g["cr"],
            "xp": g["xp_each"] if g["xp_each"] is not None else 0,
        }
        if g.get("assetId"):
            entry["assetId"] = g["assetId"]
        entries.append(entry)

    record = {
        "format": 1,
        "type": "encounter",
        "id": encounter_id,
        "name": encounter_name,
        "collection": collection,
        "difficulty": eval_data["difficulty"],
        "ruleset": eval_data["ruleset"],
        "partyLevel": eval_data["party_level"],
        "partySize": eval_data["party_size"],
        "totalXp": eval_data["raw_xp"],
        "adjustedXp": eval_data["adjusted_xp"],
        "entries": entries,
        "tags": ["encounter", "combat"],
        "createdAt": ts,
        "modifiedAt": ts,
    }
    return {
        "id": encounter_id,
        "name": encounter_name,
        "collection": collection,
        "difficulty": eval_data["difficulty"],
        "createdAt": ts,
        "modifiedAt": ts,
        "atlasRecord": record,
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(
        description="5e XP Budget Calculator & Atlas VTT 0.16.0 Encounter JSON Builder."
    )
    ap.add_argument("--name", required=True, help="Encounter display name (e.g. 'Alley Ambush')")
    ap.add_argument(
        "--enemies",
        required=True,
        help="Enemy spec, e.g. 'Road Raider:2,Skeleton Sentry:1' or 'Wolf:3@11' or 'Wolf:3@11#1/4'",
    )
    ap.add_argument("--ruleset", choices=["2024", "2014"], default="2024", help="5e XP budget ruleset (default: 2024)")
    ap.add_argument("--party-level", type=int, help="Party level 1-20 (default from campaign.config.json)")
    ap.add_argument("--party-size", type=int, help="Party size (default: len(party) from campaign.config.json)")
    ap.add_argument("--slug", help="Optional deterministic slug for encounter ID (default derived from --name)")
    ap.add_argument("--collection", help="Atlas VTT collection override (default from campaign.config.json)")
    ap.add_argument("--vault", help="Vault root directory override (default from campaign.config.json)")
    ap.add_argument("--config", help="Optional path to campaign.config.json")
    ap.add_argument("--out-dir", help="Alternative output vault directory for isolated tests")
    ap.add_argument("--dry-run", action="store_true", help="Simulate and print XP breakdown without writing files")
    args = ap.parse_args(argv)

    cfg = load_runtime_config(pathlib.Path(args.config).resolve() if args.config else None)
    vault_dir = pathlib.Path(args.vault).resolve() if args.vault else cfg["vault_dir"]
    collection = args.collection or cfg["collection"]
    party = cfg["party"]
    fallbacks = cfg["fallback_tokens"]

    party_level = args.party_level if args.party_level is not None else cfg["party_level"]
    party_size = args.party_size if args.party_size is not None else len(party)

    if not (1 <= party_level <= 20):
        ap.error("--party-level must be between 1 and 20.")
    if party_size < 1:
        ap.error("--party-size must be at least 1.")

    encounter_name = sanitize_filename(args.name)
    slug = sanitize_slug(args.slug or encounter_name)[:48]
    if slug.startswith("encounter-"):
        encounter_id = slug
    elif slug.startswith("encounter_"):
        encounter_id = "encounter-" + slug[len("encounter_") :].lstrip("_-")
    else:
        encounter_id = f"encounter-{slug}"

    catalog = load_monster_catalog(vault_dir, collection, fallbacks)
    groups = parse_enemy_groups(args.enemies, catalog, fallbacks)
    if not groups:
        print("ERROR: No valid enemies parsed from --enemies.", file=sys.stderr)
        return 1

    eval_data = evaluate_encounter(groups, party_level, party_size, args.ruleset)
    if eval_data["unknown_cr_names"]:
        unknown_list = ", ".join(sorted(set(eval_data["unknown_cr_names"])))
        print(
            f"WARNING: Unrated creature(s) without a statblock CR ({unknown_list}); "
            f"difficulty marked '{eval_data['difficulty']}'. Add statblocks in Monsters/ or append #<CR> (e.g. 'Wolf:3@11#1/4').",
            file=sys.stderr,
        )
    ts = int(time.time() * 1000)

    md_text = render_encounter_md(encounter_name, encounter_id, collection, groups, eval_data, party)
    enc_json = build_atlas_encounter_json(encounter_id, encounter_name, collection, groups, eval_data, ts)

    md_rel = f"Encounters/{encounter_name}.md"
    json_rel = f"atlas-vtt/collections/{collection}/encounters/{encounter_id}.json"

    if args.dry_run:
        print(f"[DRY-RUN] Encounter '{encounter_name}' (ruleset={args.ruleset}, party={party_size}x Lv.{party_level})")
        print(f"  Difficulty: {eval_data['difficulty']} | Raw XP: {eval_data['raw_xp']:,} | Adjusted XP: {eval_data['adjusted_xp']:,} (x{eval_data['multiplier']})")
        print("  Budgets:    " + " | ".join(f"{k}={v:,}" for k, v in eval_data["budgets"].items()))
        print(f"  Action Eco: {eval_data['total_enemies']} foes vs {party_size} PCs ({eval_data['ratio']:.2f}:1)")
        for g in groups:
            xp_str = f"{g['xp_each']} XP" if g["xp_each"] is not None else "unknown XP"
            print(
                f"    - {g['count']}x {g['name']} (CR {g['cr'] or '?'}, {xp_str}, HP {g['hp']}, AC {g['ac']}, size={g['size']}) "
                f"img={g['imagePath']} sb={g['statblockPath'] or '-'}"
            )
        print(f"  Would write MD:   {md_rel} ({len(md_text.encode('utf-8'))} bytes)")
        print(f"  Would write JSON: {json_rel}")
        return 0

    root_vault = pathlib.Path(args.out_dir).resolve() if args.out_dir else vault_dir
    md_path = root_vault / "Encounters" / f"{encounter_name}.md"
    json_path = root_vault / "atlas-vtt" / "collections" / collection / "encounters" / f"{encounter_id}.json"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    md_path.write_text(md_text, encoding="utf-8", newline="\n")
    json_path.write_text(json.dumps(enc_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(
        f"Built encounter '{encounter_name}' ({args.ruleset}, {eval_data['difficulty']}, "
        f"{eval_data['raw_xp']:,} XP, {eval_data['total_enemies']} foes vs {party_size} PCs)"
    )
    print(f"  Markdown:  {md_path}")
    print(f"  AtlasJSON: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
