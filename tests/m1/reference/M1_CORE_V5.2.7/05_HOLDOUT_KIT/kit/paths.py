"""Locate the M1 core package and make its pinned tools importable (no copies, no edits)."""
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
CORE_ROOT = KIT_ROOT.parent
TOOLS = CORE_ROOT / '04_TOOLS'
SCHEMA = CORE_ROOT / '01_M1a' / 'HOLDOUT-TEMPLATE-SCHEMA.json'
YAML = CORE_ROOT / '01_M1a' / 'AKZEPTANZGRENZEN.yaml'
FAMILY_SCHEMA = KIT_ROOT / 'FAMILY-SPEC-SCHEMA.json'

if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
