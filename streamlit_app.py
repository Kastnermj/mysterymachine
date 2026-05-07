"""Cloud entrypoint for Streamlit Community Cloud.

Streamlit Cloud can run this root file directly. The real dashboard lives in
app/dashboard.py so local launchers and cloud deployment use the same UI.
"""

from __future__ import annotations

import runpy
from pathlib import Path

import streamlit as st


EARLY_UI_OVERRIDES = """
<style>
/* Initial tab readability before the dashboard loads. */
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

/* Hide the Mobile Lite tab button. The regular Big Board works better on mobile. */
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2) {
    display: none !important;
}

/* Rename the old 5th tab label visually. */
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
"""

FINAL_UI_OVERRIDES = """
<style>
/* Remove the old traveling color band/gradient that distorted text while scrolling. */
.stApp,
section.main,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background: #f5f7fb !important;
    background-image: none !important;
}

header[data-testid="stHeader"] {
    background: #f5f7fb !important;
    background-image: none !important;
}

/* Strong final tab override after dashboard CSS loads. */
div[data-testid="stTabs"] div[role="tablist"] {
    position: sticky !important;
    top: 0 !important;
    z-index: 999 !important;
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

/* Hide Mobile Lite tab. */
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2) {
    display: none !important;
}

/* Rename old Math Playbook visible label to Math Appendix. */
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

/* Make Scout Card ticker entry feel like an obvious search box. */
div[data-testid="stTextInput"] label p,
div[data-testid="stTextInput"] label,
div[data-testid="stTextInput"] label span {
    color: #0f172a !important;
    font-weight: 900 !important;
    font-size: 1.05rem !important;
}

div[data-testid="stTextInput"] input {
    background: #ffffff !important;
    color: #0f172a !important;
    border: 3px solid #2563eb !important;
    border-radius: 14px !important;
    min-height: 3.25rem !important;
    font-size: 1.25rem !important;
    font-weight: 900 !important;
    padding: 0.75rem 1rem !important;
    box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.14), 0 12px 28px rgba(15, 23, 42, 0.14) !important;
}

div[data-testid="stTextInput"] input:focus {
    border-color: #111827 !important;
    box-shadow: 0 0 0 5px rgba(17, 24, 39, 0.18), 0 14px 32px rgba(15, 23, 42, 0.18) !important;
}

/* General text safety after removing old dark/gradient background. */
.block-container,
.block-container p,
.block-container li,
.block-container label,
.block-container span,
.block-container div {
    text-shadow: none !important;
}
</style>
"""

st.markdown(EARLY_UI_OVERRIDES, unsafe_allow_html=True)

runpy.run_path(str(Path(__file__).parent / "app" / "dashboard.py"), run_name="__main__")

st.markdown(FINAL_UI_OVERRIDES, unsafe_allow_html=True)
