"""Cloud entrypoint for Streamlit Community Cloud.

Streamlit Cloud can run this root file directly. The real dashboard lives in
app/dashboard.py so local launchers and cloud deployment use the same UI.
"""

from __future__ import annotations

import runpy
from pathlib import Path


runpy.run_path(str(Path(__file__).parent / "app" / "dashboard.py"), run_name="__main__")

