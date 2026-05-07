"""Cloud entrypoint for Streamlit Community Cloud.

Streamlit Cloud can run this root file directly. The real dashboard lives in
app/dashboard.py so local launchers and cloud deployment use the same UI.
"""

from __future__ import annotations

import runpy
from pathlib import Path

import streamlit as st


st.markdown(
    """
    <style>
    /* Hard override for Streamlit tabs on desktop and mobile. */
    div[data-testid="stTabs"] div[role="tablist"] {
        background: #ffffff !important;
        border: 2px solid #111827 !important;
        border-radius: 10px !important;
        padding: 6px !important;
        gap: 4px !important;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.18) !important;
    }

    div[data-testid="stTabs"] button[role="tab"] {
        background: #f8fafc !important;
        border: 1px solid #94a3b8 !important;
        border-radius: 8px !important;
        color: #0f172a !important;
        font-weight: 900 !important;
        padding: 10px 14px !important;
        opacity: 1 !important;
    }

    div[data-testid="stTabs"] button[role="tab"] * {
        color: #0f172a !important;
        font-weight: 900 !important;
        opacity: 1 !important;
        text-shadow: none !important;
    }

    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        background: #111827 !important;
        border-color: #111827 !important;
        color: #ffffff !important;
    }

    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] * {
        color: #ffffff !important;
    }

    div[data-testid="stTabs"] button[role="tab"]:hover {
        background: #e2e8f0 !important;
        color: #020617 !important;
    }

    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"]:hover {
        background: #020617 !important;
        color: #ffffff !important;
    }

    /* The dashboard still creates the old 5th tab label. Rename it visually. */
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(5) p,
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(5) span {
        font-size: 0 !important;
    }

    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(5) p::after,
    div[data-testid="stTabs"] button[role="tab"]:nth-of-type(5) span::after {
        content: "Math Appendix" !important;
        font-size: 1rem !important;
        font-weight: 900 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

runpy.run_path(str(Path(__file__).parent / "app" / "dashboard.py"), run_name="__main__")
