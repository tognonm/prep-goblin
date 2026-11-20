#!/usr/bin/env python3
"""Procedural battlemap & Atlas VTT 0.16.0 scene generator (Demiurge Core — Quick Battlemap).

Produces tactile WebP battlemaps with Pillow + Atlas VTT .atlasmap scenes
(schema version 4) + map/scene JSON records + thumbnails + compact DM Dashboard
Markdown notes (< 5 KB) ready for live tabletop or online sessions.

Configuration (vault path, collection name, party PCs & passives, fallback tokens,
grid units) is loaded from `campaign.config.json` in the repository root and can
be overridden via CLI flags.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import re
import sys
import time
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]

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

PRESET_DEFAULTS: dict[str, dict[str, Any]] = {
    "whiteboard": {
        "cols": 16,
        "rows": 12,
        "lighting": "day",
        "default_name": "Quick Battlemap - Tactical Whiteboard",
        "icon": "📐",
        "subtitle": "Clean dry-erase parchment tactical canvas ready for live DM drawings.",
    },
    "alley": {
        "cols": 16,
        "rows": 12,
        "lighting": "dusk",
        "default_name": "Quick Battlemap - Urban Alley",
        "icon": "🏮",
        "subtitle": "Cobblestone street with a T-junction alley, crate cover, streetlamps, and a two-door side warehouse.",
    },
    "road": {
        "cols": 18,
        "rows": 12,
        "lighting": "day",
        "default_name": "Quick Battlemap - Country Road",
        "icon": "🛤️",
        "subtitle": "Muddy wagon track beside a shallow reed-lined riverbank with a halted merchant wagon and boulder cover.",
    },
    "hills": {
        "cols": 18,
        "rows": 12,
        "lighting": "dusk",
        "default_name": "Quick Battlemap - Rocky Hills",
        "icon": "🪨",
        "subtitle": "Limestone moorland with three sight-blocking rock outcrops, flanking lanes, an ancient menhir, and a campfire.",
    },
    "interior": {
        "cols": 14,
        "rows": 10,
        "lighting": "night",
        "default_name": "Quick Battlemap - Building Interior",
        "icon": "🏠",
        "subtitle": "Versatile shop, tavern, or townhouse featuring a main hall, counter, pillars, backroom, and hidden rear alley secret door.",
    },
}

LIGHTING_AMBIENT = {
    "day": 1.0,
    "dusk": 0.35,
    "night": 0.0,
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


# ---------------------------------------------------------------------------
# Configuration, Units & Party Helpers
# ---------------------------------------------------------------------------

def load_runtime_config(config_path: pathlib.Path | None = None) -> dict[str, Any]:
    cfg_file = config_path or (REPO_ROOT / "campaign.config.json")
    raw: dict[str, Any] = {}
    if cfg_file.is_file():
        try:
            raw = json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception:
            raw = {}

    vault_dir_val = raw.get("vault_dir")
    if isinstance(vault_dir_val, str) and vault_dir_val.strip():
        vault_path = (REPO_ROOT / vault_dir_val).resolve()
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
        "grid_unit_type": str(raw.get("grid_unit_type") or "feet"),
        "grid_unit_distance": float(raw.get("grid_unit_distance") or 5),
    }


def unit_suffix(unit_type: str) -> str:
    return "m" if unit_type.lower().startswith("m") else "ft"


def fmt_dist(cells_count: float, unit_dist: float, unit_type: str) -> str:
    val = cells_count * unit_dist
    suffix = unit_suffix(unit_type)
    val_str = f"{int(val)}" if abs(val - round(val)) < 1e-6 else f"{val:.1f}"
    return f"{val_str} {suffix}"


def make_torch_preset(unit_dist: float) -> dict[str, Any]:
    # Standard 5e torch: 4 cells bright / 8 cells dim (20 ft / 40 ft or 6 m / 12 m)
    return {
        "bright": round(4.0 * unit_dist, 2),
        "dim": round(8.0 * unit_dist, 2),
        "color": "#ff9a3c",
        "intensity": 1,
        "animation": "torch",
        "sourceRadius": round(1.33 * unit_dist, 2),
        "kind": "torch",
        "preset": "dnd5e-torch",
    }


def make_lamp_emission(
    bright_cells: float,
    dim_cells: float,
    unit_dist: float,
    color: str = "#ff9a3c",
    intensity: float = 0.9,
    kind: str = "lantern",
) -> dict[str, Any]:
    return {
        "bright": round(bright_cells * unit_dist, 2),
        "dim": round(dim_cells * unit_dist, 2),
        "color": color,
        "intensity": intensity,
        "animation": "torch",
        "sourceRadius": round(1.0 * unit_dist, 2),
        "kind": kind,
    }


def best_passive_pc(party: list[dict[str, Any]], stat: str) -> tuple[str, int]:
    best_name = "PC"
    best_val = 10
    for pc in party:
        passives = pc.get("passives") or {}
        val = int(passives.get(stat, 10))
        if val > best_val or best_name == "PC":
            best_val = val
            best_name = str(pc.get("name", "PC"))
    return best_name, best_val


def format_party_passives_line(party: list[dict[str, Any]]) -> str:
    chunks = []
    for pc in party:
        p = pc.get("passives") or {}
        chunks.append(
            f"**{pc['name']}** Perc. `{p.get('perception', 10)}` / Inv. `{p.get('investigation', 10)}` / Ins. `{p.get('insight', 10)}`"
        )
    return " | ".join(chunks)


def format_party_links(party: list[dict[str, Any]]) -> str:
    links = []
    for pc in party:
        note = pc.get("note") or pc["name"]
        if note == pc["name"]:
            links.append(f"[[{note}]]")
        else:
            links.append(f"[[{note}|{pc['name']}]]")
    return ", ".join(links)


# ---------------------------------------------------------------------------
# Geometry & Wall Helpers
# ---------------------------------------------------------------------------

def pt_seg_dist(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def cell_center(col: int, row: int, cell: int, size: int = 1) -> tuple[float, float]:
    return (col + 0.5 * size) * cell, (row + 0.5 * size) * cell


def make_wall(
    wid: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    chain_id: str,
    wtype: str = "solid",
    closed: bool = True,
    locked: bool = False,
) -> dict[str, Any]:
    wall: dict[str, Any] = {
        "id": wid,
        "kind": "wall",
        "type": wtype,
        "p1": {"x": float(x1), "y": float(y1)},
        "p2": {"x": float(x2), "y": float(y2)},
        "chainId": chain_id,
        "closed": closed,
    }
    if locked:
        wall["locked"] = True
    return wall


class WallBuilder:
    def __init__(self, prefix: str, cell: int) -> None:
        self.prefix = prefix
        self.cell = cell
        self.walls: dict[str, dict[str, Any]] = {}
        self._seq = 1

    def add_px(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        chain_id: str,
        wtype: str = "solid",
        closed: bool = True,
        locked: bool = False,
    ) -> None:
        if x1 == x2 and y1 == y2:
            return
        wid = f"wall_{self.prefix}_{self._seq:04d}"
        self.walls[wid] = make_wall(wid, x1, y1, x2, y2, chain_id, wtype, closed, locked)
        self._seq += 1

    def add_grid(
        self,
        c1: float,
        r1: float,
        c2: float,
        r2: float,
        chain_id: str,
        wtype: str = "solid",
        closed: bool = True,
        locked: bool = False,
    ) -> None:
        self.add_px(c1 * self.cell, r1 * self.cell, c2 * self.cell, r2 * self.cell, chain_id, wtype, closed, locked)

    def add_rect_grid(self, c0: int, r0: int, c1: int, r1: int, chain_id: str) -> None:
        self.add_grid(c0, r0, c1, r0, chain_id)
        self.add_grid(c1, r0, c1, r1, chain_id)
        self.add_grid(c1, r1, c0, r1, chain_id)
        self.add_grid(c0, r1, c0, r0, chain_id)

    def add_segmented_h(
        self,
        r: int,
        c0: int,
        c1: int,
        chain_prefix: str,
        doors: dict[int, tuple[str, bool, bool]] | None = None,
    ) -> None:
        doors = doors or {}
        cur = c0
        seg_idx = 1
        for dc in sorted(k for k in doors if c0 <= k < c1):
            if dc > cur:
                self.add_grid(cur, r, dc, r, f"{chain_prefix}_s{seg_idx}")
                seg_idx += 1
            wtype, closed, locked = doors[dc]
            self.add_grid(dc, r, dc + 1, r, f"{chain_prefix}_d{dc}", wtype=wtype, closed=closed, locked=locked)
            cur = dc + 1
        if cur < c1:
            self.add_grid(cur, r, c1, r, f"{chain_prefix}_s{seg_idx}")

    def add_segmented_v(
        self,
        c: int,
        r0: int,
        r1: int,
        chain_prefix: str,
        doors: dict[int, tuple[str, bool, bool]] | None = None,
    ) -> None:
        doors = doors or {}
        cur = r0
        seg_idx = 1
        for dr in sorted(k for k in doors if r0 <= k < r1):
            if dr > cur:
                self.add_grid(c, cur, c, dr, f"{chain_prefix}_s{seg_idx}")
                seg_idx += 1
            wtype, closed, locked = doors[dr]
            self.add_grid(c, dr, c, dr + 1, f"{chain_prefix}_d{dr}", wtype=wtype, closed=closed, locked=locked)
            cur = dr + 1
        if cur < r1:
            self.add_grid(c, cur, c, r1, f"{chain_prefix}_s{seg_idx}")


# ---------------------------------------------------------------------------
# Monster Catalog & Enemy Specification Parsing
# ---------------------------------------------------------------------------

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
        cr_raw = extract("cr")
        difficulty = f"CR {cr_raw}" if cr_raw and not cr_raw.upper().startswith("CR") else (cr_raw or "")
        size_raw = extract("size").lower()
        tok_size = 2 if "large" in size_raw else (3 if "huge" in size_raw else 1)

        sb_rel = f"Monsters/{md.name}"
        stem_key = md.stem.lower()
        name_key = disp_name.lower()

        token_info = (
            by_statblock.get(sb_rel.lower())
            or by_token_name.get(name_key)
            or by_token_name.get(stem_key)
        )
        image_path = token_info["imagePath"] if token_info else pick_fallback_art(name_key, fallbacks)
        entry = {
            "name": disp_name,
            "stem": md.stem,
            "hp": hp,
            "ac": ac,
            "cr": cr_raw,
            "difficulty": difficulty,
            "size": tok_size,
            "statblockPath": sb_rel,
            "imagePath": image_path,
        }
        catalog[stem_key] = entry
        catalog[name_key] = entry
    return catalog


def resolve_enemy(
    raw_name: str,
    hp_override: int | None,
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
        return out

    return {
        "name": cleaned,
        "stem": cleaned,
        "hp": hp_override if hp_override is not None else 11,
        "ac": 12,
        "cr": "",
        "difficulty": "",
        "size": 1,
        "statblockPath": "",
        "imagePath": pick_fallback_art(key, fallbacks),
    }


def parse_enemies_spec(
    spec: str,
    catalog: dict[str, dict[str, Any]],
    fallbacks: dict[str, str],
) -> list[dict[str, Any]]:
    if not spec or not spec.strip():
        return []
    expanded: list[dict[str, Any]] = []
    instance_counts: dict[str, int] = {}

    for chunk in re.split(r"[,;]+", spec):
        item = chunk.strip()
        if not item:
            continue
        count = 1
        hp_override: int | None = None

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

        proto = resolve_enemy(name_part, hp_override, catalog, fallbacks)
        for _ in range(count):
            inst = dict(proto)
            nm = inst["name"]
            instance_counts[nm] = instance_counts.get(nm, 0) + 1
            inst["instanceNumber"] = instance_counts[nm]
            expanded.append(inst)
    return expanded


# ---------------------------------------------------------------------------
# Procedural Pillow Drawing Helpers
# ---------------------------------------------------------------------------

def add_grain(img: Image.Image, rng: random.Random, strength: int = 8) -> Image.Image:
    np_rng = np.random.default_rng(rng.randint(0, 2**31 - 1))
    arr = np.array(img, dtype=np.int16)
    noise = np_rng.integers(-strength, strength + 1, size=(arr.shape[0], arr.shape[1], 1))
    if arr.shape[2] == 4:
        arr[:, :, :3] = np.clip(arr[:, :, :3] + noise, 0, 255)
    else:
        arr = np.clip(arr + noise, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), mode=img.mode)


def composite_soft_layer(base: Image.Image, draw_fn, blur_radius: float = 5.0) -> Image.Image:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    draw_fn(d)
    if blur_radius > 0:
        layer = layer.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    return Image.alpha_composite(base, layer)


def draw_crate(draw: ImageDraw.ImageDraw, x: float, y: float, w: float, h: float, rng: random.Random) -> None:
    shade = rng.randint(-8, 8)
    base = (138 + shade, 96 + shade, 56 + shade, 255)
    dark = (84 + shade, 54 + shade, 30 + shade, 255)
    hi = (168 + shade, 124 + shade, 76 + shade, 255)
    draw.rectangle([x + 3, y + 4, x + w + 3, y + h + 4], fill=(10, 12, 16, 95))
    draw.rectangle([x, y, x + w, y + h], fill=base, outline=dark, width=2)
    draw.rectangle([x + 4, y + 4, x + w - 4, y + h - 4], outline=hi, width=1)
    draw.line([(x + 4, y + 4), (x + w - 4, y + h - 4)], fill=dark, width=2)
    draw.line([(x + 5, y + 4), (x + w - 3, y + h - 4)], fill=hi, width=1)


def draw_barrel(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float) -> None:
    draw.ellipse([cx - r + 3, cy - r + 4, cx + r + 3, cy + r + 4], fill=(10, 12, 16, 95))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(128, 84, 48, 255), outline=(58, 42, 30, 255), width=2)
    draw.ellipse([cx - r * 0.78, cy - r * 0.78, cx + r * 0.78, cy + r * 0.78], outline=(90, 92, 96, 220), width=2)
    for off in (-r * 0.35, 0, r * 0.35):
        draw.line([(cx - r * 0.65, cy + off), (cx + r * 0.65, cy + off)], fill=(90, 56, 30, 160), width=1)


def draw_boulder_polygon(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    rng: random.Random,
    base_rgb: tuple[int, int, int] = (128, 126, 118),
    sides: int = 9,
) -> None:
    pts = []
    for i in range(sides):
        ang = (2 * math.pi * i) / sides + rng.uniform(-0.18, 0.18)
        rad_x = rx * rng.uniform(0.78, 1.08)
        rad_y = ry * rng.uniform(0.78, 1.08)
        pts.append((cx + math.cos(ang) * rad_x, cy + math.sin(ang) * rad_y))
    sh_pts = [(px + 5, py + 6) for px, py in pts]
    draw.polygon(sh_pts, fill=(14, 16, 18, 95))
    r0, g0, b0 = base_rgb
    dark = (max(0, r0 - 38), max(0, g0 - 38), max(0, b0 - 36), 255)
    mid = (r0, g0, b0, 255)
    hi = (min(255, r0 + 34), min(255, g0 + 34), min(255, b0 + 30), 255)
    draw.polygon(pts, fill=mid, outline=dark)
    inner = [(cx + (px - cx) * 0.62 - 2, cy + (py - cy) * 0.62 - 2) for px, py in pts]
    draw.polygon(inner, fill=hi)


def draw_bush(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    r: float,
    rng: random.Random,
    palette: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]] = (
        (46, 72, 38),
        (68, 102, 50),
        (98, 134, 68),
    ),
) -> None:
    dark, mid, hi = palette
    draw.ellipse([cx - r + 4, cy - r + 5, cx + r + 4, cy + r + 5], fill=(12, 18, 10, 85))
    for _ in range(6):
        ox = rng.uniform(-r * 0.45, r * 0.45)
        oy = rng.uniform(-r * 0.45, r * 0.45)
        cr = r * rng.uniform(0.45, 0.68)
        draw.ellipse([cx + ox - cr, cy + oy - cr, cx + ox + cr, cy + oy + cr], fill=(*dark, 245))
    for _ in range(5):
        ox = rng.uniform(-r * 0.35, r * 0.35)
        oy = rng.uniform(-r * 0.35, r * 0.35)
        cr = r * rng.uniform(0.35, 0.55)
        draw.ellipse([cx + ox - cr, cy + oy - cr, cx + ox + cr, cy + oy + cr], fill=(*mid, 245))
    for _ in range(3):
        ox = rng.uniform(-r * 0.35, r * 0.15)
        oy = rng.uniform(-r * 0.35, r * 0.15)
        cr = r * rng.uniform(0.20, 0.34)
        draw.ellipse([cx + ox - cr, cy + oy - cr, cx + ox + cr, cy + oy + cr], fill=(*hi, 235))


def draw_door_slab(
    draw: ImageDraw.ImageDraw,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    locked: bool = False,
) -> None:
    fill = (102, 108, 118, 255) if locked else (136, 86, 46, 255)
    outline = (42, 26, 16, 255)
    if abs(x1 - x2) < 1:
        top, bot = min(y1, y2), max(y1, y2)
        draw.rectangle([x1 - 5, top + 4, x1 + 5, bot - 4], fill=fill, outline=outline, width=2)
        draw.ellipse([x1 - 2, (top + bot) / 2 - 2, x1 + 2, (top + bot) / 2 + 2], fill=(224, 186, 92, 255))
    else:
        left, right = min(x1, x2), max(x1, x2)
        draw.rectangle([left + 4, y1 - 5, right - 4, y1 + 5], fill=fill, outline=outline, width=2)
        draw.ellipse([(left + right) / 2 - 2, y1 - 2, (left + right) / 2 + 2, y1 + 2], fill=(224, 186, 92, 255))


def draw_lamp_prop(img: Image.Image, cx: float, cy: float, active_glow: bool = True, style: str = "lamp") -> Image.Image:
    if active_glow:
        def _glow(d: ImageDraw.ImageDraw) -> None:
            d.ellipse([cx - 58, cy - 58, cx + 58, cy + 58], fill=(255, 160, 62, 55))
            d.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], fill=(255, 198, 102, 95))
        img = composite_soft_layer(img, _glow, blur_radius=12)
    draw = ImageDraw.Draw(img, "RGBA")
    if style == "campfire":
        for i in range(8):
            ang = i * (2 * math.pi / 8)
            sx, sy = cx + math.cos(ang) * 18, cy + math.sin(ang) * 18
            draw.ellipse([sx - 6, sy - 5, sx + 6, sy + 5], fill=(92, 90, 84, 255), outline=(42, 40, 38, 255), width=1)
        draw.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=(48, 34, 28, 240))
        if active_glow:
            draw.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], fill=(235, 108, 32, 230))
            draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(255, 212, 96, 250))
        else:
            draw.line([(cx - 8, cy - 5), (cx + 8, cy + 6)], fill=(64, 48, 36, 255), width=3)
            draw.line([(cx - 7, cy + 6), (cx + 7, cy - 5)], fill=(54, 40, 30, 255), width=3)
    else:
        draw.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=(42, 46, 52, 245), outline=(92, 98, 108, 255), width=2)
        core = (255, 196, 92, 250) if active_glow else (196, 168, 118, 220)
        draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=core, outline=(255, 240, 190, 255), width=1)
    return img


def paint_grid_walls(draw: ImageDraw.ImageDraw, walls: dict[str, dict[str, Any]], thickness: int = 10) -> None:
    wall_col = (38, 42, 50, 255)
    wall_hi = (92, 98, 112, 255)
    for w in walls.values():
        p1, p2 = w["p1"], w["p2"]
        x1, y1, x2, y2 = p1["x"], p1["y"], p2["x"], p2["y"]
        wtype = w.get("type", "solid")
        if wtype == "door":
            draw_door_slab(draw, x1, y1, x2, y2, locked=bool(w.get("locked")))
        else:
            half = thickness // 2
            rx0, rx1 = min(x1, x2) - half, max(x1, x2) + half
            ry0, ry1 = min(y1, y2) - half, max(y1, y2) + half
            draw.rectangle([rx0, ry0, rx1, ry1], fill=wall_col, outline=wall_hi, width=1)


# ---------------------------------------------------------------------------
# 5 Procedural Preset Builders
# ---------------------------------------------------------------------------

def build_preset_whiteboard(
    cols: int, rows: int, cell: int, lighting: str, seed: int, prefix: str,
    party: list[dict[str, Any]], unit_dist: float, unit_type: str,
) -> dict[str, Any]:
    rng = random.Random(seed)
    w, h = cols * cell, rows * cell
    img = Image.new("RGBA", (w, h), (244, 240, 230, 255))
    img = add_grain(img, rng, strength=5)

    def _vignette(d: ImageDraw.ImageDraw) -> None:
        d.rectangle([0, 0, w, h], outline=(188, 178, 158, 95), width=26)

    img = composite_soft_layer(img, _vignette, blur_radius=14)
    draw = ImageDraw.Draw(img, "RGBA")

    for c in range(cols + 1):
        x = c * cell
        col_line = (196, 189, 174, 200) if c % 4 == 0 else (214, 208, 194, 175)
        draw.line([(x, 0), (x, h)], fill=col_line, width=1)
    for r in range(rows + 1):
        y = r * cell
        row_line = (196, 189, 174, 200) if r % 4 == 0 else (214, 208, 194, 175)
        draw.line([(0, y), (w, y)], fill=row_line, width=1)

    draw.rectangle([3, 3, w - 4, h - 4], outline=(146, 138, 122, 220), width=3)
    draw.rectangle([9, 9, w - 10, h - 10], outline=(176, 168, 152, 160), width=1)

    ccx, ccy = (cols - 0.5) * cell, (rows - 0.5) * cell
    cr = cell * 0.28
    draw.ellipse([ccx - cr, ccy - cr, ccx + cr, ccy + cr], outline=(168, 160, 144, 150), width=1)
    draw.polygon([(ccx, ccy - cr - 5), (ccx + 5, ccy), (ccx, ccy - 4), (ccx - 5, ccy)], fill=(142, 134, 118, 165))
    draw.line([(ccx - cr - 3, ccy), (ccx + cr + 3, ccy)], fill=(168, 160, 144, 150), width=1)
    draw.line([(ccx, ccy - cr - 3), (ccx, ccy + cr + 3)], fill=(168, 160, 144, 150), width=1)

    wb = WallBuilder(prefix, cell)
    wb.add_rect_grid(0, 0, cols, rows, "chain_outer")

    mid_r = rows // 2
    pc_cells = [(2, max(1, mid_r - 1)), (2, mid_r), (2, min(rows - 2, mid_r + 1))]
    enemy_cells = [
        (cols - 3, max(1, mid_r - 1)),
        (cols - 3, mid_r),
        (cols - 3, min(rows - 2, mid_r + 1)),
        (cols - 4, max(1, mid_r - 2)),
        (cols - 4, min(rows - 2, mid_r + 2)),
        (cols - 2, mid_r),
        (cols - 5, mid_r),
        (cols - 4, mid_r),
    ]

    pins = [
        {"label": "A", "name": "Open Sketch Area", "heading": "A. Open Sketch Area", "col": 1, "row": 1},
        {"label": "B", "name": "Enemy Zone", "heading": "B. Enemy Zone and Improvised Cover", "col": cols - 2, "row": 1},
    ]

    sections = [
        (
            "A. Open Sketch Area",
            [
                f"Neutral dry-erase tactical canvas (`{fmt_dist(1, unit_dist, unit_type)}` per square), free of interior walls.",
                "Use Atlas VTT's *Drawing* tools to sketch walls, rivers, furniture, or spell areas on the fly.",
                "Outer perimeter walls keep dynamic vision bounded cleanly inside the grid.",
            ],
        ),
        (
            "B. Enemy Zone and Improvised Cover",
            [
                "Eastern half reserved for improvised foes or reinforcements.",
                "Quick 5e cover reminder: half cover `+2 AC / +2 Dex saves`, three-quarters cover `+5 AC / +5 Dex saves`, difficult terrain costs double movement.",
            ],
        ),
    ]

    return {
        "image": img.convert("RGB"),
        "walls": wb.walls,
        "lights": {},
        "pins": pins,
        "pc_cells": pc_cells,
        "enemy_cells": enemy_cells,
        "blocked_cells": set(),
        "sections": sections,
        "grid_opacity": 0.30,
    }


def build_preset_alley(
    cols: int, rows: int, cell: int, lighting: str, seed: int, prefix: str,
    party: list[dict[str, Any]], unit_dist: float, unit_type: str,
) -> dict[str, Any]:
    rng = random.Random(seed)
    w, h = cols * cell, rows * cell
    perc_name, perc_val = best_passive_pc(party, "perception")

    st_r0 = max(3, min(rows - 5, int(round(rows * 0.42))))
    st_r1 = min(rows - 2, st_r0 + 4)
    al_c0 = max(4, cols // 2 - 1)
    al_c1 = min(cols - 5, al_c0 + 3)
    wh_c0 = al_c1
    wh_c1 = cols - 1
    wh_r0 = 1
    wh_r1 = st_r0
    alc_c0 = max(2, al_c0 - 3)
    alc_c1 = alc_c0 + 2
    has_alcove = st_r1 + 1 < rows

    img = Image.new("RGBA", (w, h), (58, 62, 68, 255))
    draw = ImageDraw.Draw(img, "RGBA")

    stone_w, stone_h = 18, 12
    for row_i, sy in enumerate(range(0, h, stone_h)):
        offset = (stone_w // 2) if (row_i % 2) else 0
        for sx in range(-offset, w, stone_w):
            v = rng.randint(-12, 12)
            col_s = (78 + v, 81 + v, 87 + v, 255)
            draw.rectangle([sx + 1, sy + 1, sx + stone_w - 1, sy + stone_h - 1], fill=col_s, outline=(42, 45, 50, 170), width=1)

    draw.rectangle([0, st_r0 * cell, al_c0 * cell, st_r0 * cell + 8], fill=(104, 106, 110, 255))
    draw.rectangle([wh_c0 * cell, st_r0 * cell, w, st_r0 * cell + 8], fill=(104, 106, 110, 255))
    draw.rectangle([0, st_r1 * cell - 8, w, st_r1 * cell], fill=(104, 106, 110, 255))

    px_p, py_p = (al_c0 + 1.2) * cell, (st_r0 + 2.3) * cell
    draw.ellipse([px_p - 42, py_p - 18, px_p + 42, py_p + 18], fill=(56, 70, 86, 125), outline=(92, 110, 130, 90), width=1)

    wx0, wy0, wx1, wy1 = wh_c0 * cell, wh_r0 * cell, wh_c1 * cell, wh_r1 * cell
    draw.rectangle([wx0, wy0, wx1, wy1], fill=(122, 96, 68, 255))
    plank_h = 14
    for py in range(wy0, wy1, plank_h):
        dv = rng.randint(-10, 10)
        draw.rectangle([wx0, py, wx1, min(wy1, py + plank_h)], fill=(124 + dv, 96 + dv, 66 + dv, 255), outline=(74, 54, 36, 160), width=1)
        seam_x = wx0 + rng.randint(40, max(45, (wx1 - wx0) - 40))
        draw.line([(seam_x, py), (seam_x, min(wy1, py + plank_h))], fill=(74, 54, 36, 170), width=1)

    draw_crate(draw, wx1 - 54, wy0 + 14, 38, 34, rng)
    draw_barrel(draw, wx1 - 36, wy0 + 68, 15)

    def paint_roof(x0: int, y0: int, x1: int, y1: int, base_rgb: tuple[int, int, int], ridge_horiz: bool = True) -> None:
        if x1 <= x0 or y1 <= y0:
            return
        r0, g0, b0 = base_rgb
        draw.rectangle([x0, y0, x1, y1], fill=(r0, g0, b0, 255))
        step = 14
        if ridge_horiz:
            mid_y = (y0 + y1) // 2
            for ty in range(y0, y1, step):
                shade = -14 if ty > mid_y else 10
                draw.rectangle([x0, ty, x1, min(y1, ty + step)], fill=(max(0, r0 + shade), max(0, g0 + shade), max(0, b0 + shade), 255), outline=(22, 24, 28, 120), width=1)
            draw.line([(x0, mid_y), (x1, mid_y)], fill=(min(255, r0 + 36), min(255, g0 + 36), min(255, b0 + 34), 255), width=4)
        else:
            mid_x = (x0 + x1) // 2
            for tx in range(x0, x1, step):
                shade = -14 if tx > mid_x else 10
                draw.rectangle([tx, y0, min(x1, tx + step), y1], fill=(max(0, r0 + shade), max(0, g0 + shade), max(0, b0 + shade), 255), outline=(22, 24, 28, 120), width=1)
            draw.line([(mid_x, y0), (mid_x, y1)], fill=(min(255, r0 + 36), min(255, g0 + 36), min(255, b0 + 34), 255), width=4)
        draw.rectangle([x0, y0, x1, y1], outline=(24, 26, 32, 255), width=3)

    def _roof_shadows(d: ImageDraw.ImageDraw) -> None:
        d.rectangle([0, 0, al_c0 * cell + 12, st_r0 * cell + 14], fill=(10, 12, 16, 130))
        d.rectangle([wx0 - 10, wy0 - 10, wx1 + 12, wy1 + 14], fill=(10, 12, 16, 110))
        d.rectangle([0, st_r1 * cell - 10, w, h], fill=(10, 12, 16, 115))

    img = composite_soft_layer(img, _roof_shadows, blur_radius=7)
    draw = ImageDraw.Draw(img, "RGBA")

    paint_roof(0, 0, al_c0 * cell, st_r0 * cell, (54, 58, 70), ridge_horiz=True)
    draw.rectangle([al_c0 * cell - 88, st_r0 * cell - 78, al_c0 * cell - 52, st_r0 * cell - 46], fill=(78, 70, 68, 255), outline=(30, 26, 26, 255), width=2)
    draw.rectangle([al_c0 * cell - 80, st_r0 * cell - 70, al_c0 * cell - 60, st_r0 * cell - 54], fill=(24, 22, 24, 255))

    paint_roof(wh_c0 * cell, 0, w, wh_r0 * cell, (62, 52, 48), ridge_horiz=True)
    paint_roof(wh_c1 * cell, wh_r0 * cell, w, wh_r1 * cell, (62, 52, 48), ridge_horiz=False)

    if has_alcove:
        paint_roof(0, st_r1 * cell, alc_c0 * cell, h, (68, 56, 52), ridge_horiz=True)
        paint_roof(alc_c1 * cell, st_r1 * cell, w, h, (58, 54, 62), ridge_horiz=True)
        paint_roof(alc_c0 * cell, (st_r1 + 1) * cell, alc_c1 * cell, h, (62, 54, 54), ridge_horiz=True)
    else:
        paint_roof(0, st_r1 * cell, w, h, (64, 54, 52), ridge_horiz=True)

    draw_crate(draw, al_c0 * cell + 8, (st_r0 - 1) * cell + 14, 34, 32, rng)
    draw_barrel(draw, al_c0 * cell + 52, (st_r0 - 1) * cell + 48, 13)
    if has_alcove:
        draw_crate(draw, alc_c0 * cell + 12, st_r1 * cell + 16, 36, 32, rng)
        draw_barrel(draw, (alc_c0 + 1) * cell + 28, st_r1 * cell + 34, 16)
    ec = min(cols - 3, wh_c0 + 1)
    draw_crate(draw, ec * cell + 14, (st_r1 - 1) * cell + 24, 34, 30, rng)
    draw_barrel(draw, ec * cell + 56, (st_r1 - 1) * cell + 42, 13)

    img = add_grain(img, rng, strength=6)
    draw = ImageDraw.Draw(img, "RGBA")

    wb = WallBuilder(prefix, cell)
    wb.add_grid(al_c0, 0, al_c1, 0, "chain_outer_n")
    wb.add_grid(0, st_r0, 0, st_r1, "chain_outer_w")
    wb.add_grid(cols, st_r0, cols, st_r1, "chain_outer_e")
    wb.add_grid(0, st_r0, al_c0, st_r0, "chain_nw_bldg")
    wb.add_grid(al_c0, st_r0, al_c0, 0, "chain_nw_bldg")

    door_alley_r = max(wh_r0, st_r0 - 2)
    door_street_c = min(wh_c1 - 1, wh_c0 + 2)
    wb.add_grid(wh_c0, wh_r0, wh_c1, wh_r0, "chain_wh_n")
    wb.add_grid(wh_c1, wh_r0, wh_c1, wh_r1, "chain_wh_e")
    wb.add_segmented_v(wh_c0, wh_r0, wh_r1, "chain_wh_w", doors={door_alley_r: ("door", True, False)})
    wb.add_segmented_h(wh_r1, wh_c0, wh_c1, "chain_wh_s", doors={door_street_c: ("door", True, False)})
    wb.add_grid(wh_c1, st_r0, cols, st_r0, "chain_ne_edge")
    wb.add_grid(wh_c0, 0, wh_c0, wh_r0, "chain_alley_ne")

    if has_alcove:
        wb.add_grid(0, st_r1, alc_c0, st_r1, "chain_south_bldg")
        wb.add_grid(alc_c0, st_r1, alc_c0, st_r1 + 1, "chain_south_bldg")
        wb.add_grid(alc_c0, st_r1 + 1, alc_c1, st_r1 + 1, "chain_south_bldg")
        wb.add_grid(alc_c1, st_r1 + 1, alc_c1, st_r1, "chain_south_bldg")
        wb.add_grid(alc_c1, st_r1, cols, st_r1, "chain_south_bldg")
    else:
        wb.add_grid(0, st_r1, cols, st_r1, "chain_south_bldg")

    paint_grid_walls(draw, wb.walls, thickness=10)

    lamp1_col, lamp1_row = max(2, al_c0 - 1), st_r0
    lamp2_col, lamp2_row = min(cols - 2, wh_c0 + 3), st_r1 - 1
    l1x, l1y = cell_center(lamp1_col, lamp1_row, cell)
    l2x, l2y = cell_center(lamp2_col, lamp2_row, cell)
    lamps_lit = lighting in ("dusk", "night")
    img = draw_lamp_prop(img, l1x, l1y, active_glow=lamps_lit, style="lamp")
    img = draw_lamp_prop(img, l2x, l2y, active_glow=lamps_lit, style="lamp")

    lamp_em = make_lamp_emission(3.0, 6.0, unit_dist)
    lights = {
        f"light_{prefix}_001": {
            "id": f"light_{prefix}_001",
            "kind": "light",
            "x": l1x,
            "y": l1y,
            "emission": dict(lamp_em),
            "activeBelowAmbient": 0.5,
        },
        f"light_{prefix}_002": {
            "id": f"light_{prefix}_002",
            "kind": "light",
            "x": l2x,
            "y": l2y,
            "emission": dict(lamp_em),
            "activeBelowAmbient": 0.5,
        },
    }

    blocked: set[tuple[int, int]] = set()
    for c in range(cols):
        for r in range(rows):
            in_street = st_r0 <= r < st_r1
            in_alley = al_c0 <= c < al_c1 and 0 <= r < st_r0
            in_wh = wh_c0 <= c < wh_c1 and wh_r0 <= r < wh_r1
            in_alcove = has_alcove and alc_c0 <= c < alc_c1 and r == st_r1
            if not (in_street or in_alley or in_wh or in_alcove):
                blocked.add((c, r))

    pc_cells = [(1, st_r0 + 1), (1, st_r0 + 2), (2, st_r0 + 1)]
    enemy_cells = [
        (al_c0 + 1, max(1, st_r0 - 3)),
        (al_c0 + 1, max(1, st_r0 - 1)),
        (wh_c0 + 1, st_r0 + 1),
        (wh_c0 + 2, st_r0 + 2),
        (wh_c0 + 1, wh_r0 + 1),
        (cols - 2, st_r0 + 1),
        (al_c0 + 2, st_r0 + 2),
        (wh_c0 + 2, wh_r0 + 1),
    ]

    pins = [
        {"label": "A", "name": "Cobblestone Street", "heading": "A. Cobblestone Street (West Entry)", "col": 2, "row": st_r0},
        {"label": "B", "name": "Side Alley", "heading": "B. Side Alley and T-Junction", "col": al_c0 + 1, "row": max(1, st_r0 - 2)},
        {"label": "C", "name": "Side Warehouse", "heading": "C. Side Warehouse (Two Doors)", "col": min(wh_c1 - 1, wh_c0 + 2), "row": wh_r0 + 1},
    ]

    sections = [
        (
            "A. Cobblestone Street (West Entry)",
            [
                f"Main street (`{fmt_dist(4, unit_dist, unit_type)}` wide) lit by two oil streetlamps (`bright {fmt_dist(3, unit_dist, unit_type)} / dim {fmt_dist(6, unit_dist, unit_type)}` at dusk and night).",
                "Crates and barrels in the southern loading alcove and along the curb provide **half cover (`+2 AC`)**.",
            ],
        ),
        (
            "B. Side Alley and T-Junction",
            [
                f"Narrow side alley (`{fmt_dist(3, unit_dist, unit_type)}` wide), ideal for ambushes, flanking maneuvers, or a northward escape.",
                f"⚡ `[Automatic Passive — {perc_name} (Perc. {perc_val})]` Immediately spots stacked crates at the northwest corner of the junction offering ideal cover for a ranged attacker.",
            ],
        ),
        (
            "C. Side Warehouse (Two Doors)",
            [
                "Accessible via **two closed unlocked doors** (one facing the main street, one opening onto the side alley).",
                "Clicking either door in Atlas VTT immediately updates dynamic line of sight and light propagation for all players.",
                "🎲 `[Active Roll — Perception or Investigation DC 14]` To search the stacked crates in the northeast corner of the warehouse.",
            ],
        ),
    ]

    return {
        "image": img.convert("RGB"),
        "walls": wb.walls,
        "lights": lights,
        "pins": pins,
        "pc_cells": pc_cells,
        "enemy_cells": enemy_cells,
        "blocked_cells": blocked,
        "sections": sections,
        "grid_opacity": 0.40,
    }


def build_preset_road(
    cols: int, rows: int, cell: int, lighting: str, seed: int, prefix: str,
    party: list[dict[str, Any]], unit_dist: float, unit_type: str,
) -> dict[str, Any]:
    rng = random.Random(seed)
    w, h = cols * cell, rows * cell
    inv_name, inv_val = best_passive_pc(party, "investigation")

    img = Image.new("RGBA", (w, h), (88, 108, 62, 255))

    def _grass_mottle(d: ImageDraw.ImageDraw) -> None:
        for _ in range(cols * rows * 2):
            gx = rng.randint(0, w)
            gy = rng.randint(0, h)
            gr = rng.randint(28, 70)
            dv = rng.randint(-14, 14)
            d.ellipse([gx - gr, gy - gr * 0.75, gx + gr, gy + gr * 0.75], fill=(84 + dv, 108 + dv, 56 + dv, 120))

    img = composite_soft_layer(img, _grass_mottle, blur_radius=16)
    draw = ImageDraw.Draw(img, "RGBA")

    for _ in range(cols * rows * 3):
        tx = rng.randint(8, w - 8)
        ty = rng.randint(8, int((rows - 2) * cell))
        draw.line([(tx, ty), (tx - 2, ty - 5)], fill=(66, 86, 44, 120), width=1)
        draw.line([(tx, ty), (tx + 2, ty - 6)], fill=(110, 132, 74, 110), width=1)

    river_y = (rows - 2) * cell + 18
    bank_pts = [(0, h)]
    for x in range(0, w + 40, 40):
        wave = math.sin(x * 0.012 + seed) * 14 + rng.uniform(-4, 4)
        bank_pts.append((x, river_y + wave))
    bank_pts.append((w, h))
    draw.polygon(bank_pts, fill=(96, 90, 68, 255))

    water_pts = [(0, h)]
    for x in range(0, w + 40, 40):
        wave = math.sin(x * 0.012 + seed) * 14 + 26
        water_pts.append((x, river_y + wave))
    water_pts.append((w, h))
    draw.polygon(water_pts, fill=(56, 94, 104, 245))
    for _ in range(18):
        rx = rng.randint(20, w - 20)
        ry = rng.randint(int(river_y + 34), h - 10)
        draw.line([(rx - 18, ry), (rx + 18, ry)], fill=(122, 168, 174, 110), width=2)

    road_mid = (rows * 0.48) * cell
    road_half = cell * 1.45
    top_edge, bot_edge = [], []
    for x in range(0, w + 35, 35):
        curve = math.sin(x * 0.0055 + 0.6) * (cell * 0.35)
        top_edge.append((x, road_mid + curve - road_half))
        bot_edge.append((x, road_mid + curve + road_half))
    road_poly = top_edge + list(reversed(bot_edge))
    draw.polygon(road_poly, fill=(134, 112, 82, 255))

    def _road_detail(d: ImageDraw.ImageDraw) -> None:
        inner_top = [(x, y + 18) for x, y in top_edge]
        inner_bot = [(x, y - 18) for x, y in bot_edge]
        d.polygon(inner_top + list(reversed(inner_bot)), fill=(148, 126, 94, 160))
        rut1 = [(x, y + 34) for x, y in top_edge]
        rut2 = [(x, y - 34) for x, y in bot_edge]
        d.line(rut1, fill=(96, 76, 52, 145), width=8)
        d.line(rut2, fill=(96, 76, 52, 145), width=8)

    img = composite_soft_layer(img, _road_detail, blur_radius=4)
    draw = ImageDraw.Draw(img, "RGBA")

    for _ in range(45):
        px = rng.randint(10, w - 10)
        py = int(road_mid + rng.uniform(-road_half + 10, road_half - 10))
        draw.ellipse([px - 2, py - 2, px + 3, py + 2], fill=(104, 92, 76, 170))

    wag_c = max(6, cols // 2)
    wag_r = max(2, int(rows * 0.25))
    wx, wy = wag_c * cell + 8, wag_r * cell + 14
    ww, wh = int(cell * 1.9), int(cell * 0.95)
    draw.rectangle([wx + 5, wy + 7, wx + ww + 5, wy + wh + 7], fill=(18, 22, 14, 105))
    for w_x in (wx + 22, wx + ww - 22):
        draw.rectangle([w_x - 12, wy - 7, w_x + 12, wy + 2], fill=(74, 48, 28, 255), outline=(36, 22, 12, 255), width=1)
        draw.rectangle([w_x - 12, wy + wh - 2, w_x + 12, wy + wh + 7], fill=(74, 48, 28, 255), outline=(36, 22, 12, 255), width=1)
    draw.line([(wx, wy + 18), (wx - 32, wy + 24)], fill=(96, 66, 38, 255), width=4)
    draw.line([(wx, wy + wh - 18), (wx - 32, wy + wh - 24)], fill=(96, 66, 38, 255), width=4)
    draw.rectangle([wx, wy, wx + ww, wy + wh], fill=(138, 96, 56, 255), outline=(66, 42, 22, 255), width=2)
    for sx in range(wx + 16, wx + ww, 16):
        draw.line([(sx, wy + 2), (sx, wy + wh - 2)], fill=(92, 60, 32, 165), width=1)
    draw.rectangle([wx + 10, wy + 8, wx + ww * 0.58, wy + wh - 8], fill=(214, 202, 174, 245), outline=(146, 134, 108, 255), width=2)
    draw_crate(draw, wx + ww * 0.64, wy + 12, 32, 28, rng)
    draw_crate(draw, wx + ww + 12, wy + wh - 12, 28, 24, rng)
    draw_barrel(draw, wx + 28, wy + wh + 22, 13)

    blocker1 = (max(4, cols // 3), max(1, wag_r - 1))
    blocker2 = (min(cols - 4, int(cols * 0.72)), min(rows - 3, int(rows * 0.68)))
    blocked: set[tuple[int, int]] = {blocker1, blocker2}

    for bc, br in (blocker1, blocker2):
        bx, by = cell_center(bc, br, cell)
        draw_boulder_polygon(draw, bx, by, cell * 0.50, cell * 0.48, rng, base_rgb=(112, 114, 106), sides=11)
        draw_boulder_polygon(draw, bx - 4, by - 4, cell * 0.30, cell * 0.28, rng, base_rgb=(142, 144, 134), sides=8)
        draw_bush(draw, bx - 10, by - 8, 15, rng)

    bush_spots = [
        (2, 1), (4, 2), (cols - 4, 1), (cols - 2, 2), (cols - 3, 7),
        (3, rows - 3), (7, rows - 3), (cols - 6, 2),
    ]
    for bc, br in bush_spots:
        if (bc, br) in blocked:
            continue
        bx = (bc + rng.uniform(0.25, 0.75)) * cell
        by = (br + rng.uniform(0.25, 0.75)) * cell
        draw_bush(draw, bx, by, rng.uniform(20, 28), rng)

    for rc in range(1, cols - 1, 2):
        rx = (rc + rng.uniform(0.1, 0.9)) * cell
        ry = river_y + rng.uniform(4, 22)
        draw_bush(draw, rx, ry, rng.uniform(14, 20), rng, palette=((56, 78, 42), (82, 108, 56), (118, 138, 72)))

    for _ in range(5):
        rc = rng.randint(3, cols - 3)
        rr = rng.choice([1, 2, rows - 4, rows - 3])
        if (rc, rr) not in blocked:
            draw_boulder_polygon(draw, (rc + 0.5) * cell, (rr + 0.5) * cell, 16, 13, rng, base_rgb=(126, 124, 114), sides=7)

    img = add_grain(img, rng, strength=6)

    wb = WallBuilder(prefix, cell)
    wb.add_rect_grid(0, 0, cols, rows, "chain_outer")
    for idx, (bc, br) in enumerate((blocker1, blocker2), 1):
        wb.add_rect_grid(bc, br, bc + 1, br + 1, f"chain_rock_{idx}")

    l_col, l_row = wag_c + 1, wag_r + 1
    lx, ly = cell_center(l_col, l_row, cell)
    lamps_lit = lighting in ("dusk", "night")
    img = draw_lamp_prop(img, lx, ly, active_glow=lamps_lit, style="lamp")
    lights: dict[str, Any] = {
        f"light_{prefix}_001": {
            "id": f"light_{prefix}_001",
            "kind": "light",
            "x": lx,
            "y": ly,
            "emission": make_lamp_emission(3.0, 6.0, unit_dist, intensity=0.88),
            "activeBelowAmbient": 0.5,
        }
    }

    mid_r = int(round(rows * 0.45))
    pc_cells = [(2, mid_r), (2, mid_r + 1), (3, mid_r)]
    enemy_cells = [
        (min(cols - 3, wag_c + 3), mid_r),
        (min(cols - 2, wag_c + 4), mid_r + 1),
        (wag_c + 1, max(1, wag_r - 1)),
        (min(cols - 2, wag_c + 5), max(2, wag_r)),
        (min(cols - 2, wag_c + 5), min(rows - 3, mid_r + 2)),
        (wag_c, min(rows - 3, mid_r + 2)),
        (cols - 3, mid_r),
        (wag_c + 2, min(rows - 3, mid_r + 3)),
    ]

    pins = [
        {"label": "A", "name": "Muddy Track", "heading": "A. Muddy Wagon Track (West Entry)", "col": 2, "row": max(1, mid_r - 1)},
        {"label": "B", "name": "Halted Wagon", "heading": "B. Halted Wagon and Cover", "col": wag_c, "row": max(1, wag_r - 1)},
        {"label": "C", "name": "Riverbank Reeds", "heading": "C. Riverbank and Reeds", "col": min(cols - 3, wag_c + 4), "row": rows - 2},
    ]

    sections = [
        (
            "A. Muddy Wagon Track (West Entry)",
            [
                f"Rutted dirt road roughly `{fmt_dist(3, unit_dist, unit_type)}` wide with open sightlines eastward.",
                "Two tall mossy boulders off the road break line of sight and grant total cover behind them.",
            ],
        ),
        (
            "B. Halted Wagon and Cover",
            [
                "A merchant wagon stopped along the northern shoulder with crates and barrels spilled nearby (**half cover `+2 AC`**, or **three-quarters cover `+5 AC`** crouching behind the bed).",
                "A lantern hanging from the wagon automatically turns on at dusk or night.",
                f"⚡ `[Automatic Passive — {inv_name} (Inv. {inv_val})]` Fresh skid ruts in the mud immediately reveal the wagon braked sharply off the track.",
            ],
        ),
        (
            "C. Riverbank and Reeds",
            [
                "Tall reeds and shallow mud along the southern edge count as **difficult terrain** and **lightly obscured** areas for hiding.",
                "🎲 `[Active Roll — Perception DC 14]` To spot crouched silhouettes hidden among the reeds.",
            ],
        ),
    ]

    return {
        "image": img.convert("RGB"),
        "walls": wb.walls,
        "lights": lights,
        "pins": pins,
        "pc_cells": pc_cells,
        "enemy_cells": enemy_cells,
        "blocked_cells": blocked,
        "sections": sections,
        "grid_opacity": 0.40,
    }


def build_preset_hills(
    cols: int, rows: int, cell: int, lighting: str, seed: int, prefix: str,
    party: list[dict[str, Any]], unit_dist: float, unit_type: str,
) -> dict[str, Any]:
    rng = random.Random(seed)
    w, h = cols * cell, rows * cell
    perc_name, perc_val = best_passive_pc(party, "perception")

    img = Image.new("RGBA", (w, h), (108, 102, 82, 255))

    def _moor_mottle(d: ImageDraw.ImageDraw) -> None:
        for _ in range(cols * rows * 2):
            px, py = rng.randint(0, w), rng.randint(0, h)
            rx, ry = rng.randint(36, 92), rng.randint(24, 64)
            choice = rng.random()
            if choice < 0.45:
                col_p = (90 + rng.randint(-8, 8), 94 + rng.randint(-8, 8), 66 + rng.randint(-6, 6), 130)
            elif choice < 0.78:
                col_p = (134 + rng.randint(-10, 10), 126 + rng.randint(-10, 10), 106 + rng.randint(-10, 10), 125)
            else:
                col_p = (118 + rng.randint(-8, 8), 96 + rng.randint(-8, 8), 86 + rng.randint(-8, 8), 95)
            d.ellipse([px - rx, py - ry, px + rx, py + ry], fill=col_p)

    img = composite_soft_layer(img, _moor_mottle, blur_radius=20)
    draw = ImageDraw.Draw(img, "RGBA")

    for i in range(4):
        cy_line = int(h * (0.2 + i * 0.22))
        pts = [(x, cy_line + math.sin(x * 0.008 + i * 1.4 + seed) * 28) for x in range(0, w + 30, 30)]
        draw.line(pts, fill=(82, 76, 62, 85), width=2)
    for _ in range(cols * rows * 2):
        tx, ty = rng.randint(10, w - 10), rng.randint(10, h - 10)
        draw.line([(tx, ty), (tx - 2, ty - 4)], fill=(78, 76, 56, 110), width=1)
        draw.line([(tx, ty), (tx + 3, ty - 5)], fill=(128, 120, 94, 105), width=1)

    trail_pts = [
        (0, rows * 0.52 * cell),
        (cols * 0.25 * cell, rows * 0.54 * cell),
        (cols * 0.48 * cell, rows * 0.46 * cell),
        (cols * 0.65 * cell, rows * 0.48 * cell),
        (w, rows * 0.58 * cell),
    ]
    def _trail(d: ImageDraw.ImageDraw) -> None:
        d.line(trail_pts, fill=(142, 132, 108, 145), width=int(cell * 1.05), joint="curve")
    img = composite_soft_layer(img, _trail, blur_radius=10)
    draw = ImageDraw.Draw(img, "RGBA")

    outcrops = [
        (max(4, cols // 4 + 1), 2, max(6, cols // 4 + 3), 4),
        (max(6, cols // 2 - 1), max(rows - 4, 6), min(cols - 5, cols // 2 + 2), max(rows - 2, 8)),
        (min(cols - 4, int(cols * 0.78)), 3, min(cols - 2, int(cols * 0.78) + 2), 5),
    ]

    blocked: set[tuple[int, int]] = set()
    for c0, r0, c1, r1 in outcrops:
        for c in range(c0, c1):
            for r in range(r0, r1):
                blocked.add((c, r))

    def crag_polygon(x0: float, y0: float, x1: float, y1: float, inset: float, jitter: float) -> list[tuple[float, float]]:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rx, ry = (x1 - x0) / 2 - inset, (y1 - y0) / 2 - inset
        pts = []
        n = 14
        for i in range(n):
            ang = (2 * math.pi * i) / n
            ca, sa = math.cos(ang), math.sin(ang)
            sc = (abs(ca) ** 3.2 + abs(sa) ** 3.2) ** (-1.0 / 3.2)
            rad = rng.uniform(1.0 - jitter, 1.0 + jitter * 0.35)
            px = max(x0 - 2, min(x1 + 2, cx + ca * sc * rx * rad))
            py = max(y0 - 2, min(y1 + 2, cy + sa * sc * ry * rad))
            pts.append((px, py))
        return pts

    crag_shapes = [(c0, r0, c1, r1, crag_polygon(c0 * cell, r0 * cell, c1 * cell, r1 * cell, inset=3, jitter=0.14)) for (c0, r0, c1, r1) in outcrops]

    def _crag_shadow(d: ImageDraw.ImageDraw) -> None:
        for _, _, _, _, poly in crag_shapes:
            d.polygon([(px + 8, py + 10) for px, py in poly], fill=(16, 16, 14, 145))
    img = composite_soft_layer(img, _crag_shadow, blur_radius=7)
    draw = ImageDraw.Draw(img, "RGBA")

    for c0, r0, c1, r1, outer_poly in crag_shapes:
        x0, y0, x1, y1 = c0 * cell, r0 * cell, c1 * cell, r1 * cell
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        draw.polygon(outer_poly, fill=(104, 102, 94, 255), outline=(46, 44, 40, 255))
        mid_poly = [(cx + (px - cx) * 0.78 - 3, cy + (py - cy) * 0.78 - 3) for px, py in outer_poly]
        draw.polygon(mid_poly, fill=(138, 134, 122, 255), outline=(78, 76, 68, 220))
        top_poly = [(cx + (px - cx) * 0.52 - 5, cy + (py - cy) * 0.52 - 5) for px, py in outer_poly]
        draw.polygon(top_poly, fill=(168, 164, 150, 255), outline=(116, 112, 100, 200))
        for idx_p in (1, 5, 9, 12):
            draw.line([top_poly[idx_p], outer_poly[idx_p]], fill=(64, 62, 56, 185), width=2)
        draw.line([(cx - 18, cy + 4), (cx + 2, cy - 6), (cx + 22, cy + 8)], fill=(72, 70, 62, 190), width=2)
        draw_bush(draw, x0 + 22, y1 - 20, 12, rng, palette=((64, 72, 46), (86, 92, 58), (114, 104, 76)))

    men_c = min(cols - 6, max(outcrops[0][2] + 2, cols // 2 + 1))
    men_r = 4
    mx, my = cell_center(men_c, men_r, cell)
    draw.ellipse([mx - 30, my - 30, mx + 30, my + 30], fill=(124, 118, 102, 165), outline=(88, 84, 72, 220), width=2)
    draw.polygon([(mx - 6, my + 4), (mx + 14, my - 6), (mx + 38, my + 24), (mx + 16, my + 34)], fill=(20, 20, 18, 105))
    men_pts = [(mx - 15, my - 10), (mx + 2, my - 17), (mx + 16, my - 7), (mx + 12, my + 12), (mx - 6, my + 16), (mx - 17, my + 5)]
    draw.polygon(men_pts, fill=(148, 146, 138, 255), outline=(56, 54, 50, 255))
    draw.arc([mx - 8, my - 8, mx + 8, my + 8], 20, 310, fill=(74, 84, 88, 220), width=2)
    draw.ellipse([mx - 2, my - 2, mx + 2, my + 2], fill=(74, 84, 88, 220))

    for _ in range(16):
        sc = rng.randint(1, cols - 2)
        sr = rng.randint(1, rows - 2)
        if (sc, sr) in blocked or (sc, sr) == (men_c, men_r) or sc <= 3:
            continue
        sx = (sc + rng.uniform(0.25, 0.75)) * cell
        sy = (sr + rng.uniform(0.25, 0.75)) * cell
        if rng.random() < 0.55:
            draw_boulder_polygon(draw, sx, sy, rng.uniform(10, 16), rng.uniform(9, 14), rng, base_rgb=(136, 132, 120), sides=7)
        else:
            draw_bush(draw, sx, sy, rng.uniform(12, 18), rng, palette=((64, 72, 46), (86, 92, 58), (114, 104, 76)))

    img = add_grain(img, rng, strength=7)

    wb = WallBuilder(prefix, cell)
    wb.add_rect_grid(0, 0, cols, rows, "chain_outer")
    for idx, (c0, r0, c1, r1) in enumerate(outcrops, 1):
        wb.add_rect_grid(c0, r0, c1, r1, f"chain_crag_{idx}")

    fire_c = min(cols - 5, men_c + 1)
    fire_r = men_r + 1
    fx, fy = cell_center(fire_c, fire_r, cell)
    fire_lit = lighting in ("dusk", "night")
    img = draw_lamp_prop(img, fx, fy, active_glow=fire_lit, style="campfire")

    lights: dict[str, Any] = {}
    if lighting in ("dusk", "night"):
        lights[f"light_{prefix}_001"] = {
            "id": f"light_{prefix}_001",
            "kind": "light",
            "x": fx,
            "y": fy,
            "emission": make_lamp_emission(3.0, 6.0, unit_dist, kind="torch"),
            "activeBelowAmbient": 0.5,
        }

    mid_r = rows // 2
    pc_cells = [(2, mid_r - 1), (2, mid_r), (3, mid_r)]
    enemy_cells = [
        (fire_c + 1, fire_r - 1),
        (fire_c + 1, fire_r + 1),
        (fire_c, fire_r + 2),
        (men_c - 1, men_r - 1),
        (cols - 3, 5),
        (cols - 2, 6),
        (outcrops[0][2] + 1, 5),
        (outcrops[2][0] - 1, 2),
    ]

    pins = [
        {"label": "A", "name": "Moorland Trail", "heading": "A. Moorland Trail (West Entry)", "col": 2, "row": max(1, mid_r - 2)},
        {"label": "B", "name": "Ancient Menhir", "heading": "B. Ancient Menhir and Campfire", "col": men_c - 1, "row": men_r},
        {"label": "C", "name": "Limestone Crags", "heading": "C. Limestone Outcrops and Cover", "col": outcrops[1][0] + 1, "row": outcrops[1][1] - 1},
    ]

    sections = [
        (
            "A. Moorland Trail (West Entry)",
            [
                "Windswept footpath threading between dry heather and weathered limestone gravel.",
                "Sloping lanes around the crags allow flanking maneuvers without crossing the open center.",
            ],
        ),
        (
            "B. Ancient Menhir and Campfire",
            [
                f"Weathered standing stone carved with spiral motifs beside a stone firepit (`bright {fmt_dist(3, unit_dist, unit_type)} / dim {fmt_dist(6, unit_dist, unit_type)}` at dusk or night).",
                f"⚡ `[Automatic Passive — {perc_name} (Perc. {perc_val})]` The spiral carvings are centuries old, but the ash ring in the firepit is fresh.",
                "🎲 `[Active Roll — History or Religion DC 14]` To estimate the stone's age or identify its original purpose as a trail marker.",
            ],
        ),
        (
            "C. Limestone Outcrops and Cover",
            [
                "Three steep limestone crags block line of sight and dynamic lighting completely, carving natural ambush corridors.",
                "Smaller scattered boulders and scrub bushes provide **half cover (`+2 AC`)**.",
            ],
        ),
    ]

    return {
        "image": img.convert("RGB"),
        "walls": wb.walls,
        "lights": lights,
        "pins": pins,
        "pc_cells": pc_cells,
        "enemy_cells": enemy_cells,
        "blocked_cells": blocked,
        "sections": sections,
        "grid_opacity": 0.40,
    }


def build_preset_interior(
    cols: int, rows: int, cell: int, lighting: str, seed: int, prefix: str,
    party: list[dict[str, Any]], unit_dist: float, unit_type: str,
) -> dict[str, Any]:
    rng = random.Random(seed)
    w, h = cols * cell, rows * cell
    inv_name, inv_val = best_passive_pc(party, "investigation")

    b_x0 = 1
    b_y0 = 1
    b_y1 = rows - 1
    b_x1 = cols - 2
    back_w = max(3, min(4, cols // 4))
    part_x = max(b_x0 + 5, b_x1 - back_w)
    mid_r = rows // 2
    secret_r = max(b_y0 + 1, 2)

    img = Image.new("RGBA", (w, h), (48, 52, 58, 255))
    draw = ImageDraw.Draw(img, "RGBA")

    sw, sh = 18, 12
    for ri, sy in enumerate(range(0, h, sh)):
        off = (sw // 2) if (ri % 2) else 0
        for sx in range(-off, w, sw):
            v = rng.randint(-10, 10)
            draw.rectangle([sx + 1, sy + 1, sx + sw - 1, sy + sh - 1], fill=(64 + v, 67 + v, 74 + v, 255), outline=(36, 38, 44, 165), width=1)

    mx0, my0, mx1, my1 = b_x0 * cell, b_y0 * cell, part_x * cell, b_y1 * cell
    plank_h = 14
    for py in range(my0, my1, plank_h):
        dv = rng.randint(-9, 9)
        draw.rectangle([mx0, py, mx1, min(my1, py + plank_h)], fill=(154 + dv, 118 + dv, 80 + dv, 255), outline=(102, 74, 46, 160), width=1)
        for _ in range(2):
            sx = rng.randint(mx0 + 25, mx1 - 25)
            draw.line([(sx, py), (sx, min(my1, py + plank_h))], fill=(96, 70, 44, 175), width=1)

    bx0, by0, bx1, by1 = part_x * cell, b_y0 * cell, b_x1 * cell, b_y1 * cell
    for c in range(part_x, b_x1):
        for r in range(b_y0, b_y1):
            tx, ty = c * cell, r * cell
            dv = rng.randint(-8, 8)
            draw.rectangle([tx, ty, tx + cell, ty + cell], fill=(134 + dv, 128 + dv, 118 + dv, 255), outline=(92, 86, 78, 160), width=1)

    def _ao(d: ImageDraw.ImageDraw) -> None:
        d.rectangle([mx0, my0, bx1, by1], outline=(24, 20, 16, 110), width=16)
        d.line([(part_x * cell, my0), (part_x * cell, by1)], fill=(24, 20, 16, 110), width=14)
    img = composite_soft_layer(img, _ao, blur_radius=6)
    draw = ImageDraw.Draw(img, "RGBA")

    cnt_c0 = max(b_x0 + 4, part_x - 3)
    cnt_c1 = part_x - 1
    cx0, cy0, cx1, cy1 = cnt_c0 * cell + 6, (b_y0 + 1) * cell + 14, cnt_c1 * cell - 6, (b_y0 + 1) * cell + 46
    draw.rectangle([cx0 + 4, cy0 + 5, cx1 + 4, cy1 + 5], fill=(22, 16, 12, 95))
    draw.rectangle([cx0, cy0, cx1, cy1], fill=(116, 76, 42, 255), outline=(56, 34, 18, 255), width=2)
    draw.rectangle([cx0 + 4, cy0 + 4, cx1 - 4, cy1 - 4], outline=(148, 104, 62, 200), width=1)
    for sx in range(cx0 + 20, cx1 - 12, 34):
        draw.ellipse([sx - 8, cy1 + 8, sx + 8, cy1 + 24], fill=(128, 86, 48, 255), outline=(56, 36, 18, 255), width=2)

    def draw_table(tx0: float, ty0: float, tw: float, th: float) -> None:
        draw.rectangle([tx0 + 4, ty0 + 5, tx0 + tw + 4, ty0 + th + 5], fill=(20, 14, 10, 95))
        draw.rectangle([tx0, ty0, tx0 + tw, ty0 + th], fill=(128, 88, 52, 255), outline=(62, 38, 20, 255), width=2)
        draw.line([(tx0 + 3, ty0 + th / 2), (tx0 + tw - 3, ty0 + th / 2)], fill=(86, 56, 30, 150), width=1)
        for ch_x in (tx0 + tw * 0.28, tx0 + tw * 0.72):
            draw.rectangle([ch_x - 9, ty0 - 11, ch_x + 9, ty0 - 2], fill=(104, 68, 38, 255), outline=(48, 30, 16, 255), width=1)
            draw.rectangle([ch_x - 9, ty0 + th + 2, ch_x + 9, ty0 + th + 11], fill=(104, 68, 38, 255), outline=(48, 30, 16, 255), width=1)

    draw_table((b_x0 + 1) * cell + 12, (b_y0 + 1) * cell + 16, cell * 1.15, cell * 0.65)
    draw_table((part_x - 3) * cell + 14, (b_y1 - 2) * cell + 16, cell * 1.25, cell * 0.65)

    draw_crate(draw, bx0 + 14, by0 + 14, 34, 30, rng)
    draw_barrel(draw, bx0 + 62, by0 + 28, 14)
    draw_crate(draw, bx1 - 48, by1 - 54, 36, 34, rng)
    draw.rectangle([bx0 + 16, by1 - 56, bx0 + 82, by1 - 18], fill=(110, 74, 44, 255), outline=(52, 32, 18, 255), width=2)

    draw_barrel(draw, (b_x1 + 1) * cell + 28, (b_y1 - 2) * cell + 34, 14)
    draw_crate(draw, (b_x1 + 1) * cell + 14, (b_y1 - 1) * cell + 16, 32, 28, rng)

    pil_c = max(b_x0 + 3, (b_x0 + part_x) // 2 - 1)
    pil1 = (pil_c, max(b_y0 + 1, mid_r - 2))
    pil2 = (pil_c, min(b_y1 - 2, mid_r + 1))
    blocked: set[tuple[int, int]] = {pil1, pil2}

    for pc, pr in (pil1, pil2):
        px0, py0 = pc * cell, pr * cell
        draw.rectangle([px0 + 4, py0 + 5, px0 + cell + 2, py0 + cell + 3], fill=(16, 14, 12, 110))
        draw.rectangle([px0 + 2, py0 + 2, px0 + cell - 2, py0 + cell - 2], fill=(74, 70, 68, 255), outline=(40, 38, 36, 255), width=2)
        draw.rectangle([px0 + 12, py0 + 12, px0 + cell - 12, py0 + cell - 12], fill=(104, 96, 88, 255), outline=(142, 134, 124, 180), width=1)

    img = add_grain(img, rng, strength=5)
    draw = ImageDraw.Draw(img, "RGBA")

    wb = WallBuilder(prefix, cell)
    wb.add_rect_grid(0, 0, cols, rows, "chain_outer")
    wb.add_grid(b_x0, b_y0, b_x1, b_y0, "chain_bldg_n")
    wb.add_grid(b_x0, b_y1, b_x1, b_y1, "chain_bldg_s")
    wb.add_segmented_v(b_x0, b_y0, b_y1, "chain_bldg_w", doors={mid_r: ("door", True, False)})
    wb.add_segmented_v(part_x, b_y0, b_y1, "chain_part", doors={mid_r: ("door", True, False)})
    wb.add_segmented_v(b_x1, b_y0, b_y1, "chain_bldg_e", doors={secret_r: ("secret-door", True, False)})
    for idx, (pc, pr) in enumerate((pil1, pil2), 1):
        wb.add_rect_grid(pc, pr, pc + 1, pr + 1, f"chain_pil_{idx}")

    paint_grid_walls(draw, wb.walls, thickness=10)

    l1_col = min(part_x - 2, pil_c + 2)
    l1_row = mid_r - 1
    l2_col = part_x + 1
    l2_row = mid_r - 1
    l1x, l1y = cell_center(l1_col, l1_row, cell)
    l2x, l2y = cell_center(l2_col, l2_row, cell)
    img = draw_lamp_prop(img, l1x, l1y, active_glow=True, style="lamp")
    img = draw_lamp_prop(img, l2x, l2y, active_glow=True, style="lamp")

    lights = {
        f"light_{prefix}_001": {
            "id": f"light_{prefix}_001",
            "kind": "light",
            "x": l1x,
            "y": l1y,
            "emission": make_lamp_emission(3.0, 6.0, unit_dist),
        },
        f"light_{prefix}_002": {
            "id": f"light_{prefix}_002",
            "kind": "light",
            "x": l2x,
            "y": l2y,
            "emission": make_lamp_emission(2.0, 4.0, unit_dist, color="#ffb35c", intensity=0.85),
        },
    }

    pc_cells = [(b_x0 + 1, mid_r - 1), (b_x0 + 1, mid_r), (b_x0 + 1, mid_r + 1)]
    enemy_cells = [
        (part_x - 2, max(b_y0 + 2, mid_r - 2)),
        (part_x - 2, mid_r),
        (part_x - 2, min(b_y1 - 2, mid_r + 1)),
        (part_x + 1, max(b_y0 + 1, mid_r - 2)),
        (part_x + 1, min(b_y1 - 2, mid_r + 1)),
        (part_x - 3, min(b_y1 - 2, mid_r + 2)),
        (part_x + 1, mid_r),
        (b_x1, secret_r + 1),
    ]

    pins = [
        {"label": "A", "name": "Main Hall", "heading": "A. Main Hall and Counter", "col": b_x0 + 2, "row": mid_r},
        {"label": "B", "name": "Backroom", "heading": "B. Backroom and Secret Door", "col": part_x + 1, "row": min(b_y1 - 2, mid_r + 1)},
        {"label": "C", "name": "Service Alley", "heading": "C. Rear Service Alley (Escape Route)", "col": cols - 1, "row": secret_r},
    ]

    sections = [
        (
            "A. Main Hall and Counter",
            [
                "Versatile ground-floor interior (shop, tavern common room, or townhouse) with oak floorboards, counter, and two sturdy tables (**half cover `+2 AC`**).",
                "Two structural pillars cast dynamic shadows; both the west entrance door and the east partition door are **closed but unlocked**.",
            ],
        ),
        (
            "B. Backroom and Secret Door",
            [
                "Private storeroom with crates, writing desk, and a warm hanging lantern.",
                "**Secret door on the east wall** (invisible in Atlas VTT Player View until opened by the DM).",
                "🎲 `[Active Roll — Investigation or Perception DC 15]` To spot the concealed masonry panel opening into the rear service alley.",
            ],
        ),
        (
            "C. Rear Service Alley (Escape Route)",
            [
                "Cobblestone back alley ideal for stealthy infiltration, reinforcements, or a hasty getaway.",
                f"⚡ `[Automatic Passive — {inv_name} (Inv. {inv_val})]` Spots fresh scrape marks on the flagstones right beside the eastern exterior wall.",
            ],
        ),
    ]

    return {
        "image": img.convert("RGB"),
        "walls": wb.walls,
        "lights": lights,
        "pins": pins,
        "pc_cells": pc_cells,
        "enemy_cells": enemy_cells,
        "blocked_cells": blocked,
        "sections": sections,
        "grid_opacity": 0.40,
    }


PRESET_BUILDERS = {
    "whiteboard": build_preset_whiteboard,
    "alley": build_preset_alley,
    "road": build_preset_road,
    "hills": build_preset_hills,
    "interior": build_preset_interior,
}


# ---------------------------------------------------------------------------
# Token Placement, Note Generation & Scene Assembly
# ---------------------------------------------------------------------------

def cell_fits(col: int, row: int, size: int, cols: int, rows: int, blocked: set[tuple[int, int]], used: set[tuple[int, int]]) -> bool:
    if col < 0 or row < 0 or col + size > cols or row + size > rows:
        return False
    for dc in range(size):
        for dr in range(size):
            if (col + dc, row + dr) in blocked or (col + dc, row + dr) in used:
                return False
    return True


def reserve_cells(col: int, row: int, size: int, used: set[tuple[int, int]]) -> None:
    for dc in range(size):
        for dr in range(size):
            used.add((col + dc, row + dr))


def pick_cell(
    preferred: list[tuple[int, int]],
    size: int,
    cols: int,
    rows: int,
    blocked: set[tuple[int, int]],
    used: set[tuple[int, int]],
    prefer_east: bool = True,
) -> tuple[int, int]:
    for c, r in preferred:
        if cell_fits(c, r, size, cols, rows, blocked, used):
            reserve_cells(c, r, size, used)
            return c, r
    col_order = list(range(cols - 2, 0, -1)) if prefer_east else list(range(1, cols - 1))
    row_order = list(range(1, rows - 1))
    for c in col_order:
        for r in row_order:
            if cell_fits(c, r, size, cols, rows, blocked, used):
                reserve_cells(c, r, size, used)
                return c, r
    raise RuntimeError(f"No walkable grid cell available for token of size {size}")


def build_tokens(
    prefix: str,
    cols: int,
    rows: int,
    cell: int,
    lighting: str,
    include_pcs: bool,
    party: list[dict[str, Any]],
    unit_dist: float,
    pc_cells: list[tuple[int, int]],
    enemy_cells: list[tuple[int, int]],
    blocked: set[tuple[int, int]],
    enemies: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    tokens: dict[str, Any] = {}
    used: set[tuple[int, int]] = set()
    placed_enemies: list[dict[str, Any]] = []
    dark_mode = lighting in ("dusk", "night")
    torch_preset = make_torch_preset(unit_dist)
    seq = 1

    if include_pcs:
        for pc in party:
            c, r = pick_cell(pc_cells, 1, cols, rows, blocked, used, prefer_east=False)
            tx, ty = cell_center(c, r, cell, 1)
            tid = f"tok_{prefix}_{seq:03d}"
            hp_val = int(pc.get("hp", 20))
            tok: dict[str, Any] = {
                "id": tid,
                "assetId": pc.get("assetId", f"token-pc-{seq}"),
                "x": tx,
                "y": ty,
                "imagePath": pc.get("imagePath", DEFAULT_FALLBACK_TOKENS["default"]),
                "kind": "character",
                "name": pc["name"],
                "size": 1,
                "showRing": True,
                "playerCharacter": True,
                "vision": {"enabled": True},
                "layer": seq,
                "hp": {"current": hp_val, "max": hp_val},
            }
            if dark_mode and pc.get("torch_in_dark"):
                tok["light"] = dict(torch_preset)
            tokens[tid] = tok
            seq += 1

    for en in enemies:
        tsize = int(en.get("size") or 1)
        c, r = pick_cell(enemy_cells, tsize, cols, rows, blocked, used, prefer_east=True)
        tx, ty = cell_center(c, r, cell, tsize)
        tid = f"tok_{prefix}_{seq:03d}"
        tok = {
            "id": tid,
            "x": tx,
            "y": ty,
            "imagePath": en["imagePath"],
            "kind": "character",
            "name": en["name"],
            "size": tsize,
            "showRing": True,
            "instanceNumber": en["instanceNumber"],
            "layer": seq,
            "hp": {"current": en["hp"], "max": en["hp"]},
        }
        if en.get("statblockPath"):
            tok["statblockPath"] = en["statblockPath"]
        if en.get("difficulty"):
            tok["difficulty"] = en["difficulty"]
        tokens[tid] = tok
        placed_enemies.append({**en, "col": c, "row": r})
        seq += 1

    return tokens, placed_enemies


def build_pins(prefix: str, pin_specs: list[dict[str, Any]], note_rel: str, cell: int) -> dict[str, Any]:
    pins: dict[str, Any] = {}
    for idx, ps in enumerate(pin_specs, 1):
        px, py = cell_center(ps["col"], ps["row"], cell, 1)
        pid = f"pin_{prefix}_{idx:03d}"
        pins[pid] = {
            "id": pid,
            "kind": "pin",
            "x": px,
            "y": py,
            "notePath": f"{note_rel}#{ps['heading']}",
            "icon": "letter",
            "label": ps["label"],
            "name": ps["name"],
            "showName": True,
        }
    return pins


def render_dashboard_md(
    name: str,
    collection: str,
    preset: str,
    cols: int,
    rows: int,
    lighting: str,
    include_pcs: bool,
    party: list[dict[str, Any]],
    party_level: int,
    unit_dist: float,
    unit_type: str,
    sections: list[tuple[str, list[str]]],
    placed_enemies: list[dict[str, Any]],
) -> str:
    meta = PRESET_DEFAULTS[preset]
    torch_holders = [pc["name"] for pc in party if pc.get("torch_in_dark")]
    torch_note = f"{', '.join(torch_holders)} carrying torch" if torch_holders else "PC torch"
    light_labels = {
        "day": "Day (`ambient: 1.0`, dynamic line of sight active)",
        "dusk": f"Dusk (`ambient: 0.35`, {torch_note} and ambient lights active)",
        "night": f"Night (`ambient: 0.0`, {torch_note} and ambient lights active)",
    }
    lines: list[str] = [
        "---",
        f'title: "{name}"',
        f'icon: "{meta["icon"]}"',
        "tags: [atlas, dashboard, quick-battlemap]",
        f'collection: "{collection}"',
        f'preset: "{preset}"',
        f'lighting: "{lighting}"',
        'status: "draft"',
        "---",
        "",
        f"# {name}",
        "",
        f"{meta['subtitle']}",
        "",
        f"- **Dimensions:** `{cols}x{rows}` cells (`{fmt_dist(cols, unit_dist, unit_type)} x {fmt_dist(rows, unit_dist, unit_type)}`, `{fmt_dist(1, unit_dist, unit_type)}` per square).",
        f"- **Lighting:** {light_labels[lighting]}.",
        f"- **PC Tokens:** {format_party_links(party) + ' ready on the grid.' if include_pcs else 'Omitted (`--no-pcs`).'}",
        f"- **Party Passives (Lv. {party_level}):** {format_party_passives_line(party)}.",
        "",
        "---",
        "",
    ]

    for heading, bullets in sections:
        lines.append(f"### {heading}")
        for b in bullets:
            lines.append(f"- {b}")
        lines.append("")

    if placed_enemies:
        lines.extend([
            "---",
            "",
            "## Placed Enemies",
            "",
            "| Creature | Qty | HP | AC | CR | Statblock |",
            "| :--- | :---: | :---: | :---: | :---: | :--- |",
        ])
        grouped: dict[tuple[str, int, int, str, str], int] = {}
        for en in placed_enemies:
            key = (en["name"], en["hp"], en["ac"], en["cr"] or "-", en["statblockPath"])
            grouped[key] = grouped.get(key, 0) + 1
        for (en_name, hp, ac, cr, sb), qty in grouped.items():
            if sb.endswith(".md"):
                sb_no_ext = sb[:-3]
                link = f"[[{sb_no_ext}\\|{en_name}]]"
            else:
                link = "Ad hoc"
            lines.append(f"| {en_name} | {qty} | {hp} | {ac} | {cr} | {link} |")
        lines.append("")
    else:
        lines.extend([
            "---",
            "",
            "## Quick Table Use",
            "",
            "- Ready-to-play Wildcard scene with no fixed enemies: drag tokens from Atlas VTT's *Tokens* library or run `quick-battlemap` with `--enemies` to populate on demand.",
            "- Hold **`H`** (*Lighting Peek*) to preview player vision; press **`Tab`** to toggle this Linked Note.",
            "",
        ])

    return "\n".join(lines).rstrip() + "\n"


def self_validate(
    scene_data: dict[str, Any],
    dashboard_md: str,
    min_light_clearance: float = 25.0,
) -> list[str]:
    issues: list[str] = []
    st = scene_data["state"]
    objs = st["objects"]
    grid = st["grid"]
    lighting = st["lighting"]

    md_bytes = len(dashboard_md.encode("utf-8"))
    if md_bytes >= 30720:
        issues.append(f"Dashboard markdown too large ({md_bytes} bytes)")

    headings = set(re.findall(r"^###\s+(.+)$", dashboard_md, flags=re.MULTILINE))
    for pid, pin in objs["pins"].items():
        np_str = pin.get("notePath", "")
        if "#" in np_str:
            h = np_str.split("#", 1)[1]
            if h not in headings:
                issues.append(f"Pin {pid} heading missing in dashboard: #{h}")

    walls = list(objs["walls"].values())
    for lid, lt in objs["lights"].items():
        if walls:
            md = min(pt_seg_dist(lt["x"], lt["y"], w["p1"]["x"], w["p1"]["y"], w["p2"]["x"], w["p2"]["y"]) for w in walls)
            if md < min_light_clearance:
                issues.append(f"Light {lid} is only {md:.1f}px from a wall (< {min_light_clearance}px)")

    if lighting.get("enabled") and len(objs.get("fog") or {}) > 0:
        issues.append("Manual fog present alongside dynamic lighting")

    sz = grid["size"]
    ox, oy = grid["offsetX"], grid["offsetY"]
    for tid, tk in objs["tokens"].items():
        half = 0.5 * (tk.get("size") or 1)
        cx = (tk["x"] - ox) / sz - half
        cy = (tk["y"] - oy) / sz - half
        if abs(cx - round(cx)) > 0.01 or abs(cy - round(cy)) > 0.01:
            issues.append(f"Token {tid} ({tk.get('name')}) not snapped: ({cx:.2f}, {cy:.2f})")

    return issues


def sanitize_filename(name: str) -> str:
    clean = re.sub(r'[<>:"/\\|?*]+', "-", name).strip()
    return clean or "Quick Battlemap"


def sanitize_slug(slug: str) -> str:
    clean = re.sub(r"[^a-z0-9_]+", "_", slug.lower()).strip("_")
    return clean or "battlemap"


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="Generate procedural battlemaps & Atlas VTT 0.16.0 scenes (Quick Battlemap).")
    ap.add_argument("--preset", required=True, choices=sorted(PRESET_BUILDERS.keys()))
    ap.add_argument("--name", help="Scene name (e.g. 'Wildcard - Urban Alley')")
    ap.add_argument("--cols", type=int, help="Grid columns (min 10)")
    ap.add_argument("--rows", type=int, help="Grid rows (min 8)")
    ap.add_argument("--cell", type=int, default=70, help="Grid cell size in pixels (default 70)")
    ap.add_argument("--lighting", choices=["day", "dusk", "night"], help="Lighting mode")
    ap.add_argument("--enemies", default="", help="Enemies spec, e.g. 'Road Raider:2,Skeleton Sentry:1' or 'Wolf:3@11'")
    ap.add_argument("--seed", type=int, default=42, help="Deterministic RNG seed")
    ap.add_argument("--slug", help="Optional deterministic slug (e.g. 'wildcard_alley')")
    ap.add_argument("--collection", help="Atlas VTT collection override (default from campaign.config.json)")
    ap.add_argument("--vault", help="Vault root directory override (default from campaign.config.json)")
    ap.add_argument("--config", help="Optional path to campaign.config.json")
    ap.add_argument("--no-pcs", action="store_true", help="Omit party PC tokens")
    ap.add_argument("--dry-run", action="store_true", help="Simulate and validate without writing files")
    ap.add_argument("--out-dir", help="Alternative output vault directory for isolated tests")
    args = ap.parse_args(argv)

    cfg = load_runtime_config(pathlib.Path(args.config).resolve() if args.config else None)
    vault_dir = pathlib.Path(args.vault).resolve() if args.vault else cfg["vault_dir"]
    collection = args.collection or cfg["collection"]
    party = cfg["party"]
    fallbacks = cfg["fallback_tokens"]
    unit_type = cfg["grid_unit_type"]
    unit_dist = cfg["grid_unit_distance"]

    pdef = PRESET_DEFAULTS[args.preset]
    cols = max(10, args.cols if args.cols is not None else pdef["cols"])
    rows = max(8, args.rows if args.rows is not None else pdef["rows"])
    cell = max(50, args.cell)
    lighting = args.lighting or pdef["lighting"]
    scene_name = sanitize_filename(args.name or pdef["default_name"])

    ts = int(time.time() * 1000)
    if args.slug:
        slug = sanitize_slug(args.slug)
        map_stem = slug
        map_id = f"map-qb-{slug}"
        scene_id = f"scene-qb-{slug}"
        obj_prefix = slug
        record_tags = ["quick-battlemap", "wildcard"] if slug.startswith("wildcard") else ["quick-battlemap"]
    else:
        auto_slug = sanitize_slug(scene_name)[:24]
        map_stem = f"{auto_slug}_{ts}"
        map_id = f"map-{ts}-{auto_slug}"
        scene_id = f"scene-{ts}-{auto_slug}"
        obj_prefix = f"{auto_slug}_{ts % 100000}"
        record_tags = ["quick-battlemap"]

    map_asset_rel = f"atlas-vtt/assets/{map_stem}.webp"
    map_thumb_rel = f"atlas-vtt/assets/thumbnails/{map_stem}-thumb.webp"
    scene_rel = f"atlas-vtt/collections/{collection}/scenes/{scene_name}.atlasmap"
    note_rel = f"atlas-vtt/collections/{collection}/notes/{scene_name}.md"

    built = PRESET_BUILDERS[args.preset](cols, rows, cell, lighting, args.seed, obj_prefix, party, unit_dist, unit_type)
    monster_catalog = load_monster_catalog(vault_dir, collection, fallbacks)
    enemies_expanded = parse_enemies_spec(args.enemies, monster_catalog, fallbacks)

    tokens, placed_enemies = build_tokens(
        prefix=obj_prefix,
        cols=cols,
        rows=rows,
        cell=cell,
        lighting=lighting,
        include_pcs=not args.no_pcs,
        party=party,
        unit_dist=unit_dist,
        pc_cells=built["pc_cells"],
        enemy_cells=built["enemy_cells"],
        blocked=built["blocked_cells"],
        enemies=enemies_expanded,
    )
    pins = build_pins(obj_prefix, built["pins"], note_rel, cell)

    scene_data: dict[str, Any] = {
        "state": {
            "schema": "atlas-vtt",
            "version": 4,
            "mapPath": scene_rel,
            "background": map_asset_rel,
            "grid": {
                "enabled": True,
                "visible": True,
                "snapToGrid": True,
                "type": "square",
                "size": cell,
                "offsetX": 0,
                "offsetY": 0,
                "opacity": built["grid_opacity"],
                "lineType": "solid",
                "lineWidth": 1,
                "unitType": unit_type,
                "unitDistance": unit_dist,
                "measurementType": "units",
            },
            "objects": {
                "tokens": tokens,
                "fog": {},
                "pins": pins,
                "texts": {},
                "drawings": {},
                "walls": built["walls"],
                "lights": built["lights"],
                "lightZones": {},
                "audios": {},
            },
            "camera": {"x": 0, "y": 0, "scale": 1},
            "widgetValues": {},
            "widgetSettings": {"widgets": {}, "globalVisible": True, "position": "top", "scale": 1},
            "dmNotePath": note_rel,
            "tokenSettings": {
                "showNameplates": False,
                "hiddenResources": ["stress"],
                "showInstanceBadges": True,
                "tokenRingSize": 1,
                "showHPBars": True,
                "showStressBars": False,
            },
            "initiative": {"entries": [], "round": 1, "turn": 0, "active": False},
            "initiativeTrackerOpen": False,
            "diceLog": [],
            "pinnedNotePreviews": [],
            "lootRoller": {},
            "lighting": {
                "enabled": True,
                "ambient": LIGHTING_AMBIENT[lighting],
                "tokenVision": True,
                "exploredMemory": True,
            },
            "exploredMask": None,
        },
        "version": 4,
    }

    dashboard_md = render_dashboard_md(
        name=scene_name,
        collection=collection,
        preset=args.preset,
        cols=cols,
        rows=rows,
        lighting=lighting,
        include_pcs=not args.no_pcs,
        party=party,
        party_level=cfg["party_level"],
        unit_dist=unit_dist,
        unit_type=unit_type,
        sections=built["sections"],
        placed_enemies=placed_enemies,
    )

    issues = self_validate(scene_data, dashboard_md, min_light_clearance=25.0)
    if issues:
        for iss in issues:
            print(f"SELF-VALIDATION ERROR: {iss}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"[DRY-RUN] Scene '{scene_name}' (collection={collection}, preset={args.preset}, {cols}x{rows}, lighting={lighting}, seed={args.seed})")
        print(f"  Image size: {cols * cell}x{rows * cell} px -> {map_asset_rel}")
        print(f"  Walls: {len(built['walls'])} | Lights: {len(built['lights'])} | Pins: {len(pins)} | Tokens: {len(tokens)}")
        print(f"  Dashboard MD: {len(dashboard_md.encode('utf-8'))} bytes -> {note_rel}")
        for tk in tokens.values():
            role = "PC" if tk.get("playerCharacter") else "ENEMY"
            torch_flag = " [TORCH]" if tk.get("light") else ""
            print(f"    - [{role}] {tk['name']} ({tk['hp']['max']} HP) @ ({tk['x']}, {tk['y']}) img={tk['imagePath']} sb={tk.get('statblockPath', '-')}{torch_flag}")
        print("[DRY-RUN] Self-validation PASSED (0 issues).")
        return 0

    root_vault = pathlib.Path(args.out_dir).resolve() if args.out_dir else vault_dir
    atlas_root = root_vault / "atlas-vtt"
    col_root = atlas_root / "collections" / collection
    assets_dir = atlas_root / "assets"
    thumbs_dir = assets_dir / "thumbnails"
    scenes_dir = col_root / "scenes"
    maps_dir = col_root / "maps"
    notes_dir = col_root / "notes"
    for d in (assets_dir, thumbs_dir, scenes_dir, maps_dir, notes_dir):
        d.mkdir(parents=True, exist_ok=True)

    im: Image.Image = built["image"]
    im_path = assets_dir / f"{map_stem}.webp"
    im.save(im_path, "WEBP", quality=90)

    thumb_webp = im.copy()
    thumb_webp.thumbnail((300, 300), Image.Resampling.LANCZOS)
    thumb_webp_path = thumbs_dir / f"{map_stem}-thumb.webp"
    thumb_webp.save(thumb_webp_path, "WEBP", quality=82)

    thumb_jpg = im.copy()
    thumb_jpg.thumbnail((360, 360), Image.Resampling.LANCZOS)
    thumb_jpg_path = scenes_dir / f"{scene_name}.thumb.jpg"
    thumb_jpg.save(thumb_jpg_path, "JPEG", quality=85)

    atlasmap_path = scenes_dir / f"{scene_name}.atlasmap"
    atlasmap_path.write_text(json.dumps(scene_data, ensure_ascii=False, indent=2), encoding="utf-8")

    map_record = {
        "id": map_id,
        "name": scene_name,
        "mapFilePath": map_asset_rel,
        "tags": record_tags,
        "collection": collection,
        "createdAt": ts,
        "modifiedAt": ts,
        "atlasRecord": {
            "format": 1,
            "type": "map",
            "name": scene_name,
            "mapFilePath": map_asset_rel,
            "collection": collection,
            "tags": record_tags,
            "thumbnailPath": map_thumb_rel,
            "id": map_id,
            "createdAt": ts,
            "modifiedAt": ts,
        },
    }
    map_json_path = maps_dir / f"{map_id}.json"
    map_json_path.write_text(json.dumps(map_record, ensure_ascii=False, indent=2), encoding="utf-8")

    scene_record = {
        "mapPath": scene_rel,
        "atlasRecord": {
            "format": 1,
            "type": "scene",
            "name": scene_name,
            "collection": collection,
            "tags": record_tags,
            "id": scene_id,
            "createdAt": ts,
            "modifiedAt": ts,
        },
    }
    scene_json_path = scenes_dir / f"{scene_id}.json"
    scene_json_path.write_text(json.dumps(scene_record, ensure_ascii=False, indent=2), encoding="utf-8")

    note_path = notes_dir / f"{scene_name}.md"
    note_path.write_text(dashboard_md, encoding="utf-8")

    print(f"Generated '{scene_name}' (collection={collection}, preset={args.preset}, {cols}x{rows}, lighting={lighting}, tokens={len(tokens)}, walls={len(built['walls'])}, lights={len(built['lights'])})")
    print(f"  Scene:     {atlasmap_path}")
    print(f"  SceneRec:  {scene_json_path}")
    print(f"  MapRec:    {map_json_path}")
    print(f"  MapWebP:   {im_path}")
    print(f"  NoteMD:    {note_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
