#!/usr/bin/env python3
"""Register a square portrait/token image into an Atlas VTT 0.16.0 collection."""
from __future__ import annotations

import argparse
import json
import os
import random
import string
import sys
import time
from pathlib import Path
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[4]


def load_defaults() -> tuple[Path, str]:
    vault_dir = REPO_ROOT / "template-vault"
    collection = "Campaign"
    cfg_path = REPO_ROOT / "campaign.config.json"
    if cfg_path.is_file():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            if cfg.get("vault_dir"):
                cand = (REPO_ROOT / cfg["vault_dir"]).resolve()
                if cand.is_dir():
                    vault_dir = cand
            if cfg.get("atlas_collection"):
                collection = str(cfg["atlas_collection"])
        except Exception:
            pass
    elif (REPO_ROOT / "Vault").is_dir():
        vault_dir = REPO_ROOT / "Vault"
    return vault_dir, collection


def main(argv: list[str] | None = None) -> int:
    default_vault, default_collection = load_defaults()
    ap = argparse.ArgumentParser(description="Register a token image for Atlas VTT 0.16.0.")
    ap.add_argument("image", help="Path to source image (PNG/JPG/WEBP)")
    ap.add_argument("--name", required=True, help="Display name in Atlas VTT")
    ap.add_argument("--statblock", help="Relative statblock note path inside the vault (e.g. Mostri/Predone di Strada.md)")
    ap.add_argument("--tags", nargs="*", default=[])
    ap.add_argument("--collection", default=default_collection, help=f"Atlas collection name (default: {default_collection})")
    ap.add_argument("--vault", default=str(default_vault), help=f"Vault root path (default: {default_vault})")
    ap.add_argument("--player", action="store_true", help="Mark token as playerCharacter: true")
    ap.add_argument("--update-metadata", action="store_true", help="Legacy: also update .atlas-data/assets-metadata.json if present")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    vault_path = Path(a.vault).resolve()
    assets_dir = vault_path / "atlas-vtt" / "assets"
    thumbs_dir = assets_dir / "thumbnails"

    im = Image.open(a.image).convert("RGBA")
    s = min(im.size)
    left, top = (im.width - s) // 2, (im.height - s) // 2
    im = im.crop((left, top, left + s, top + s)).resize((400, 400), Image.Resampling.LANCZOS)

    ts = int(time.time() * 1000)
    rnd = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    h_rnd = "".join(random.choices("0123456789abcdef", k=8))
    safe = "".join(c if c.isalnum() else "_" for c in a.name.encode("ascii", "ignore").decode()) or "token"
    fname = f"{safe}_{ts}_{rnd}.webp"
    thumb_fname = f"{safe}_{ts}_{rnd}-{h_rnd}.webp"
    rel = f"atlas-vtt/assets/{fname}"
    thumb_rel = f"atlas-vtt/assets/thumbnails/{thumb_fname}"

    tid = f"token-{ts}-{rnd}"
    token_entry: dict[str, object] = {
        "name": a.name,
        "imagePath": rel,
        "collection": a.collection,
        "tags": a.tags,
        "showRing": True,
        "type": "token",
        "id": tid,
        "createdAt": ts,
        "modifiedAt": ts,
        "thumbnailPath": thumb_rel,
    }
    if a.statblock:
        token_entry["statblockPath"] = a.statblock
    if a.player:
        token_entry["playerCharacter"] = True

    print(("[dry-run] " if a.dry_run else "") + f"{a.name} -> {rel} ({tid}) [collection: {a.collection}, statblock: {a.statblock}]")
    if a.dry_run:
        return 0

    assets_dir.mkdir(parents=True, exist_ok=True)
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    im.save(vault_path / rel, "WEBP", quality=90)

    thumb_im = im.resize((128, 128), Image.Resampling.LANCZOS)
    thumb_im.save(vault_path / thumb_rel, "WEBP", quality=85)

    tokens_dir = vault_path / "atlas-vtt" / "collections" / a.collection / "tokens"
    tokens_dir.mkdir(parents=True, exist_ok=True)
    token_file = tokens_dir / f"{tid}.json"
    token_file.write_text(
        json.dumps({"atlasRecord": {"format": 1, **token_entry}}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if a.update_metadata:
        meta_path = vault_path / "atlas-vtt" / ".atlas-data" / "assets-metadata.json"
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            col = meta.setdefault("collections", {}).setdefault(
                a.collection, {"id": a.collection, "name": a.collection, "tags": {}}
            )
            for tag in a.tags:
                col.setdefault("tags", {}).setdefault(
                    f"tokens:{tag.lower()}", {"id": tag.lower(), "name": tag, "group": "tokens"}
                )
            meta.setdefault("assets", {})[tid] = token_entry
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
