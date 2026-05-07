"""Small hosted-entry patch for Mystery Machine.

Keep this intentionally boring. Streamlit's native sidebar worked well before,
so this file must not override sidebar width, mobile layout, or global text
colors. It only applies the small structural changes that are not yet committed
directly into the hosted dashboard file.
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
.verdict-pill,
.verdict-pill *,
.mini-score,
.mini-score *,
.grade-pill,
.grade-pill *,
.metric-card,
.metric-card *,
.scout-card,
.scout-card *,
.toolbar-note,
.toolbar-note * {
    text-shadow: none !important;
}
.verdict-scooby,
.verdict-scooby * { color: #14532d !important; }
.verdict-watch,
.verdict-watch * { color: #1e3a8a !important; }
.verdict-mid,
.verdict-mid * { color: #334155 !important; }
.verdict-risk,
.verdict-risk * { color: #92400e !important; }
.verdict-garbage,
.verdict-garbage * { color: #991b1b !important; }
.mini-score,
.mini-score *,
.big-board-table td,
.big-board-table td * {
    color: #172033 !important;
}
.big-board-table th,
.big-board-table th *,
.cfe-hero,
.cfe-hero *,
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"],
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
    source = source.replace('table_width = max(1900, 520 + len(board.columns) * 112)', 'table_width = max(1680, 460 + len(board.columns) * 96)', 1)
    source = source.replace('height: 18px;\n            margin-bottom: 6px;', 'height: 20px;\n            margin-bottom: 8px;', 1)
    source = source.replace(
        'background: #f8fbff;\n        }}\n        .top-scroll-inner {{',
        'background: #f8fbff;\n            position: sticky;\n            top: 0;\n            z-index: 20;\n        }}\n'
        '        .bottom-scroll {{\n'
        '            width: 100%;\n'
        '            overflow-x: auto;\n'
        '            overflow-y: hidden;\n'
        '            height: 20px;\n'
        '            margin-top: 8px;\n'
        '            border: 1px solid #ccd6e6;\n'
        '            border-radius: 8px;\n'
        '            background: #f8fbff;\n'
        '            position: sticky;\n'
        '            bottom: 0;\n'
        '            z-index: 20;\n'
        '        }}\n'
        '        .scroll-inner {{',
        1,
    )
    source = source.replace('font-size: 13px;', 'font-size: 12.5px;', 1)
    source = source.replace('padding: 10px 11px;', 'padding: 9px 10px;', 1)
    source = source.replace('padding: 9px 11px;', 'padding: 8px 10px;', 1)
    source = source.replace('width: 86px;\n            min-width: 86px;', 'width: 80px;\n            min-width: 80px;', 1)
    source = source.replace('max-width: 260px;\n            min-width: 180px;', 'max-width: 235px;\n            min-width: 165px;', 1)
    source = source.replace('min-width: 92px;', 'min-width: 86px;', 1)
    source = source.replace('min-width: 43px;', 'min-width: 39px;', 1)
    source = source.replace('width: 45px;', 'width: 40px;', 1)
    source = source.replace(
        '<div class="top-scroll" id="topScroll"><div class="top-scroll-inner" id="topScrollInner"></div></div>',
        '<div class="top-scroll synced-scroll" id="topScroll"><div class="scroll-inner" id="topScrollInner"></div></div>',
        1,
    )
    source = source.replace(
        '        </div>\n        <div class="cell-detail" id="cellDetail">',
        '        </div>\n'
        '        <div class="bottom-scroll synced-scroll" id="bottomScroll"><div class="scroll-inner" id="bottomScrollInner"></div></div>\n'
        '        <div class="cell-detail" id="cellDetail">',
        1,
    )
    source = source.replace(
        'const topScrollInner = document.getElementById("topScrollInner");\n'
        '        const boardScroll = document.getElementById("boardScroll");',
        'const topScrollInner = document.getElementById("topScrollInner");\n'
        '        const bottomScroll = document.getElementById("bottomScroll");\n'
        '        const bottomScrollInner = document.getElementById("bottomScrollInner");\n'
        '        const boardScroll = document.getElementById("boardScroll");',
        1,
    )
    source = source.replace(
        'topScrollInner.style.width = `${{width}}px`;\n'
        '        }}\n'
        '        syncTopScrollbarWidth();\n'
        '        window.addEventListener("resize", syncTopScrollbarWidth);',
        'topScrollInner.style.width = `${{width}}px`;\n'
        '            bottomScrollInner.style.width = `${{width}}px`;\n'
        '        }}\n'
        '        function syncScrollLeft(source, targetA, targetB) {{\n'
        '            targetA.scrollLeft = source.scrollLeft;\n'
        '            targetB.scrollLeft = source.scrollLeft;\n'
        '        }}\n'
        '        syncTopScrollbarWidth();\n'
        '        requestAnimationFrame(syncTopScrollbarWidth);\n'
        '        setTimeout(syncTopScrollbarWidth, 250);\n'
        '        setTimeout(syncTopScrollbarWidth, 1000);\n'
        '        if (window.ResizeObserver) {{\n'
        '            new ResizeObserver(syncTopScrollbarWidth).observe(table);\n'
        '            new ResizeObserver(syncTopScrollbarWidth).observe(boardScroll);\n'
        '        }}\n'
        '        window.addEventListener("resize", syncTopScrollbarWidth);',
        1,
    )
    source = source.replace(
        'boardScroll.scrollLeft = topScroll.scrollLeft;\n'
        '            syncingBoard = false;\n'
        '        }});\n'
        '        boardScroll.addEventListener("scroll", () => {{',
        'syncScrollLeft(topScroll, boardScroll, bottomScroll);\n'
        '            syncingBoard = false;\n'
        '        }});\n'
        '        bottomScroll.addEventListener("scroll", () => {{\n'
        '            if (syncingTop) return;\n'
        '            syncingBoard = true;\n'
        '            syncScrollLeft(bottomScroll, boardScroll, topScroll);\n'
        '            syncingBoard = false;\n'
        '        }});\n'
        '        boardScroll.addEventListener("scroll", () => {{',
        1,
    )
    source = source.replace('topScroll.scrollLeft = boardScroll.scrollLeft;', 'syncScrollLeft(boardScroll, topScroll, bottomScroll);', 1)
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
        '        st.caption("Start typing in the box, then pick the ticker from the same control.")\n'
        '        selected = st.selectbox("Choose or enter ticker", tickers, key="scout_ticker_picker")\n'
        '        score_row = theory_scores[theory_scores["ticker"].astype(str).str.upper() == selected].iloc[0]',
        1,
    )
    return source


code = compile(patched_dashboard_source(), str(SOURCE_PATH), "exec")
exec(code, globals())
