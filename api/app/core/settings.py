from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from gridboss_config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
