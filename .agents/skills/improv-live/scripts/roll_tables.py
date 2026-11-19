#!/usr/bin/env python3
"""Markdown rollable table engine for Obsidian + Atlas VTT live improvisation.

Dynamically discovers all rollable Markdown tables (`| dN | ... |`) inside
`<Vault>/Tabelle/`, supports configurable presets from `campaign.config.json`
(or `Tabelle/presets.json`), and allows targeted rolls on any file/sub-table.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import random
import re
import sys
import unicodedata


@dataclass(frozen=True)
class TableRow:
    low: int
    high: int
    cells: list[str]


@dataclass(frozen=True)
class RollTable:
    file_path: Path
    index: int
    title: str
    sides: int
    headers: list[str]
    rows: list[TableRow]


DEFAULT_PRESETS: dict[str, dict[str, object]] = {
    "demo-npc": {
        "label": "PNG al Volo (Tabella Demo)",
        "steps": [
            ("Tabella Demo - Spunti e Incontri Rapidi.md", [0]),
        ],
    },
    "demo-luogo": {
        "label": "Dettaglio Ambientale / Edificio (Tabella Demo)",
        "steps": [
            ("Tabella Demo - Spunti e Incontri Rapidi.md", [1]),
        ],
    },
    "demo-imprevisto": {
        "label": "Incontro o Imprevisto Rapido (Tabella Demo)",
        "steps": [
            ("Tabella Demo - Spunti e Incontri Rapidi.md", [2]),
        ],
    },
    "demo-scena": {
        "label": "Scena Completa Improvvisata (PNG + Dettaglio + Imprevisto)",
        "steps": [
            ("Tabella Demo - Spunti e Incontri Rapidi.md", [0, 1, 2]),
        ],
    },
}

DIE_HEADER_RE = re.compile(r"^(?:1)?d(\d+|%)$", re.IGNORECASE)
SEP_CELL_RE = re.compile(r"^:?-{1,}:?$")
RANGE_RE = re.compile(r"^(\d+)\s*[-–—]\s*(\d+)$")
SINGLE_NUM_RE = re.compile(r"^(\d+)$")
WIKILINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")


def find_repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def load_campaign_config(repo_root: Path) -> dict[str, object]:
    cfg_path = repo_root / "campaign.config.json"
    if cfg_path.is_file():
        try:
            return json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def find_tabelle_dir(explicit_dir: str | None = None, explicit_vault: str | None = None) -> Path:
    if explicit_dir:
        cand = Path(explicit_dir).resolve()
        if cand.is_dir():
            return cand
        raise FileNotFoundError(f"Directory delle tabelle non trovata: {cand}")

    if explicit_vault:
        cand = Path(explicit_vault).resolve() / "Tabelle"
        if cand.is_dir():
            return cand
        raise FileNotFoundError(f"Directory 'Tabelle' non trovata nel vault: {cand}")

    repo_root = find_repo_root()
    cfg = load_campaign_config(repo_root)
    vault_dir_cfg = cfg.get("vault_dir")
    if isinstance(vault_dir_cfg, str) and vault_dir_cfg.strip():
        cand = (repo_root / vault_dir_cfg / "Tabelle").resolve()
        if cand.is_dir():
            return cand

    for base in (repo_root, Path.cwd()):
        for vname in ("Vault", "template-vault"):
            cand = base / vname / "Tabelle"
            if cand.is_dir():
                return cand

    raise FileNotFoundError(
        "Impossibile trovare 'Vault/Tabelle' o 'template-vault/Tabelle'. Usa --tables-dir o --vault."
    )


def load_presets(tabelle_dir: Path, repo_root: Path) -> dict[str, dict[str, object]]:
    presets: dict[str, dict[str, object]] = {}

    cfg = load_campaign_config(repo_root)
    cfg_presets = cfg.get("roll_table_presets")
    if isinstance(cfg_presets, dict):
        presets.update(cfg_presets)

    local_presets = tabelle_dir / "presets.json"
    if local_presets.is_file():
        try:
            data = json.loads(local_presets.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                presets.update(data)
        except Exception:
            pass

    if not presets:
        presets = dict(DEFAULT_PRESETS)
    return presets


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return ascii_only.lower().strip()


def split_markdown_row(line: str) -> list[str]:
    """Split a Markdown table row while ignoring `|` inside `[[Link|Alias]]` or `\\|`."""
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]

    cells: list[str] = []
    current: list[str] = []
    bracket_depth = 0
    i = 0
    length = len(stripped)

    while i < length:
        ch = stripped[i]
        if ch == "\\" and i + 1 < length and stripped[i + 1] == "|":
            current.append("|")
            i += 2
            continue
        if ch == "[" and i + 1 < length and stripped[i + 1] == "[":
            bracket_depth += 1
            current.append("[[")
            i += 2
            continue
        if ch == "]" and i + 1 < length and stripped[i + 1] == "]" and bracket_depth > 0:
            bracket_depth -= 1
            current.append("]]")
            i += 2
            continue
        if ch == "|" and bracket_depth == 0:
            cells.append("".join(current).strip())
            current = []
            i += 1
            continue
        current.append(ch)
        i += 1

    cells.append("".join(current).strip())
    return cells


def strip_token_formatting(text: str) -> str:
    return text.replace("*", "").replace("_", "").replace("`", "").strip()


def clean_display_text(text: str, raw: bool = False) -> str:
    if raw:
        return text.strip()

    def _replace_wikilink(match: re.Match[str]) -> str:
        inner = match.group(1)
        if "|" in inner:
            return inner.split("|", 1)[1].strip()
        return inner.strip()

    cleaned = WIKILINK_RE.sub(_replace_wikilink, text)
    cleaned = cleaned.replace("**", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def parse_die_sides(header_cell: str) -> int | None:
    token = strip_token_formatting(header_cell)
    match = DIE_HEADER_RE.match(token)
    if not match:
        return None
    raw_sides = match.group(1)
    if raw_sides == "%":
        return 100
    sides = int(raw_sides)
    return sides if sides > 0 else None


def parse_range(cell: str, sides: int) -> tuple[int, int] | None:
    token = strip_token_formatting(cell)
    range_match = RANGE_RE.match(token)
    if range_match:
        low_s, high_s = range_match.group(1), range_match.group(2)
        low = 100 if (sides == 100 and low_s == "00") else int(low_s)
        high = 100 if (sides == 100 and high_s == "00") else int(high_s)
        return (min(low, high), max(low, high))

    single_match = SINGLE_NUM_RE.match(token)
    if single_match:
        num_s = single_match.group(1)
        val = 100 if (sides == 100 and num_s == "00") else int(num_s)
        return (val, val)

    return None


def is_separator_row(cells: list[str]) -> bool:
    if not cells:
        return False
    return all(bool(SEP_CELL_RE.match(c.strip())) for c in cells)


def strip_frontmatter(lines: list[str]) -> list[str]:
    if lines and lines[0].strip() == "---":
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                return lines[idx + 1 :]
    return lines


def parse_tables_from_file(file_path: Path) -> list[RollTable]:
    content = file_path.read_text(encoding="utf-8")
    lines = strip_frontmatter(content.splitlines())

    tables: list[RollTable] = []
    current_heading = file_path.stem
    i = 0
    total_lines = len(lines)

    while i < total_lines:
        stripped = lines[i].strip()
        heading_match = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        if heading_match:
            current_heading = heading_match.group(2).strip()
            i += 1
            continue

        if stripped.startswith("|") and stripped.endswith("|"):
            block: list[str] = []
            while i < total_lines:
                line_s = lines[i].strip()
                if line_s.startswith("|") and "|" in line_s[1:]:
                    block.append(line_s)
                    i += 1
                else:
                    break

            if len(block) >= 3:
                header_cells = split_markdown_row(block[0])
                sep_cells = split_markdown_row(block[1])
                sides = parse_die_sides(header_cells[0]) if header_cells else None

                if sides is not None and is_separator_row(sep_cells):
                    parsed_rows: list[TableRow] = []
                    for row_line in block[2:]:
                        cells = split_markdown_row(row_line)
                        if not cells:
                            continue
                        rng = parse_range(cells[0], sides)
                        if rng is None:
                            continue
                        parsed_rows.append(TableRow(low=rng[0], high=rng[1], cells=cells))

                    if parsed_rows:
                        tables.append(
                            RollTable(
                                file_path=file_path,
                                index=len(tables),
                                title=current_heading,
                                sides=sides,
                                headers=header_cells,
                                rows=parsed_rows,
                            )
                        )
            continue

        i += 1

    return tables


def load_all_tables(tabelle_dir: Path) -> dict[str, list[RollTable]]:
    catalog: dict[str, list[RollTable]] = {}
    for md_file in sorted(tabelle_dir.glob("*.md"), key=lambda p: p.name.lower()):
        parsed = parse_tables_from_file(md_file)
        if parsed:
            catalog[md_file.name] = parsed
    return catalog


def roll_on_table(table: RollTable, rng: random.Random) -> tuple[int, TableRow]:
    value = rng.randint(1, table.sides)
    for row in table.rows:
        if row.low <= value <= row.high:
            return value, row
    closest = min(table.rows, key=lambda r: min(abs(value - r.low), abs(value - r.high)))
    return value, closest


def format_row_result(table: RollTable, roll_value: int, row: TableRow, raw: bool = False) -> str:
    payload = [clean_display_text(cell, raw=raw) for cell in row.cells[1:] if cell.strip()]
    if len(payload) == 0:
        body = "(nessun contenuto)"
    elif len(payload) == 1:
        body = payload[0]
    elif len(payload) == 2:
        body = f"{payload[0]} — {payload[1]}"
    else:
        body = " | ".join(payload)

    return f"[{table.index}] {table.title} (d{table.sides} -> {roll_value})\n    {body}"


def resolve_file(catalog: dict[str, list[RollTable]], query: str) -> str:
    norm_q = normalize_text(query)
    exact_matches = [
        name
        for name in catalog
        if normalize_text(name) == norm_q or normalize_text(Path(name).stem) == norm_q
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]

    partial_matches = [name for name in catalog if norm_q in normalize_text(name)]
    if len(partial_matches) == 1:
        return partial_matches[0]
    if len(partial_matches) > 1:
        options = "\n".join(f"  - {m}" for m in partial_matches)
        raise ValueError(f"Query file ambigua '{query}'. File corrispondenti:\n{options}")
    available = "\n".join(f"  - {name}" for name in catalog)
    raise ValueError(f"Nessuna tabella rollabile trovata per '{query}'. File disponibili:\n{available}")


def cmd_list(
    tabelle_dir: Path,
    catalog: dict[str, list[RollTable]],
    presets: dict[str, dict[str, object]],
) -> int:
    print(f"TABELLE ROLLABILI IN {tabelle_dir}")
    print("=" * 64)
    total_tables = 0
    for filename, tables in catalog.items():
        print(f"\n- {filename}")
        for tbl in tables:
            total_tables += 1
            print(f"    [{tbl.index}] d{tbl.sides:<3} | {tbl.title} ({len(tbl.rows)} righe)")
    print(f"\nTotale: {len(catalog)} file, {total_tables} sotto-tabelle indicizzate.")
    print("\nPRESET DISPONIBILI (--preset <nome>):")
    for key, meta in presets.items():
        steps = meta.get("steps") if isinstance(meta, dict) else []
        ready = True
        if isinstance(steps, list):
            for step in steps:
                if isinstance(step, (list, tuple)) and len(step) >= 1 and step[0] not in catalog:
                    ready = False
                    break
        status = "" if ready else " [file non presente]"
        label = meta.get("label", "") if isinstance(meta, dict) else ""
        print(f"  - {key:<24} : {label}{status}")
    return 0


def cmd_preset(
    catalog: dict[str, list[RollTable]],
    presets: dict[str, dict[str, object]],
    preset_name: str,
    count: int,
    rng: random.Random,
    raw: bool,
) -> int:
    preset_key = normalize_text(preset_name)
    norm_map = {normalize_text(k): k for k in presets}
    if preset_key not in norm_map:
        valid = ", ".join(presets.keys())
        print(f"Errore: preset '{preset_name}' non riconosciuto. Validi: {valid}", file=sys.stderr)
        return 1

    real_key = norm_map[preset_key]
    preset = presets[real_key]
    label = str(preset.get("label", real_key))
    steps = preset.get("steps")
    if not isinstance(steps, list):
        print(f"Errore: preset '{real_key}' malformato.", file=sys.stderr)
        return 1

    for iteration in range(1, count + 1):
        suffix = f" (#{iteration}/{count})" if count > 1 else ""
        print(f"=== PRESET: {real_key}{suffix} — {label} ===")
        for step in steps:
            filename, table_indices = step[0], step[1]
            if filename not in catalog:
                print(
                    f"Errore: file '{filename}' richiesto dal preset '{real_key}' non trovato nella cartella Tabelle.",
                    file=sys.stderr,
                )
                return 1
            file_tables = catalog[filename]
            for idx in table_indices:
                if idx < 0 or idx >= len(file_tables):
                    print(
                        f"Errore: indice tabella {idx} fuori intervallo in '{filename}' (disponibili: 0..{len(file_tables) - 1}).",
                        file=sys.stderr,
                    )
                    return 1
                tbl = file_tables[idx]
                roll_val, row = roll_on_table(tbl, rng)
                print(format_row_result(tbl, roll_val, row, raw=raw))
        if iteration < count:
            print()

    return 0


def cmd_file(
    catalog: dict[str, list[RollTable]],
    file_query: str,
    table_arg: str,
    count: int,
    rng: random.Random,
    raw: bool,
) -> int:
    try:
        filename = resolve_file(catalog, file_query)
    except ValueError as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return 1

    file_tables = catalog[filename]
    if table_arg.lower() == "all":
        indices = list(range(len(file_tables)))
    else:
        try:
            idx = int(table_arg)
        except ValueError:
            print(f"Errore: --table deve essere un intero o 'all', ricevuto '{table_arg}'.", file=sys.stderr)
            return 1
        if idx < 0 or idx >= len(file_tables):
            print(
                f"Errore: indice {idx} non valido per '{filename}' (disponibili: 0..{len(file_tables) - 1}).",
                file=sys.stderr,
            )
            return 1
        indices = [idx]

    for iteration in range(1, count + 1):
        suffix = f" (#{iteration}/{count})" if count > 1 else ""
        print(f"=== {Path(filename).stem}{suffix} ===")
        for idx in indices:
            tbl = file_tables[idx]
            roll_val, row = roll_on_table(tbl, rng)
            print(format_row_result(tbl, roll_val, row, raw=raw))
        if iteration < count:
            print()

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tira sulle tabelle Markdown casuali in <Vault>/Tabelle/ per improvvisazione live (Obsidian + Atlas VTT)."
    )
    parser.add_argument("--vault", type=str, default=None, help="Percorso alternativo del vault (default: campaign.config.json).")
    parser.add_argument("--tables-dir", type=str, default=None, help="Percorso diretto alla cartella Tabelle/.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true", help="Elenca file, sotto-tabelle indicizzate e preset disponibili.")
    group.add_argument("--preset", type=str, help="Esegue un preset rapido configurato in campaign.config.json o Tabelle/presets.json.")
    group.add_argument("--file", type=str, help="Nome completo o parziale di un file .md in Tabelle/.")
    parser.add_argument("--table", type=str, default="0", help="Indice sotto-tabella (default: 0) o 'all'.")
    parser.add_argument("--count", type=int, default=1, help="Numero di tiri da eseguire (default: 1).")
    parser.add_argument("--seed", type=str, default=None, help="Seed opzionale per tiri riproducibili.")
    parser.add_argument("--raw", action="store_true", help="Mantiene wikilink e formattazione Markdown grezza.")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.count < 1:
        print("Errore: --count deve essere almeno 1.", file=sys.stderr)
        return 1

    repo_root = find_repo_root()
    try:
        tabelle_dir = find_tabelle_dir(args.tables_dir, args.vault)
    except FileNotFoundError as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return 1

    catalog = load_all_tables(tabelle_dir)
    if not catalog:
        print(f"Errore: nessuna tabella rollabile trovata in {tabelle_dir}.", file=sys.stderr)
        return 1

    presets = load_presets(tabelle_dir, repo_root)
    rng = random.Random(args.seed) if args.seed is not None else random.Random()

    if args.list:
        return cmd_list(tabelle_dir, catalog, presets)
    if args.preset:
        return cmd_preset(catalog, presets, args.preset, args.count, rng, args.raw)
    if args.file:
        return cmd_file(catalog, args.file, args.table, args.count, rng, args.raw)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
