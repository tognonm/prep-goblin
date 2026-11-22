#!/usr/bin/env python3
"""60-second Campaign Setup Wizard for Prep Goblin (Obsidian + Atlas VTT 0.16.0).

Supports both interactive prompts and full `--non-interactive` CLI flags for
automation and isolated testing.

Example (non-interactive):
    python scripts/init_campaign.py \\
      --name "Crimson Frontier" \\
      --vault-dir "Vault" \\
      --collection "Crimson Frontier" \\
      --units feet \\
      --party-level 1 \\
      --party "Lyra:Cleric:11:14:10:15:torch,Theron:Rogue:10:12:15:11,Garrick:Fighter:13:11:9:10" \\
      --with-wildcards \\
      --non-interactive
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_VAULT = REPO_ROOT / "template-vault"
BASE_CONFIG_PATH = REPO_ROOT / "campaign.config.json"
BASE_AGENTS_PATH = REPO_ROOT / "AGENTS.md"
QUICK_BATTLEMAP_SCRIPT = (
    REPO_ROOT / ".agents" / "skills" / "quick-battlemap" / "scripts" / "quick_battlemap.py"
)

TEMPLATE_CAMPAIGN_UUID = "00000000-0000-4000-8000-000000000001"
DEMO_PC_NOTES = ("Mira the Cleric.md", "Kael the Rogue.md", "Bram the Fighter.md")
DEMO_PC_TOKEN_FILES = ("token-demo-mira.json", "token-demo-kael.json", "token-demo-bram.json")

WILDCARD_SPECS: list[tuple[str, str, str, str, int]] = [
    ("whiteboard", "Wildcard - Tactical Whiteboard", "wildcard_whiteboard", "day", 101),
    ("alley", "Wildcard - Urban Alley", "wildcard_alley", "dusk", 102),
    ("road", "Wildcard - Country Road", "wildcard_road", "day", 103),
    ("hills", "Wildcard - Rocky Hills", "wildcard_hills", "dusk", 104),
    ("interior", "Wildcard - Building Interior", "wildcard_interior", "night", 105),
    ("camp", "Wildcard - Forest Camp", "wildcard_camp", "night", 106),
    ("bridge", "Wildcard - Stone Bridge", "wildcard_bridge", "day", 107),
    ("crypt", "Wildcard - Forgotten Crypt", "wildcard_crypt", "night", 108),
]

TOKEN_PALETTES: list[tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]] = [
    # (center_rgb, edge_rgb, accent_rgb) — rich dark-fantasy jewel tones
    ((46, 86, 138), (18, 28, 48), (226, 192, 118)),   # Sapphire & Gold
    ((136, 44, 52), (46, 16, 22), (232, 196, 126)),   # Crimson & Brass
    ((40, 108, 74), (16, 38, 28), (222, 194, 120)),   # Emerald & Antique Gold
    ((96, 54, 126), (32, 18, 46), (226, 196, 136)),   # Amethyst & Silver-Gold
    ((142, 88, 36), (48, 28, 14), (242, 212, 138)),   # Amber & Warm Gold
    ((38, 102, 114), (14, 34, 42), (224, 196, 132)),  # Deep Teal & Bronze
]

ROLE_ICONS: list[tuple[tuple[str, ...], str]] = [
    (("cleric", "priest", "healer", "oracle"), "✨"),
    (("rogue", "thief", "assassin", "scout"), "🗡️"),
    (("fighter", "warrior", "knight", "soldier"), "🛡️"),
    (("paladin", "templar", "crusader"), "⚔️"),
    (("wizard", "mage", "sorcerer", "warlock", "arcanist", "artificer"), "🔮"),
    (("ranger", "hunter", "archer"), "🏹"),
    (("bard", "skald", "minstrel"), "🎵"),
    (("druid", "shaman", "warden"), "🌿"),
    (("barbarian", "berserker"), "🪓"),
    (("monk", "mystic"), "🥋"),
]


# ---------------------------------------------------------------------------
# Sanitization & Formatting Helpers
# ---------------------------------------------------------------------------

def sanitize_filename(name: str, fallback: str = "Campaign") -> str:
    clean = re.sub(r'[<>:"/\\|?*]+', "-", name).strip().strip(".")
    return clean or fallback


def to_posix_rel(path_str: str) -> str:
    """Normalize a relative vault or asset path to POSIX forward slashes."""
    normalized = path_str.replace("\\", "/").strip()
    normalized = re.sub(r"/+", "/", normalized).strip("/")
    return normalized


def yaml_quote(value: str) -> str:
    """Safely double-quote a scalar string for YAML frontmatter."""
    return json.dumps(value, ensure_ascii=False)


def slugify_underscore(text: str, fallback: str = "pc") -> str:
    ascii_only = text.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_only).strip("_")
    return slug or fallback


def slugify_hyphen(text: str, fallback: str = "campaign") -> str:
    ascii_only = text.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    return slug or fallback


def pick_role_icon(role: str) -> str:
    lower = role.lower()
    for keywords, emoji in ROLE_ICONS:
        if any(k in lower for k in keywords):
            return emoji
    return "🧭"


def pc_wikilink(pc: dict[str, Any], escape_pipe: bool = False) -> str:
    note = str(pc.get("note") or pc["name"])
    name = str(pc["name"])
    if note == name:
        return f"[[{name}]]"
    sep = "\\|" if escape_pipe else "|"
    return f"[[{note}{sep}{name}]]"


def parse_bool_flag(raw: str) -> bool:
    val = raw.strip().lower()
    if val in {"torch", "true", "1", "yes", "y", "light"}:
        return True
    if val in {"", "false", "0", "no", "n", "none", "-"}:
        return False
    raise ValueError(f"Unrecognized torch flag '{raw}'. Expected 'torch', 'true', or 'false'.")


def normalize_party_entries(raw_party: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not raw_party:
        raise ValueError("Party list cannot be empty.")

    normalized: list[dict[str, Any]] = []
    used_slugs: set[str] = set()

    for idx, entry in enumerate(raw_party, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"Party entry #{idx} must be a JSON object.")
        name = str(entry.get("name") or "").strip()
        if not name:
            raise ValueError(f"Party entry #{idx} is missing a 'name'.")

        role = str(entry.get("role") or "Adventurer").strip() or "Adventurer"
        note = sanitize_filename(str(entry.get("note") or name).strip(), fallback=f"PC {idx}")

        base_slug = slugify_underscore(name, fallback=f"pc_{idx}")
        slug = base_slug
        suffix = 2
        while slug in used_slugs:
            slug = f"{base_slug}_{suffix}"
            suffix += 1
        used_slugs.add(slug)

        hp = max(1, int(entry.get("hp", 10)))
        passives_in = entry.get("passives") if isinstance(entry.get("passives"), dict) else {}
        perc = int(passives_in.get("perception", entry.get("perception", 10)))
        inv = int(passives_in.get("investigation", entry.get("investigation", 10)))
        ins = int(passives_in.get("insight", entry.get("insight", 10)))

        raw_torch = entry.get("torch_in_dark", False)
        torch = raw_torch if isinstance(raw_torch, bool) else parse_bool_flag(str(raw_torch))

        asset_id = str(entry.get("assetId") or f"token-pc-{slug}").strip()
        image_path = to_posix_rel(
            str(entry.get("imagePath") or f"atlas-vtt/assets/token_pc_{slug}.webp").strip()
        )

        normalized.append(
            {
                "name": name,
                "note": note,
                "role": role,
                "assetId": asset_id,
                "imagePath": image_path,
                "hp": hp,
                "torch_in_dark": torch,
                "passives": {
                    "perception": perc,
                    "investigation": inv,
                    "insight": ins,
                },
            }
        )
    return normalized


def parse_party_spec(spec: str) -> list[dict[str, Any]]:
    """Parse `--party "Name:Role:HP:Perc:Inv:Ins[:torch],..."` into normalized PCs."""
    raw_entries: list[dict[str, Any]] = []
    for chunk in re.split(r"[,;]+", spec):
        item = chunk.strip()
        if not item:
            continue
        parts = [p.strip() for p in item.split(":")]
        if len(parts) not in (6, 7):
            raise ValueError(
                f"Invalid --party item '{item}'. Expected 'Name:Role:HP:Perc:Inv:Ins[:torch]'."
            )
        name, role, hp_s, perc_s, inv_s, ins_s = parts[:6]
        torch = parse_bool_flag(parts[6]) if len(parts) == 7 else False
        try:
            hp = int(hp_s)
            perc = int(perc_s)
            inv = int(inv_s)
            ins = int(ins_s)
        except ValueError as exc:
            raise ValueError(
                f"HP and passive scores must be integers in '{item}'."
            ) from exc

        raw_entries.append(
            {
                "name": name,
                "note": name,
                "role": role,
                "hp": hp,
                "torch_in_dark": torch,
                "passives": {
                    "perception": perc,
                    "investigation": inv,
                    "insight": ins,
                },
            }
        )
    return normalize_party_entries(raw_entries)


def parse_party_json(raw_arg: str) -> list[dict[str, Any]]:
    """Load party entries from a JSON file path or raw JSON string."""
    candidate = Path(raw_arg)
    if candidate.is_file():
        data = json.loads(candidate.read_text(encoding="utf-8"))
    else:
        data = json.loads(raw_arg)

    if isinstance(data, dict) and isinstance(data.get("party"), list):
        raw_list = data["party"]
    elif isinstance(data, list):
        raw_list = data
    else:
        raise ValueError("--party-json must be a JSON array of PCs or an object containing 'party'.")

    return normalize_party_entries(raw_list)


def load_base_config() -> dict[str, Any]:
    if BASE_CONFIG_PATH.is_file():
        return json.loads(BASE_CONFIG_PATH.read_text(encoding="utf-8"))
    return {
        "campaign_name": "{{CAMPAIGN_NAME}}",
        "vault_dir": "template-vault",
        "atlas_collection": "Campaign",
        "atlas_campaign_slug": "campaign",
        "atlas_campaign_id": TEMPLATE_CAMPAIGN_UUID,
        "grid_unit_type": "feet",
        "grid_unit_distance": 5,
        "party_level": 3,
        "party": [],
        "fallback_tokens": {
            "default": "atlas-vtt/assets/token_generic_fighter.webp",
            "scout": "atlas-vtt/assets/token_generic_scout.webp",
            "arcane": "atlas-vtt/assets/token_generic_arcane.webp",
        },
        "roll_table_presets": {},
    }


# ---------------------------------------------------------------------------
# Monogram WebP Token Generator (Pillow)
# ---------------------------------------------------------------------------

def monogram_letters(name: str) -> str:
    words = [w for w in re.split(r"[\s\-_]+", name.strip()) if w]
    if len(words) >= 2:
        letters = f"{words[0][0]}{words[1][0]}"
    elif words:
        letters = words[0][:2]
    else:
        letters = "PC"
    return letters.upper()


def load_monogram_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    font_candidates = [
        "Georgia Bold.ttf",
        "georgiab.ttf",
        "DejaVuSerif-Bold.ttf",
        "DejaVuSans-Bold.ttf",
        "arialbd.ttf",
        "LiberationSerif-Bold.ttf",
        "LiberationSans-Bold.ttf",
    ]
    for font_name in font_candidates:
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def generate_monogram_token(
    name: str,
    role: str,
    palette_index: int,
    image_dest: Path,
    thumb_dest: Path,
) -> None:
    """Create a crisp 400x400 dark-fantasy monogram WebP token + 128x128 thumbnail."""
    size = 400
    center_rgb, edge_rgb, accent_rgb = TOKEN_PALETTES[palette_index % len(TOKEN_PALETTES)]

    img = Image.new("RGBA", (size, size), (*edge_rgb, 255))
    cx = cy = size / 2.0
    max_r = math.hypot(cx, cy)

    # Radial vignette background filling the full 1:1 square (no outer circular frame)
    pixels = img.load()
    for y in range(size):
        dy = y - cy
        for x in range(size):
            dx = x - cx
            t = min(1.0, math.hypot(dx, dy) / max_r)
            blend = t ** 1.35
            r = int(center_rgb[0] * (1.0 - blend) + edge_rgb[0] * blend)
            g = int(center_rgb[1] * (1.0 - blend) + edge_rgb[1] * blend)
            b = int(center_rgb[2] * (1.0 - blend) + edge_rgb[2] * blend)
            pixels[x, y] = (r, g, b, 255)

    draw = ImageDraw.Draw(img, "RGBA")

    # Subtle inner heraldic medallion ring (kept well inside the square so Atlas ring fits cleanly)
    pad = 44
    draw.ellipse(
        [pad, pad, size - pad, size - pad],
        outline=(*accent_rgb, 180),
        width=4,
    )
    draw.ellipse(
        [pad + 10, pad + 10, size - pad - 10, size - pad - 10],
        outline=(*accent_rgb, 80),
        width=2,
    )

    letters = monogram_letters(name)
    font = load_monogram_font(148)
    bbox = draw.textbbox((0, 0), letters, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) / 2.0 - bbox[0]
    ty = (size - th) / 2.0 - bbox[1] - 12

    # Drop shadow + gold-ivory lettering
    draw.text((tx + 4, ty + 5), letters, font=font, fill=(10, 12, 16, 170))
    draw.text((tx, ty), letters, font=font, fill=(246, 236, 208, 255))

    # Compact role subtitle below monogram
    role_label = role.strip().upper()[:14]
    if role_label:
        sub_font = load_monogram_font(26)
        sb = draw.textbbox((0, 0), role_label, font=sub_font)
        sw = sb[2] - sb[0]
        sx = (size - sw) / 2.0 - sb[0]
        sy = size - 104 - sb[1]
        draw.text((sx + 2, sy + 2), role_label, font=sub_font, fill=(10, 12, 16, 160))
        draw.text((sx, sy), role_label, font=sub_font, fill=(*accent_rgb, 235))

    image_dest.parent.mkdir(parents=True, exist_ok=True)
    thumb_dest.parent.mkdir(parents=True, exist_ok=True)

    rgb_img = img.convert("RGB")
    rgb_img.save(image_dest, "WEBP", quality=90)
    thumb_img = rgb_img.resize((128, 128), Image.Resampling.LANCZOS)
    thumb_img.save(thumb_dest, "WEBP", quality=85)


# ---------------------------------------------------------------------------
# Vault Customization Helpers
# ---------------------------------------------------------------------------

def render_pc_note(pc: dict[str, Any], party_level: int) -> str:
    icon = pick_role_icon(pc["role"])
    note_title = pc["note"]
    p = pc["passives"]
    light_text = (
        "Carries a torch in dark scenes (`torch_in_dark: true` in `campaign.config.json`)"
        if pc["torch_in_dark"]
        else "Standard vision / no default torch (`torch_in_dark: false`)"
    )
    return "\n".join(
        [
            "---",
            f"title: {yaml_quote(note_title)}",
            f"icon: {yaml_quote(icon)}",
            "tags: [player, pc]",
            'type: "Player Character"',
            f'class: {yaml_quote(pc["role"])}',
            f"level: {party_level}",
            f'passive_perception: {p["perception"]}',
            f'passive_investigation: {p["investigation"]}',
            f'passive_insight: {p["insight"]}',
            'status: "ready"',
            "---",
            "",
            f"# {icon} {note_title}",
            "",
            f'- **Level / Class:** {party_level} — {pc["role"]}',
            f'- **Max HP:** `{pc["hp"]}` | **Light Role:** {light_text}',
            f'- **Passives:** Perception **{p["perception"]}** | Investigation **{p["investigation"]}** | Insight **{p["insight"]}**',
            "",
            "## Personal Front & Bonds",
            "- **Goal:** *(Define personal objective before Session 1.)*",
            "- **Bond:** *(Link key NPCs, factions, or locations here.)*",
            "",
        ]
    )


def render_dm_screen_party_section(party: list[dict[str, Any]], party_level: int) -> str:
    max_perc = max(int(pc["passives"]["perception"]) for pc in party)
    max_inv = max(int(pc["passives"]["investigation"]) for pc in party)
    max_ins = max(int(pc["passives"]["insight"]) for pc in party)

    def fmt_score(val: int, top: int) -> str:
        return f"**{val}**" if val == top else str(val)

    lines = [
        f"## 👥 Party & Pre-Calculated Passives *(Lv. {party_level})*",
        "",
        "| PC | Role | Passive Perception | Passive Investigation | Passive Insight | Max HP |",
        "| :--- | :--- | :---: | :---: | :---: | :---: |",
    ]
    for pc in party:
        p = pc["passives"]
        role_cell = f'{pc["role"]} *(Torchbearer)*' if pc.get("torch_in_dark") else pc["role"]
        link = pc_wikilink(pc, escape_pipe=True)
        lines.append(
            f'| {link} | {role_cell} | {fmt_score(int(p["perception"]), max_perc)} '
            f'| {fmt_score(int(p["investigation"]), max_inv)} '
            f'| {fmt_score(int(p["insight"]), max_ins)} | {pc["hp"]} |'
        )
    lines.extend(
        [
            "",
            f"- **Active Roll Thresholds:** Perception **DC {max_perc + 1}+**, "
            f"Investigation **DC {max_inv + 1}+**, Insight **DC {max_ins + 1}+** "
            "(or any declared physical interaction).",
        ]
    )
    return "\n".join(lines)


def update_dm_screen(
    dm_screen_path: Path,
    campaign_name: str,
    collection: str,
    party: list[dict[str, Any]],
    party_level: int,
) -> None:
    if not dm_screen_path.is_file():
        return
    content = dm_screen_path.read_text(encoding="utf-8")
    content = content.replace("{{CAMPAIGN_NAME}}", campaign_name)
    content = content.replace("{{ATLAS_COLLECTION}}", collection)

    new_party_block = render_dm_screen_party_section(party, party_level)
    pattern = re.compile(
        r"^## 👥 Party & Pre-Calculated Passives.*?(?=\r?\n---\r?\n)",
        re.MULTILINE | re.DOTALL,
    )
    if pattern.search(content):
        content = pattern.sub(lambda _m: new_party_block, content, count=1)

    with dm_screen_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def update_collection_records(dest_vault: Path, collection: str) -> Path:
    collections_root = dest_vault / "atlas-vtt" / "collections"
    src_col_dir = collections_root / "Campaign"
    dst_col_dir = collections_root / collection

    if collection != "Campaign" and src_col_dir.is_dir():
        if dst_col_dir.exists():
            if os.path.samefile(src_col_dir, dst_col_dir):
                # Case-only rename on Windows/macOS case-insensitive filesystems
                tmp_dir = collections_root / f"_tmp_col_rename_{uuid.uuid4().hex[:8]}"
                src_col_dir.rename(tmp_dir)
                tmp_dir.rename(dst_col_dir)
            else:
                shutil.rmtree(dst_col_dir)
                src_col_dir.rename(dst_col_dir)
        else:
            src_col_dir.rename(dst_col_dir)

    col_json = dst_col_dir / "collection.json"
    if col_json.is_file():
        data = json.loads(col_json.read_text(encoding="utf-8"))
        data["id"] = collection
        data["name"] = collection
        col_json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    old_prefix = "atlas-vtt/collections/Campaign/"
    new_prefix = f"atlas-vtt/collections/{collection}/"

    for json_file in dst_col_dir.rglob("*"):
        if not json_file.is_file() or json_file.suffix not in {".json", ".atlasmap"}:
            continue
        if json_file == col_json:
            continue
        raw_text = json_file.read_text(encoding="utf-8")
        if collection != "Campaign":
            raw_text = raw_text.replace(old_prefix, new_prefix)
            try:
                parsed = json.loads(raw_text)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                if parsed.get("collection") == "Campaign":
                    parsed["collection"] = collection
                rec = parsed.get("atlasRecord")
                if isinstance(rec, dict) and rec.get("collection") == "Campaign":
                    rec["collection"] = collection
                raw_text = json.dumps(parsed, ensure_ascii=False, indent=2) + "\n"
        with json_file.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(raw_text)

    # Keep table documentation consistent with the renamed collection
    demo_table = dest_vault / "Tables" / "Demo Table - Quick Prompts and Encounters.md"
    if demo_table.is_file() and collection != "Campaign":
        txt = demo_table.read_text(encoding="utf-8").replace(
            "atlas-vtt/collections/Campaign/collection.json",
            f"atlas-vtt/collections/{collection}/collection.json",
        )
        with demo_table.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(txt)

    return dst_col_dir


def update_demo_scene_and_dashboard(
    col_dir: Path,
    collection: str,
    party: list[dict[str, Any]],
    party_level: int,
    unit_type: str,
    unit_distance: float,
    custom_party: bool,
) -> None:
    """Keep the included Demo - Oakhaven Alley scene & dashboard synced with config."""
    scene_path = col_dir / "scenes" / "Demo - Oakhaven Alley.atlasmap"
    note_path = col_dir / "notes" / "Demo - Oakhaven Alley.md"

    # 1. Update .atlasmap grid units, light radii, and (if custom_party) PC tokens
    if scene_path.is_file():
        scene = json.loads(scene_path.read_text(encoding="utf-8"))
        st = scene.get("state", {})
        grid = st.get("grid", {})
        old_unit_dist = float(grid.get("unitDistance") or 5.0)
        grid["unitType"] = unit_type
        grid["unitDistance"] = unit_distance

        scale = unit_distance / old_unit_dist if old_unit_dist > 0 else 1.0
        if abs(scale - 1.0) > 1e-6:
            for lt in (st.get("objects", {}).get("lights") or {}).values():
                em = lt.get("emission")
                if isinstance(em, dict):
                    for k in ("bright", "dim", "sourceRadius"):
                        if k in em and isinstance(em[k], (int, float)):
                            em[k] = round(float(em[k]) * scale, 2)

        tokens = st.get("objects", {}).get("tokens")
        if isinstance(tokens, dict):
            if custom_party:
                non_pc_tokens = {
                    tid: tk for tid, tk in tokens.items() if not tk.get("playerCharacter")
                }
                cell = int(grid.get("size") or 70)
                pc_spawn_cells = [(1, 6), (1, 7), (2, 6), (2, 7), (3, 6), (3, 7), (4, 6), (4, 7)]
                rebuilt_tokens: dict[str, Any] = {}
                layer = 1
                for idx, pc in enumerate(party):
                    col, row = pc_spawn_cells[idx % len(pc_spawn_cells)]
                    tid = f"tok_demo_oakhaven_alley_{idx + 1:03d}"
                    tok: dict[str, Any] = {
                        "id": tid,
                        "assetId": pc["assetId"],
                        "x": float((col + 0.5) * cell),
                        "y": float((row + 0.5) * cell),
                        "imagePath": pc["imagePath"],
                        "kind": "character",
                        "name": pc["name"],
                        "size": 1,
                        "showRing": True,
                        "playerCharacter": True,
                        "vision": {"enabled": True},
                        "layer": layer,
                        "hp": {"current": int(pc["hp"]), "max": int(pc["hp"])},
                    }
                    if pc.get("torch_in_dark"):
                        tok["light"] = {
                            "bright": round(4.0 * unit_distance, 2),
                            "dim": round(8.0 * unit_distance, 2),
                            "color": "#ff9a3c",
                            "intensity": 1,
                            "animation": "torch",
                            "sourceRadius": round(1.33 * unit_distance, 2),
                            "kind": "torch",
                            "preset": "dnd5e-torch",
                        }
                    rebuilt_tokens[tid] = tok
                    layer += 1
                for tid, tk in non_pc_tokens.items():
                    tk_copy = dict(tk)
                    tk_copy["layer"] = layer
                    rebuilt_tokens[tid] = tk_copy
                    layer += 1
                st["objects"]["tokens"] = rebuilt_tokens
            elif abs(scale - 1.0) > 1e-6:
                for tk in tokens.values():
                    lt = tk.get("light")
                    if isinstance(lt, dict):
                        for k in ("bright", "dim", "sourceRadius"):
                            if k in lt and isinstance(lt[k], (int, float)):
                                lt[k] = round(float(lt[k]) * scale, 2)

        scene_path.write_text(
            json.dumps(scene, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    # 2. Update Demo - Oakhaven Alley.md dashboard (collection, PC links, passives, units)
    if note_path.is_file():
        md = note_path.read_text(encoding="utf-8")
        md = re.sub(
            r'^collection:\s*"[^"]*"',
            lambda _m: f"collection: {yaml_quote(collection)}",
            md,
            count=1,
            flags=re.MULTILINE,
        )

        suffix = "m" if unit_type.startswith("m") else "ft"

        def fmt_d(cells: float) -> str:
            v = cells * unit_distance
            return f"{int(v)} {suffix}" if abs(v - round(v)) < 1e-6 else f"{v:.1f} {suffix}"

        dims_line = (
            f"- **Dimensions:** `16x12` cells (`{fmt_d(16)} x {fmt_d(12)}`, "
            f"`{fmt_d(1)}` per square)."
        )
        md = re.sub(
            r"^- \*\*Dimensions:\*\* .*$",
            lambda _m: dims_line,
            md,
            count=1,
            flags=re.MULTILINE,
        )

        torchbearers = [pc["name"] for pc in party if pc.get("torch_in_dark")]
        if torchbearers:
            tb_txt = ", ".join(torchbearers) + " carrying torch and ambient lights active"
        else:
            tb_txt = "ambient streetlamps active"
        lighting_line = f"- **Lighting:** Dusk (`ambient: 0.35`, {tb_txt})."
        md = re.sub(
            r"^- \*\*Lighting:\*\* .*$",
            lambda _m: lighting_line,
            md,
            count=1,
            flags=re.MULTILINE,
        )

        pc_links = ", ".join(pc_wikilink(pc) for pc in party)
        pc_tokens_line = f"- **PC Tokens:** {pc_links} ready on the grid."
        md = re.sub(
            r"^- \*\*PC Tokens:\*\* .*$",
            lambda _m: pc_tokens_line,
            md,
            count=1,
            flags=re.MULTILINE,
        )

        passives_chunks = [
            f"**{pc['name']}** Perc. `{pc['passives']['perception']}` / "
            f"Inv. `{pc['passives']['investigation']}` / Ins. `{pc['passives']['insight']}`"
            for pc in party
        ]
        passives_line = f"- **Party Passives (Lv. {party_level}):** {' | '.join(passives_chunks)}."
        md = re.sub(
            r"^- \*\*Party Passives \(Lv\. \d+\):\*\* .*$",
            lambda _m: passives_line,
            md,
            count=1,
            flags=re.MULTILINE,
        )

        # Convert body distances when metric units are selected (zero imperial drift)
        if unit_type == "meters":
            md = md.replace(
                "bright 15 ft / dim 30 ft",
                f"bright {fmt_d(3)} / dim {fmt_d(6)}",
            )
            md = md.replace("20 ft", fmt_d(4))
            md = md.replace("15 ft", fmt_d(3))

        best_pc = max(party, key=lambda item: int(item["passives"]["perception"]))
        best_perc = int(best_pc["passives"]["perception"])
        if best_perc >= 13:
            check_line = (
                f"- ⚡ `[Automatic Passive — {best_pc['name']} (Perc. {best_perc})]` "
                "Immediately spots stacked crates at the northwest corner of the junction "
                "offering ideal cover for a ranged attacker."
            )
        else:
            check_line = (
                "- 🎲 `[Active Roll — Perception DC 13]` Spots stacked crates at the northwest "
                "corner of the junction offering ideal cover for a ranged attacker."
            )
        md = re.sub(
            r"^- ⚡ `\[Automatic Passive — .*$",
            lambda _m: check_line,
            md,
            count=1,
            flags=re.MULTILINE,
        )

        with note_path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(md)


def update_demo_item_owner(dest_vault: Path, party: list[dict[str, Any]]) -> None:
    """Ensure Items/Lantern of Steady Flame.md points to an existing PC note."""
    item_path = dest_vault / "Items" / "Lantern of Steady Flame.md"
    if not item_path.is_file() or not party:
        return
    owner = next((pc for pc in party if pc.get("torch_in_dark")), party[0])
    content = item_path.read_text(encoding="utf-8")
    owner_note = str(owner["note"])
    owner_yaml = f"owner: {yaml_quote(f'[[{owner_note}]]')}"
    content = re.sub(
        r'^owner:\s*"\[\[[^\]]+\]\]"',
        lambda _m: owner_yaml,
        content,
        count=1,
        flags=re.MULTILINE,
    )
    content = content.replace("[[Mira the Cleric|Mira]]", pc_wikilink(owner))
    content = content.replace("[[Mira the Cleric]]", f'[[{owner["note"]}]]')
    with item_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def update_agents_governance(
    target_root: Path,
    campaign_name: str,
    collection: str,
    campaign_slug: str,
    campaign_id: str,
    party: list[dict[str, Any]],
    party_level: int,
) -> Path:
    agents_dest = target_root / "AGENTS.md"
    if agents_dest.is_file():
        content = agents_dest.read_text(encoding="utf-8")
    elif BASE_AGENTS_PATH.is_file():
        content = BASE_AGENTS_PATH.read_text(encoding="utf-8")
    else:
        raise FileNotFoundError(f"Base AGENTS.md not found at {BASE_AGENTS_PATH}")

    content = content.replace("{{CAMPAIGN_NAME}}", campaign_name)
    content = content.replace("{{ATLAS_COLLECTION}}", collection)
    content = content.replace("{{ATLAS_CAMPAIGN_SLUG}}", campaign_slug)
    content = content.replace(TEMPLATE_CAMPAIGN_UUID, campaign_id)

    passive_lines = [
        f"- **Party Passives (Level {party_level} — synced with `campaign.config.json`):**"
    ]
    for pc in party:
        p = pc["passives"]
        link = pc_wikilink(pc)
        passive_lines.append(
            f"  - **{link}:** Passive Perception **{p['perception']}** | "
            f"Passive Investigation **{p['investigation']}** | Passive Insight **{p['insight']}**"
        )
    replacement_block = "\n".join(passive_lines) + "\n"

    passives_re = re.compile(
        r"^- \*\*(?:Example )?Party Passives[^\n]*\r?\n(?:  - [^\n]*\r?\n)+",
        re.MULTILINE,
    )
    if passives_re.search(content):
        content = passives_re.sub(lambda _m: replacement_block, content, count=1)

    agents_dest.parent.mkdir(parents=True, exist_ok=True)
    with agents_dest.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    return agents_dest


def run_wildcards(
    dest_vault: Path,
    collection: str,
    config_path: Path,
) -> None:
    if not QUICK_BATTLEMAP_SCRIPT.is_file():
        raise FileNotFoundError(f"quick_battlemap.py not found at {QUICK_BATTLEMAP_SCRIPT}")

    print(
        f"\nGenerating {len(WILDCARD_SPECS)} Wildcard battlemap scenes via quick_battlemap.py...",
        flush=True,
    )
    for preset, scene_name, slug, lighting, seed in WILDCARD_SPECS:
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
            str(seed),
            "--config",
            str(config_path),
            "--vault",
            str(dest_vault),
            "--collection",
            collection,
            "--out-dir",
            str(dest_vault),
        ]
        subprocess.run(cmd, check=True)


# ---------------------------------------------------------------------------
# Main Campaign Initialization Workflow
# ---------------------------------------------------------------------------

def init_campaign(
    *,
    campaign_name: str,
    vault_dir_name: str,
    collection: str,
    units: str,
    party_level: int,
    party: list[dict[str, Any]],
    custom_party: bool,
    target_root: Path,
    with_wildcards: bool = False,
    update_governance: bool = True,
    force: bool = False,
) -> dict[str, Any]:
    if not TEMPLATE_VAULT.is_dir():
        raise FileNotFoundError(f"Starter template vault not found at {TEMPLATE_VAULT}")

    clean_name = campaign_name.strip() or "My Campaign"
    clean_vault_dir = to_posix_rel(vault_dir_name) or "Vault"
    clean_collection = sanitize_filename(collection.strip() or "Campaign", fallback="Campaign")
    unit_type = "meters" if units.lower().startswith("m") else "feet"
    unit_distance: int | float = 1.5 if unit_type == "meters" else 5
    level = max(1, int(party_level))

    target_root = target_root.resolve()
    target_root.mkdir(parents=True, exist_ok=True)
    dest_vault = (target_root / clean_vault_dir).resolve()

    if dest_vault == TEMPLATE_VAULT.resolve():
        raise ValueError(
            "Refusing to overwrite template-vault/ directly. Choose a different --vault-dir (e.g. 'Vault')."
        )

    if dest_vault.exists():
        if not force:
            raise FileExistsError(
                f"Target vault directory already exists: {dest_vault}\n"
                "Re-run with --force to overwrite it, or specify a different --vault-dir."
            )
        shutil.rmtree(dest_vault)

    # 1. Copy template-vault -> <target_root>/<vault_dir>
    shutil.copytree(
        TEMPLATE_VAULT,
        dest_vault,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "Thumbs.db"),
    )

    # 2. Rename Atlas collection directory and update collection references
    col_dir = update_collection_records(dest_vault, clean_collection)

    # 3. Fresh campaign UUID v4 and slug
    campaign_id = str(uuid.uuid4())
    campaign_slug = slugify_hyphen(clean_name, fallback="campaign")

    # 4. Player notes, monogram tokens, Atlas token JSONs, and characters.json
    players_dir = dest_vault / "Campaign" / "Players"
    players_dir.mkdir(parents=True, exist_ok=True)
    tokens_dir = col_dir / "tokens"
    tokens_dir.mkdir(parents=True, exist_ok=True)

    generated_monograms = 0
    if custom_party:
        for old_note in DEMO_PC_NOTES:
            p_old = players_dir / old_note
            if p_old.is_file():
                p_old.unlink()
        for old_tok in DEMO_PC_TOKEN_FILES:
            t_old = tokens_dir / old_tok
            if t_old.is_file():
                t_old.unlink()

        for idx, pc in enumerate(party):
            note_file = players_dir / f"{pc['note']}.md"
            with note_file.open("w", encoding="utf-8", newline="\n") as fh:
                fh.write(render_pc_note(pc, level))

            img_rel = to_posix_rel(pc["imagePath"])
            pc["imagePath"] = img_rel
            img_abs = dest_vault / img_rel
            img_stem = Path(img_rel).stem
            thumb_rel = to_posix_rel(f"atlas-vtt/assets/thumbnails/{img_stem}-thumb.webp")
            thumb_abs = dest_vault / thumb_rel

            if not img_abs.is_file():
                generate_monogram_token(pc["name"], pc["role"], idx, img_abs, thumb_abs)
                generated_monograms += 1
            elif not thumb_abs.is_file():
                thumb_abs.parent.mkdir(parents=True, exist_ok=True)
                with Image.open(img_abs) as src_im:
                    t_im = src_im.convert("RGB").resize((128, 128), Image.Resampling.LANCZOS)
                    t_im.save(thumb_abs, "WEBP", quality=85)

            token_record = {
                "atlasRecord": {
                    "format": 1,
                    "type": "token",
                    "id": pc["assetId"],
                    "name": pc["name"],
                    "collection": clean_collection,
                    "imagePath": img_rel,
                    "thumbnailPath": thumb_rel,
                    "showRing": True,
                    "playerCharacter": True,
                    "tags": ["pc", "party"],
                }
            }
            tok_file = tokens_dir / f"{pc['assetId']}.json"
            tok_file.write_text(
                json.dumps(token_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
    else:
        # Demo party kept: update level in existing demo notes if party_level differs
        for note_name in DEMO_PC_NOTES:
            p_note = players_dir / note_name
            if p_note.is_file():
                txt = p_note.read_text(encoding="utf-8")
                txt = re.sub(
                    r"^level:\s*\d+",
                    lambda _m: f"level: {level}",
                    txt,
                    count=1,
                    flags=re.MULTILINE,
                )
                txt = re.sub(
                    r"^- \*\*Level / Class:\*\* \d+ —",
                    lambda _m: f"- **Level / Class:** {level} —",
                    txt,
                    count=1,
                    flags=re.MULTILINE,
                )
                with p_note.open("w", encoding="utf-8", newline="\n") as fh:
                    fh.write(txt)

    # Write Atlas VTT campaigns/<slug>/characters.json
    campaigns_dir = dest_vault / "atlas-vtt" / "campaigns"
    old_campaign_dir = campaigns_dir / "campaign"
    new_campaign_dir = campaigns_dir / campaign_slug
    if campaign_slug != "campaign" and old_campaign_dir.is_dir():
        shutil.rmtree(old_campaign_dir)
    new_campaign_dir.mkdir(parents=True, exist_ok=True)

    characters_payload = {
        "campaignId": campaign_id,
        "campaignName": clean_name,
        "characters": [
            {
                "id": pc["assetId"],
                "name": pc["name"],
                "notePath": to_posix_rel(f"Campaign/Players/{pc['note']}.md"),
                "hp": {"current": int(pc["hp"]), "max": int(pc["hp"])},
            }
            for pc in party
        ],
    }
    characters_path = new_campaign_dir / "characters.json"
    characters_path.write_text(
        json.dumps(characters_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # 5. Replace placeholders and synchronize starter notes + demo scene
    update_dm_screen(dest_vault / "DM Screen.md", clean_name, clean_collection, party, level)

    world_state = dest_vault / "Campaign" / "World State.md"
    if world_state.is_file():
        ws_txt = world_state.read_text(encoding="utf-8")
        ws_txt = ws_txt.replace("{{CAMPAIGN_NAME}}", clean_name)
        ws_txt = ws_txt.replace("{{ATLAS_COLLECTION}}", clean_collection)
        ws_txt = re.sub(
            r"^- \*\*Party Level:\*\* `\d+`",
            lambda _m: f"- **Party Level:** `{level}`",
            ws_txt,
            count=1,
            flags=re.MULTILINE,
        )
        with world_state.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(ws_txt)

    for md_file in dest_vault.rglob("*.md"):
        txt = md_file.read_text(encoding="utf-8")
        updated = (
            txt.replace("{{CAMPAIGN_NAME}}", clean_name)
            .replace("{{ATLAS_COLLECTION}}", clean_collection)
            .replace("{{ATLAS_CAMPAIGN_SLUG}}", campaign_slug)
            .replace(TEMPLATE_CAMPAIGN_UUID, campaign_id)
        )
        if updated != txt:
            with md_file.open("w", encoding="utf-8", newline="\n") as fh:
                fh.write(updated)

    if custom_party:
        update_demo_item_owner(dest_vault, party)

    update_demo_scene_and_dashboard(
        col_dir=col_dir,
        collection=clean_collection,
        party=party,
        party_level=level,
        unit_type=unit_type,
        unit_distance=float(unit_distance),
        custom_party=custom_party,
    )

    # 6. Write campaign.config.json in target_root (normalized POSIX relative paths)
    cfg = copy.deepcopy(load_base_config())
    cfg["campaign_name"] = clean_name
    cfg["vault_dir"] = clean_vault_dir
    cfg["atlas_collection"] = clean_collection
    cfg["atlas_campaign_slug"] = campaign_slug
    cfg["atlas_campaign_id"] = campaign_id
    cfg["grid_unit_type"] = unit_type
    cfg["grid_unit_distance"] = unit_distance
    cfg["party_level"] = level
    cfg["party"] = party
    if isinstance(cfg.get("fallback_tokens"), dict):
        cfg["fallback_tokens"] = {
            str(k): to_posix_rel(str(v)) for k, v in cfg["fallback_tokens"].items()
        }

    config_dest = target_root / "campaign.config.json"
    config_dest.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    # 7. Update AGENTS.md in target_root when requested
    agents_dest: Path | None = None
    if update_governance:
        agents_dest = update_agents_governance(
            target_root=target_root,
            campaign_name=clean_name,
            collection=clean_collection,
            campaign_slug=campaign_slug,
            campaign_id=campaign_id,
            party=party,
            party_level=level,
        )

    # 8. Optional Wildcard scenes
    if with_wildcards:
        run_wildcards(
            dest_vault=dest_vault,
            collection=clean_collection,
            config_path=config_dest,
        )

    return {
        "campaign_name": clean_name,
        "vault_path": dest_vault,
        "collection": clean_collection,
        "campaign_slug": campaign_slug,
        "campaign_id": campaign_id,
        "units": unit_type,
        "unit_distance": unit_distance,
        "party_level": level,
        "party_count": len(party),
        "generated_monograms": generated_monograms,
        "config_path": config_dest,
        "characters_path": characters_path,
        "agents_path": agents_dest,
        "with_wildcards": with_wildcards,
    }


# ---------------------------------------------------------------------------
# Interactive Prompt Helpers
# ---------------------------------------------------------------------------

def prompt_text(label: str, default: str) -> str:
    raw = input(f"{label} [{default}]: ").strip()
    return raw if raw else default


def prompt_int(label: str, default: int, minimum: int = 1) -> int:
    while True:
        raw = input(f"{label} [{default}]: ").strip()
        if not raw:
            return default
        try:
            val = int(raw)
            if val >= minimum:
                return val
            print(f"Please enter an integer >= {minimum}.")
        except ValueError:
            print("Please enter a valid integer.")


def prompt_yes_no(label: str, default: bool = False) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{label} [{hint}]: ").strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("Please answer y or n.")


def prompt_party_interactive() -> list[dict[str, Any]]:
    print("\nEnter each Player Character (leave Name blank when finished):")
    entries: list[dict[str, Any]] = []
    idx = 1
    while True:
        name = input(f"  PC #{idx} Name (blank to finish): ").strip()
        if not name:
            if entries:
                break
            print("  Please enter at least one player character.")
            continue
        role = prompt_text(f"  {name} Class/Role", "Fighter")
        hp = prompt_int(f"  {name} Max HP", 12, minimum=1)
        perc = prompt_int(f"  {name} Passive Perception", 12, minimum=1)
        inv = prompt_int(f"  {name} Passive Investigation", 10, minimum=1)
        ins = prompt_int(f"  {name} Passive Insight", 10, minimum=1)
        torch = prompt_yes_no(f"  Does {name} carry a torch in dark scenes?", default=(idx == 1))
        entries.append(
            {
                "name": name,
                "note": name,
                "role": role,
                "hp": hp,
                "torch_in_dark": torch,
                "passives": {
                    "perception": perc,
                    "investigation": inv,
                    "insight": ins,
                },
            }
        )
        idx += 1
    return normalize_party_entries(entries)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Initialize a customized Prep Goblin campaign vault (interactive or --non-interactive)."
    )
    parser.add_argument("--name", help="Campaign name (e.g. 'Shadows of Oakhaven').")
    parser.add_argument(
        "--vault-dir",
        default="Vault",
        help="Target Obsidian vault folder name inside target root (default: 'Vault').",
    )
    parser.add_argument(
        "--collection",
        help="Atlas VTT collection name (default: 'Campaign').",
    )
    parser.add_argument(
        "--units",
        choices=("feet", "meters"),
        default="feet",
        help="Tactical grid distance units: 'feet' (5 ft) or 'meters' (1.5 m). Default: feet.",
    )
    parser.add_argument(
        "--party-level",
        type=int,
        default=1,
        help="Starting party level (default: 1).",
    )
    parser.add_argument(
        "--party-json",
        help="Custom party as a JSON string or path to a JSON file.",
    )
    parser.add_argument(
        "--party",
        help="Custom party shorthand: 'Name:Role:HP:Perc:Inv:Ins[:torch],...'.",
    )
    parser.add_argument(
        "--target-root",
        type=Path,
        default=None,
        help="Target root directory (defaults to the Prep Goblin repo root; useful for isolated testing).",
    )
    parser.add_argument(
        "--with-wildcards",
        action="store_true",
        help=f"Generate all {len(WILDCARD_SPECS)} Wildcard battlemap scenes via quick_battlemap.py.",
    )
    parser.add_argument(
        "--update-governance",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Update AGENTS.md with campaign name, collection, UUID, and party passives (default: enabled).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting an existing target vault directory.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run without interactive prompts using CLI flags and defaults.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.party and args.party_json:
        parser.error("Use either --party or --party-json, not both.")

    base_cfg = load_base_config()
    default_demo_party = copy.deepcopy(base_cfg.get("party") or [])

    if args.non_interactive:
        campaign_name = args.name or "My Campaign"
        vault_dir_name = args.vault_dir or "Vault"
        collection = args.collection or "Campaign"
        units = args.units
        party_level = max(1, args.party_level)
        with_wildcards = args.with_wildcards
        update_governance = args.update_governance

        if args.party_json:
            party = parse_party_json(args.party_json)
            custom_party = True
        elif args.party:
            party = parse_party_spec(args.party)
            custom_party = True
        else:
            party = normalize_party_entries(default_demo_party)
            custom_party = False
    else:
        print("=== Prep Goblin — 60-Second Campaign Setup Wizard ===\n")
        campaign_name = prompt_text("Campaign name", args.name or "Shadows of Oakhaven")
        vault_dir_name = prompt_text("Vault directory name", args.vault_dir or "Vault")
        collection = prompt_text("Atlas VTT collection name", args.collection or "Campaign")

        while True:
            units_in = prompt_text("Grid units (feet / meters)", args.units).lower()
            if units_in in {"feet", "ft", "meters", "m"}:
                units = "meters" if units_in in {"meters", "m"} else "feet"
                break
            print("Please enter 'feet' or 'meters'.")

        party_level = prompt_int("Starting party level", max(1, args.party_level), minimum=1)

        if args.party_json:
            party = parse_party_json(args.party_json)
            custom_party = True
        elif args.party:
            party = parse_party_spec(args.party)
            custom_party = True
        elif prompt_yes_no(
            "Configure custom Player Characters? (No keeps demo party Mira/Kael/Bram)",
            default=True,
        ):
            party = prompt_party_interactive()
            custom_party = True
        else:
            party = normalize_party_entries(default_demo_party)
            custom_party = False

        with_wildcards = (
            True
            if args.with_wildcards
            else prompt_yes_no(
                f"Generate the {len(WILDCARD_SPECS)} pre-built Wildcard battlemap scenes now?",
                default=False,
            )
        )
        update_governance = prompt_yes_no(
            "Update AGENTS.md with campaign name and party passives?",
            default=args.update_governance,
        )

    target_root = args.target_root.resolve() if args.target_root else REPO_ROOT

    try:
        result = init_campaign(
            campaign_name=campaign_name,
            vault_dir_name=vault_dir_name,
            collection=collection,
            units=units,
            party_level=party_level,
            party=party,
            custom_party=custom_party,
            target_root=target_root,
            with_wildcards=with_wildcards,
            update_governance=update_governance,
            force=args.force,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("\n=== Campaign Initialized Successfully ===")
    print(f"  Campaign:         {result['campaign_name']}")
    print(f"  Vault:            {result['vault_path']}")
    print(f"  Atlas Collection: {result['collection']}")
    print(f"  Campaign UUID:    {result['campaign_id']} (slug: {result['campaign_slug']})")
    print(f"  Grid Units:       {result['unit_distance']} {result['units']}")
    print(f"  Party:            {result['party_count']} PCs (Level {result['party_level']})")
    if result["generated_monograms"]:
        print(f"  Monogram Tokens:  {result['generated_monograms']} WebP tokens generated")
    print(f"  Config Written:   {result['config_path']}")
    print(f"  Characters JSON:  {result['characters_path']}")
    if result["agents_path"]:
        print(f"  Governance:       {result['agents_path']}")
    if result["with_wildcards"]:
        print(f"  Wildcards:        {len(WILDCARD_SPECS)} Wildcard battlemap scenes generated")

    print("\nNext steps:")
    print(f'  1. Verify links & Atlas: python scripts/lint_vault.py --vault "{result["vault_path"]}" --strict-links --full-atlas')
    print(f'  2. Open "{result["vault_path"]}" in Obsidian and enable Atlas VTT, Fantasy Statblocks, and Dice Roller.')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
