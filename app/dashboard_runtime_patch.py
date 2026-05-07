"""Small hosted-entry patch for Mystery Machine.

Keep this intentionally boring. Streamlit's native sidebar worked well before,
so this file must not override sidebar width or mobile layout. It only applies
small structural changes plus safe visual contrast fixes for the hosted app.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "app" / "dashboard.py"

SAFE_HOSTED_CSS = """
<style>
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background: #f5f7fb !important;
    background-image: none !important;
}
header[data-testid="stHeader"] {
    background: rgba(245, 247, 251, .96) !important;
    background-image: none !important;
}
#MainMenu,
footer,
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stToolbar"],
[data-testid="manage-app-button"],
a[href*="streamlit.io/cloud"],
a[href*="share.streamlit.io"] {
    display: none !important;
    visibility: hidden !important;
}
header[data-testid="stHeader"] button,
button[aria-label*="sidebar" i],
button[title*="sidebar" i],
button[aria-label*="menu" i],
button[title*="menu" i],
[data-testid="stSidebarCollapsedControl"] button {
    opacity: 1 !important;
    visibility: visible !important;
    background: #111827 !important;
    color: #ffffff !important;
    border: 2px solid #ffffff !important;
    border-radius: 999px !important;
    min-width: 46px !important;
    min-height: 46px !important;
    width: 46px !important;
    height: 46px !important;
    box-shadow: 0 10px 28px rgba(15, 23, 42, .35) !important;
}
header[data-testid="stHeader"] button svg,
button[aria-label*="sidebar" i] svg,
button[title*="sidebar" i] svg,
button[aria-label*="menu" i] svg,
button[title*="menu" i] svg,
[data-testid="stSidebarCollapsedControl"] svg {
    color: #ffffff !important;
    fill: #ffffff !important;
    stroke: #ffffff !important;
    width: 25px !important;
    height: 25px !important;
}
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div {
    background: #f7f9fd !important;
}
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] *,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div,
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] *,
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] *,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {
    color: #0f172a !important;
    text-shadow: none !important;
}
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea,
section[data-testid="stSidebar"] [data-baseweb="select"] > div,
section[data-testid="stSidebar"] [data-baseweb="slider"] {
    background: #ffffff !important;
    color: #0f172a !important;
}
.cfe-hero {
    background: linear-gradient(135deg, #0f172a, #1e293b) !important;
    border: 1px solid #334155 !important;
    color: #f8fafc !important;
}
.cfe-hero,
.cfe-hero h1,
.cfe-hero p,
.cfe-hero div,
.cfe-hero span {
    color: #f8fafc !important;
    text-shadow: none !important;
}
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] *,
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] *,
[data-testid="stMetric"],
[data-testid="stMetric"] *,
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] *,
[data-testid="stAlert"],
[data-testid="stAlert"] *,
label,
input,
textarea,
[data-baseweb="select"] * {
    color: #0f172a !important;
    text-shadow: none !important;
}
input,
textarea,
[data-baseweb="select"] > div {
    background: #ffffff !important;
}
div[data-testid="stTabs"] button[role="tab"] {
    background: #f8fafc !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
    font-weight: 800 !important;
}
div[data-testid="stTabs"] button[role="tab"] * {
    color: #0f172a !important;
}
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    background: #111827 !important;
    border-color: #111827 !important;
}
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] * {
    color: #ffffff !important;
}
@media (max-width: 900px) {
    header[data-testid="stHeader"] {
        min-height: 64px !important;
    }
    header[data-testid="stHeader"] button,
    button[aria-label*="sidebar" i],
    button[title*="sidebar" i],
    button[aria-label*="menu" i],
    button[title*="menu" i],
    [data-testid="stSidebarCollapsedControl"] button {
        min-width: 54px !important;
        min-height: 54px !important;
        width: 54px !important;
        height: 54px !important;
    }
}
</style>
"""


def patched_dashboard_source() -> str:
    """Return dashboard source with small hosted-only text/structure changes."""
    source = SOURCE_PATH.read_text(encoding="utf-8")

    source = source.replace(
        'st.set_page_config(page_title="Contrarian 10-Bagger Engine", layout="wide")',
        'st.set_page_config(page_title="Contrarian 10-Bagger Engine", layout="wide", initial_sidebar_state="expanded")',
        1,
    )
    source = source.replace(
        'st.set_page_config(page_title="Contrarian 10-Bagger Engine", layout="wide", initial_sidebar_state="expanded")',
        'st.set_page_config(page_title="Contrarian 10-Bagger Engine", layout="wide", initial_sidebar_state="expanded")\n'
        'st.markdown(SAFE_HOSTED_CSS, unsafe_allow_html=True)',
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
        'st.caption("Cleaner by default. Turn on Advanced columns in the sidebar when you want the full model guts.")',
        'st.caption("Cleaner by default. Turn on Advanced columns in the sidebar when you want the full model guts.")',
        1,
    )

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
        '        st.subheader("Scout Card")\n'
        '        st.caption("Type a ticker or pick one from the board. This is the clean single-stock readout.")\n'
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
