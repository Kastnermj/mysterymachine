"""Cloud entrypoint for Streamlit Community Cloud."""

from __future__ import annotations

import runpy
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
runpy.run_path(str(ROOT / "app" / "dashboard_runtime_patch.py"), run_name="__main__")

# Late-loading contrast guard for Streamlit mobile markdown/expander/code blocks.
st.markdown(
    """
    <style>
    div[data-testid="stExpander"],
    div[data-testid="stExpander"] *,
    div[data-testid="stCode"],
    div[data-testid="stCode"] *,
    [data-testid="stMarkdownContainer"] pre,
    [data-testid="stMarkdownContainer"] pre *,
    [data-testid="stMarkdownContainer"] code,
    [data-testid="stMarkdownContainer"] table,
    [data-testid="stMarkdownContainer"] table *,
    [data-testid="stMarkdownContainer"] blockquote,
    [data-testid="stMarkdownContainer"] blockquote * {
        color: #0f172a !important;
        text-shadow: none !important;
    }
    div[data-testid="stExpander"],
    div[data-testid="stExpander"] details,
    div[data-testid="stExpander"] summary,
    div[data-testid="stCode"],
    [data-testid="stMarkdownContainer"] pre,
    [data-testid="stMarkdownContainer"] table,
    [data-testid="stMarkdownContainer"] blockquote {
        background: #ffffff !important;
        border-color: #cbd5e1 !important;
    }
    [data-testid="stMarkdownContainer"] code,
    div[data-testid="stExpander"] code {
        background: #eef4ff !important;
        border: 1px solid #c8d9ff !important;
        border-radius: 6px !important;
        padding: .08rem .28rem !important;
    }
    @media (max-width: 900px) {
        [data-testid="stMarkdownContainer"],
        [data-testid="stMarkdownContainer"] *,
        div[data-testid="stExpander"],
        div[data-testid="stExpander"] * {
            color: #0f172a !important;
            text-shadow: none !important;
        }
        [data-testid="stMarkdownContainer"] pre,
        [data-testid="stMarkdownContainer"] code,
        div[data-testid="stExpander"] pre,
        div[data-testid="stExpander"] code {
            white-space: pre-wrap !important;
            word-break: break-word !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)
