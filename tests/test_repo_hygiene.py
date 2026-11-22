"""Repository hygiene regression tests: English-only, zero spoilers, valid configs."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import yaml

from conftest import REPO_ROOT, TEMPLATE_VAULT

TEXT_EXTENSIONS = {
    ".md",
    ".py",
    ".json",
    ".yml",
    ".yaml",
    ".base",
    ".mdc",
    ".txt",
    ".atlasmap",
}

SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    "node_modules",
}

# Accented Italian vowel characters (escaped so this file itself stays strictly ASCII-clean)
ITALIAN_ACCENT_RE = re.compile(r"[\u00e0\u00e8\u00e9\u00ec\u00f2\u00f9\u00c0\u00c8\u00c9\u00cc\u00d2\u00d9]")

# Hardcoded personal user home paths must never appear in tracked text files
LOCAL_USER_PATH_RE = re.compile(
    r"(?:[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s]+|/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/)"
)

WORD_RE = re.compile(r"[A-Za-z]+")

# SHA-256 digests of blocked lowercased terms (copyrighted D&D setting names & Italian TTRPG nouns)
# Stored as digests so zero sensitive or non-English terms exist literally anywhere in the repo.
BLOCKED_TERM_SHA256 = {
    "70bea1991c3ad7cf32836cfc92d27df74da970cb24e3e52b8c57a7e371dc2b29",
    "31422abcade6d37c0935c99daebdd02849133cdb0ed9bcc4ce89badcabff3636",
    "77b23442c5b935aba5e275ded4d32179f1e50d23e0802be887524bb851feec8c",
    "480115c3a83ae45d184e579732a798842f45036964a9c9e290bc45791c8c1b99",
    "a29e0b78917dad44559b8b11f87b55b3bb95cf3ac353a593af9a24933d6cc2d0",
    "522183afe6ac960e19cca2b07c415c77fd51586def37f3f56022e8517545d966",
    "b6fd8e9ec9a48397961b65cb2b70f79cda08c9b363cdaa1ecb8f457dfa7aec93",
    "de645af5814894825f604813f819800952a074e4123e1381b43a3f8a1e6d6632",
    "bd1a2dad3d1a1dbd195f8ec6574be8abfdfa4ae7bc270693e967a3412f23a741",
    "bba62c27abe42846526073b050f37bc7e8f27cb78b6cd3a35337fdf2c6351608",
    "f292d7b4a1ed9dacf4ee91e31fde51fdb9ab171138e2b41be2fe37ad307ca23f",
    "1aa2cdc98541f2b9bf4f59d64e965639bacf555b6ecc6e6113843918fe41735c",
    "c966fffc189856665838c354f0d7ef58b90386492ac919e9fe760473364f41ef",
    "c9c906e8256a4f07248e8e44a129e8410f6d409b660380375f0b29d4d0234165",
    "e52912179933ac35ff66f8e12122271b04c637d645e2e1067c233396c70e2d57",
    "76d433533ef9ca327b698a0c62fe27860b18abc70de893d9b1998b069cd46633",
    "7fec1d8b64612e783aa7a867d3c984571e3a5ec4dcfd4fbec7d25dac770dd278",
    "93c82570924729bc3bf2af3096aae693bc7ff3601e87d2f3b50adbb8194836cd",
    "f87c969b6eaa44eea659de19619049ccf78ed6b7d19967ca1148b1cb57158134",
    "6e4166fa1a7a44cb7e437ffe3a0decf080cc94bff1662a9f2f3ce26afc5f0382",
    "eb28c4a6d772b8edd143298b33b875f2866c5da385f6dee21054b695d42fede7",
    "34029020c46f584b995fb511fbdd0f7d868a224ecfeab576ddada51f2a3768c9",
    "5cf0c40b6191ab10ea4b728f3d81b9af66230e4a75d75190a71fba22d7a95381",
    "80b67c89f4a23386d71a082fb4f346e485d25bfdc49b38b1f6e68c3ad51417b5",
    "b65a77ab7b8c7c63df3eece78c0a89b4d0865e887138ffd449219c115e9d4948",
    "c74d5ba5d94c8bd5ab2308ace06a65dd9056d2594941de10d16bfcbf9e42e2dd",
    "5567ecdea32955e7db7b34381a0fe4c38003bfe44915795c6d67dd5c58d173e1",
}


def iter_repo_text_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(REPO_ROOT.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_EXTENSIONS:
            files.append(path)
    return files


def test_zero_italian_accented_characters_across_repo() -> None:
    violations: list[str] = []
    for path in iter_repo_text_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            found = ITALIAN_ACCENT_RE.findall(line)
            if found:
                violations.append(f"{rel}:{lineno}: accented chars {sorted(set(found))}")
    assert not violations, "Italian accented characters found:\n" + "\n".join(violations)


def test_zero_sensitive_campaign_terms_or_local_paths_across_repo() -> None:
    violations: list[str] = []
    for path in iter_repo_text_files():
        rel = path.relative_to(REPO_ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if LOCAL_USER_PATH_RE.search(line):
                violations.append(f"{rel}:{lineno}: local user path detected")
            for token in WORD_RE.findall(line):
                digest = hashlib.sha256(token.lower().encode("utf-8")).hexdigest()
                if digest in BLOCKED_TERM_SHA256:
                    violations.append(f"{rel}:{lineno}: blocked term '{token}'")
    assert not violations, "Repository hygiene violations found:\n" + "\n".join(violations)


def test_template_vault_bases_and_json_integrity() -> None:
    # All Obsidian .base files must parse as valid YAML with expected views
    base_files = sorted(TEMPLATE_VAULT.rglob("*.base"))
    assert len(base_files) >= 2
    for bf in base_files:
        parsed = yaml.safe_load(bf.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict), f"Invalid YAML object in {bf}"
        assert "views" in parsed and isinstance(parsed["views"], list)

    # All JSON and .atlasmap files in repo config & template-vault must parse cleanly
    json_files = [REPO_ROOT / "campaign.config.json"]
    json_files.extend(sorted(TEMPLATE_VAULT.rglob("*.json")))
    json_files.extend(sorted(TEMPLATE_VAULT.rglob("*.atlasmap")))
    for jf in json_files:
        parsed = json.loads(jf.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict), f"Invalid JSON root object in {jf}"

    # Ensure collection.json wires Items/Loot.base into lootBases
    col_cfg = json.loads(
        (TEMPLATE_VAULT / "atlas-vtt" / "collections" / "Campaign" / "collection.json").read_text(
            encoding="utf-8"
        )
    )
    assert "Items/Loot.base" in col_cfg.get("settings", {}).get("lootBases", [])

    # Ensure GitHub Actions CI workflow parses as valid YAML
    ci_path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    assert ci_path.is_file()
    ci_cfg = yaml.safe_load(ci_path.read_text(encoding="utf-8"))
    assert isinstance(ci_cfg, dict)
    assert "jobs" in ci_cfg and "test-and-validate" in ci_cfg["jobs"]

    # Ensure .gitignore guards private source folders
    gitignore_txt = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    for folder in ("Sources/", "Manuals/", "Reference/", "Archive/"):
        assert folder in gitignore_txt

