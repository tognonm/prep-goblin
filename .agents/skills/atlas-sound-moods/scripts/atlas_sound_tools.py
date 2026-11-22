#!/usr/bin/env python3
"""Atlas VTT 0.19.0+ Sound & Moods Automation Tool (Prep Goblin).

Manages <Vault>/atlas-vtt/sounds/records/, <Vault>/atlas-vtt/sounds/moods/,
and state.sound (mood + combatMood) bindings inside .atlasmap scene files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
AUDIO_EXTS = {".opus", ".mp3", ".ogg", ".wav", ".flac", ".m4a", ".aac", ".webm"}
VALID_ROOMS = {"room", "hall", "cave", "cathedral"}
VALID_TONES = {
    "gules", "tenne", "or", "amber", "vert", "sea",
    "azure", "indigo", "purpure", "rose", "earth", "stone",
}


def load_campaign_defaults(config_override: str | None = None) -> tuple[Path, str]:
    cfg_path = Path(config_override).resolve() if config_override else (REPO_ROOT / "campaign.config.json")
    vault_dir: Path | None = None
    collection = "Campaign"
    if cfg_path.is_file():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            vval = cfg.get("vault_dir")
            if isinstance(vval, str) and vval.strip():
                cand = (cfg_path.parent / vval).resolve()
                if cand.is_dir():
                    vault_dir = cand
            cval = cfg.get("atlas_collection")
            if isinstance(cval, str) and cval.strip():
                collection = cval.strip()
        except Exception:
            pass

    if vault_dir is None:
        for base in (Path.cwd(), REPO_ROOT):
            if (base / "atlas-vtt").is_dir():
                vault_dir = base.resolve()
                break
            for name in ("Vault", "template-vault"):
                cand = base / name
                if (cand / "atlas-vtt").is_dir():
                    vault_dir = cand.resolve()
                    break
            if vault_dir is not None:
                break

    if vault_dir is None:
        raise FileNotFoundError(
            "Cannot locate vault directory containing 'atlas-vtt/'. Pass --vault <path>."
        )
    return vault_dir, collection


def resolve_vault_and_collection(args) -> tuple[Path, str]:
    default_vault, default_col = load_campaign_defaults(getattr(args, "config", None))
    vault = Path(args.vault).resolve() if getattr(args, "vault", None) else default_vault
    collection = getattr(args, "collection", None) or default_col
    return vault, collection


def slugify(text: str) -> str:
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:40] or "track"


def deterministic_sound_id(audio_path: str) -> str:
    digest = hashlib.sha1(audio_path.encode("utf-8")).hexdigest()[:10]
    stem = slugify(Path(audio_path).stem)[:24]
    return f"sound-{stem}-{digest}"


def scan_audio_library(vault: Path) -> dict[str, dict]:
    """Scan sounds/music/ and sounds/ambience/, indexing by POSIX vault path and stem."""
    sounds_dir = vault / "atlas-vtt" / "sounds"
    by_path: dict[str, dict] = {}
    by_name: dict[str, list[dict]] = {}

    for kind in ("music", "ambience"):
        root = sounds_dir / kind
        if not root.is_dir():
            continue
        for dirpath, _, filenames in os.walk(root):
            for fn in sorted(filenames):
                ext = Path(fn).suffix.lower()
                if ext not in AUDIO_EXTS:
                    continue
                full = Path(dirpath) / fn
                rel = full.relative_to(vault).as_posix()
                stem = Path(fn).stem
                entry = {
                    "audioPath": rel,
                    "fullPath": full,
                    "name": stem,
                    "kind": kind,
                    "audioSize": full.stat().st_size,
                }
                by_path[rel] = entry
                by_name.setdefault(stem.lower(), []).append(entry)
    return {"by_path": by_path, "by_name": by_name}


def load_existing_records(vault: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    """Return (by_audio_path, by_id) from <Vault>/atlas-vtt/sounds/records/*.json."""
    rec_dir = vault / "atlas-vtt" / "sounds" / "records"
    by_path: dict[str, dict] = {}
    by_id: dict[str, dict] = {}
    if not rec_dir.is_dir():
        return by_path, by_id
    for jf in sorted(rec_dir.glob("*.json")):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and data.get("id") and data.get("audioPath"):
            by_path[data["audioPath"]] = data
            by_id[data["id"]] = data
    return by_path, by_id


def resolve_audio_ref(ref: str, kind: str, library: dict) -> dict:
    """Resolve either an exact vault-relative audioPath or a track stem name."""
    by_path = library["by_path"]
    by_name = library["by_name"]
    norm_path = ref.replace("\\", "/")

    if norm_path in by_path:
        return by_path[norm_path]

    matches = [m for m in by_name.get(ref.lower(), []) if m["kind"] == kind]
    if not matches:
        norm_ref = ref.lower().replace("\u2019", "'")
        for key, items in by_name.items():
            if key.replace("\u2019", "'") == norm_ref:
                matches.extend(m for m in items if m["kind"] == kind)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        inst = [m for m in matches if "/instrumental/" in m["audioPath"].lower()]
        if len(inst) == 1:
            return inst[0]
        paths = ", ".join(m["audioPath"] for m in matches)
        raise ValueError(f"Ambiguous {kind} track '{ref}': matches [{paths}]")
    raise FileNotFoundError(f"Track not found ({kind}): '{ref}'")


def ensure_sound_record(
    vault: Path,
    entry: dict,
    rec_by_path: dict[str, dict],
    rec_by_id: dict[str, dict],
    now_ms: int,
) -> tuple[str, bool]:
    """Reuse existing record by audioPath or write a new native Atlas record JSON."""
    existing = rec_by_path.get(entry["audioPath"])
    if existing:
        return existing["id"], False

    sid = deterministic_sound_id(entry["audioPath"])
    record = {
        "format": 1,
        "id": sid,
        "name": entry["name"],
        "tags": [],
        "createdAt": now_ms,
        "modifiedAt": now_ms,
        "audioPath": entry["audioPath"],
        "audioSize": entry["audioSize"],
        "kind": entry["kind"],
    }
    rec_dir = vault / "atlas-vtt" / "sounds" / "records"
    rec_dir.mkdir(parents=True, exist_ok=True)
    out = rec_dir / f"{sid}.json"
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    rec_by_path[entry["audioPath"]] = record
    rec_by_id[sid] = record
    return sid, True


def cmd_inventory(args) -> int:
    vault, _ = resolve_vault_and_collection(args)
    lib = scan_audio_library(vault)
    rec_by_path, _ = load_existing_records(vault)
    moods_dir = vault / "atlas-vtt" / "sounds" / "moods"
    mood_files = sorted(moods_dir.glob("*.json")) if moods_dir.is_dir() else []

    music_count = sum(1 for v in lib["by_path"].values() if v["kind"] == "music")
    amb_count = sum(1 for v in lib["by_path"].values() if v["kind"] == "ambience")
    print(f"Vault: {vault}")
    print(f"Library: {music_count} music file(s), {amb_count} ambience file(s)")
    print(f"Sound records: {len(rec_by_path)} | Moods: {len(mood_files)}")

    if args.list_ambience:
        print("\nAmbience files:")
        for v in sorted(lib["by_path"].values(), key=lambda x: x["audioPath"]):
            if v["kind"] == "ambience":
                print(f"  - {v['name']} ({v['audioPath']})")

    if mood_files:
        print("\nExisting moods:")
        for mf in mood_files:
            d = json.loads(mf.read_text(encoding="utf-8"))
            m = d.get("music")
            tcount = len(m.get("tracks", [])) if isinstance(m, dict) else m
            print(
                f"  [{d.get('order', '?')}] {d.get('name')} ({d.get('id')}) "
                f"| room={d.get('room')} | music={tcount} | layers={len(d.get('layers', []))}"
            )
    return 0


def cmd_build_moods(args) -> int:
    vault, _ = resolve_vault_and_collection(args)
    cfg = json.loads(Path(args.moods_config).read_text(encoding="utf-8"))
    lib = scan_audio_library(vault)
    rec_by_path, rec_by_id = load_existing_records(vault)
    moods_dir = vault / "atlas-vtt" / "sounds" / "moods"
    moods_dir.mkdir(parents=True, exist_ok=True)

    now_ms = int(time.time() * 1000)
    created_records = 0
    reused_records = 0
    written_moods = 0

    for idx, mcfg in enumerate(cfg.get("moods", [])):
        mid = mcfg["id"]
        name = mcfg["name"]
        order = mcfg.get("order", idx)
        fade = mcfg.get("fadeSeconds", 4)
        room = mcfg.get("room", "room")
        tone = mcfg.get("tone")
        icon = mcfg.get("icon")

        if room not in VALID_ROOMS:
            raise ValueError(f"Mood '{name}': invalid room '{room}'")
        if tone and tone not in VALID_TONES:
            raise ValueError(f"Mood '{name}': invalid tone '{tone}'")

        music_cfg = mcfg.get("music", "keep")
        if isinstance(music_cfg, str):
            music_out: dict | str = music_cfg
        else:
            track_ids = []
            for tref in music_cfg.get("tracks", []):
                entry = resolve_audio_ref(tref, "music", lib)
                sid, created = ensure_sound_record(vault, entry, rec_by_path, rec_by_id, now_ms)
                created_records += int(created)
                reused_records += int(not created)
                track_ids.append(sid)
            music_out = {
                "tracks": track_ids,
                "shuffle": bool(music_cfg.get("shuffle", True)),
                "levelDb": float(music_cfg.get("levelDb", 0)),
            }
            if music_cfg.get("repeat") in ("one", "off"):
                music_out["repeat"] = music_cfg["repeat"]
            if music_cfg.get("reverb", 0) > 0:
                music_out["reverb"] = min(1.0, float(music_cfg["reverb"]))

        layers_out = []
        for lcfg in mcfg.get("layers", []):
            entry = resolve_audio_ref(lcfg["sound"], "ambience", lib)
            sid, created = ensure_sound_record(vault, entry, rec_by_path, rec_by_id, now_ms)
            created_records += int(created)
            reused_records += int(not created)
            layer: dict = {
                "sound": sid,
                "levelDb": float(lcfg.get("levelDb", -6)),
            }
            if lcfg.get("reverb", 0) > 0:
                layer["reverb"] = min(1.0, float(lcfg["reverb"]))
            layers_out.append(layer)

        mood_doc: dict = {
            "format": 1,
            "id": mid,
            "name": name,
            "order": order,
            "fadeSeconds": fade,
            "music": music_out,
            "layers": layers_out,
        }
        if icon:
            mood_doc["icon"] = icon
        if tone:
            mood_doc["tone"] = tone
        if room:
            mood_doc["room"] = room

        out_path = moods_dir / f"{mid}.json"
        out_path.write_text(json.dumps(mood_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        written_moods += 1
        t_summary = f"{len(music_out['tracks'])} track(s)" if isinstance(music_out, dict) else music_out
        print(f"  [OK] {name} ({mid}) -> {t_summary}, {len(layers_out)} ambience layer(s), room={room}")

    print(f"\nDone: {written_moods} mood(s) written | {created_records} new record(s) created, {reused_records} reused.")
    return 0


def link_single_scene(scene_path: Path, mood_id: str | None, combat_mood_id: str | None) -> None:
    data = json.loads(scene_path.read_text(encoding="utf-8"))
    st = data["state"]
    sound = dict(st.get("sound") or {})
    if mood_id:
        sound["mood"] = mood_id
    if combat_mood_id:
        sound["combatMood"] = combat_mood_id
    if sound:
        st["sound"] = sound
    scene_path.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"  [LINKED] {scene_path.name} -> mood={sound.get('mood')} | combatMood={sound.get('combatMood')}")


def cmd_link_scene(args) -> int:
    link_single_scene(Path(args.atlasmap), args.mood, args.combat_mood)
    return 0


def cmd_link_all(args) -> int:
    vault, default_col = resolve_vault_and_collection(args)
    cfg = json.loads(Path(args.moods_config).read_text(encoding="utf-8"))
    collection = getattr(args, "collection", None) or cfg.get("collection") or default_col
    scenes_dir = vault / "atlas-vtt" / "collections" / collection / "scenes"
    for scfg in cfg.get("sceneLinks", []):
        sp = scenes_dir / scfg["scene"]
        if not sp.is_file():
            print(f"  [SKIP] Scene not found: {sp}")
            continue
        link_single_scene(sp, scfg.get("mood"), scfg.get("combatMood"))
    return 0


def cmd_validate(args) -> int:
    vault, _ = resolve_vault_and_collection(args)
    _, rec_by_id = load_existing_records(vault)
    moods_dir = vault / "atlas-vtt" / "sounds" / "moods"
    errors: list[str] = []
    warnings: list[str] = []
    mood_ids: set[str] = set()

    # 1. Validate records
    for sid, rec in rec_by_id.items():
        ap = rec["audioPath"]
        if "\\" in ap:
            errors.append(f"Record {sid}: audioPath uses Windows backslashes: {ap}")
        fp = vault / ap.replace("\\", "/")
        if not fp.is_file():
            errors.append(f"Record {sid} ({rec.get('name')}) points to missing file: {ap}")

    # 2. Validate moods
    if moods_dir.is_dir():
        for mf in sorted(moods_dir.glob("*.json")):
            d = json.loads(mf.read_text(encoding="utf-8"))
            mid = d.get("id")
            if not mid:
                errors.append(f"Mood file {mf.name} missing id")
                continue
            mood_ids.add(mid)
            if d.get("room") and d["room"] not in VALID_ROOMS:
                errors.append(f"Mood {mid}: invalid room '{d['room']}'")
            if d.get("tone") and d["tone"] not in VALID_TONES:
                errors.append(f"Mood {mid}: invalid tone '{d['tone']}'")
            m = d.get("music")
            if isinstance(m, dict):
                for tid in m.get("tracks", []):
                    if tid not in rec_by_id:
                        errors.append(f"Mood {mid}: missing music track record '{tid}'")
            for lay in d.get("layers", []):
                if lay.get("sound") not in rec_by_id:
                    errors.append(f"Mood {mid}: missing ambience record '{lay.get('sound')}'")

    # 3. Validate scene links across all collections (or the specified collection)
    cols_root = vault / "atlas-vtt" / "collections"
    scene_paths: list[Path] = []
    if getattr(args, "collection", None):
        sdir = cols_root / args.collection / "scenes"
        if sdir.is_dir():
            scene_paths.extend(sorted(sdir.glob("*.atlasmap")))
    elif cols_root.is_dir():
        for sdir in sorted(cols_root.glob("*/scenes")):
            scene_paths.extend(sorted(sdir.glob("*.atlasmap")))

    linked_count = 0
    for sp in scene_paths:
        d = json.loads(sp.read_text(encoding="utf-8"))
        snd = (d.get("state") or {}).get("sound") or {}
        if snd:
            linked_count += 1
            for key in ("mood", "combatMood"):
                ref = snd.get(key)
                if ref and ref not in mood_ids:
                    errors.append(f"Scene {sp.name}: {key}='{ref}' does not exist in sounds/moods/")

    print(f"Validated {len(rec_by_id)} record(s), {len(mood_ids)} mood(s), {linked_count} linked scene(s).")
    for w in warnings:
        print(f"WARNING: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    if errors:
        return 1
    print("Validation PASSED.")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="Atlas VTT 0.19.0+ Sound & Moods Tool (Prep Goblin)")
    ap.add_argument("--vault", help="Vault root directory override (defaults to campaign.config.json)")
    ap.add_argument("--collection", help="Atlas VTT collection override")
    ap.add_argument("--config", help="Optional path to campaign.config.json")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_inv = sub.add_parser("inventory", help="List available local music/ambience, records, and moods")
    p_inv.add_argument("--list-ambience", action="store_true")
    p_inv.set_defaults(func=cmd_inventory)

    p_build = sub.add_parser("build-moods", help="Build sound records and moods from a JSON config")
    p_build.add_argument("moods_config", help="Path to moods config JSON")
    p_build.set_defaults(func=cmd_build_moods)

    p_link = sub.add_parser("link-scene", help="Link mood and combatMood to a closed .atlasmap scene")
    p_link.add_argument("atlasmap")
    p_link.add_argument("--mood")
    p_link.add_argument("--combat-mood")
    p_link.set_defaults(func=cmd_link_scene)

    p_link_all = sub.add_parser("link-all", help="Link all scenes defined in sceneLinks of a moods config JSON")
    p_link_all.add_argument("moods_config")
    p_link_all.set_defaults(func=cmd_link_all)

    p_val = sub.add_parser("validate", help="Validate all sound records, moods, and scene links")
    p_val.set_defaults(func=cmd_validate)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
