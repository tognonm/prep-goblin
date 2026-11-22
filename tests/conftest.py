"""Shared pytest helpers and paths for the Demiurge Core CLI test suite."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_VAULT = REPO_ROOT / "template-vault"

SCRIPT_LINT = REPO_ROOT / "scripts" / "lint_vault.py"
SCRIPT_SYNC_ADAPTERS = REPO_ROOT / "scripts" / "sync_agent_adapters.py"
SCRIPT_INIT_CAMPAIGN = REPO_ROOT / "scripts" / "init_campaign.py"
SCRIPT_EXPORT_PORTAL = REPO_ROOT / "scripts" / "export_player_view.py"
SCRIPT_CONTEXT_PACK = REPO_ROOT / "scripts" / "build_context_pack.py"
SCRIPT_PREP_TRANSCRIPT = REPO_ROOT / "scripts" / "prep_transcript.py"
SCRIPT_BUILD_ENCOUNTER = REPO_ROOT / "scripts" / "build_encounter.py"

SCRIPT_QUICK_BATTLEMAP = (
    REPO_ROOT / ".agents" / "skills" / "quick-battlemap" / "scripts" / "quick_battlemap.py"
)
SCRIPT_ATLAS_TOOLS = (
    REPO_ROOT / ".agents" / "skills" / "dungeons-and-maps" / "scripts" / "atlas_scene_tools.py"
)
SCRIPT_ROLL_TABLES = (
    REPO_ROOT / ".agents" / "skills" / "live-improv" / "scripts" / "roll_tables.py"
)
SCRIPT_REGISTER_TOKEN = (
    REPO_ROOT / ".agents" / "skills" / "atlas-token-art" / "scripts" / "register_token.py"
)

DEMO_SCENE = (
    TEMPLATE_VAULT
    / "atlas-vtt"
    / "collections"
    / "Campaign"
    / "scenes"
    / "Demo - Oakhaven Alley.atlasmap"
)
DEMO_DASHBOARD = (
    TEMPLATE_VAULT
    / "atlas-vtt"
    / "collections"
    / "Campaign"
    / "notes"
    / "Demo - Oakhaven Alley.md"
)


def run_cli(
    script_path: Path,
    *args: str | Path,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a Demiurge Core Python CLI script with deterministic UTF-8 I/O."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    cmd = [sys.executable, str(script_path), *(str(a) for a in args)]
    return subprocess.run(
        cmd,
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


@pytest.fixture
def isolated_vault(tmp_path: Path) -> Path:
    """Return a fresh mutable copy of template-vault/ inside tmp_path."""
    dst = tmp_path / "vault"
    shutil.copytree(
        TEMPLATE_VAULT,
        dst,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "Thumbs.db"),
    )
    return dst
