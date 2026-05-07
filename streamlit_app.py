"""Cloud entrypoint for Streamlit Community Cloud."""

from __future__ import annotations

import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
runpy.run_path(str(ROOT / "app" / "dashboard_runtime_patch.py"), run_name="__main__")
