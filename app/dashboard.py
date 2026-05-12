"""Streamlit dashboard for Contrarian 10-Bagger Engine."""

from __future__ import annotations

import html
import math
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


ROOT = Path(__file__).resolve().parents[1]
UNIVERSE_PATH = ROOT / "data" / "processed" / "universe.csv"
RESEARCH_BATCH_PATH = ROOT / "data" / "processed" / "research_batch.csv"
THEORY_SCORES_PATH = ROOT / "data" / "processed" / "theory_scores.csv"
SEC_FLAGS_PATH = ROOT / "data" / "processed" / "sec_filing_flags.csv"
SEC_SIGNALS_PATH = ROOT / "data" / "processed" / "sec_filing_signals.csv"
EVENT_SHOCKS_PATH = ROOT / "data" / "processed" / "event_shocks.csv"
PRICE_HISTORY_PATH = ROOT / "data" / "processed" / "price_history_features.csv"
FUNDAMENTALS_PATH = ROOT / "data" / "processed" / "fundamentals_stub.csv"
SOURCE_STATUS_PATH = ROOT / "data" / "processed" / "source_status.csv"
MATH_APPENDIX_PATH = ROOT / "docs" / "math_appendix.md"


st.set_page_config(page_title="Contrarian 10-Bagger Engine", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    #MainMenu,
    footer,
    [data-testid="stDecoration"],
    [data-testid="manage-app-button"],
    a[href*="streamlit.io/cloud"],
    a[href*="share.streamlit.io"] {
        display: none !important;
        visibility: hidden !important;
    }
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
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] > div {
        background: #f7f9fd !important;
    }
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] *,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] *,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] * {
        color: #0f172a !important;
        text-shadow: none !important;
    }
    section[data-testid="stSidebar"] button,
    section[data-testid="stSidebar"] [role="button"] {
        background: #ffffff !important;
        color: #0f172a !important;
        border-color: #cbd5e1 !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] button *,
    section[data-testid="stSidebar"] [role="button"] * {
        color: #0f172a !important;
    }
    section[data-testid="stSidebar"] button[aria-pressed="true"],
    section[data-testid="stSidebar"] button[aria-selected="true"],
    section[data-testid="stSidebar"] [role="button"][aria-pressed="true"],
    section[data-testid="stSidebar"] [role="button"][aria-selected="true"] {
        background: #1d4ed8 !important;
        color: #ffffff !important;
        border-color: #1d4ed8 !important;
    }
    section[data-testid="stSidebar"] button[aria-pressed="true"] *,
    section[data-testid="stSidebar"] button[aria-selected="true"] *,
    section[data-testid="stSidebar"] [role="button"][aria-pressed="true"] *,
    section[data-testid="stSidebar"] [role="button"][aria-selected="true"] * {
        color: #ffffff !important;
    }
    header[data-testid="stHeader"] button,
    button[aria-label*="sidebar" i],
    button[title*="sidebar" i],
    button[aria-label*="menu" i],
    button[title*="menu" i],
    [data-testid="stSidebarCollapsedControl"] button {
        opacity: 1 !important;
        visibility: visible !important;
        background: #ffffff !important;
        color: #0f172a !important;
        border: 2px solid #2563eb !important;
        box-shadow: 0 10px 28px rgba(37, 99, 235, .28) !important;
        z-index: 999999 !important;
    }
    header[data-testid="stHeader"] button *,
    button[aria-label*="sidebar" i] *,
    button[title*="sidebar" i] *,
    button[aria-label*="menu" i] *,
    button[title*="menu" i] *,
    [data-testid="stSidebarCollapsedControl"] button * {
        color: #0f172a !important;
        fill: #0f172a !important;
        stroke: #0f172a !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


GITHUB_ACTIONS_URL = "https://github.com/Kastnermj/mysterymachine/actions/workflows/refresh-data.yml"


@st.cache_data(show_spinner=False)
def load_csv(path_text: str) -> pd.DataFrame:
    """Load a CSV once per Streamlit session."""
    path = Path(path_text)
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError):
        return pd.DataFrame()


def clean_text(value: Any, fallback: str = "") -> str:
    """Return display-safe text for Streamlit."""
    if pd.isna(value):
        return fallback
    text = str(value).strip()
    return text if text and text.lower() != "nan" else fallback


def safe_number(value: Any, fallback: float = 0.0) -> float:
    """Convert values into numbers for metrics and filters."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    if pd.isna(number):
        return fallback
    return number


def money(value: Any) -> str:
    """Format market values compactly."""
    number = safe_number(value, None)
    if number is None:
        return "n/a"
    if abs(number) >= 1_000_000_000:
        return f"${number / 1_000_000_000:.2f}B"
    if abs(number) >= 1_000_000:
        return f"${number / 1_000_000:.1f}M"
    if abs(number) >= 1_000:
        return f"${number / 1_000:.1f}K"
    return f"${number:,.0f}"


def price_money(value: Any) -> str:
    """Format stock prices with visible cents in scout cards."""
    number = safe_number(value, None)
    if number is None:
        return "n/a"
    return f"${number:,.2f}"


def score_band(score: Any) -> str:
    """Return a compact visual band for score cards."""
    value = safe_number(score)
    if value >= 78:
        return "hot"
    if value >= 60:
        return "warm"
    if value >= 42:
        return "mixed"
    return "cold"


def health_label(status_frame: pd.DataFrame) -> tuple[str, str]:
    """Summarize source health into one dashboard label."""
    if status_frame.empty:
        return "Unknown", "No source-health file yet"
    statuses = status_frame.get("status", pd.Series(dtype=str)).astype(str).str.lower()
    if statuses.str.contains("failed|error").any():
        return "Needs Review", "At least one source stage reported a failure"
    if statuses.str.contains("degraded|reused_cache|skipped").any():
        return "Mixed", "Some data came from fallback/cache or was incomplete"
    return "Healthy", "All recorded stages reported usable data"


def refresh_label(status_frame: pd.DataFrame) -> tuple[str, str]:
    """Summarize the latest refresh timestamp."""
    if status_frame.empty or "timestamp_utc" not in status_frame.columns:
        return "Unknown", "No refresh timestamp found"
    timestamps = pd.to_datetime(status_frame["timestamp_utc"], errors="coerce", utc=True).dropna()
    if timestamps.empty:
        return "Unknown", "No usable refresh timestamp found"
    latest = timestamps.max()
    age_hours = max(0.0, (pd.Timestamp.now(tz="UTC") - latest).total_seconds() / 3600)
    if age_hours < 1:
        age = f"{age_hours * 60:.0f} minutes ago"
    elif age_hours < 48:
        age = f"{age_hours:.1f} hours ago"
    else:
        age = f"{age_hours / 24:.1f} days ago"
    return latest.strftime("%Y-%m-%d %H:%M UTC"), age


def metric_panel(label: str, value: Any, note: str = "") -> None:
    """Render one compact dashboard metric."""
    st.markdown(
        f"""
        <div class="cfe-panel">
            <div class="cfe-panel-label">{label}</div>
            <div class="cfe-panel-value">{value}</div>
            <div class="cfe-panel-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def score_panel(label: str, value: Any, note: str = "") -> None:
    """Render a selected-ticker score block."""
    number = safe_number(value)
    st.markdown(
        f"""
        <div class="score-panel {score_band(number)}">
            <div class="score-label">{label}</div>
            <div class="score-value">{number:.1f}</div>
            <div class="score-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def label_class(label: Any) -> str:
    """Return a CSS class for the user's personal verdict label."""
    text = clean_text(label).lower()
    if "scooby" in text:
        return "verdict-scooby"
    if "scrappy" in text or "pricing gap" in text or "long-term clue" in text:
        return "verdict-watch"
    if "garbage" in text or "hard stop" in text or "liquidation" in text:
        return "verdict-garbage"
    if "red flags" in text or "old thesis" in text or "hayek" in text:
        return "verdict-risk"
    return "verdict-mid"


def verdict_badge(label: Any) -> str:
    """Return an HTML badge for fun verdict labels."""
    text = clean_text(label, "Unlabeled")
    return f'<span class="verdict-pill {label_class(text)}">{text}</span>'


def clamp_score(value: Any, floor: float = 0.0, ceiling: float = 100.0) -> float:
    """Return a bounded score for visual elements."""
    return max(floor, min(ceiling, safe_number(value)))


def scout_dimensions(row: pd.Series) -> list[tuple[str, float, str]]:
    """Return the six headline dimensions for the Scout power hexagon."""
    return [
        ("Austrian", clamp_score(row.get("austrian_mispricing_score")), "Pricing gap"),
        ("Hume", clamp_score(row.get("hume_flow_potential_score")), "Money flow"),
        ("Keynes", clamp_score(row.get("keynes_repricing_potential_score")), "Story power"),
        ("Relative", clamp_score(row.get("relative_mispricing_score")), "Value context"),
        ("Asymmetry", clamp_score(row.get("asymmetry_score")), "Upside shape"),
        ("Pre-Flow", clamp_score(row.get("pre_flow_opportunity_score")), "Latent setup"),
    ]


def scout_hexagon(row: pd.Series) -> str:
    """Build an SVG radar chart for one ticker."""
    dimensions = scout_dimensions(row)
    center = 150
    max_radius = 94
    angles = [-90, -30, 30, 90, 150, 210]

    def point(radius: float, angle: float) -> tuple[float, float]:
        radians = math.radians(angle)
        return center + radius * math.cos(radians), center + radius * math.sin(radians)

    rings = []
    for fraction in (0.33, 0.66, 1.0):
        ring_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(max_radius * fraction, angle) for angle in angles))
        rings.append(f'<polygon points="{ring_points}" class="power-ring" />')

    spokes = []
    labels = []
    value_points = []
    for (name, value, _note), angle in zip(dimensions, angles):
        outer_x, outer_y = point(max_radius, angle)
        label_x, label_y = point(max_radius + 30, angle)
        value_x, value_y = point(max_radius * (value / 100), angle)
        spokes.append(f'<line x1="{center}" y1="{center}" x2="{outer_x:.1f}" y2="{outer_y:.1f}" class="power-spoke" />')
        labels.append(
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" class="power-label" text-anchor="middle">'
            f'<tspan>{html.escape(name)}</tspan><tspan x="{label_x:.1f}" dy="13">{value:.0f}</tspan></text>'
        )
        value_points.append(f"{value_x:.1f},{value_y:.1f}")

    return (
        '<div class="power-hex-card">'
        '<div class="power-heading">Power Hexagon</div>'
        '<svg class="power-hex" viewBox="0 0 300 300" role="img" aria-label="Scout power hexagon">'
        + "".join(rings)
        + "".join(spokes)
        + f'<polygon points="{" ".join(value_points)}" class="power-shape" />'
        + "".join(labels)
        + f'<circle cx="{center}" cy="{center}" r="3.8" class="power-core" />'
        '</svg>'
        '</div>'
    )


def power_bar(label: str, value: Any, note: str = "") -> str:
    """Return one compact power bar."""
    score = clamp_score(value)
    return (
        '<div class="power-bar-row">'
        f'<div><strong>{html.escape(label)}</strong><span>{html.escape(note)}</span></div>'
        f'<b>{score:.0f}</b>'
        f'<div class="power-bar"><div style="width:{score:.0f}%"></div></div>'
        '</div>'
    )


def story_tile(title: str, body: Any, tone: str = "blue") -> str:
    """Return one compact Scout story tile."""
    text = clean_text(body, "No signal available yet.")
    return (
        f'<div class="story-tile story-{tone}">'
        f'<div class="story-title">{html.escape(title)}</div>'
        f'<div class="story-body">{html.escape(text)}</div>'
        '</div>'
    )


def scout_console_html(row: pd.Series, compact: bool = False) -> str:
    """Return the futuristic Scout analytics console for one ticker."""
    ticker = clean_text(row.get("ticker"), "???")
    company = clean_text(row.get("company_name"), "Unknown company")
    sector = clean_text(row.get("sector"), "Unknown sector")
    grade = clean_text(row.get("movement_grade"), "n/a")
    move = clamp_score(row.get("movement_score"))
    risk_text = clean_text(row.get("risk_posture"), "No risk posture")
    event_text = clean_text(row.get("event_callouts"), "No event callout")
    if len(event_text) > 220:
        event_text = event_text[:217] + "..."

    bars = [
        power_bar("Scooby Score", row.get("scooby_score"), "whole case"),
        power_bar("Adjusted Movement", row.get("movement_score"), grade),
        power_bar("Raw Movement", row.get("raw_movement_score"), "before haircut"),
        power_bar("Pre-Flow", row.get("pre_flow_opportunity_score"), clean_text(row.get("flow_state"), "flow read")),
        power_bar("Catalyst", row.get("catalyst_probability_score"), clean_text(row.get("viability_window"), "viability")),
        power_bar("Long-Term", row.get("long_term_investment_score"), clean_text(row.get("long_term_investment_label"), "business lens")),
        power_bar("Data", row.get("data_confidence_score"), clean_text(row.get("data_confidence_label"), "confidence")),
    ]
    if not compact:
        bars.extend(
            [
                power_bar("Dilution Risk", row.get("dilution_pressure_score"), "higher means more danger"),
                power_bar("Survival Risk", row.get("survival_risk_score"), "higher means more danger"),
            ]
        )

    tiles = [
        story_tile("Why It Could Move", row.get("ranking_note"), "green"),
        story_tile("Setup Read", row.get("setup_type"), "blue"),
        story_tile("Flow State", row.get("flow_state"), "teal"),
        story_tile("Risk Console", risk_text, "amber"),
        story_tile("Event Shock", event_text, "red"),
        story_tile("Next Research Question", row.get("final_rank_interpretation"), "purple"),
    ]
    if not compact:
        tiles.extend(
            [
                story_tile("Long-Term Reality", row.get("long_term_investment_note"), "blue"),
                story_tile("Thesis Integrity", row.get("thesis_integrity_note"), "amber"),
                story_tile("DCF Plausibility", row.get("dcf_plausibility_note"), "green"),
            ]
        )

    console_class = "scout-console scout-console-compact" if compact else "scout-console"
    badges = verdict_badge(row.get("what_i_think"))
    secondary_label = clean_text(row.get("secondary_what_i_think"))
    if secondary_label:
        badges += verdict_badge(secondary_label)

    return f"""
    <div class="{console_class}">
        <div class="scout-console-hero">
            <div>
                <div class="scout-kicker">Mystery Machine Scout Console</div>
                <div class="scout-console-title">{html.escape(ticker)} <span>{html.escape(company)}</span></div>
                <div class="scout-console-subtitle">{html.escape(sector)} | Price {price_money(row.get('price'))} | Market cap {money(row.get('market_cap'))}</div>
                <div class="scout-console-badges">{badges}</div>
            </div>
            <div class="scout-grade-orb">
                <span>{html.escape(grade)}</span>
                <small>{move:.1f} move</small>
            </div>
        </div>
        <div class="scout-console-grid">
            {scout_hexagon(row)}
            <div class="power-bars">{''.join(bars)}</div>
        </div>
        <div class="story-grid">{''.join(tiles)}</div>
    </div>
    """


def render_scout_console(row: pd.Series, compact: bool = False) -> None:
    """Render the Scout analytics console."""
    st.markdown(scout_console_html(row, compact=compact), unsafe_allow_html=True)


def ticker_card(row: pd.Series, rank: int) -> None:
    """Render one compact front-office card."""
    ticker = clean_text(row.get("ticker"), "???")
    name = clean_text(row.get("company_name"), "Unknown company")
    if len(name) > 46:
        name = name[:43] + "..."
    move = safe_number(row.get("movement_score"))
    grade = clean_text(row.get("movement_grade"), "n/a")
    risk = clean_text(row.get("risk_posture"), "No risk posture")
    flow = clean_text(row.get("flow_state"), "No flow read")
    with st.container(border=True):
        head_left, head_mid, head_right = st.columns([1.02, 1.25, .58], vertical_alignment="center")
        with head_left:
            st.markdown(
                f'<div class="draft-native-head"><span class="draft-rank">#{rank}</span> '
                f'<span class="draft-ticker">{ticker}</span></div>',
                unsafe_allow_html=True,
            )
        with head_mid:
            if st.button("Scout", key=f"front_office_{rank}_{ticker}", use_container_width=True):
                front_office_scout_dialog(row.to_dict())
        with head_right:
            st.markdown(f'<div class="draft-grade native-grade">{grade}</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="draft-card-content">
                <div class="draft-name">{name}</div>
                <div class="draft-scorebar"><div style="width:{max(0, min(100, move)):.0f}%"></div></div>
                <div class="draft-meta">Move {move:.1f} | Hume {safe_number(row.get("hume_flow_potential_score")):.0f} | Keynes {safe_number(row.get("keynes_repricing_potential_score")):.0f}</div>
                <div class="draft-badge">{verdict_badge(row.get("what_i_think"))}{verdict_badge(row.get("secondary_what_i_think")) if clean_text(row.get("secondary_what_i_think")) else ""}</div>
                <div class="draft-note">{risk} | {flow}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def scout_note(row: pd.Series) -> str:
    """Build a short plain-English scouting note."""
    bits = []
    label = clean_text(row.get("what_i_think"))
    risk = clean_text(row.get("risk_posture"))
    flow = clean_text(row.get("flow_state"))
    if label:
        bits.append(f"Verdict: {label}.")
    if risk:
        bits.append(f"Risk posture: {risk}.")
    if flow:
        bits.append(f"Flow read: {flow}.")
    sequence = clean_text(row.get("sequence_interpretation"))
    if sequence:
        bits.append(f"Sequence: {sequence}.")
    return " ".join(bits) or "No scout note available yet."


def compact_scout_card(row: pd.Series) -> None:
    """Render a condensed ticker scout view for front-office popovers."""
    render_scout_console(row, compact=True)


@st.dialog("Front Office Scout Card", width="large")
def front_office_scout_dialog(row_data: dict[str, Any]) -> None:
    """Show a compact scout-card popout from a front-office tile."""
    row = pd.Series(row_data)
    compact_scout_card(row)
    st.caption("Use the Scout Card tab when you want the full 250-name research board and factor stack.")


BOARD_LABELS = {
    "ticker": "Ticker",
    "company_name": "Company",
    "movement_grade": "Grade",
    "raw_movement_score": "Raw Movement",
    "movement_score": "Adjusted Movement",
    "scooby_score": "Scooby Score",
    "what_i_think": "What I Think",
    "secondary_what_i_think": "Also Think",
    "risk_posture": "Risk Read",
    "price": "Price",
    "market_cap": "Mkt Cap",
    "sector": "Sector",
    "setup_type": "Setup",
    "flow_state": "Flow",
    "pre_flow_opportunity_score": "Pre-Flow",
    "austrian_mispricing_score": "Austrian",
    "hume_flow_potential_score": "Hume",
    "keynes_repricing_potential_score": "Keynes",
    "relative_mispricing_score": "Relative",
    "asymmetry_score": "Asymmetry",
    "long_term_investment_score": "Long-Term",
    "data_confidence_score": "Data",
    "dilution_pressure_score": "Dilution",
    "survival_risk_score": "Survival",
    "event_shock_penalty": "Event",
    "viability_window": "Viability",
    "event_callouts": "Event Callout",
    "ranking_note": "Why",
}


SCORE_COLUMNS = {
    "raw_movement_score",
    "movement_score",
    "scooby_score",
    "pre_flow_opportunity_score",
    "austrian_mispricing_score",
    "hume_flow_potential_score",
    "keynes_repricing_potential_score",
    "relative_mispricing_score",
    "asymmetry_score",
    "long_term_investment_score",
    "data_confidence_score",
    "dilution_pressure_score",
    "survival_risk_score",
    "event_shock_penalty",
}

BOARD_NUMERIC_COLUMNS = SCORE_COLUMNS | {"price", "market_cap"}


def board_sort_value(column: str, value: Any) -> str:
    """Return a raw sortable value for the browser table."""
    if column in BOARD_NUMERIC_COLUMNS:
        return str(safe_number(value, -1_000_000_000))
    return clean_text(value).lower()


def board_full_text(column: str, value: Any) -> str:
    """Return full text for click-to-expand board cells."""
    if column == "price":
        number = safe_number(value, None)
        return "n/a" if number is None else f"${number:,.2f}"
    if column == "market_cap":
        return money(value)
    if column in SCORE_COLUMNS:
        return f"{safe_number(value):.1f}"
    return clean_text(value, "n/a")


def board_cell(column: str, value: Any) -> str:
    """Format one big-board cell."""
    if column == "price":
        number = safe_number(value, None)
        return "n/a" if number is None else html.escape(f"${number:,.2f}")
    if column == "market_cap":
        return html.escape(money(value))
    if column in SCORE_COLUMNS:
        number = max(0, min(100, safe_number(value)))
        return (
            f'<div class="mini-score">'
            f'<span>{number:.1f}</span>'
            f'<div class="mini-bar"><div style="width:{number:.0f}%"></div></div>'
            f"</div>"
        )
    if column == "what_i_think":
        return verdict_badge(value)
    text = clean_text(value, "n/a")
    if len(text) > 120:
        text = text[:117] + "..."
    return html.escape(text)


def render_big_board(frame: pd.DataFrame, columns: list[str]) -> None:
    """Render a scrollable table with a frozen ticker column."""
    board = frame[available_columns(frame, columns)].copy()
    if board.empty:
        st.info("No rows match the current board filters.")
        return

    headers = []
    for index, column in enumerate(board.columns):
        label = BOARD_LABELS.get(column, column.replace("_", " ").title())
        classes = ["col-" + column]
        if column == "ticker":
            classes.append("sticky-" + column)
        sort_type = "number" if column in BOARD_NUMERIC_COLUMNS else "text"
        headers.append(
            f'<th class="{" ".join(classes)}" data-index="{index}" data-sort-type="{sort_type}">'
            f'{html.escape(label)} <span class="sort-cue">↕</span></th>'
        )

    rows = []
    for _, row in board.iterrows():
        cells = []
        for column in board.columns:
            classes = ["col-" + column]
            if column == "ticker":
                classes.append("sticky-" + column)
            label = BOARD_LABELS.get(column, column.replace("_", " ").title())
            sort_value = html.escape(board_sort_value(column, row.get(column)), quote=True)
            full_text = html.escape(board_full_text(column, row.get(column)), quote=True)
            cells.append(
                f'<td class="{" ".join(classes)}" data-sort-value="{sort_value}" '
                f'data-label="{html.escape(label, quote=True)}" data-full-text="{full_text}">'
                f"{board_cell(column, row.get(column))}</td>"
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")

    table_width = max(1680, 460 + len(board.columns) * 96)
    board_html = f"""
        <style>
        body {{
            margin: 0;
            background: transparent;
            font-family: "Source Sans Pro", Arial, sans-serif;
        }}
        .top-scroll {{
            width: 100%;
            overflow-x: auto;
            overflow-y: hidden;
            height: 20px;
            margin-bottom: 8px;
            border: 1px solid #ccd6e6;
            border-radius: 8px;
            background: #f8fbff;
            position: sticky;
            top: 0;
            z-index: 20;
        }}
        .bottom-scroll {{
            width: 100%;
            overflow-x: auto;
            overflow-y: hidden;
            height: 20px;
            margin-top: 8px;
            border: 1px solid #ccd6e6;
            border-radius: 8px;
            background: #f8fbff;
            position: sticky;
            bottom: 0;
            z-index: 20;
        }}
        .scroll-inner {{
            width: {table_width}px;
            height: 1px;
        }}
        .board-wrap {{
            width: 100%;
            max-height: 650px;
            overflow: auto;
            border: 1px solid #ccd6e6;
            border-radius: 8px;
            background: #ffffff;
            box-shadow: 0 12px 34px rgba(20,31,56,0.08);
        }}
        .big-board-table {{
            border-collapse: separate;
            border-spacing: 0;
            min-width: {table_width}px;
            width: max-content;
            font-size: 12.5px;
            color: #172033;
        }}
        .big-board-table th {{
            position: sticky;
            top: 0;
            z-index: 5;
            background: #111827;
            color: #f8fafc;
            text-align: left;
            padding: 9px 10px;
            border-bottom: 1px solid #334155;
            white-space: nowrap;
            cursor: pointer;
            user-select: none;
        }}
        .big-board-table th:hover {{
            background: #1e293b;
        }}
        .sort-cue {{
            color: #93a4bd;
            font-size: 11px;
            margin-left: 4px;
        }}
        .big-board-table td {{
            padding: 8px 10px;
            border-bottom: 1px solid #e6ecf5;
            background: #ffffff;
            vertical-align: middle;
            cursor: pointer;
        }}
        .big-board-table tr:nth-child(even) td {{
            background: #f8fbff;
        }}
        .big-board-table tr:hover td {{
            background: #eef6ff;
        }}
        .big-board-table .sticky-ticker {{
            position: sticky;
            left: 0;
            z-index: 6;
            width: 80px;
            min-width: 80px;
            font-weight: 900;
            color: #0f172a;
            box-shadow: 1px 0 0 #d7deea;
        }}
        .big-board-table th.sticky-ticker {{
            z-index: 8;
            background: #0b1220;
        }}
        .big-board-table .col-ranking_note,
        .big-board-table .col-event_callouts,
        .big-board-table .col-risk_posture,
        .big-board-table .col-flow_state {{
            max-width: 235px;
            min-width: 165px;
        }}
        .mini-score {{
            min-width: 86px;
        }}
        .mini-score span {{
            display: inline-block;
            min-width: 39px;
            font-weight: 800;
            color: #172033;
        }}
        .mini-bar {{
            display: inline-block;
            width: 40px;
            height: 6px;
            margin-left: 4px;
            background: #dbe4f0;
            border-radius: 99px;
            overflow: hidden;
            vertical-align: middle;
        }}
        .mini-bar div {{
            height: 100%;
            background: linear-gradient(90deg, #2563eb, #16a34a);
        }}
        .verdict-pill {{
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 4px 9px;
            font-weight: 850;
            font-size: 12px;
            border: 1px solid transparent;
            white-space: normal;
        }}
        .verdict-scooby {{ background: #dcfce7; color: #14532d; border-color: #86efac; }}
        .verdict-watch {{ background: #dbeafe; color: #1e3a8a; border-color: #93c5fd; }}
        .verdict-mid {{ background: #f1f5f9; color: #334155; border-color: #cbd5e1; }}
        .verdict-risk {{ background: #fef3c7; color: #92400e; border-color: #fcd34d; }}
        .verdict-garbage {{ background: #fee2e2; color: #991b1b; border-color: #fecaca; }}
        .cell-detail {{
            display: none;
            margin-top: 8px;
            border: 1px solid #c8d9ff;
            background: #eef4ff;
            color: #172033;
            border-radius: 8px;
            padding: 12px 14px;
            line-height: 1.45;
            white-space: pre-wrap;
        }}
        .cell-detail-title {{
            color: #1e3a8a;
            font-weight: 900;
            margin-bottom: 5px;
        }}
        </style>
        <div class="top-scroll synced-scroll" id="topScroll"><div class="scroll-inner" id="topScrollInner"></div></div>
        <div class="board-wrap" id="boardScroll">
            <table class="big-board-table">
                <thead><tr>{''.join(headers)}</tr></thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </div>
        <div class="bottom-scroll synced-scroll" id="bottomScroll"><div class="scroll-inner" id="bottomScrollInner"></div></div>
        <div class="cell-detail" id="cellDetail">
            <div class="cell-detail-title" id="cellDetailTitle"></div>
            <div id="cellDetailText"></div>
        </div>
        <script>
        const topScroll = document.getElementById("topScroll");
        const topScrollInner = document.getElementById("topScrollInner");
        const bottomScroll = document.getElementById("bottomScroll");
        const bottomScrollInner = document.getElementById("bottomScrollInner");
        const boardScroll = document.getElementById("boardScroll");
        const table = document.querySelector(".big-board-table");
        const tbody = table.querySelector("tbody");
        const detail = document.getElementById("cellDetail");
        const detailTitle = document.getElementById("cellDetailTitle");
        const detailText = document.getElementById("cellDetailText");
        let syncingTop = false;
        let syncingBoard = false;
        function syncTopScrollbarWidth() {{
            const width = Math.max(table.scrollWidth, boardScroll.scrollWidth, boardScroll.clientWidth);
            topScrollInner.style.width = `${{width}}px`;
            bottomScrollInner.style.width = `${{width}}px`;
        }}
        function syncScrollLeft(source, targetA, targetB) {{
            targetA.scrollLeft = source.scrollLeft;
            targetB.scrollLeft = source.scrollLeft;
        }}
        syncTopScrollbarWidth();
        requestAnimationFrame(syncTopScrollbarWidth);
        setTimeout(syncTopScrollbarWidth, 250);
        setTimeout(syncTopScrollbarWidth, 1000);
        if (window.ResizeObserver) {{
            new ResizeObserver(syncTopScrollbarWidth).observe(table);
            new ResizeObserver(syncTopScrollbarWidth).observe(boardScroll);
        }}
        window.addEventListener("resize", syncTopScrollbarWidth);
        topScroll.addEventListener("scroll", () => {{
            if (syncingTop) return;
            syncingBoard = true;
            syncScrollLeft(topScroll, boardScroll, bottomScroll);
            syncingBoard = false;
        }});
        bottomScroll.addEventListener("scroll", () => {{
            if (syncingTop) return;
            syncingBoard = true;
            syncScrollLeft(bottomScroll, boardScroll, topScroll);
            syncingBoard = false;
        }});
        boardScroll.addEventListener("scroll", () => {{
            if (syncingBoard) return;
            syncingTop = true;
            syncScrollLeft(boardScroll, topScroll, bottomScroll);
            syncingTop = false;
        }});
        table.querySelectorAll("th").forEach((header) => {{
            header.dataset.direction = "none";
            header.addEventListener("click", () => {{
                const index = Number(header.dataset.index);
                const type = header.dataset.sortType;
                const nextDirection = header.dataset.direction === "asc" ? "desc" : "asc";
                table.querySelectorAll("th").forEach((other) => {{
                    other.dataset.direction = "none";
                    const cue = other.querySelector(".sort-cue");
                    if (cue) cue.textContent = "↕";
                }});
                header.dataset.direction = nextDirection;
                const cue = header.querySelector(".sort-cue");
                if (cue) cue.textContent = nextDirection === "asc" ? "↑" : "↓";

                const rows = Array.from(tbody.querySelectorAll("tr"));
                rows.sort((a, b) => {{
                    const aCell = a.children[index];
                    const bCell = b.children[index];
                    const aRaw = aCell ? aCell.dataset.sortValue || aCell.textContent : "";
                    const bRaw = bCell ? bCell.dataset.sortValue || bCell.textContent : "";
                    let result = 0;
                    if (type === "number") {{
                        result = (parseFloat(aRaw) || 0) - (parseFloat(bRaw) || 0);
                    }} else {{
                        result = aRaw.localeCompare(bRaw, undefined, {{ numeric: true, sensitivity: "base" }});
                    }}
                    return nextDirection === "asc" ? result : -result;
                }});
                rows.forEach((row) => tbody.appendChild(row));
            }});
        }});
        table.querySelectorAll("td").forEach((cell) => {{
            cell.addEventListener("click", () => {{
                detailTitle.textContent = cell.dataset.label || "Cell detail";
                detailText.textContent = cell.dataset.fullText || cell.textContent || "";
                detail.style.display = "block";
            }});
        }});
        </script>
    """
    components.html(
        board_html,
        height=690,
        scrolling=False,
    )


def available_columns(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    """Return only columns that exist in a DataFrame."""
    return [column for column in columns if column in frame.columns]


def numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    """Return a numeric series aligned to a frame for filters."""
    return pd.to_numeric(frame.get(column, pd.Series(0, index=frame.index)), errors="coerce").fillna(0)


def option_values(frame: pd.DataFrame, column: str) -> list[str]:
    """Return clean sorted values for filter controls."""
    if column not in frame.columns:
        return []
    values = [clean_text(value) for value in frame[column].dropna().unique()]
    return sorted(value for value in values if value)


def what_i_think_options(frame: pd.DataFrame) -> list[str]:
    """Return combined primary/secondary What I Think labels for one filter."""
    values: set[str] = set()
    for column in ["what_i_think", "secondary_what_i_think"]:
        if column in frame.columns:
            values.update(clean_text(value) for value in frame[column].dropna().unique())
    return sorted(value for value in values if value)


def filter_by_what_i_think(frame: pd.DataFrame, labels: list[str] | str) -> pd.DataFrame:
    """Match labels against both What I Think columns."""
    if frame.empty:
        return frame
    if isinstance(labels, str):
        labels = [labels]
    labels = [label for label in labels if label and label != "All"]
    if not labels:
        return frame
    primary = frame.get("what_i_think", pd.Series("", index=frame.index)).astype(str)
    secondary = frame.get("secondary_what_i_think", pd.Series("", index=frame.index)).astype(str)
    return frame[primary.isin(labels) | secondary.isin(labels)]


def apply_watchlist_mode(frame: pd.DataFrame, mode: str) -> pd.DataFrame:
    """Apply one high-level research view without deleting the underlying data."""
    if frame.empty:
        return frame
    output = frame.copy()
    verdict = output.get("what_i_think", pd.Series("", index=output.index)).astype(str)
    risk = output.get("risk_posture", pd.Series("", index=output.index)).astype(str)
    long_term_label = output.get("long_term_investment_label", pd.Series("", index=output.index)).astype(str)

    weak_labels = ["This is Garbage", "Needs More Clues"]

    if mode == "Clean Research":
        return output[~verdict.isin(weak_labels)]
    if mode == "Garbage Lab":
        return output[verdict.isin(weak_labels)]
    if mode == "Best Overall":
        return output[
            ~verdict.isin(weak_labels)
            & ~risk.str.contains("Extreme dilution|Catastrophic|Old thesis broken", case=False, na=False)
            & (numeric_series(output, "data_confidence_score") >= 75)
        ]
    if mode == "Long-Term Hunt":
        return output[
            long_term_label.isin(["Long-Term Microcap Candidate", "Long-Term Watchlist", "Business Looks Real, Risks Bite"])
        ]
    if mode == "Danger Zone":
        return output[
            verdict.isin(weak_labels)
            | risk.str.contains("Extreme dilution|Catastrophic|Survival|Old thesis broken|Dilution", case=False, na=False)
        ]
    return output


def lens_sort_column(lens: str) -> str:
    """Map a front-office lens to the score column it should emphasize."""
    lens_map = {
        "Overall Big Board": "scooby_score",
        "Hume Flow": "hume_flow_potential_score",
        "Keynes Story": "keynes_repricing_potential_score",
        "Austrian Pricing Gap": "austrian_mispricing_score",
        "Relative Value": "relative_mispricing_score",
        "Asymmetry": "asymmetry_score",
        "Long-Term Quality": "long_term_investment_score",
        "Pre-Flow Sleeper": "pre_flow_opportunity_score",
        "Data Confidence": "data_confidence_score",
        "Danger Review": "event_shock_penalty",
    }
    return lens_map.get(lens, "scooby_score")


def apply_lens(frame: pd.DataFrame, lens: str) -> pd.DataFrame:
    """Apply a non-destructive research lens to the visible board."""
    if frame.empty:
        return frame
    output = frame.copy()
    if lens == "Hume Flow":
        output = output[numeric_series(output, "hume_flow_potential_score") >= 35]
    elif lens == "Keynes Story":
        output = output[numeric_series(output, "keynes_repricing_potential_score") >= 45]
    elif lens == "Austrian Pricing Gap":
        output = output[numeric_series(output, "austrian_mispricing_score") >= 45]
    elif lens == "Relative Value":
        output = output[numeric_series(output, "relative_mispricing_score") >= 35]
    elif lens == "Asymmetry":
        output = output[numeric_series(output, "asymmetry_score") >= 35]
    elif lens == "Long-Term Quality":
        output = output[numeric_series(output, "long_term_investment_score") >= 35]
    elif lens == "Pre-Flow Sleeper":
        output = output[
            (numeric_series(output, "pre_flow_opportunity_score") >= 45)
            & (numeric_series(output, "hume_flow_potential_score") <= 55)
        ]
    elif lens == "Data Confidence":
        output = output[numeric_series(output, "data_confidence_score") >= 80]
    elif lens == "Danger Review":
        output = output[
            (numeric_series(output, "event_shock_penalty") >= 10)
            | (numeric_series(output, "dilution_pressure_score") >= 70)
            | (numeric_series(output, "survival_risk_score") >= 70)
        ]
    return output


st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #0b1020 0%, #14213a 32%, #f5f7fb 32%, #f5f7fb 100%);
    }
    .block-container {
        padding-top: 1.5rem;
    }
    .cfe-hero {
        border: 1px solid rgba(147, 197, 253, 0.45);
        background:
            radial-gradient(circle at 92% 8%, rgba(34, 197, 94, .24), transparent 28%),
            linear-gradient(135deg, #0f172a, #1d4ed8);
        color: #f9fafb;
        padding: 1.25rem 1.45rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        box-shadow: 0 18px 46px rgba(15, 23, 42, 0.22);
    }
    .cfe-hero h1 {
        margin: 0 0 .35rem 0;
        font-size: 2.25rem;
        letter-spacing: 0;
    }
    .cfe-hero p {
        margin: 0;
        color: #dbeafe;
        font-size: 1rem;
    }
    .hero-kicker {
        color: #bfdbfe;
        text-transform: uppercase;
        font-size: .74rem;
        font-weight: 800;
        margin-bottom: .2rem;
    }
    .cfe-panel, .score-panel {
        border: 1px solid #d8deea;
        background: #ffffff;
        border-radius: 8px;
        padding: .85rem .95rem;
        min-height: 6rem;
        box-shadow: 0 8px 24px rgba(20,31,56,0.06);
    }
    .cfe-panel-label, .score-label {
        color: #687386;
        font-size: .78rem;
        text-transform: uppercase;
        letter-spacing: 0;
    }
    .cfe-panel-value, .score-value {
        color: #111827;
        font-size: 1.45rem;
        font-weight: 750;
        margin-top: .18rem;
    }
    .cfe-panel-note, .score-note {
        color: #586174;
        font-size: .86rem;
        margin-top: .18rem;
    }
    .score-panel.hot { border-left: 7px solid #16a34a; }
    .score-panel.warm { border-left: 7px solid #2563eb; }
    .score-panel.mixed { border-left: 7px solid #d97706; }
    .score-panel.cold { border-left: 7px solid #6b7280; }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff !important;
        border: 2px solid #c7d4e8 !important;
        border-radius: 8px !important;
        box-shadow: 0 12px 28px rgba(15, 23, 42, .10) !important;
        padding: .78rem .9rem .9rem .9rem !important;
    }
    .draft-card-content {
        margin-top: .35rem;
    }
    .draft-native-head {
        color: #111827;
        line-height: 1.2;
        white-space: nowrap;
    }
    .draft-topline {
        display: flex;
        align-items: center;
        gap: .45rem;
        margin-bottom: .25rem;
    }
    .draft-rank {
        color: #64748b;
        font-weight: 800;
        font-size: .8rem;
    }
    .draft-ticker {
        color: #111827;
        font-weight: 900;
        font-size: 1.2rem;
    }
    .draft-grade {
        margin-left: auto;
        background: #101827;
        color: #ffffff !important;
        border-radius: 6px;
        padding: .2rem .5rem;
        font-weight: 900;
        font-size: .8rem;
        line-height: 1;
        min-width: 2.35rem;
        min-height: 1.45rem;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        white-space: nowrap;
    }
    .native-grade {
        margin-left: 0;
        width: 100%;
    }
    .draft-grade * { color: #ffffff !important; }
    .draft-name {
        color: #475569;
        min-height: 2.4rem;
        font-size: .9rem;
    }
    .draft-scorebar {
        height: .48rem;
        background: #e5eaf3;
        border-radius: 999px;
        overflow: hidden;
        margin: .65rem 0 .45rem 0;
    }
    .draft-scorebar div {
        height: 100%;
        background: linear-gradient(90deg, #2563eb, #16a34a);
    }
    .draft-meta, .draft-note {
        color: #64748b;
        font-size: .82rem;
        line-height: 1.25rem;
    }
    .draft-badge {
        margin: .55rem 0 .3rem 0;
    }
    div[data-testid="stButton"] button {
        border-radius: 8px !important;
        border: 1px solid #2563eb !important;
        background: #eff6ff !important;
        color: #1e3a8a !important;
        font-weight: 900 !important;
        min-height: 2.05rem !important;
        padding-left: .85rem !important;
        padding-right: .85rem !important;
        width: 100% !important;
    }
    div[data-testid="stButton"] button *,
    div[data-testid="stButton"] button p,
    div[data-testid="stButton"] button span {
        color: #1e3a8a !important;
        font-weight: 900 !important;
    }
    .verdict-pill {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: .24rem .55rem;
        font-weight: 850;
        font-size: .78rem;
        border: 1px solid transparent;
        white-space: normal;
    }
    .verdict-scooby { background: #dcfce7; color: #14532d; border-color: #86efac; }
    .verdict-watch { background: #dbeafe; color: #1e3a8a; border-color: #93c5fd; }
    .verdict-mid { background: #f1f5f9; color: #334155; border-color: #cbd5e1; }
    .verdict-risk { background: #fef3c7; color: #92400e; border-color: #fcd34d; }
    .verdict-garbage { background: #fee2e2; color: #991b1b; border-color: #fecaca; }
    .verdict-scooby, .verdict-scooby * { color: #14532d !important; }
    .verdict-watch, .verdict-watch * { color: #1e3a8a !important; }
    .verdict-mid, .verdict-mid * { color: #334155 !important; }
    .verdict-risk, .verdict-risk * { color: #92400e !important; }
    .verdict-garbage, .verdict-garbage * { color: #991b1b !important; }
    .scout-card {
        border: 1px solid #cbd5e1;
        background: linear-gradient(180deg, #ffffff, #f8fbff);
        border-radius: 8px;
        padding: 1.15rem;
        box-shadow: 0 16px 34px rgba(20,31,56,0.10);
        margin-top: .75rem;
    }
    .scout-mini {
        border: 1px solid #c8d9ff;
        background: linear-gradient(180deg, #ffffff, #f8fbff);
        border-radius: 8px;
        padding: .95rem;
        margin-bottom: .75rem;
    }
    .scout-mini-title {
        color: #0f172a;
        font-size: 1.1rem;
        font-weight: 950;
        margin-bottom: .25rem;
    }
    .scout-mini-subtitle {
        color: #475569;
        font-size: .88rem;
        margin-bottom: .55rem;
    }
    .scout-mini,
    .scout-mini * {
        text-shadow: none !important;
    }
    .scout-console {
        border: 1px solid #b9c8df;
        background:
            radial-gradient(circle at 88% 5%, rgba(37, 99, 235, .16), transparent 28%),
            radial-gradient(circle at 8% 18%, rgba(22, 163, 74, .12), transparent 25%),
            linear-gradient(180deg, #ffffff, #f7fbff);
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 18px 42px rgba(15, 23, 42, .12);
        margin: .75rem 0 1rem 0;
    }
    .scout-console,
    .scout-console * {
        color: #0f172a !important;
        text-shadow: none !important;
    }
    .scout-console-hero {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        border-bottom: 1px solid #dbe6f5;
        padding-bottom: .85rem;
        margin-bottom: .9rem;
    }
    .scout-kicker {
        color: #2563eb !important;
        font-size: .76rem;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: 0;
    }
    .scout-console-title {
        color: #0f172a !important;
        font-size: 1.55rem;
        line-height: 1.1;
        font-weight: 950;
        margin-top: .15rem;
    }
    .scout-console-title span {
        color: #475569 !important;
        font-size: .95rem;
        font-weight: 750;
        margin-left: .35rem;
    }
    .scout-console-subtitle {
        color: #64748b !important;
        font-size: .9rem;
        margin: .3rem 0 .55rem 0;
    }
    .scout-grade-orb {
        min-width: 5.7rem;
        min-height: 5.7rem;
        border-radius: 999px;
        background: linear-gradient(135deg, #0f172a, #1d4ed8);
        border: 3px solid #bfdbfe;
        box-shadow: 0 16px 32px rgba(29, 78, 216, .24);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
    }
    .scout-grade-orb span,
    .scout-grade-orb small {
        color: #ffffff !important;
    }
    .scout-grade-orb span {
        font-size: 1.5rem;
        font-weight: 950;
        line-height: 1;
    }
    .scout-grade-orb small {
        font-size: .72rem;
        margin-top: .25rem;
        opacity: .9;
    }
    .scout-console-grid {
        display: grid;
        grid-template-columns: minmax(250px, 340px) minmax(260px, 1fr);
        gap: 1rem;
        align-items: stretch;
    }
    .power-hex-card,
    .power-bars,
    .story-tile {
        border: 1px solid #d5e1f0;
        border-radius: 8px;
        background: rgba(255, 255, 255, .86);
        box-shadow: inset 0 1px 0 rgba(255,255,255,.75);
    }
    .power-hex-card {
        padding: .75rem .65rem .55rem .65rem;
    }
    .power-heading {
        color: #1e3a8a !important;
        font-weight: 950;
        font-size: .9rem;
        margin: 0 0 .2rem .2rem;
    }
    .power-hex {
        width: 100%;
        min-height: 250px;
        display: block;
    }
    .power-ring {
        fill: none;
        stroke: #cbd5e1;
        stroke-width: 1.1;
    }
    .power-spoke {
        stroke: #d8e2ef;
        stroke-width: 1;
    }
    .power-shape {
        fill: rgba(37, 99, 235, .22);
        stroke: #2563eb;
        stroke-width: 3;
    }
    .power-core {
        fill: #16a34a;
    }
    .power-label {
        fill: #334155;
        font-size: 10.5px;
        font-weight: 850;
    }
    .power-bars {
        padding: .85rem;
    }
    .power-bar-row {
        display: grid;
        grid-template-columns: minmax(96px, 1fr) 2.4rem;
        gap: .55rem;
        align-items: center;
        margin-bottom: .72rem;
    }
    .power-bar-row strong {
        display: block;
        color: #0f172a !important;
        font-size: .86rem;
        font-weight: 950;
    }
    .power-bar-row span {
        display: block;
        color: #64748b !important;
        font-size: .73rem;
        line-height: 1.05rem;
    }
    .power-bar-row b {
        color: #1d4ed8 !important;
        font-size: .9rem;
        text-align: right;
    }
    .power-bar {
        grid-column: 1 / 3;
        height: .5rem;
        border-radius: 999px;
        background: #e2eaf5;
        overflow: hidden;
    }
    .power-bar div {
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, #2563eb, #16a34a);
    }
    .story-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: .7rem;
        margin-top: .9rem;
    }
    .story-tile {
        padding: .75rem;
        min-height: 6.2rem;
        border-left: 5px solid #2563eb;
    }
    .story-title {
        color: #0f172a !important;
        font-size: .8rem;
        font-weight: 950;
        text-transform: uppercase;
        letter-spacing: 0;
        margin-bottom: .35rem;
    }
    .story-body {
        color: #475569 !important;
        font-size: .86rem;
        line-height: 1.25rem;
    }
    .story-green { border-left-color: #16a34a; }
    .story-teal { border-left-color: #0891b2; }
    .story-amber { border-left-color: #d97706; }
    .story-red { border-left-color: #dc2626; }
    .story-purple { border-left-color: #7c3aed; }
    .scout-picker {
        border: 1px solid #c8d9ff;
        background: linear-gradient(135deg, #eff6ff, #ffffff);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 12px 28px rgba(20,31,56,0.07);
    }
    .scout-picker-title {
        color: #0f172a;
        font-size: 1.45rem;
        font-weight: 950;
        margin-bottom: .15rem;
    }
    .scout-picker-note {
        color: #475569;
        font-size: .95rem;
    }
    .scout-title {
        font-size: 1.85rem;
        font-weight: 900;
        color: #0f172a;
        margin-bottom: .15rem;
    }
    .scout-subtitle {
        color: #64748b;
        margin-bottom: .65rem;
    }
    .toolbar-note {
        background: #eef4ff;
        border: 1px solid #c8d9ff;
        color: #1e3a8a;
        border-radius: 8px;
        padding: .75rem .9rem;
        margin: .5rem 0 1rem 0;
    }
    .quick-scout-shell {
        border: 1px solid #bfdbfe;
        background:
            radial-gradient(circle at 96% 0%, rgba(37, 99, 235, .16), transparent 30%),
            linear-gradient(135deg, #ffffff, #eff6ff);
        border-radius: 8px;
        padding: .9rem 1rem;
        margin: .35rem 0 1rem 0;
        box-shadow: 0 14px 32px rgba(37, 99, 235, .12);
    }
    .quick-scout-title {
        color: #0f172a !important;
        font-weight: 950;
        font-size: 1.05rem;
        margin-bottom: .15rem;
    }
    .quick-scout-note {
        color: #475569 !important;
        font-size: .88rem;
    }
    .board-command-row {
        border: 1px solid #bfd1eb;
        background: linear-gradient(135deg, #ffffff, #f4f8ff);
        border-radius: 8px;
        padding: .85rem;
        margin: .25rem 0 1rem 0;
        box-shadow: 0 12px 28px rgba(37, 99, 235, .10);
    }
    .board-command-row [data-testid="stWidgetLabel"] *,
    .board-command-row label,
    .board-command-row p {
        color: #0f172a !important;
        font-weight: 850 !important;
    }
    .board-wrap {
        width: 100%;
        max-height: 680px;
        overflow: auto;
        border: 1px solid #ccd6e6;
        border-radius: 8px;
        background: #ffffff;
        box-shadow: 0 12px 34px rgba(20,31,56,0.08);
    }
    .big-board-table {
        border-collapse: separate;
        border-spacing: 0;
        min-width: 1680px;
        width: max-content;
        font-size: .8rem;
        color: #172033;
    }
    .big-board-table th {
        position: sticky;
        top: 0;
        z-index: 5;
        background: #111827;
        color: #f8fafc;
        text-align: left;
        padding: .55rem .62rem;
        border-bottom: 1px solid #334155;
        white-space: nowrap;
    }
    .big-board-table td {
        padding: .5rem .62rem;
        border-bottom: 1px solid #e6ecf5;
        background: #ffffff;
        vertical-align: middle;
    }
    .big-board-table tr:nth-child(even) td {
        background: #f8fbff;
    }
    .big-board-table tr:hover td {
        background: #eef6ff;
    }
    .big-board-table .sticky-ticker {
        position: sticky;
        left: 0;
        z-index: 6;
        width: 80px;
        min-width: 80px;
        font-weight: 900;
        color: #0f172a;
        box-shadow: 1px 0 0 #d7deea;
    }
    .big-board-table th.sticky-ticker {
        z-index: 8;
        background: #0b1220;
    }
    .big-board-table td,
    .big-board-table td *,
    .mini-score,
    .mini-score * {
        color: #172033 !important;
    }
    .big-board-table th,
    .big-board-table th * {
        color: #ffffff !important;
    }
    .big-board-table .col-ranking_note,
    .big-board-table .col-event_callouts,
    .big-board-table .col-risk_posture,
    .big-board-table .col-flow_state {
        max-width: 260px;
        min-width: 180px;
    }
    .mini-score {
        min-width: 92px;
    }
    .mini-score span {
        display: inline-block;
        min-width: 2.8rem;
        font-weight: 800;
        color: #172033;
    }
    .mini-bar {
        display: inline-block;
        width: 45px;
        height: .38rem;
        margin-left: .28rem;
        background: #dbe4f0;
        border-radius: 99px;
        overflow: hidden;
        vertical-align: middle;
    }
    .mini-bar div {
        height: 100%;
        background: linear-gradient(90deg, #2563eb, #16a34a);
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #d8deea;
        border-radius: 8px;
        overflow: hidden;
    }
    div[data-testid="stTabs"] div[role="tablist"] {
        background: linear-gradient(135deg, #ffffff, #eef6ff) !important;
        border: 1px solid #bfdbfe !important;
        border-radius: 10px !important;
        padding: .45rem !important;
        gap: .35rem !important;
        box-shadow: 0 14px 34px rgba(37,99,235,0.14);
    }
    div[data-testid="stTabs"] button[role="tab"] {
        color: #0f172a !important;
        background: linear-gradient(180deg, #ffffff, #eaf2ff) !important;
        border: 2px solid #bfdbfe !important;
        border-radius: 8px !important;
        font-weight: 950 !important;
        min-height: 3rem !important;
        padding: .55rem 1rem !important;
        box-shadow: 0 10px 22px rgba(37, 99, 235, .12) !important;
    }
    div[data-testid="stTabs"] button[role="tab"] p {
        color: #0f172a !important;
        font-size: 1rem !important;
        font-weight: 950 !important;
    }
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #0f172a, #1d4ed8) !important;
        border-color: #93c5fd !important;
        color: #ffffff !important;
        box-shadow: 0 16px 32px rgba(29, 78, 216, .28), 0 0 0 3px rgba(147, 197, 253, .35) !important;
    }
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] p {
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] button,
    section[data-testid="stSidebar"] [role="button"] {
        background: #ffffff !important;
        color: #0f172a !important;
        border-color: #cbd5e1 !important;
        box-shadow: none !important;
    }
    section[data-testid="stSidebar"] button *,
    section[data-testid="stSidebar"] [role="button"] * {
        color: #0f172a !important;
        text-shadow: none !important;
    }
    section[data-testid="stSidebar"] button[aria-pressed="true"],
    section[data-testid="stSidebar"] button[aria-selected="true"],
    section[data-testid="stSidebar"] [role="button"][aria-pressed="true"],
    section[data-testid="stSidebar"] [role="button"][aria-selected="true"] {
        background: #1d4ed8 !important;
        color: #ffffff !important;
        border-color: #1d4ed8 !important;
    }
    section[data-testid="stSidebar"] button[aria-pressed="true"] *,
    section[data-testid="stSidebar"] button[aria-selected="true"] *,
    section[data-testid="stSidebar"] [role="button"][aria-pressed="true"] *,
    section[data-testid="stSidebar"] [role="button"][aria-selected="true"] * {
        color: #ffffff !important;
    }
    div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        display: none !important;
    }
    section[data-testid="stSidebar"] {
        background: #f7f9fd;
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
        div[data-testid="stTabs"] div[role="tablist"] {
            display: grid !important;
            grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
            gap: .18rem !important;
            padding: .28rem !important;
            overflow: visible !important;
        }
        div[data-testid="stTabs"] button[role="tab"] {
            min-width: 0 !important;
            min-height: 2.45rem !important;
            padding: .3rem .08rem !important;
            border-width: 1px !important;
        }
        div[data-testid="stTabs"] button[role="tab"] p {
            font-size: .68rem !important;
            line-height: .82rem !important;
            white-space: normal !important;
            text-align: center !important;
        }
        .scout-console {
            padding: .8rem;
        }
        .scout-console-hero,
        .scout-console-grid {
            display: block;
        }
        .scout-grade-orb {
            margin-top: .7rem;
            min-width: 4.8rem;
            min-height: 4.8rem;
        }
        .story-grid {
            grid-template-columns: 1fr;
        }
        .scout-console-title {
            font-size: 1.25rem;
        }
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
    /*
    Contrast guardrail:
    Keep Streamlit/BaseWeb controls readable across desktop, mobile, and
    Streamlit Cloud theme changes without repainting the custom dark hero,
    selected tabs, table headers, or Scout grade orb.
    */
    .block-container h1:not(.cfe-hero h1),
    .block-container h2,
    .block-container h3,
    .block-container h4,
    .block-container h5,
    .block-container h6,
    .block-container p:not(.cfe-hero p),
    .block-container li,
    .block-container label,
    .block-container span:not(.verdict-pill):not(.draft-grade):not(.scout-grade-orb span),
    .block-container small:not(.scout-grade-orb small),
    .block-container div[data-testid="stMarkdownContainer"]:not(.cfe-hero):not(.scout-grade-orb),
    .block-container [data-testid="stCaptionContainer"],
    .block-container [data-testid="stCaptionContainer"] *,
    .block-container [data-testid="stWidgetLabel"],
    .block-container [data-testid="stWidgetLabel"] *,
    .block-container [data-testid="stMetric"],
    .block-container [data-testid="stMetric"] * {
        color: #0f172a !important;
        text-shadow: none !important;
    }
    section[data-testid="stSidebar"],
    section[data-testid="stSidebar"] *,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] small,
    section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"],
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] * {
        color: #0f172a !important;
        text-shadow: none !important;
    }
    [data-baseweb="select"] > div,
    [data-baseweb="input"] > div,
    [data-baseweb="textarea"] > div,
    input,
    textarea {
        background: #ffffff !important;
        color: #0f172a !important;
        border-color: #cbd5e1 !important;
        text-shadow: none !important;
    }
    [data-baseweb="select"] *,
    [data-baseweb="input"] *,
    [data-baseweb="textarea"] *,
    [data-baseweb="popover"] *,
    [role="listbox"] *,
    [role="option"] *,
    input::placeholder,
    textarea::placeholder {
        color: #0f172a !important;
        text-shadow: none !important;
    }
    [data-baseweb="popover"],
    [data-baseweb="popover"] > div,
    [role="listbox"],
    [role="option"] {
        background: #ffffff !important;
    }
    div[data-testid="stRadio"] label,
    div[data-testid="stRadio"] label *,
    div[data-testid="stCheckbox"] label,
    div[data-testid="stCheckbox"] label *,
    div[data-testid="stSlider"] label,
    div[data-testid="stSlider"] label *,
    div[data-testid="stSlider"] [data-testid="stTickBar"],
    div[data-testid="stSlider"] [data-testid="stTickBar"] *,
    div[data-testid="stSlider"] [role="slider"] + div,
    div[data-testid="stSlider"] [role="slider"] + div *,
    div[data-testid="stNumberInput"] *,
    div[data-testid="stTextInput"] *,
    div[data-testid="stSelectbox"] *,
    div[data-testid="stMultiSelect"] * {
        color: #0f172a !important;
        text-shadow: none !important;
    }
    div[data-testid="stCheckbox"] [data-testid="stMarkdownContainer"] p,
    div[data-testid="stRadio"] [data-testid="stMarkdownContainer"] p {
        color: #0f172a !important;
    }
    div[data-testid="stCheckbox"] span,
    div[data-testid="stRadio"] span {
        color: #0f172a !important;
    }
    div[data-testid="stSlider"] [role="slider"] {
        background: #1d4ed8 !important;
        border-color: #ffffff !important;
        box-shadow: 0 0 0 2px rgba(29, 78, 216, .18) !important;
    }
    div[data-testid="stSlider"] [data-baseweb="slider"] div {
        color: #0f172a !important;
    }
    div[data-testid="stDataFrame"],
    div[data-testid="stDataFrame"] *,
    div[data-testid="stTable"],
    div[data-testid="stTable"] * {
        color: #0f172a !important;
        text-shadow: none !important;
    }
    div[data-testid="stDataFrame"] [role="columnheader"],
    div[data-testid="stDataFrame"] [role="columnheader"] *,
    div[data-testid="stTable"] th,
    div[data-testid="stTable"] th * {
        color: #ffffff !important;
        background: #111827 !important;
    }
    a,
    a *,
    div[data-testid="stLinkButton"] button,
    div[data-testid="stLinkButton"] button * {
        color: #1e3a8a !important;
        text-shadow: none !important;
    }
    div[data-testid="stLinkButton"] button {
        background: #eff6ff !important;
        border: 1px solid #2563eb !important;
    }
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapsedControl"] *,
    header[data-testid="stHeader"] button[aria-label*="sidebar" i],
    header[data-testid="stHeader"] button[aria-label*="sidebar" i] *,
    button[aria-label*="sidebar" i],
    button[aria-label*="sidebar" i] *,
    button[title*="sidebar" i],
    button[title*="sidebar" i] * {
        opacity: 1 !important;
        visibility: visible !important;
        color: #0f172a !important;
        fill: #0f172a !important;
        stroke: #0f172a !important;
        text-shadow: none !important;
    }
    [data-testid="stSidebarCollapsedControl"] button,
    header[data-testid="stHeader"] button[aria-label*="sidebar" i],
    button[aria-label*="sidebar" i],
    button[title*="sidebar" i] {
        background: #ffffff !important;
        border: 2px solid #2563eb !important;
        border-radius: 999px !important;
        box-shadow: 0 10px 28px rgba(37, 99, 235, .30), 0 0 0 4px rgba(219, 234, 254, .9) !important;
        min-width: 2.6rem !important;
        min-height: 2.6rem !important;
        z-index: 999999 !important;
    }
    @media (max-width: 900px) {
        [data-testid="stSidebarCollapsedControl"] {
            position: fixed !important;
            top: 44vh !important;
            left: .55rem !important;
            z-index: 999999 !important;
        }
        [data-testid="stSidebarCollapsedControl"] button,
        header[data-testid="stHeader"] button[aria-label*="sidebar" i],
        button[aria-label*="sidebar" i],
        button[title*="sidebar" i] {
            min-width: 3rem !important;
            min-height: 3rem !important;
        }
    }
    [data-baseweb="tag"] {
        background: #dbeafe !important;
        border: 1px solid #93c5fd !important;
    }
    [data-baseweb="tag"],
    [data-baseweb="tag"] * {
        color: #1e3a8a !important;
    }
    [data-testid="stAlert"],
    [data-testid="stAlert"] *,
    [data-testid="stNotification"],
    [data-testid="stNotification"] * {
        color: #0f172a !important;
        text-shadow: none !important;
    }
    div[data-testid="stDialog"],
    div[data-testid="stDialog"] *,
    div[role="dialog"],
    div[role="dialog"] * {
        color: #0f172a !important;
        text-shadow: none !important;
    }
    div[data-testid="stDialog"],
    div[role="dialog"] {
        background: #ffffff !important;
        max-height: 88vh !important;
        overflow-y: auto !important;
        overscroll-behavior: contain !important;
    }
    .cfe-hero,
    .cfe-hero *,
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"],
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] *,
    .big-board-table th,
    .big-board-table th *,
    .draft-grade,
    .draft-grade *,
    .scout-grade-orb,
    .scout-grade-orb * {
        color: #ffffff !important;
    }
    .toolbar-note,
    .toolbar-note *,
    .quick-scout-shell,
    .quick-scout-shell *,
    .cfe-panel,
    .cfe-panel *,
    .score-panel,
    .score-panel *,
    .story-tile,
    .story-tile *,
    .power-bars,
    .power-bars *,
    .power-hex-card,
    .power-hex-card * {
        text-shadow: none !important;
    }
    div[role="dialog"] .scout-console-compact {
        border: 1px solid rgba(147, 197, 253, .55) !important;
        background:
            radial-gradient(circle at 88% 8%, rgba(37, 99, 235, .36), transparent 30%),
            radial-gradient(circle at 10% 12%, rgba(22, 163, 74, .22), transparent 24%),
            linear-gradient(145deg, #07111f, #111827 55%, #0b1220) !important;
        box-shadow: 0 24px 70px rgba(2, 6, 23, .34) !important;
    }
    div[role="dialog"] .scout-console-compact,
    div[role="dialog"] .scout-console-compact * {
        color: #e5eefc !important;
        text-shadow: none !important;
    }
    div[role="dialog"] .scout-console-compact .scout-console-hero {
        border-bottom-color: rgba(191, 219, 254, .24) !important;
    }
    div[role="dialog"] .scout-console-compact .scout-kicker {
        color: #93c5fd !important;
    }
    div[role="dialog"] .scout-console-compact .scout-console-title,
    div[role="dialog"] .scout-console-compact .scout-console-title span {
        color: #f8fafc !important;
    }
    div[role="dialog"] .scout-console-compact .scout-console-subtitle,
    div[role="dialog"] .scout-console-compact .story-body,
    div[role="dialog"] .scout-console-compact .power-bar-row span {
        color: #cbd5e1 !important;
    }
    div[role="dialog"] .scout-console-compact .power-hex-card,
    div[role="dialog"] .scout-console-compact .power-bars,
    div[role="dialog"] .scout-console-compact .story-tile {
        background: rgba(15, 23, 42, .82) !important;
        border-color: rgba(148, 163, 184, .35) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.08) !important;
    }
    div[role="dialog"] .scout-console-compact .power-heading,
    div[role="dialog"] .scout-console-compact .story-title,
    div[role="dialog"] .scout-console-compact .power-bar-row strong,
    div[role="dialog"] .scout-console-compact .power-bar-row b {
        color: #bfdbfe !important;
    }
    div[role="dialog"] .scout-console-compact .power-label {
        fill: #dbeafe !important;
    }
    div[role="dialog"] .scout-console-compact .power-ring {
        stroke: #334155 !important;
    }
    div[role="dialog"] .scout-console-compact .power-spoke {
        stroke: #475569 !important;
    }
    div[role="dialog"] .scout-console-compact .verdict-scooby,
    div[role="dialog"] .scout-console-compact .verdict-scooby * { color: #14532d !important; }
    div[role="dialog"] .scout-console-compact .verdict-watch,
    div[role="dialog"] .scout-console-compact .verdict-watch * { color: #1e3a8a !important; }
    div[role="dialog"] .scout-console-compact .verdict-mid,
    div[role="dialog"] .scout-console-compact .verdict-mid * { color: #334155 !important; }
    div[role="dialog"] .scout-console-compact .verdict-risk,
    div[role="dialog"] .scout-console-compact .verdict-risk * { color: #92400e !important; }
    div[role="dialog"] .scout-console-compact .verdict-garbage,
    div[role="dialog"] .scout-console-compact .verdict-garbage * { color: #991b1b !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="cfe-hero">
        <div class="hero-kicker">Front office scouting board</div>
        <h1>Contrarian 10-Bagger Engine</h1>
        <p>A playable research dashboard for speculative microcap candidates. Movement potential, not buy/sell advice.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

universe = load_csv(str(UNIVERSE_PATH))
theory_scores = load_csv(str(THEORY_SCORES_PATH))
research_batch = load_csv(str(RESEARCH_BATCH_PATH))
price_history = load_csv(str(PRICE_HISTORY_PATH))
source_status = load_csv(str(SOURCE_STATUS_PATH))

if universe.empty:
    st.warning("No universe file found yet. Run the data refresh launcher first.")
    st.stop()

if not theory_scores.empty and not research_batch.empty and "ticker" in research_batch.columns:
    batch_tickers = set(research_batch["ticker"].astype(str).str.upper())
    display_scores = theory_scores[theory_scores["ticker"].astype(str).str.upper().isin(batch_tickers)].copy()
else:
    display_scores = theory_scores.copy()

if not display_scores.empty:
    for score_column in [
        "movement_score",
        "pre_flow_opportunity_score",
        "long_term_investment_score",
        "data_confidence_score",
        "dilution_pressure_score",
        "survival_risk_score",
        "zombie_decay_penalty",
        "event_shock_penalty",
        "austrian_mispricing_score",
        "hume_flow_potential_score",
        "keynes_repricing_potential_score",
        "relative_mispricing_score",
        "asymmetry_score",
    ]:
        if score_column in display_scores.columns:
            display_scores[score_column] = pd.to_numeric(display_scores[score_column], errors="coerce")

LENS_OPTIONS = [
    "Overall Big Board",
    "Hume Flow",
    "Keynes Story",
    "Austrian Pricing Gap",
    "Relative Value",
    "Asymmetry",
    "Long-Term Quality",
    "Pre-Flow Sleeper",
    "Data Confidence",
    "Danger Review",
]
research_lens = st.session_state.get("big_board_lens", "Overall Big Board")

with st.sidebar:
    st.subheader("Filters")
    sort_options = {
        f"Lens default ({BOARD_LABELS.get(lens_sort_column(research_lens), lens_sort_column(research_lens))})": lens_sort_column(research_lens),
        "Scooby Score": "scooby_score",
        "Adjusted Movement": "movement_score",
        "Raw Movement": "raw_movement_score",
        "Long-term score": "long_term_investment_score",
        "Pre-flow sleeper score": "pre_flow_opportunity_score",
        "Data confidence": "data_confidence_score",
        "Hume flow": "hume_flow_potential_score",
        "Keynes story": "keynes_repricing_potential_score",
        "Austrian pricing gap": "austrian_mispricing_score",
        "Relative value": "relative_mispricing_score",
        "Asymmetry": "asymmetry_score",
        "Dilution pressure": "dilution_pressure_score",
        "Survival risk": "survival_risk_score",
        "Event penalty": "event_shock_penalty",
        "Ticker A-Z": "ticker",
    }
    sort_label = st.selectbox(
        "Sort by",
        list(sort_options),
        index=0,
    )
    sort_by = sort_options[sort_label]
    sort_direction = st.radio("Sort direction", ["High to low", "Low to high"], horizontal=True)
    top_n = st.slider("Rows to show", 10, 500, 250, 10)
    advanced_mode = st.toggle("Advanced columns", value=False)

    st.divider()
    st.caption("Quick Checks")
    hide_garbage_check = st.checkbox("Hide garbage rows", value=False)
    require_good_data_check = st.checkbox("Require good data", value=False)
    event_flags_check = st.checkbox("Only event/shock flags", value=False)
    low_flow_sleepers_check = st.checkbox("Low-flow sleepers", value=False)
    high_dilution_check = st.checkbox("Show dilution danger only", value=False)

    st.divider()
    st.caption("Score Floors")
    min_move = st.slider("Movement", 0, 100, 0, 1)
    min_long_term = st.slider("Long-term", 0, 100, 0, 1)
    min_data = st.slider("Data quality", 0, 100, 0, 1)
    min_pre_flow = st.slider("Pre-flow", 0, 100, 0, 1)

    st.caption("Risk Ceilings")
    max_dilution = st.slider("Max dilution pressure", 0, 100, 100, 1)
    max_survival = st.slider("Max survival risk", 0, 100, 100, 1)
    max_zombie = st.slider("Max zombie drag", 0, 30, 30, 1)
    max_event = st.slider("Max event penalty", 0, 100, 100, 1)

    st.divider()
    sector_options = option_values(display_scores, "sector")
    selected_sectors = st.multiselect("Sector", sector_options)
    verdict_options = what_i_think_options(display_scores)
    selected_labels = st.multiselect("What I think", verdict_options)
    risk_options = option_values(display_scores, "risk_posture")
    selected_risks = st.multiselect("Risk posture", risk_options)
    long_term_options = option_values(display_scores, "long_term_investment_label")
    selected_long_terms = st.multiselect("Long-term label", long_term_options)
    data_options = option_values(display_scores, "data_confidence_label")
    selected_data_labels = st.multiselect("Data confidence", data_options)
    query_text = st.text_input("Search ticker/company")

def build_visible_scores(active_research_lens: str, active_sort_by: str) -> pd.DataFrame:
    """Apply the current board controls and sidebar filters."""
    visible = display_scores.copy()
    if visible.empty:
        return visible
    visible = apply_lens(visible, active_research_lens or "Overall Big Board")
    if hide_garbage_check and "what_i_think" in visible.columns:
        visible = visible[~visible["what_i_think"].astype(str).isin(["This is Garbage", "Needs More Clues"])]
    if require_good_data_check:
        visible = visible[numeric_series(visible, "data_confidence_score") >= 75]
    if event_flags_check:
        visible = visible[
            (numeric_series(visible, "event_shock_penalty") >= 10)
            | visible.get("event_callouts", pd.Series("", index=visible.index)).astype(str).str.contains(
                "liquidation|bankruptcy|thesis|resignation|delisting|offering|warrant|going concern",
                case=False,
                na=False,
            )
        ]
    if low_flow_sleepers_check:
        visible = visible[
            (numeric_series(visible, "hume_flow_potential_score") <= 45)
            & (
                (numeric_series(visible, "austrian_mispricing_score") >= 45)
                | (numeric_series(visible, "keynes_repricing_potential_score") >= 45)
                | (numeric_series(visible, "pre_flow_opportunity_score") >= 45)
            )
        ]
    if high_dilution_check:
        visible = visible[numeric_series(visible, "dilution_pressure_score") >= 70]
    visible = visible[numeric_series(visible, "movement_score") >= min_move]
    visible = visible[numeric_series(visible, "long_term_investment_score") >= min_long_term]
    visible = visible[numeric_series(visible, "data_confidence_score") >= min_data]
    visible = visible[numeric_series(visible, "pre_flow_opportunity_score") >= min_pre_flow]
    visible = visible[numeric_series(visible, "dilution_pressure_score") <= max_dilution]
    visible = visible[numeric_series(visible, "survival_risk_score") <= max_survival]
    visible = visible[numeric_series(visible, "zombie_decay_penalty") <= max_zombie]
    visible = visible[numeric_series(visible, "event_shock_penalty") <= max_event]
    if selected_sectors:
        visible = visible[visible["sector"].astype(str).isin(selected_sectors)]
    if selected_labels:
        visible = filter_by_what_i_think(visible, selected_labels)
    if selected_risks:
        visible = visible[visible["risk_posture"].astype(str).isin(selected_risks)]
    if selected_long_terms:
        visible = visible[visible["long_term_investment_label"].astype(str).isin(selected_long_terms)]
    if selected_data_labels:
        visible = visible[visible["data_confidence_label"].astype(str).isin(selected_data_labels)]
    if query_text:
        query = query_text.strip().lower()
        haystack = (
            visible.get("ticker", pd.Series("", index=visible.index)).astype(str)
            + " "
            + visible.get("company_name", pd.Series("", index=visible.index)).astype(str)
        ).str.lower()
        visible = visible[haystack.str.contains(query, na=False)]
    if active_sort_by in visible.columns:
        visible = visible.sort_values(active_sort_by, ascending=(sort_direction == "Low to high"), na_position="last")
    return visible.head(top_n)


filtered = build_visible_scores(research_lens, sort_by)

watchlist_tab, ticker_tab, data_tab, appendix_tab = st.tabs(
    ["Big Board", "Scout Card", "Data Room", "Math Appendix"]
)

with watchlist_tab:
    if display_scores.empty:
        st.info("No theory scores found yet. Run the refresh launcher to build the watchlist.")
    else:
        refreshed_at, refreshed_age = refresh_label(source_status)
        quick_tickers = sorted(display_scores["ticker"].dropna().astype(str).str.upper().unique().tolist())
        quick_scout_col, quick_open_col = st.columns([3.4, .8], vertical_alignment="bottom")
        with quick_scout_col:
            quick_selected = st.selectbox(
                "Quick scout",
                quick_tickers,
                key="big_board_quick_scout",
            )
        with quick_open_col:
            if st.button("Open", key="big_board_quick_scout_open", use_container_width=True):
                quick_rows = theory_scores[theory_scores["ticker"].astype(str).str.upper() == quick_selected]
                if quick_rows.empty:
                    st.warning(f"No scout card found for {quick_selected}.")
                else:
                    front_office_scout_dialog(quick_rows.iloc[0].to_dict())

        st.subheader("Front Office Board")
        with st.container():
            lens_col, verdict_col = st.columns(
                [1.1, 1.1],
                vertical_alignment="bottom",
            )
            with lens_col:
                research_lens = st.selectbox(
                    "Scouting lens",
                    LENS_OPTIONS,
                    index=LENS_OPTIONS.index(research_lens) if research_lens in LENS_OPTIONS else 0,
                    key="big_board_lens",
                )
            active_sort_by = lens_sort_column(research_lens) if sort_label.startswith("Lens default") else sort_by
            filtered = build_visible_scores(research_lens, active_sort_by)
            verdict_filter_options = ["All"] + what_i_think_options(filtered)
            with verdict_col:
                board_verdict_filter = st.selectbox(
                    "What I think",
                    verdict_filter_options,
                    key="big_board_verdict_filter",
                )
            if board_verdict_filter != "All":
                filtered = filter_by_what_i_think(filtered, board_verdict_filter)

        card_frame = filtered.head(6)
        if not card_frame.empty:
            card_cols = st.columns(3)
            for card_index, (_, card_row) in enumerate(card_frame.iterrows(), start=1):
                with card_cols[(card_index - 1) % 3]:
                    ticker_card(card_row, card_index)

        st.subheader("Stats Table")
        st.caption("Cleaner by default. Turn on Advanced columns in Filters & Lenses when you want the full model guts.")
        core_columns = [
            "ticker",
            "company_name",
            "movement_grade",
            "raw_movement_score",
            "movement_score",
            "scooby_score",
            "what_i_think",
            "secondary_what_i_think",
            "risk_posture",
            "price",
            "market_cap",
            "sector",
            "setup_type",
            "flow_state",
            "pre_flow_opportunity_score",
            "austrian_mispricing_score",
            "hume_flow_potential_score",
            "keynes_repricing_potential_score",
            "relative_mispricing_score",
            "asymmetry_score",
            "long_term_investment_score",
            "data_confidence_score",
            "dilution_pressure_score",
            "survival_risk_score",
            "event_shock_penalty",
            "viability_window",
            "event_callouts",
            "ranking_note",
        ]
        advanced_columns = [
            "long_term_investment_label",
            "label_basis",
            "echo_penalty_total",
            "sec_risk_penalty",
            "event_shock_penalty",
            "zombie_decay_penalty",
            "zombie_decay_label",
            "dcf_plausibility_score",
            "expectation_gap_score",
            "long_term_investment_note",
            "time_to_viability_score",
            "catalyst_probability_score",
            "volume_to_float",
            "breakout_proximity_score",
            "compression_5d_score",
            "recent_dynamism_score",
            "public_age_years_proxy",
            "factor_stack_note",
        ]
        table_columns = core_columns + advanced_columns if advanced_mode else core_columns
        st.caption("Ticker stays frozen while the rest of the board scrolls.")
        render_big_board(filtered, table_columns)

        with st.expander("Classic Streamlit table backup"):
            st.dataframe(
                filtered[available_columns(filtered, table_columns)],
                use_container_width=True,
                hide_index=True,
                height=520,
            )

        st.subheader("Research Batch & Refresh Info")
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            metric_panel("Research Batch", len(display_scores), "Top candidates currently scored")
        with col2:
            metric_panel("Shown Now", len(filtered), f"Full Batch / {clean_text(research_lens, 'Overall')}")
        with col3:
            scooby_count = int((display_scores.get("what_i_think", pd.Series(dtype=str)) == "SCOOBY DOOBY DOO!!").sum())
            metric_panel("Scooby Count", scooby_count, "Rare by design")
        with col4:
            scrappy_count = int((display_scores.get("what_i_think", pd.Series(dtype=str)) == "Scrappy Doo").sum())
            metric_panel("Scrappy Count", scrappy_count, "Fledgling with potential")
        with col5:
            garbage_count = int((display_scores.get("what_i_think", pd.Series(dtype=str)) == "This is Garbage").sum())
            clue_count = int((display_scores.get("what_i_think", pd.Series(dtype=str)) == "Needs More Clues").sum())
            metric_panel("Garbage / Clues", f"{garbage_count} / {clue_count}", "Bad math separated from thin evidence")
        with col6:
            if not price_history.empty and "price_history_status" in price_history.columns:
                coverage = (price_history["price_history_status"].astype(str) == "ok").mean() * 100
                metric_panel("History Coverage", f"{coverage:.0f}%", "Drives Hume and zombie math")
            else:
                metric_panel("History Coverage", "n/a", "No price-history file")

        health, health_note = health_label(source_status)
        h1, h2, h3, h4 = st.columns([1, 1, 1.4, 1.2])
        with h1:
            metric_panel("Data Health", health, health_note)
        with h2:
            fallback_count = 0
            if not source_status.empty and "fallback_used" in source_status.columns:
                fallback_count = int(source_status["fallback_used"].astype(str).str.lower().isin(["true", "1"]).sum())
            metric_panel("Fallback Uses", fallback_count, "Cache or backup source used")
        with h3:
            latest_detail = "No source-health detail recorded."
            if not source_status.empty:
                latest = source_status.tail(1).iloc[0]
                latest_detail = f"{latest.get('stage', '')} / {latest.get('provider', '')}: {latest.get('status', '')}"
            metric_panel("Latest Source Note", clean_text(latest_detail), "Most recent refresh event")
        with h4:
            metric_panel("Last Refreshed", refreshed_at, refreshed_age)

        with st.expander("Refresh The Hosted App"):
            st.write("Use GitHub Actions to refresh the data behind the hosted Streamlit app.")
            st.link_button("Open Refresh Workflow", GITHUB_ACTIONS_URL)
            st.caption("On GitHub, choose Run workflow. When it finishes, Streamlit will use the refreshed files from the repo.")

        if "what_i_think" in display_scores.columns:
            st.subheader("Label Dispersion")
            label_counts = display_scores["what_i_think"].value_counts(dropna=False).rename_axis("label").reset_index(name="primary_count")
            if "secondary_what_i_think" in display_scores.columns:
                secondary_counts = (
                    display_scores["secondary_what_i_think"]
                    .replace("", pd.NA)
                    .dropna()
                    .value_counts()
                    .rename_axis("label")
                    .reset_index(name="secondary_count")
                )
                label_counts = label_counts.merge(secondary_counts, on="label", how="outer")
            else:
                label_counts["secondary_count"] = 0
            label_counts["primary_count"] = pd.to_numeric(label_counts["primary_count"], errors="coerce").fillna(0).astype(int)
            label_counts["secondary_count"] = pd.to_numeric(label_counts["secondary_count"], errors="coerce").fillna(0).astype(int)
            total_labels = max(1, len(display_scores))
            label_counts["primary_pct"] = (label_counts["primary_count"] / total_labels * 100).round(1)
            label_counts["combined_count"] = label_counts["primary_count"] + label_counts["secondary_count"]
            label_counts = label_counts.sort_values(["combined_count", "primary_count"], ascending=False)
            st.dataframe(
                label_counts[["label", "primary_count", "secondary_count", "combined_count", "primary_pct"]],
                use_container_width=True,
                hide_index=True,
                height=320,
            )

with ticker_tab:
    ticker_source = display_scores
    if ticker_source.empty:
        st.info("No scored tickers available yet.")
    else:
        tickers = sorted(ticker_source["ticker"].dropna().astype(str).str.upper().unique().tolist())
        st.subheader("Scout Card")
        st.caption("Start typing in the box, then pick the ticker from the same control.")
        selected = st.selectbox("Choose or enter ticker", tickers, key="scout_ticker_picker")
        score_row = theory_scores[theory_scores["ticker"].astype(str).str.upper() == selected].iloc[0]

        render_scout_console(score_row)

        top_line = st.columns(5)
        with top_line[0]:
            metric_panel("Movement Grade", clean_text(score_row.get("movement_grade"), "n/a"), f"{safe_number(score_row.get('movement_score')):.1f} score")
        with top_line[1]:
            metric_panel("Long-Term", f"{safe_number(score_row.get('long_term_investment_score')):.1f}", clean_text(score_row.get("long_term_investment_label"), "n/a"))
        with top_line[2]:
            metric_panel("Risk Read", clean_text(score_row.get("risk_posture"), "n/a"), clean_text(score_row.get("event_callouts"), "No major event callout"))
        with top_line[3]:
            metric_panel("Setup", clean_text(score_row.get("setup_type"), "n/a"), clean_text(score_row.get("viability_window"), "Unknown viability"))
        with top_line[4]:
            metric_panel("Data", f"{safe_number(score_row.get('data_confidence_score')):.1f}", clean_text(score_row.get("data_confidence_label"), "confidence"))

        st.write(clean_text(score_row.get("final_rank_interpretation"), "No rank interpretation."))

        score_cols = st.columns(5)
        score_specs = [
            ("Austrian", "austrian_mispricing_score", "pricing gap / damage"),
            ("Hume", "hume_flow_potential_score", "money and volume flow"),
            ("Keynes", "keynes_repricing_potential_score", "story and belief"),
            ("Relative", "relative_mispricing_score", "cheap versus context"),
            ("Asymmetry", "asymmetry_score", "upside shape"),
        ]
        for column, (label, key, note) in zip(score_cols, score_specs):
            with column:
                score_panel(label, score_row.get(key), note)

        lt1, lt2, lt3 = st.columns([1, 1, 2])
        with lt1:
            score_panel("Long-Term", score_row.get("long_term_investment_score"), "business quality lens")
        with lt2:
            score_panel("DCF Belief", score_row.get("dcf_plausibility_score"), "0-3 plausibility scale")
        with lt3:
            st.info(clean_text(score_row.get("long_term_investment_note"), "No long-term note available."))

        st.subheader("Why It Ranked This Way")
        if clean_text(score_row.get("ranking_note")):
            st.info(clean_text(score_row.get("ranking_note")))
        if clean_text(score_row.get("raw_setup_note")):
            st.write(clean_text(score_row.get("raw_setup_note")))
        if clean_text(score_row.get("thesis_integrity_note")):
            st.warning(clean_text(score_row.get("thesis_integrity_note")))
        if clean_text(score_row.get("flow_confirmation_note")):
            st.info(clean_text(score_row.get("flow_confirmation_note")))
        if clean_text(score_row.get("zombie_decay_note")):
            st.info(clean_text(score_row.get("zombie_decay_note")))
        if clean_text(score_row.get("dcf_plausibility_note")):
            st.info(clean_text(score_row.get("dcf_plausibility_note")))

        with st.expander("Factor Stack"):
            factor_columns = [
                "pricing_gap_factor",
                "flow_factor",
                "story_attention_factor",
                "relative_value_factor",
                "convexity_factor",
                "trading_setup_factor",
                "animal_spirits_factor",
                "portfolio_viability_factor",
                "accounting_quality_factor",
                "catalyst_probability_score",
                "sec_risk_penalty",
                "event_shock_penalty",
                "zombie_decay_penalty",
                "echo_penalty_total",
                "dcf_plausibility_score",
                "long_term_investment_score",
                "expectation_gap_score",
            ]
            factor_frame = pd.DataFrame(
                [
                    {"factor": column.replace("_", " "), "value": score_row.get(column)}
                    for column in factor_columns
                    if column in score_row
                ]
            )
            st.dataframe(factor_frame, use_container_width=True, hide_index=True)
            st.write(clean_text(score_row.get("factor_stack_note"), "No factor stack note."))

        with st.expander("Ricardo / Malthus / Technology Details"):
            st.write(clean_text(score_row.get("subsignal_tags"), "No sub-signal tags available."))
            st.write(clean_text(score_row.get("relative_explanation"), "No relative explanation."))
            st.write(clean_text(score_row.get("asymmetry_explanation"), "No asymmetry explanation."))

with data_tab:
    st.subheader("Top 250 Research Batch")
    if research_batch.empty:
        st.info("No research batch file found.")
    else:
        st.dataframe(research_batch, use_container_width=True, hide_index=True)

    st.subheader("Price History Feature Status")
    if price_history.empty:
        st.info("No price-history feature file found.")
    else:
        st.dataframe(price_history, use_container_width=True, hide_index=True)

    st.subheader("Data Source Health")
    if source_status.empty:
        st.info("No source-health file found yet. Run the data refresh launcher to record provider status.")
    else:
        st.dataframe(source_status, use_container_width=True, hide_index=True)

    with st.expander("Broad Candidate Universe"):
        st.dataframe(universe, use_container_width=True, hide_index=True)

    for label, path in [
        ("SEC Activity Flags", SEC_FLAGS_PATH),
        ("SEC Filing Signals", SEC_SIGNALS_PATH),
        ("Event Shock Scan", EVENT_SHOCKS_PATH),
        ("Accounting Fundamentals", FUNDAMENTALS_PATH),
    ]:
        frame = load_csv(str(path))
        with st.expander(label):
            if frame.empty:
                st.info(f"No {label.lower()} file found.")
            else:
                st.dataframe(frame, use_container_width=True, hide_index=True)

with appendix_tab:
    if MATH_APPENDIX_PATH.exists():
        st.markdown(MATH_APPENDIX_PATH.read_text(encoding="utf-8"))
    else:
        st.warning("Math appendix file is missing.")
