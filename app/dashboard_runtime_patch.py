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
.block-container,
.block-container p,
.block-container li,
.block-container label,
.block-container div[data-testid="stMarkdownContainer"],
[data-testid="stMetric"],
[data-testid="stMetric"] *,
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] *,
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] *,
[data-baseweb="select"] *,
input,
textarea {
    color: #0f172a !important;
    text-shadow: none !important;
}
[data-baseweb="select"] > div,
input,
textarea {
    background: #ffffff !important;
}
.cfe-hero,
.cfe-hero h1,
.cfe-hero p,
.cfe-hero div,
.cfe-hero span,
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"],
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] * {
    color: #ffffff !important;
}
@media (max-width: 900px) {
    .block-container {
        padding-left: .85rem !important;
        padding-right: .85rem !important;
    }
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
    source = source.replace(
        'watchlist_tab, mobile_tab, ticker_tab, data_tab, appendix_tab = st.tabs(\n'
        '    ["Big Board", "Mobile Lite", "Scout Card", "Data Room", "Math Appendix"]\n'
        ')',
        'watchlist_tab, ticker_tab, data_tab, appendix_tab = st.tabs(\n'
        '    ["Big Board", "Scout Card", "Data Room", "Math Appendix"]\n'
        ')',
        1,
    )

    mobile_start = source.find("\nwith mobile_tab:\n")
    ticker_start = source.find("\nwith ticker_tab:\n")
    if mobile_start != -1 and ticker_start != -1 and mobile_start < ticker_start:
        source = source[:mobile_start] + source[ticker_start:]

    source = source.replace(
        '    .scout-subtitle {\n'
        '        color: #64748b;\n'
        '        margin-bottom: .65rem;\n'
        '    }',
        '    .scout-subtitle {\n'
        '        color: #64748b;\n'
        '        margin-bottom: .65rem;\n'
        '    }\n'
        '    .scout-picker {\n'
        '        border: 1px solid #c8d9ff;\n'
        '        background: linear-gradient(135deg, #eff6ff, #ffffff);\n'
        '        border-radius: 8px;\n'
        '        padding: 1rem;\n'
        '        margin-bottom: 1rem;\n'
        '        box-shadow: 0 12px 28px rgba(20,31,56,0.07);\n'
        '    }\n'
        '    .scout-picker-title {\n'
        '        color: #0f172a;\n'
        '        font-size: 1.45rem;\n'
        '        font-weight: 950;\n'
        '        margin-bottom: .15rem;\n'
        '    }\n'
        '    .scout-picker-note {\n'
        '        color: #475569;\n'
        '        font-size: .95rem;\n'
        '    }\n'
        '    .scout-card {\n'
        '        border: 1px solid #cbd5e1;\n'
        '        background: linear-gradient(180deg, #ffffff, #f8fbff);\n'
        '        border-radius: 8px;\n'
        '        padding: 1.15rem;\n'
        '        box-shadow: 0 16px 34px rgba(20,31,56,0.10);\n'
        '        margin-top: .75rem;\n'
        '    }',
        1,
    )

    source = source.replace(
        'with ticker_tab:\n'
        '    ticker_source = filtered if not filtered.empty else display_scores\n'
        '    if ticker_source.empty:\n'
        '        st.info("No scored tickers available yet.")\n'
        '    else:\n'
        '        tickers = ticker_source["ticker"].astype(str).tolist()\n'
        '        selected = st.selectbox("Ticker lens", tickers)\n'
        '        score_row = theory_scores[theory_scores["ticker"].astype(str) == selected].iloc[0]',
        'with ticker_tab:\n'
        '    ticker_source = display_scores\n'
        '    if ticker_source.empty:\n'
        '        st.info("No scored tickers available yet.")\n'
        '    else:\n'
        '        tickers = sorted(ticker_source["ticker"].dropna().astype(str).str.upper().unique().tolist())\n'
        '        st.markdown(\n'
        '            """\n'
        '            <div class="scout-picker">\n'
        '                <div class="scout-picker-title">Scout Card</div>\n'
        '                <div class="scout-picker-note">Type a ticker or pick one from the board. This is the clean single-stock readout.</div>\n'
        '            </div>\n'
        '            """,\n'
        '            unsafe_allow_html=True,\n'
        '        )\n'
        '        search_col, pick_col = st.columns([1, 2])\n'
        '        with search_col:\n'
        '            scout_query = st.text_input("Enter ticker", placeholder="Example: ORGN", key="scout_ticker_search").strip().upper()\n'
        '        matching_tickers = [ticker for ticker in tickers if not scout_query or ticker.startswith(scout_query)]\n'
        '        if not matching_tickers:\n'
        '            st.warning("No scored ticker matched that search.")\n'
        '            st.stop()\n'
        '        with pick_col:\n'
        '            selected = st.selectbox("Choose ticker", matching_tickers[:250], key="scout_ticker_picker")\n'
        '        score_row = theory_scores[theory_scores["ticker"].astype(str).str.upper() == selected].iloc[0]',
        1,
    )
    return source


code = compile(patched_dashboard_source(), str(SOURCE_PATH), "exec")
exec(code, globals())
