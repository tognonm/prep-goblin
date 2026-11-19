#!/usr/bin/env python3
"""CLI tools for visual analysis, verification, and validation of Atlas VTT 0.16.0 scenes."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[4]


def detect_default_vault(hint_path: str | None = None) -> Path:
    """Resolve the vault root from a hint path, campaign.config.json, or repo conventions."""
    if hint_path:
        p = Path(hint_path).resolve()
        for parent in [p, *p.parents]:
            if (parent / "atlas-vtt").is_dir():
                return parent
    cfg_path = REPO_ROOT / "campaign.config.json"
    if cfg_path.is_file():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            vdir = cfg.get("vault_dir")
            if vdir:
                cand = (REPO_ROOT / vdir).resolve()
                if cand.is_dir():
                    return cand
        except Exception:
            pass
    for name in ("Vault", "template-vault"):
        cand = REPO_ROOT / name
        if cand.is_dir():
            return cand
    return REPO_ROOT / "template-vault"


def load_font(size: int = 24):
    for name in ("arialbd.ttf", "arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def resolve_vault_path(rel_or_abs: str, vault_root: Path) -> str:
    if os.path.isabs(rel_or_abs) and os.path.exists(rel_or_abs):
        return rel_or_abs
    if os.path.exists(rel_or_abs):
        return os.path.abspath(rel_or_abs)
    candidate = vault_root / rel_or_abs.replace("/", os.sep)
    if candidate.exists():
        return str(candidate)
    return rel_or_abs


def pt_seg_dist(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return ((px - (x1 + t * dx)) ** 2 + (py - (y1 + t * dy)) ** 2) ** 0.5


def cmd_grid_preview(args) -> int:
    vault_root = Path(args.vault).resolve() if args.vault else detect_default_vault(args.source)
    size, ox, oy = args.size, args.ox, args.oy
    img_path = args.source
    if args.source.lower().endswith(".atlasmap"):
        src_path = resolve_vault_path(args.source, vault_root)
        with open(src_path, encoding="utf-8") as f:
            data = json.load(f)
        grid = data["state"].get("grid") or {}
        size = size or grid.get("size", 70)
        ox = grid.get("offsetX", 0) if ox is None else ox
        oy = grid.get("offsetY", 0) if oy is None else oy
        img_path = resolve_vault_path(data["state"]["background"], vault_root)
    else:
        size = size or 70
        ox = 0 if ox is None else ox
        oy = 0 if oy is None else oy
        img_path = resolve_vault_path(img_path, vault_root)

    im = Image.open(img_path).convert("RGBA")
    w, h = im.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = load_font(18)

    c, x = 0, ox
    while x < w:
        if x >= 0:
            draw.line([(x, 0), (x, h)], fill=(255, 255, 0, 100), width=1)
            if x + size <= w + 20:
                draw.text((x + 4, 4), str(c), fill=(255, 255, 0, 230), font=font)
        x += size
        c += 1

    r, y = 0, oy
    while y < h:
        if y >= 0:
            draw.line([(0, y), (w, y)], fill=(255, 255, 0, 100), width=1)
            if y + size <= h + 20:
                draw.text((4, y + 4), str(r), fill=(255, 255, 0, 230), font=font)
        y += size
        r += 1

    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    Image.alpha_composite(im, overlay).convert("RGB").save(args.out)
    print(f"Grid preview saved: {args.out} ({w}x{h}, size={size}, ox={ox}, oy={oy}, cols={c}, rows={r})")
    return 0


def cmd_detect_lights(args) -> int:
    vault_root = Path(args.vault).resolve() if args.vault else detect_default_vault(args.image)
    img_path = resolve_vault_path(args.image, vault_root)
    im = Image.open(img_path).convert("RGB")
    arr = np.array(im)
    h, w, _ = arr.shape
    R, G, B = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)

    masks = {
        "cyan": (B > 185) & (G > 145) & ((B - R) > 45),
        "amber": (R > 200) & (G > 110) & ((R - B) > 70),
        "emerald": (G > 180) & ((G - R) > 40) & ((G - B) > 30),
        "purple": (R > 150) & (B > 180) & ((R - G) > 35) & ((B - G) > 35),
    }
    mask = masks[args.color]
    visited = np.zeros((h, w), dtype=bool)
    clusters = []

    ys, xs = np.where(mask)
    for y0, x0 in zip(ys, xs):
        if visited[y0, x0]:
            continue
        q = deque([(int(y0), int(x0))])
        visited[y0, x0] = True
        pts = []
        while q:
            cy, cx = q.popleft()
            pts.append((cx, cy))
            for dy in (-2, -1, 0, 1, 2):
                for dx in (-2, -1, 0, 1, 2):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and mask[ny, nx]:
                        visited[ny, nx] = True
                        q.append((ny, nx))
        if len(pts) >= args.min_area:
            sx = sum(p[0] for p in pts) / len(pts)
            sy = sum(p[1] for p in pts) / len(pts)
            clusters.append((sx, sy, len(pts)))

    merged = []
    used = [False] * len(clusters)
    for i in range(len(clusters)):
        if used[i]:
            continue
        used[i] = True
        grp = [clusters[i]]
        changed = True
        while changed:
            changed = False
            for j in range(len(clusters)):
                if used[j]:
                    continue
                if any(
                    ((clusters[j][0] - gx) ** 2 + (clusters[j][1] - gy) ** 2) ** 0.5 < args.merge_dist
                    for gx, gy, _ in grp
                ):
                    used[j] = True
                    grp.append(clusters[j])
                    changed = True
        tot = sum(g[2] for g in grp)
        mx = round(sum(g[0] * g[2] for g in grp) / tot, 1)
        my = round(sum(g[1] * g[2] for g in grp) / tot, 1)
        merged.append({"x": mx, "y": my, "area": tot})

    merged.sort(key=lambda c: (c["y"], c["x"]))
    vis = im.copy()
    d = ImageDraw.Draw(vis)
    font = load_font(16)
    for idx, c in enumerate(merged):
        r = 16 if c["area"] > 400 else 10
        d.ellipse([c["x"] - r, c["y"] - r, c["x"] + r, c["y"] + r], outline="#ff00ff", width=3)
        d.text((c["x"] + 12, c["y"] - 10), str(idx), fill="#ffff00", font=font)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    vis.save(args.out)

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)
    print(f"Detected {len(merged)} {args.color} clusters -> {args.out}")
    return 0


def cmd_verify_scene(args) -> int:
    vault_root = Path(args.vault).resolve() if args.vault else detect_default_vault(args.atlasmap)
    map_path = resolve_vault_path(args.atlasmap, vault_root)
    with open(map_path, encoding="utf-8") as f:
        data = json.load(f)
    st = data["state"]
    grid = st.get("grid") or {}
    size = grid.get("size", 70)
    ox = grid.get("offsetX", 0)
    oy = grid.get("offsetY", 0)
    objs = st.get("objects") or {}

    img_path = resolve_vault_path(st["background"], vault_root)
    im = Image.open(img_path).convert("RGBA")
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    gx = ox
    while gx < im.size[0]:
        draw.line([(gx, 0), (gx, im.size[1])], fill=(255, 255, 0, 55), width=1)
        gx += size
    gy = oy
    while gy < im.size[1]:
        draw.line([(0, gy), (im.size[0], gy)], fill=(255, 255, 0, 55), width=1)
        gy += size

    for fg in (objs.get("fog") or {}).values():
        if fg.get("type") == "rectangle" and not fg.get("isErasing"):
            draw.rectangle(
                [fg["x"], fg["y"], fg["x"] + fg["width"], fg["y"] + fg["height"]],
                fill=(88, 28, 135, 50),
                outline=(192, 132, 252, 120),
                width=2,
            )

    unit_dist = grid.get("unitDistance", 1.5) or 1.5
    for lt in (objs.get("lights") or {}).values():
        em = lt.get("emission") or {}
        r = (em.get("dim", 3) / unit_dist) * size * 0.45
        draw.ellipse(
            [lt["x"] - r, lt["y"] - r, lt["x"] + r, lt["y"] + r],
            fill=(56, 189, 248, 30),
            outline=(125, 211, 252, 130),
            width=1,
        )

    for dr in (objs.get("drawings") or {}).values():
        pts = [(p["x"], p["y"]) for p in (dr.get("points") or [])]
        if len(pts) >= 2:
            if dr.get("fill") == "solid" and len(pts) >= 3:
                draw.polygon(pts, fill=dr.get("color", "#334155"))
            else:
                draw.line(pts, fill=dr.get("color", "#0f172a"), width=3)

    for w in (objs.get("walls") or {}).values():
        p1 = (w["p1"]["x"], w["p1"]["y"])
        p2 = (w["p2"]["x"], w["p2"]["y"])
        if w.get("type") == "secret-door":
            draw.line([p1, p2], fill=(217, 70, 239, 255), width=7)
        elif w.get("type") == "door":
            col = (239, 68, 68, 255) if w.get("locked") else (250, 204, 21, 255)
            draw.line([p1, p2], fill=col, width=7)
        else:
            draw.line([p1, p2], fill=(34, 211, 238, 230), width=4)

    for tk in (objs.get("tokens") or {}).values():
        r = 24
        col = (34, 197, 94, 230) if tk.get("playerCharacter") else (239, 68, 68, 230)
        draw.ellipse([tk["x"] - r, tk["y"] - r, tk["x"] + r, tk["y"] + r], fill=col, outline=(255, 255, 255, 255), width=3)

    pfont = load_font(12)
    for pn in (objs.get("pins") or {}).values():
        r = 14
        draw.ellipse([pn["x"] - r, pn["y"] - r, pn["x"] + r, pn["y"] + r], fill=(255, 255, 255, 240), outline=(15, 23, 42, 255), width=3)
        lbl = pn.get("label")
        if lbl:
            bb = draw.textbbox((0, 0), str(lbl), font=pfont)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
            draw.text((pn["x"] - tw / 2, pn["y"] - th / 2 - 1), str(lbl), fill=(15, 23, 42, 255), font=pfont)

    if args.labels_json:
        with open(args.labels_json, encoding="utf-8") as f:
            labels = json.load(f)
        lfont = load_font(26)
        for item in labels:
            lx = ox + item["col"] * size if "col" in item else item["x"]
            ly = oy + item["row"] * size if "row" in item else item["y"]
            code = item["code"]
            color = item.get("color", "#f59e0b")
            br = 25
            draw.ellipse([lx - br, ly - br, lx + br, ly + br], fill=(15, 23, 42, 225), outline=color, width=3)
            bb = draw.textbbox((0, 0), code, font=lfont)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
            draw.text((lx - tw / 2, ly - th / 2 - 3), code, fill=(255, 255, 255, 255), font=lfont)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    Image.alpha_composite(im, overlay).convert("RGB").save(args.out)
    counts = {k: len(v) for k, v in objs.items() if isinstance(v, dict)}
    print(f"Verify image saved: {args.out} | objects={counts}")
    return 0


def cmd_validate(args) -> int:
    vault_root = Path(args.vault).resolve() if args.vault else detect_default_vault(args.atlasmap)
    map_path = resolve_vault_path(args.atlasmap, vault_root)
    errors, warnings = [], []
    with open(map_path, encoding="utf-8") as f:
        data = json.load(f)
    st = data["state"]
    objs = st.get("objects") or {}
    grid = st.get("grid") or {}
    lighting = st.get("lighting") or {}

    bg_rel = st.get("background")
    if bg_rel:
        bg_resolved = resolve_vault_path(bg_rel, vault_root)
        if not os.path.exists(bg_resolved):
            errors.append(f"Background asset not found: {bg_rel}")

    dashboard_arg = args.dashboard or st.get("dmNotePath")
    if dashboard_arg:
        dash_path = resolve_vault_path(dashboard_arg, vault_root)
        if not os.path.exists(dash_path):
            errors.append(f"Dashboard file not found: {dashboard_arg}")
        else:
            bsize = os.path.getsize(dash_path)
            print(f"Dashboard size: {bsize} bytes ({bsize / 1024:.2f} KB)")
            if bsize >= 32768:
                errors.append(f"Dashboard exceeds Atlas 32768 byte limit ({bsize} bytes)")
            elif bsize >= 30720:
                warnings.append(f"Dashboard is close to 32 KB limit ({bsize} bytes)")
            with open(dash_path, encoding="utf-8") as f:
                headings = set(re.findall(r"^###\s+(.+)$", f.read(), flags=re.MULTILINE))
            for pid, pin in (objs.get("pins") or {}).items():
                np_str = pin.get("notePath", "")
                if "#" in np_str:
                    h = np_str.split("#", 1)[1]
                    if h not in headings:
                        errors.append(f"Pin {pid} heading not found in Dashboard: #{h}")

    walls = list((objs.get("walls") or {}).values())
    for lid, lt in (objs.get("lights") or {}).items():
        if walls:
            md = min(
                pt_seg_dist(lt["x"], lt["y"], w["p1"]["x"], w["p1"]["y"], w["p2"]["x"], w["p2"]["y"])
                for w in walls
            )
            if md < 18:
                warnings.append(f"Light {lid} ({lt['x']}, {lt['y']}) is only {md:.1f}px from a wall")

    if lighting.get("enabled") and len(objs.get("fog") or {}) > 0:
        warnings.append("Both Dynamic Lighting and manual Fog are active: opening doors may not reveal rooms under Fog")

    if grid.get("snapToGrid", True) and grid.get("size"):
        sz, ox, oy = grid["size"], grid.get("offsetX", 0), grid.get("offsetY", 0)
        for tid, tk in (objs.get("tokens") or {}).items():
            half = 0.5 * (tk.get("size") or 1)
            cx = (tk["x"] - ox) / sz - half
            cy = (tk["y"] - oy) / sz - half
            if abs(cx - round(cx)) > 0.05 or abs(cy - round(cy)) > 0.05:
                warnings.append(
                    f"Token {tid} ({tk.get('name')}) is not snapped to an integer grid cell ({cx:.2f}, {cy:.2f})"
                )

    if args.reset_test:
        st["exploredMask"] = None
        st["exploredEdits"] = 0
        st["diceLog"] = []
        with open(map_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        print("Reset exploredMask, exploredEdits, and diceLog.")

    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        return 1
    print("Validation PASSED.")
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="Atlas VTT 0.16.0 Scene Tools")
    ap.add_argument("--vault", help="Optional vault root directory override")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("grid-preview", help="Overlay Atlas grid with column/row numbers")
    p1.add_argument("source", help="Path to .atlasmap or image")
    p1.add_argument("--size", type=float)
    p1.add_argument("--ox", type=float)
    p1.add_argument("--oy", type=float)
    p1.add_argument("--out", required=True)
    p1.set_defaults(func=cmd_grid_preview)

    p2 = sub.add_parser("detect-lights", help="Detect glowing crystal/torch clusters on a battlemap")
    p2.add_argument("image")
    p2.add_argument("--color", choices=["cyan", "amber", "emerald", "purple"], default="cyan")
    p2.add_argument("--min-area", type=int, default=25)
    p2.add_argument("--merge-dist", type=float, default=42)
    p2.add_argument("--out", required=True)
    p2.add_argument("--json")
    p2.set_defaults(func=cmd_detect_lights)

    p3 = sub.add_parser("verify-scene", help="Render scene walls, doors, lights, tokens, pins, drawings")
    p3.add_argument("atlasmap")
    p3.add_argument("--out", required=True)
    p3.add_argument("--labels-json", help="Optional JSON array of {code, col, row, color} room badges")
    p3.set_defaults(func=cmd_verify_scene)

    p4 = sub.add_parser("validate", help="Validate Dashboard size, pin headings, light clearances, and snap")
    p4.add_argument("atlasmap")
    p4.add_argument("--dashboard", help="Optional Dashboard .md path (auto-detected from dmNotePath if omitted)")
    p4.add_argument("--reset-test", action="store_true")
    p4.set_defaults(func=cmd_validate)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
