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


def patched_dashboard_source() -> str:
    """Return dashboard source with small hosted-only text/structure changes."""
    source = SOURCE_PATH.read_text(encoding="utf-8")

    source = source.replace(
        'st.set_page_config(page_title="Contrarian 10-Bagger Engine", layout="wide")',
        'st.set_page_config(page_title="Contrarian 10-Bagger Engine", layout="wide", initial_sidebar_state="expanded")',
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
