"""Cloud entrypoint for Streamlit Community Cloud."""

from __future__ import annotations

import runpy
from pathlib import Path

import streamlit as st

try:
    from app.refresh_stamp import REFRESH_RUN_ID, REFRESH_STAMP_UTC
except Exception:
    REFRESH_RUN_ID = "unknown"
    REFRESH_STAMP_UTC = "unknown"


ROOT = Path(__file__).resolve().parent
st.session_state["_refresh_stamp_utc"] = REFRESH_STAMP_UTC
st.session_state["_refresh_run_id"] = REFRESH_RUN_ID
runpy.run_path(str(ROOT / "app" / "dashboard.py"), run_name="__main__")

# Narrow, late-loading fix for the Math Appendix only. The previous broad guard
# repainted unrelated mobile controls, so keep this scoped to the final tab panel.
st.markdown(
    """
    <style>
    div[data-testid="stTabs"] div[role="tabpanel"]:last-child [data-testid="stMarkdownContainer"] pre,
    div[data-testid="stTabs"] div[role="tabpanel"]:last-child [data-testid="stMarkdownContainer"] code,
    div[data-testid="stTabs"] div[role="tabpanel"]:last-child [data-testid="stMarkdownContainer"] blockquote,
    div[data-testid="stTabs"] div[role="tabpanel"]:last-child [data-testid="stMarkdownContainer"] table {
        background: linear-gradient(135deg, #fffbea, #f0fdf4) !important;
        border: 1px solid #bbf7d0 !important;
        border-radius: 8px !important;
        box-shadow: 0 0 0 1px rgba(187, 247, 208, .45), 0 10px 26px rgba(132, 204, 22, .10) !important;
    }
    div[data-testid="stTabs"] div[role="tabpanel"]:last-child [data-testid="stMarkdownContainer"] pre,
    div[data-testid="stTabs"] div[role="tabpanel"]:last-child [data-testid="stMarkdownContainer"] pre *,
    div[data-testid="stTabs"] div[role="tabpanel"]:last-child [data-testid="stMarkdownContainer"] code,
    div[data-testid="stTabs"] div[role="tabpanel"]:last-child [data-testid="stMarkdownContainer"] blockquote,
    div[data-testid="stTabs"] div[role="tabpanel"]:last-child [data-testid="stMarkdownContainer"] blockquote *,
    div[data-testid="stTabs"] div[role="tabpanel"]:last-child [data-testid="stMarkdownContainer"] table,
    div[data-testid="stTabs"] div[role="tabpanel"]:last-child [data-testid="stMarkdownContainer"] table * {
        color: #0f172a !important;
        text-shadow: none !important;
    }
    @media (max-width: 900px) {
        div[data-testid="stTabs"] div[role="tabpanel"]:last-child [data-testid="stMarkdownContainer"] pre,
        div[data-testid="stTabs"] div[role="tabpanel"]:last-child [data-testid="stMarkdownContainer"] code {
            white-space: pre-wrap !important;
            word-break: break-word !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)
