"""Cloud entrypoint for Streamlit Community Cloud."""

from __future__ import annotations

import runpy
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parent
UNIVERSE_PATH = ROOT / "data" / "processed" / "universe.csv"
RESEARCH_BATCH_PATH = ROOT / "data" / "processed" / "research_batch.csv"
THEORY_SCORES_PATH = ROOT / "data" / "processed" / "theory_scores.csv"


def _clean(value: Any, fallback: str = "") -> str:
    if pd.isna(value):
        return fallback
    text = str(value).strip()
    return text if text and text.lower() != "nan" else fallback


def _money(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if pd.isna(number):
        return "n/a"
    if abs(number) >= 1_000_000_000:
        return f"${number / 1_000_000_000:.2f}B"
    if abs(number) >= 1_000_000:
        return f"${number / 1_000_000:.1f}M"
    if abs(number) >= 1_000:
        return f"${number / 1_000:.1f}K"
    return f"${number:,.0f}"


@st.cache_data(show_spinner=False)
def _load_csv(path_text: str) -> pd.DataFrame:
    path = Path(path_text)
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _render_full_universe_scout() -> None:
    universe = _load_csv(str(UNIVERSE_PATH))
    research = _load_csv(str(RESEARCH_BATCH_PATH))
    scores = _load_csv(str(THEORY_SCORES_PATH))

    with st.sidebar:
        st.markdown("### 🔎 Full Universe Scout")
        st.caption("Searches the broad universe first. Full scores appear when the ticker is in the current research batch.")

        if universe.empty or "ticker" not in universe.columns:
            st.info("Universe file not loaded yet.")
            return

        tickers = sorted(universe["ticker"].dropna().astype(str).str.upper().unique().tolist())
        query = st.text_input(
            "Ticker search",
            placeholder="Try HUBC, UGRO, AMS...",
            key="full_universe_sidebar_ticker_search",
        ).strip().upper()

        if not query:
            st.caption(f"Universe available: {len(tickers):,} tickers")
            st.caption(f"Research batch available: {len(research):,} rows")
            return

        matches = [ticker for ticker in tickers if ticker.startswith(query)]
        if not matches:
            st.warning("No matching ticker found in universe.csv")
            return

        selected = st.selectbox(
            "Match",
            matches[:50],
            key="full_universe_sidebar_ticker_match",
        )

        universe_row = universe[universe["ticker"].astype(str).str.upper() == selected].head(1)
        research_row = pd.DataFrame()
        score_row = pd.DataFrame()
        if not research.empty and "ticker" in research.columns:
            research_row = research[research["ticker"].astype(str).str.upper() == selected].head(1)
        if not scores.empty and "ticker" in scores.columns:
            score_row = scores[scores["ticker"].astype(str).str.upper() == selected].head(1)

        source_row = universe_row.iloc[0]
        company = _clean(source_row.get("company_name"), "Unknown company")
        st.markdown(f"#### {selected}")
        st.write(company)

        c1, c2 = st.columns(2)
        c1.metric("Price", _clean(source_row.get("price"), "n/a"))
        c2.metric("Market Cap", _money(source_row.get("market_cap")))

        st.write(f"**Sector:** {_clean(source_row.get('sector'), 'n/a')}")
        st.write(f"**Industry:** {_clean(source_row.get('industry'), 'n/a')}")
        st.write(f"**Dollar Volume:** {_money(source_row.get('dollar_volume'))}")

        if not research_row.empty:
            r = research_row.iloc[0]
            st.success("In current research batch")
            if "ten_bagger_prescreen_score" in r.index:
                st.metric("Prescreen", f"{float(r.get('ten_bagger_prescreen_score', 0)):.1f}")
            reason = _clean(r.get("prescreen_reason"))
            if reason:
                st.write("**Prescreen reason:**")
                st.caption(reason)
        else:
            st.info("In full universe, not in the current deep-research batch.")

        if not score_row.empty:
            s = score_row.iloc[0]
            for label, col in [
                ("Movement", "movement_score"),
                ("Austrian", "austrian_mispricing_score"),
                ("Hume", "hume_flow_potential_score"),
                ("Keynes", "keynes_repricing_potential_score"),
                ("Long-Term", "long_term_investment_score"),
            ]:
                if col in s.index:
                    try:
                        st.metric(label, f"{float(s.get(col)):.1f}")
                    except Exception:
                        pass


UI_OVERRIDES = """
<style>
/* Flat page background: removes the old traveling color band. */
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

/* Restore the main title/hero contrast. */
.cfe-hero {
    background: linear-gradient(135deg, #0f172a, #1e293b) !important;
    color: #f8fafc !important;
    border: 1px solid #334155 !important;
}

.cfe-hero h1,
.cfe-hero h2,
.cfe-hero h3,
.cfe-hero p,
.cfe-hero div,
.cfe-hero span {
    color: #f8fafc !important;
    opacity: 1 !important;
    text-shadow: none !important;
}

.hero-kicker {
    color: #cbd5e1 !important;
    opacity: 1 !important;
    text-shadow: none !important;
}

/* High-contrast Streamlit tabs. */
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

/* Hide Mobile Lite tab. */
div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2) {
    display: none !important;
}

/* Rename old Math Playbook visible tab label to Math Appendix. */
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

/* Make Scout Card ticker entry obvious and inviting. */
div[data-testid="stTextInput"] label,
div[data-testid="stTextInput"] label p,
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

st.markdown(UI_OVERRIDES, unsafe_allow_html=True)
_render_full_universe_scout()
runpy.run_path(str(ROOT / "app" / "dashboard.py"), run_name="__main__")
st.markdown(UI_OVERRIDES, unsafe_allow_html=True)
