"""Runtime patch layer for the hosted Mystery Machine dashboard.

This keeps the hosted app resilient when Streamlit hides the native sidebar.
The real dashboard remains app/dashboard.py; this file applies tiny UI fixes at
startup without changing the model math or the data files.
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
div[data-testid="stExpander"] details {
    background: #ffffff;
    border: 1px solid #d7deea;
    border-radius: 14px;
    box-shadow: 0 14px 32px rgba(15, 23, 42, .07);
}
div[data-testid="stExpander"] summary p {
    color: #111827 !important;
    font-weight: 900 !important;
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
        'st.set_page_config(page_title="Contrarian 10-Bagger Engine", layout="wide")\n'
        'st.markdown(EXTRA_CSS, unsafe_allow_html=True)',
        1,
    )
    source = source.replace(
        'with st.sidebar:\n    st.subheader("Front Office")',
        'with st.sidebar:\n'
        '    st.subheader("Mystery Machine")\n'
        '    st.caption("Filters now live in the main page under Filters & Lenses so they stay visible on hosted Streamlit.")\n'
        '    st.link_button("Refresh Data", GITHUB_ACTIONS_URL)\n\n'
        'with st.expander("Filters & Lenses", expanded=True):\n'
        '    st.subheader("Front Office")\n'
        '    st.caption("Choose the lens, sorting, and risk checks for the board. These controls no longer depend on the left sidebar.")',
        1,
    )
    source = source.replace(
        'top_n = st.slider("Rows to show", 10, 500, 100, 10)',
        'top_n = st.slider("Rows to show", 10, 500, 250, 10)',
        1,
    )
    source = source.replace('"Math Playbook"', '"Math Appendix"')
    source = source.replace(
        'st.caption("Cleaner by default. Turn on Advanced columns in the sidebar when you want the full model guts.")',
        'st.caption("Cleaner by default. Turn on Advanced columns in Filters & Lenses when you want the full model guts.")',
        1,
    )
    source = source.replace('st.subheader("Top 100 Research Batch")', 'st.subheader("Top 250 Research Batch")', 1)
    return source


code = compile(patched_dashboard_source(), str(SOURCE_PATH), "exec")
exec(code, globals())
