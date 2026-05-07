"""Runtime patch layer for the hosted Mystery Machine dashboard.

This keeps the hosted app readable without moving the working controls out of
the sidebar. The real dashboard remains app/dashboard.py; this file applies
small hosted UI fixes at startup without changing the model math or data files.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "app" / "dashboard.py"

EXTRA_CSS = """
<style>
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
section[data-testid="stSidebar"] {
    background: #f7f9fd !important;
    border-right: 1px solid #d7deea !important;
    min-width: 18rem !important;
    max-width: 22rem !important;
}
section[data-testid="stSidebar"] * {
    color: #0f172a !important;
    text-shadow: none !important;
}
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
.block-container p,
.block-container li,
.block-container label,
.block-container span,
.block-container div {
    text-shadow: none !important;
}
</style>
"""


def patched_dashboard_source() -> str:
    """Return dashboard source with hosted UI fixes applied."""
    source = SOURCE_PATH.read_text(encoding="utf-8")

    source = source.replace(
        'st.set_page_config(page_title="Contrarian 10-Bagger Engine", layout="wide")',
        'st.set_page_config(page_title="Contrarian 10-Bagger Engine", layout="wide", initial_sidebar_state="expanded")\n'
        'st.markdown(EXTRA_CSS, unsafe_allow_html=True)',
        1,
    )
    source = source.replace(
        'top_n = st.slider("Rows to show", 10, 500, 100, 10)',
        'top_n = st.slider("Rows to show", 10, 500, 250, 10)',
        1,
    )
    source = source.replace('"Math Playbook"', '"Math Appendix"')
    source = source.replace('st.subheader("Top 100 Research Batch")', 'st.subheader("Top 250 Research Batch")', 1)
    return source


code = compile(patched_dashboard_source(), str(SOURCE_PATH), "exec")
exec(code, globals())
