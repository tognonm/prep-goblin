#!/usr/bin/env python3
"""CLI tools for visual analysis, verification, and validation of Atlas VTT 0.16.0 scenes."""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import deque
from pathlib import Path
from typing import Any

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
    norm_rel = rel_or_abs.replace("\\", "/").lstrip("/")
    candidate = vault_root / norm_rel.replace("/", os.sep)
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

    unit_dist = grid.get("unitDistance", 5) or 5
    for lt in (objs.get("lights") or {}).values():
        em = lt.get("emission") or {}
        r = (em.get("dim", unit_dist * 2) / unit_dist) * size * 0.45
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
        with open(map_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        print("Reset exploredMask, exploredEdits, and diceLog.")

    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        return 1
    print("Validation PASSED.")
    return 0


def _segments_overlap_collinear(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
    tol: float = 1.0,
) -> float:
    """Return overlap length (> 0) if two non-degenerate segments are collinear and overlap."""
    la = math.hypot(a2[0] - a1[0], a2[1] - a1[1])
    lb = math.hypot(b2[0] - b1[0], b2[1] - b1[1])
    if la < 1.0 or lb < 1.0:
        return 0.0
    ux, uy = (a2[0] - a1[0]) / la, (a2[1] - a1[1]) / la
    # Check parallelism (|sin(theta)| <= 0.02, ~1.1 deg)
    cross = abs(ux * (b2[1] - b1[1]) - uy * (b2[0] - b1[0])) / lb
    if cross > 0.02:
        return 0.0
    # Perpendicular distance of B endpoints to infinite line through A
    perp1 = abs((b1[0] - a1[0]) * (-uy) + (b1[1] - a1[1]) * ux)
    perp2 = abs((b2[0] - a1[0]) * (-uy) + (b2[1] - a1[1]) * ux)
    if perp1 > tol or perp2 > tol:
        return 0.0
    t1 = (b1[0] - a1[0]) * ux + (b1[1] - a1[1]) * uy
    t2 = (b2[0] - a1[0]) * ux + (b2[1] - a1[1]) * uy
    lo, hi = (t1, t2) if t1 <= t2 else (t2, t1)
    overlap = min(la, hi) - max(0.0, lo)
    return overlap if overlap > tol else 0.0


def _segments_intersect(
    a1: tuple[float, float],
    a2: tuple[float, float],
    b1: tuple[float, float],
    b2: tuple[float, float],
    eps: float = 1e-6,
) -> bool:
    """Return True if closed 2D segments a1-a2 and b1-b2 intersect (crossing, T, or shared vertex)."""
    if (
        max(a1[0], a2[0]) + eps < min(b1[0], b2[0])
        or max(b1[0], b2[0]) + eps < min(a1[0], a2[0])
        or max(a1[1], a2[1]) + eps < min(b1[1], b2[1])
        or max(b1[1], b2[1]) + eps < min(a1[1], a2[1])
    ):
        return False

    def orient(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    def on_seg(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> bool:
        return (
            min(p[0], r[0]) - eps <= q[0] <= max(p[0], r[0]) + eps
            and min(p[1], r[1]) - eps <= q[1] <= max(p[1], r[1]) + eps
        )

    o1 = orient(a1, a2, b1)
    o2 = orient(a1, a2, b2)
    o3 = orient(b1, b2, a1)
    o4 = orient(b1, b2, a2)

    if ((o1 > eps and o2 < -eps) or (o1 < -eps and o2 > eps)) and (
        (o3 > eps and o4 < -eps) or (o3 < -eps and o4 > eps)
    ):
        return True
    if abs(o1) <= eps and on_seg(a1, b1, a2):
        return True
    if abs(o2) <= eps and on_seg(a1, b2, a2):
        return True
    if abs(o3) <= eps and on_seg(b1, a1, b2):
        return True
    if abs(o4) <= eps and on_seg(b1, a2, b2):
        return True
    return False


def cmd_audit_walls(args) -> int:
    vault_root = Path(args.vault).resolve() if args.vault else detect_default_vault(args.atlasmap)
    map_path = resolve_vault_path(args.atlasmap, vault_root)
    with open(map_path, encoding="utf-8") as f:
        data = json.load(f)

    st = data.get("state") or {}
    objs = st.get("objects") or {}
    walls_dict = objs.get("walls") or {}
    lights_dict = objs.get("lights") or {}

    gap_threshold = float(args.gap_threshold)
    light_clearance = float(args.light_clearance)

    degenerate: list[str] = []
    duplicates: list[str] = []
    near_gaps: list[str] = []
    tight_lights: list[str] = []

    wall_items: list[tuple[str, tuple[float, float], tuple[float, float], float]] = []
    for wid, w in walls_dict.items():
        p1 = (float(w["p1"]["x"]), float(w["p1"]["y"]))
        p2 = (float(w["p2"]["x"]), float(w["p2"]["y"]))
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        if seg_len < 1.0:
            degenerate.append(
                f"{wid}: zero-length/degenerate wall (len={seg_len:.2f}px at ({p1[0]:.1f}, {p1[1]:.1f}))"
            )
        wall_items.append((wid, p1, p2, seg_len))

    valid_walls = [item for item in wall_items if item[3] >= 1.0]
    n = len(valid_walls)

    # 1. Cluster endpoints within 1.0 px (Union-Find) to determine vertex connectivity
    ep_coords: list[tuple[float, float]] = []
    for _, p1, p2, _ in valid_walls:
        ep_coords.append(p1)
        ep_coords.append(p2)

    parent = list(range(2 * n))

    def find(u: int) -> int:
        while parent[u] != u:
            parent[u] = parent[parent[u]]
            u = parent[u]
        return u

    def union(u: int, v: int) -> None:
        ru, rv = find(u), find(v)
        if ru != rv:
            parent[rv] = ru

    for u in range(2 * n):
        ux, uy = ep_coords[u]
        for v in range(u + 1, 2 * n):
            if math.hypot(ux - ep_coords[v][0], uy - ep_coords[v][1]) <= 1.0:
                union(u, v)

    # Group distinct wall indices per vertex cluster
    cluster_walls: dict[int, set[int]] = {}
    for e_idx in range(2 * n):
        root = find(e_idx)
        cluster_walls.setdefault(root, set()).add(e_idx // 2)

    # 2. Detect collinear overlapping duplicates + build wall adjacency (vertices, T-junctions, X-junctions)
    wall_adj: list[set[int]] = [set() for _ in range(n)]
    sealed_ep: list[bool] = [False] * (2 * n)

    for e_idx in range(2 * n):
        if len(cluster_walls[find(e_idx)]) >= 2:
            sealed_ep[e_idx] = True

    for i in range(n):
        wid_a, a1, a2, _ = valid_walls[i]
        for j in range(i + 1, n):
            wid_b, b1, b2, _ = valid_walls[j]

            ov = _segments_overlap_collinear(a1, a2, b1, b2, tol=1.0)
            if ov > 1.0:
                duplicates.append(
                    f"{wid_a} <-> {wid_b}: duplicate/overlapping collinear wall segments ({ov:.1f}px overlap)"
                )
                wall_adj[i].add(j)
                wall_adj[j].add(i)
                continue

            # Check shared vertex cluster
            connected = (
                find(2 * i) == find(2 * j)
                or find(2 * i) == find(2 * j + 1)
                or find(2 * i + 1) == find(2 * j)
                or find(2 * i + 1) == find(2 * j + 1)
            )

            # Check valid T-junction sealing (endpoint sitting directly on another wall <= 1.0 px)
            if pt_seg_dist(a1[0], a1[1], b1[0], b1[1], b2[0], b2[1]) <= 1.0:
                sealed_ep[2 * i] = True
                connected = True
            if pt_seg_dist(a2[0], a2[1], b1[0], b1[1], b2[0], b2[1]) <= 1.0:
                sealed_ep[2 * i + 1] = True
                connected = True
            if pt_seg_dist(b1[0], b1[1], a1[0], a1[1], a2[0], a2[1]) <= 1.0:
                sealed_ep[2 * j] = True
                connected = True
            if pt_seg_dist(b2[0], b2[1], a1[0], a1[1], a2[0], a2[1]) <= 1.0:
                sealed_ep[2 * j + 1] = True
                connected = True

            # Check exact segment-segment crossing (X-junction)
            if not connected and _segments_intersect(a1, a2, b1, b2):
                connected = True

            if connected:
                wall_adj[i].add(j)
                wall_adj[j].add(i)

    # 3. Test ONLY open / unsealed degree-1 endpoints against non-incident walls (catches both corner & T-junction cracks)
    short_curve_limit = 2.0 * gap_threshold
    best_pair_gaps: dict[tuple[int, int], tuple[float, str]] = {}

    for i in range(n):
        wid_a, a1, a2, len_a = valid_walls[i]
        # Exclude self, all 1-hop connected/crossing walls, and 2-hop walls along a short chained curve
        excluded = {i} | wall_adj[i]
        if len_a <= short_curve_limit:
            for nb in wall_adj[i]:
                if valid_walls[nb][3] <= short_curve_limit:
                    excluded |= wall_adj[nb]

        for local_idx, pt in ((0, a1), (1, a2)):
            e_idx = 2 * i + local_idx
            if sealed_ep[e_idx]:
                continue
            for j in range(n):
                if j in excluded:
                    continue
                wid_b, b1, b2, _ = valid_walls[j]
                d = pt_seg_dist(pt[0], pt[1], b1[0], b1[1], b2[0], b2[1])
                if 1.0 < d <= gap_threshold:
                    pair_key = (i, j) if i < j else (j, i)
                    ep_dist_min = min(
                        math.hypot(pt[0] - b1[0], pt[1] - b1[1]),
                        math.hypot(pt[0] - b2[0], pt[1] - b2[1]),
                    )
                    gap_kind = "corner" if abs(ep_dist_min - d) <= 1.0 else "T-junction"
                    desc = (
                        f"{wid_a} open endpoint ({pt[0]:.1f}, {pt[1]:.1f}) -> {wid_b}: "
                        f"near-miss {gap_kind} gap of {d:.1f}px (potential light leak)"
                    )
                    prev = best_pair_gaps.get(pair_key)
                    if prev is None or d < prev[0]:
                        best_pair_gaps[pair_key] = (d, desc)

    for _, (_, desc) in sorted(best_pair_gaps.items()):
        near_gaps.append(desc)

    for lid, lt in lights_dict.items():
        lx, ly = float(lt["x"]), float(lt["y"])
        if valid_walls:
            nearest_wid, nearest_dist = min(
                (
                    (wid, pt_seg_dist(lx, ly, p1[0], p1[1], p2[0], p2[1]))
                    for wid, p1, p2, _ in valid_walls
                ),
                key=lambda x: x[1],
            )
            if nearest_dist < light_clearance:
                tight_lights.append(
                    f"{lid} ({lx:.1f}, {ly:.1f}) is only {nearest_dist:.1f}px from {nearest_wid} (< {light_clearance:.0f}px)"
                )

    total_issues = len(degenerate) + len(duplicates) + len(near_gaps) + len(tight_lights)
    print(f"Wall Audit: {Path(map_path).name}")
    print(
        f"  Walls: {len(walls_dict)} | Lights: {len(lights_dict)} | "
        f"Gap threshold: {gap_threshold:.1f}px | Light clearance: {light_clearance:.1f}px"
    )
    print(
        f"  Findings: {total_issues} total "
        f"(degenerate={len(degenerate)}, duplicate={len(duplicates)}, "
        f"near-gaps={len(near_gaps)}, tight-lights={len(tight_lights)})"
    )

    if degenerate:
        print("\n[Degenerate / Zero-Length Walls]")
        for item in degenerate:
            print(f"  - {item}")
    if duplicates:
        print("\n[Duplicate / Overlapping Walls]")
        for item in duplicates:
            print(f"  - {item}")
    if near_gaps:
        print("\n[Near-Miss Endpoint Gaps (Potential Light Leaks)]")
        for item in near_gaps:
            print(f"  - {item}")
    if tight_lights:
        print("\n[Lights Too Close to Walls]")
        for item in tight_lights:
            print(f"  - {item}")

    if total_issues == 0:
        print("Wall audit CLEAN (0 issues).")
        return 0
    if args.strict:
        print("Wall audit FAILED (--strict).", file=sys.stderr)
        return 1
    return 0


def _infer_collection_from_paths(map_path: Path, state_map_path: str | None) -> str | None:
    pattern = re.compile(r"atlas-vtt/collections/([^/]+)/", flags=re.IGNORECASE)
    for candidate in (state_map_path or "", map_path.as_posix()):
        norm = candidate.replace("\\", "/")
        m = pattern.search(norm)
        if m and m.group(1).strip():
            return m.group(1).strip()
    return None


def _load_campaign_config(config_path: str | None = None, vault_root: Path | None = None) -> dict[str, Any]:
    if config_path:
        cfg_file = Path(config_path).resolve()
    elif vault_root and (vault_root.parent / "campaign.config.json").is_file():
        cfg_file = (vault_root.parent / "campaign.config.json").resolve()
    else:
        cfg_file = (REPO_ROOT / "campaign.config.json").resolve()
    raw: dict[str, Any] = {}
    if cfg_file.is_file():
        try:
            raw = json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception:
            raw = {}
    party = raw.get("party") if isinstance(raw.get("party"), list) and raw.get("party") else [
        {
            "name": "Mira",
            "note": "Mira the Cleric",
            "passives": {"perception": 13, "investigation": 10, "insight": 15},
        },
        {
            "name": "Kael",
            "note": "Kael the Rogue",
            "passives": {"perception": 11, "investigation": 14, "insight": 10},
        },
        {
            "name": "Bram",
            "note": "Bram the Fighter",
            "passives": {"perception": 10, "investigation": 9, "insight": 12},
        },
    ]
    return {
        "collection": str(raw.get("atlas_collection") or "Campaign"),
        "party_level": int(raw.get("party_level") or 3),
        "party": party,
    }


def _best_passive(party: list[dict[str, Any]], stat: str) -> tuple[str, int]:
    best_name, best_val = "PC", 10
    for pc in party:
        val = int((pc.get("passives") or {}).get(stat, 10))
        if val > best_val or best_name == "PC":
            best_val = val
            best_name = str(pc.get("name", "PC"))
    return best_name, best_val


def cmd_scaffold_dashboard(args) -> int:
    vault_root = Path(args.vault).resolve() if args.vault else detect_default_vault(args.atlasmap)
    map_path = Path(resolve_vault_path(args.atlasmap, vault_root))
    with open(map_path, encoding="utf-8") as f:
        data = json.load(f)

    cfg = _load_campaign_config(args.config, vault_root=vault_root)
    st = data.get("state") or {}
    grid = st.get("grid") or {}
    lighting = st.get("lighting") or {}
    objs = st.get("objects") or {}

    scene_stem = map_path.stem
    title = (args.name or f"{scene_stem} - Dashboard").strip()
    collection = (
        args.collection
        or _infer_collection_from_paths(map_path, str(st.get("mapPath") or ""))
        or cfg["collection"]
    )
    party = cfg["party"]
    party_level = cfg["party_level"]

    # Grid & lighting summary
    cell_px = grid.get("size", 70)
    unit_dist = grid.get("unitDistance", 5)
    unit_type = str(grid.get("unitType") or "feet")
    unit_suf = "m" if unit_type.lower().startswith("m") else "ft"
    unit_str = f"{int(unit_dist)}" if abs(float(unit_dist) - round(float(unit_dist))) < 1e-6 else f"{unit_dist}"

    ambient = lighting.get("ambient", 0.0)
    if not lighting.get("enabled", False):
        light_desc = "Dynamic Lighting disabled"
    elif ambient >= 0.8:
        light_desc = f"Day (`ambient: {ambient}`, token vision active)"
    elif ambient > 0.0:
        light_desc = f"Dusk / Dim (`ambient: {ambient}`, token vision active)"
    else:
        light_desc = "Dark / Night (`ambient: 0.0`, torches & local lights active)"

    walls = list((objs.get("walls") or {}).values())
    doors_cnt = sum(1 for w in walls if w.get("type") == "door")
    secret_cnt = sum(1 for w in walls if w.get("type") == "secret-door")
    lights_cnt = len(objs.get("lights") or {})

    # Extract 1:1 H3 headings from existing pins (or provide 2 clean starter rooms)
    pins_raw = list((objs.get("pins") or {}).values())
    pins_raw.sort(key=lambda p: (str(p.get("label") or ""), str(p.get("name") or ""), float(p.get("y", 0)), float(p.get("x", 0))))

    headings: list[str] = []
    seen_headings: set[str] = set()
    for idx, pin in enumerate(pins_raw, 1):
        np_str = str(pin.get("notePath") or "")
        if "#" in np_str:
            h = np_str.split("#", 1)[1].strip()
        else:
            lbl = str(pin.get("label") or idx).strip()
            nm = str(pin.get("name") or f"Area {idx}").strip()
            h = f"{lbl}. {nm}" if lbl and not nm.startswith(f"{lbl}.") else nm
        if h and h not in seen_headings:
            headings.append(h)
            seen_headings.add(h)

    if not headings:
        headings = ["1. Entry", "2. Main Chamber"]

    # Party passives & dynamic Active Roll DC (> highest Perception / Investigation passive)
    perc_name, perc_val = _best_passive(party, "perception")
    inv_name, inv_val = _best_passive(party, "investigation")
    active_dc = max(perc_val, inv_val) + 1
    passives_chunks = []
    for pc in party:
        p = pc.get("passives") or {}
        passives_chunks.append(
            f"**{pc['name']}** Perc. `{p.get('perception', 10)}` / Inv. `{p.get('investigation', 10)}` / Ins. `{p.get('insight', 10)}`"
        )
    passives_line = " \\| ".join(passives_chunks)

    tokens = list((objs.get("tokens") or {}).values())
    pc_names = [str(tk.get("name") or "PC") for tk in tokens if tk.get("playerCharacter")]
    enemy_groups: dict[tuple[str, int, str, str], int] = {}
    for tk in tokens:
        if tk.get("playerCharacter"):
            continue
        en_name = str(tk.get("name") or "Creature")
        hp_obj = tk.get("hp") or {}
        hp_max = int(hp_obj.get("max", hp_obj.get("current", 10))) if isinstance(hp_obj, dict) else 10
        diff = str(tk.get("difficulty") or "-")
        sb = str(tk.get("statblockPath") or "")
        key = (en_name, hp_max, diff, sb)
        enemy_groups[key] = enemy_groups.get(key, 0) + 1

    safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
    safe_scene = scene_stem.replace("\\", "\\\\").replace('"', '\\"')

    lines: list[str] = [
        "---",
        f'title: "{safe_title}"',
        'icon: "🗺️"',
        "tags: [atlas, dashboard, dungeon]",
        f'collection: "{collection}"',
        f'atlas_scene: "{safe_scene}"',
        'status: "draft"',
        "---",
        "",
        f"# 🛡️ {title}",
        "",
        "> [!TIP] **Atlas VTT Quick Controls**",
        "> Press **`Tab`** to open this Linked Note, hold **`H`** (*Lighting Peek*) to preview player vision, and click doors on the canvas to open them live.",
        "",
        "---",
        "",
        "## ⚡ Quick Session Reference",
        "",
        "| Parameter | Operational Detail |",
        "| :--- | :--- |",
        f"| **Grid & Scale** | `{cell_px}px` cells (`{unit_str} {unit_suf}` per square) |",
        f"| **Lighting** | {light_desc} |",
        f"| **Scene Objects** | `{len(walls)}` walls (`{doors_cnt}` doors, `{secret_cnt}` secret doors), `{lights_cnt}` lights, `{len(pins_raw)}` pins |",
        f"| **PCs on Scene** | {', '.join(pc_names) if pc_names else 'None placed yet'} |",
        f"| **Party Passives (Lv. {party_level})** | {passives_line} |",
        "",
        "---",
        "",
        "## 🗺️ Tactical Room Guide (1:1 Pin Anchors)",
        "",
    ]

    for idx, heading in enumerate(headings):
        lines.append(f"### {heading}")
        lines.append("> [!quote] 👁️ Read-Aloud Description")
        lines.append("> *Describe two crisp sights, one sound, and one smell or temperature cue here.*")
        lines.append("")
        lines.append("- **Atmosphere & Light:** Note ambient lighting, cover, and terrain hazards.")
        if idx % 2 == 0:
            lines.append(
                f"- ⚡ **`[Automatic Passive — {perc_name} (Perc. {perc_val})]`:** Immediate clue or threat spotted with DC ≤ `{perc_val}`."
            )
            lines.append(
                f"- 🎲 **`[Active Roll — Investigation DC {active_dc}]`:** Hidden detail, trap mechanism, or secondary clue."
            )
        else:
            lines.append(
                f"- ⚡ **`[Automatic Passive — {inv_name} (Inv. {inv_val})]`:** Structural tell or track spotted with DC ≤ `{inv_val}`."
            )
            lines.append(
                f"- 🎲 **`[Active Roll — Perception DC {active_dc}]`:** Concealed foe, secret catch, or subtle sound."
            )
        lines.append("- **Tactics & Exits:** Note enemy opening moves, cover, and connected doors.")
        lines.append("")

    if enemy_groups:
        lines.extend([
            "---",
            "",
            "## 👹 Placed Tokens / Enemies",
            "",
            "| Creature | Qty | HP | Difficulty | Statblock |",
            "| :--- | :---: | :---: | :---: | :--- |",
        ])
        for (en_name, hp_max, diff, sb), qty in enemy_groups.items():
            if sb.endswith(".md"):
                sb_link = f"[[{sb[:-3]}\\|{en_name}]]"
            else:
                sb_link = "Ad hoc"
            lines.append(f"| {en_name} | {qty} | {hp_max} | {diff} | {sb_link} |")
        lines.append("")

    content = "\n".join(lines).rstrip() + "\n"
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8", newline="\n")

    bsize = len(content.encode("utf-8"))
    print(f"Scaffolded Dashboard: {out_path}")
    print(f"  Size: {bsize} bytes ({bsize / 1024:.2f} KB) | Collection: {collection} | H3 Sections: {len(headings)} | Active DC: {active_dc} | Enemies grouped: {len(enemy_groups)}")
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="Atlas VTT 0.16.0 Scene Tools (Prep Goblin)")
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

    p5 = sub.add_parser("audit-walls", help="Audit walls for degenerate segments, duplicates, near-miss gaps, and light clearance")
    p5.add_argument("atlasmap", help="Path to .atlasmap scene file")
    p5.add_argument("--gap-threshold", type=float, default=18.0, help="Near-miss endpoint gap threshold in px (default: 18)")
    p5.add_argument("--light-clearance", type=float, default=20.0, help="Minimum light-to-wall clearance in px (default: 20)")
    p5.add_argument("--strict", action="store_true", help="Exit with code 1 if any wall or light issues are detected")
    p5.set_defaults(func=cmd_audit_walls)

    p6 = sub.add_parser("scaffold-dashboard", help="Generate a < 5 KB starter DM Dashboard from an .atlasmap scene")
    p6.add_argument("atlasmap", help="Path to .atlasmap scene file")
    p6.add_argument("--out", required=True, help="Output Markdown path for the starter Dashboard")
    p6.add_argument("--name", help="Optional Dashboard title (defaults to '<Scene Name> - Dashboard')")
    p6.add_argument("--collection", help="Optional Atlas collection override (inferred from scene path if omitted)")
    p6.add_argument("--config", help="Optional path to campaign.config.json")
    p6.set_defaults(func=cmd_scaffold_dashboard)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
