"""Streamlit dashboard for Contrarian 10-Bagger Engine."""

from __future__ import annotations

import html
import os
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


st.set_page_config(page_title="Contrarian 10-Bagger Engine", layout="wide")


GITHUB_ACTIONS_URL = "https://github.com/Kastnermj/mysterymachine/actions/workflows/refresh-data.yml"


def configured_password() -> str:
    """Return the app password from secrets/env, with the user's fallback."""
    try:
        secret_password = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        secret_password = ""
    return str(secret_password or os.environ.get("APP_PASSWORD") or "cheesecake")


def require_password() -> None:
    """Stop the dashboard until the user enters the app password."""
    if st.session_state.get("authenticated"):
        return
    st.title("Mystery Machine")
    st.caption("Private research dashboard")
    password = st.text_input("Password", type="password")
    if password:
        if password == configured_password():
            st.session_state["authenticated"] = True
            st.rerun()
        st.error("Wrong password.")
    st.stop()


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
    st.markdown(
        f"""
        <div class="draft-card">
            <div class="draft-topline">
                <span class="draft-rank">#{rank}</span>
                <span class="draft-ticker">{ticker}</span>
                <span class="draft-grade">{grade}</span>
            </div>
            <div class="draft-name">{name}</div>
            <div class="draft-scorebar"><div style="width:{max(0, min(100, move)):.0f}%"></div></div>
            <div class="draft-meta">Move {move:.1f} | Hume {safe_number(row.get("hume_flow_potential_score")):.0f} | Keynes {safe_number(row.get("keynes_repricing_potential_score")):.0f}</div>
            <div class="draft-badge">{verdict_badge(row.get("what_i_think"))}</div>
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


BOARD_LABELS = {
    "ticker": "Ticker",
    "company_name": "Company",
    "movement_grade": "Grade",
    "movement_score": "Move",
    "what_i_think": "What I Think",
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
    "movement_score",
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

    table_width = max(1900, 520 + len(board.columns) * 112)
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
            height: 18px;
            margin-bottom: 6px;
            border: 1px solid #ccd6e6;
            border-radius: 8px;
            background: #f8fbff;
        }}
        .top-scroll-inner {{
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
            font-size: 13px;
            color: #172033;
        }}
        .big-board-table th {{
            position: sticky;
            top: 0;
            z-index: 5;
            background: #111827;
            color: #f8fafc;
            text-align: left;
            padding: 10px 11px;
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
            padding: 9px 11px;
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
            width: 86px;
            min-width: 86px;
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
            max-width: 260px;
            min-width: 180px;
        }}
        .mini-score {{
            min-width: 92px;
        }}
        .mini-score span {{
            display: inline-block;
            min-width: 43px;
            font-weight: 800;
            color: #172033;
        }}
        .mini-bar {{
            display: inline-block;
            width: 45px;
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
        <div class="top-scroll" id="topScroll"><div class="top-scroll-inner" id="topScrollInner"></div></div>
        <div class="board-wrap" id="boardScroll">
            <table class="big-board-table">
                <thead><tr>{''.join(headers)}</tr></thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </div>
        <div class="cell-detail" id="cellDetail">
            <div class="cell-detail-title" id="cellDetailTitle"></div>
            <div id="cellDetailText"></div>
        </div>
        <script>
        const topScroll = document.getElementById("topScroll");
        const topScrollInner = document.getElementById("topScrollInner");
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
        }}
        syncTopScrollbarWidth();
        window.addEventListener("resize", syncTopScrollbarWidth);
        topScroll.addEventListener("scroll", () => {{
            if (syncingTop) return;
            syncingBoard = true;
            boardScroll.scrollLeft = topScroll.scrollLeft;
            syncingBoard = false;
        }});
        boardScroll.addEventListener("scroll", () => {{
            if (syncingBoard) return;
            syncingTop = true;
            topScroll.scrollLeft = boardScroll.scrollLeft;
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


def apply_watchlist_mode(frame: pd.DataFrame, mode: str) -> pd.DataFrame:
    """Apply one high-level research view without deleting the underlying data."""
    if frame.empty:
        return frame
    output = frame.copy()
    verdict = output.get("what_i_think", pd.Series("", index=output.index)).astype(str)
    risk = output.get("risk_posture", pd.Series("", index=output.index)).astype(str)
    long_term_label = output.get("long_term_investment_label", pd.Series("", index=output.index)).astype(str)

    if mode == "Clean Research":
        return output[verdict != "This is Garbage"]
    if mode == "Garbage Lab":
        return output[verdict == "This is Garbage"]
    if mode == "Best Overall":
        return output[
            (verdict != "This is Garbage")
            & ~risk.str.contains("Extreme dilution|Catastrophic|Old thesis broken", case=False, na=False)
            & (numeric_series(output, "data_confidence_score") >= 75)
        ]
    if mode == "Long-Term Hunt":
        return output[
            long_term_label.isin(["Long-Term Microcap Candidate", "Long-Term Watchlist", "Business Looks Real, Risks Bite"])
        ]
    if mode == "Danger Zone":
        return output[
            (verdict == "This is Garbage")
            | risk.str.contains("Extreme dilution|Catastrophic|Survival|Old thesis broken|Dilution", case=False, na=False)
        ]
    return output


def lens_sort_column(lens: str) -> str:
    """Map a front-office lens to the score column it should emphasize."""
    lens_map = {
        "Overall Big Board": "movement_score",
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
    return lens_map.get(lens, "movement_score")


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
        border: 1px solid rgba(255,255,255,0.18);
        background: linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,255,255,0.05));
        color: #f9fafb;
        padding: 1.25rem 1.45rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        box-shadow: 0 18px 60px rgba(5,10,25,0.24);
    }
    .cfe-hero h1 {
        margin: 0 0 .35rem 0;
        font-size: 2.25rem;
        letter-spacing: 0;
    }
    .cfe-hero p {
        margin: 0;
        color: #d7dde8;
        font-size: 1rem;
    }
    .hero-kicker {
        color: #9fb3d9;
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
    .draft-card {
        border: 1px solid #dbe3f0;
        background: linear-gradient(180deg, #ffffff, #f9fbff);
        border-radius: 8px;
        padding: .95rem;
        min-height: 12.5rem;
        box-shadow: 0 10px 28px rgba(20,31,56,0.08);
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
        color: #f8fafc;
        border-radius: 6px;
        padding: .15rem .45rem;
        font-weight: 900;
        font-size: .78rem;
    }
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
    .scout-card {
        border: 1px solid #dbe3f0;
        background: #ffffff;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 10px 28px rgba(20,31,56,0.08);
    }
    .scout-title {
        font-size: 1.65rem;
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
        min-width: 2350px;
        width: max-content;
        font-size: .84rem;
        color: #172033;
    }
    .big-board-table th {
        position: sticky;
        top: 0;
        z-index: 5;
        background: #111827;
        color: #f8fafc;
        text-align: left;
        padding: .62rem .7rem;
        border-bottom: 1px solid #334155;
        white-space: nowrap;
    }
    .big-board-table td {
        padding: .58rem .7rem;
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
        width: 86px;
        min-width: 86px;
        font-weight: 900;
        color: #0f172a;
        box-shadow: 1px 0 0 #d7deea;
    }
    .big-board-table th.sticky-ticker {
        z-index: 8;
        background: #0b1220;
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
    section[data-testid="stSidebar"] {
        background: #f7f9fd;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

require_password()

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

with st.sidebar:
    st.subheader("Front Office")
    view_mode = st.segmented_control(
        "Board preset",
        ["Full Batch", "Clean Research", "Best Overall", "Long-Term Hunt", "Garbage Lab", "Danger Zone"],
        default="Full Batch",
        help="Full Batch keeps the garbage rows in view. Clean Research only hides them temporarily.",
    )
    research_lens = st.selectbox(
        "Scouting lens",
        [
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
        ],
        index=0,
        help="Tilt the board toward one part of your model without changing the underlying scores.",
    )
    sort_options = {
        f"Lens default ({BOARD_LABELS.get(lens_sort_column(research_lens), lens_sort_column(research_lens))})": lens_sort_column(research_lens),
        "Movement score": "movement_score",
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
    top_n = st.slider("Rows to show", 10, 500, 100, 10)
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
    verdict_options = option_values(display_scores, "what_i_think")
    selected_labels = st.multiselect("What I think", verdict_options)
    risk_options = option_values(display_scores, "risk_posture")
    selected_risks = st.multiselect("Risk posture", risk_options)
    long_term_options = option_values(display_scores, "long_term_investment_label")
    selected_long_terms = st.multiselect("Long-term label", long_term_options)
    data_options = option_values(display_scores, "data_confidence_label")
    selected_data_labels = st.multiselect("Data confidence", data_options)
    query_text = st.text_input("Search ticker/company")

filtered = display_scores.copy()
if not filtered.empty:
    filtered = apply_watchlist_mode(filtered, view_mode or "Full Batch")
    filtered = apply_lens(filtered, research_lens or "Overall Big Board")
    if hide_garbage_check and "what_i_think" in filtered.columns:
        filtered = filtered[filtered["what_i_think"].astype(str) != "This is Garbage"]
    if require_good_data_check:
        filtered = filtered[numeric_series(filtered, "data_confidence_score") >= 75]
    if event_flags_check:
        filtered = filtered[
            (numeric_series(filtered, "event_shock_penalty") >= 10)
            | filtered.get("event_callouts", pd.Series("", index=filtered.index)).astype(str).str.contains(
                "liquidation|bankruptcy|thesis|resignation|delisting|offering|warrant|going concern",
                case=False,
                na=False,
            )
        ]
    if low_flow_sleepers_check:
        filtered = filtered[
            (numeric_series(filtered, "hume_flow_potential_score") <= 45)
            & (
                (numeric_series(filtered, "austrian_mispricing_score") >= 45)
                | (numeric_series(filtered, "keynes_repricing_potential_score") >= 45)
                | (numeric_series(filtered, "pre_flow_opportunity_score") >= 45)
            )
        ]
    if high_dilution_check:
        filtered = filtered[numeric_series(filtered, "dilution_pressure_score") >= 70]
    filtered = filtered[numeric_series(filtered, "movement_score") >= min_move]
    filtered = filtered[numeric_series(filtered, "long_term_investment_score") >= min_long_term]
    filtered = filtered[numeric_series(filtered, "data_confidence_score") >= min_data]
    filtered = filtered[numeric_series(filtered, "pre_flow_opportunity_score") >= min_pre_flow]
    filtered = filtered[numeric_series(filtered, "dilution_pressure_score") <= max_dilution]
    filtered = filtered[numeric_series(filtered, "survival_risk_score") <= max_survival]
    filtered = filtered[numeric_series(filtered, "zombie_decay_penalty") <= max_zombie]
    filtered = filtered[numeric_series(filtered, "event_shock_penalty") <= max_event]
    if selected_sectors:
        filtered = filtered[filtered["sector"].astype(str).isin(selected_sectors)]
    if selected_labels:
        filtered = filtered[filtered["what_i_think"].astype(str).isin(selected_labels)]
    if selected_risks:
        filtered = filtered[filtered["risk_posture"].astype(str).isin(selected_risks)]
    if selected_long_terms:
        filtered = filtered[filtered["long_term_investment_label"].astype(str).isin(selected_long_terms)]
    if selected_data_labels:
        filtered = filtered[filtered["data_confidence_label"].astype(str).isin(selected_data_labels)]
    if query_text:
        query = query_text.strip().lower()
        haystack = (
            filtered.get("ticker", pd.Series("", index=filtered.index)).astype(str)
            + " "
            + filtered.get("company_name", pd.Series("", index=filtered.index)).astype(str)
        ).str.lower()
        filtered = filtered[haystack.str.contains(query, na=False)]
    if sort_by in filtered.columns:
        filtered = filtered.sort_values(sort_by, ascending=(sort_direction == "Low to high"), na_position="last")
    filtered = filtered.head(top_n)

watchlist_tab, mobile_tab, ticker_tab, data_tab, appendix_tab = st.tabs(
    ["Big Board", "Mobile Lite", "Scout Card", "Data Room", "Math Playbook"]
)

with watchlist_tab:
    if display_scores.empty:
        st.info("No theory scores found yet. Run the refresh launcher to build the watchlist.")
    else:
        refreshed_at, refreshed_age = refresh_label(source_status)
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            metric_panel("Research Batch", len(display_scores), "Top candidates currently scored")
        with col2:
            metric_panel("Shown Now", len(filtered), f"{clean_text(view_mode, 'Full Batch')} / {clean_text(research_lens, 'Overall')}")
        with col3:
            scooby_count = int((display_scores.get("what_i_think", pd.Series(dtype=str)) == "SCOOBY DOOBY DOO!!").sum())
            metric_panel("Scooby Count", scooby_count, "Rare by design")
        with col4:
            scrappy_count = int((display_scores.get("what_i_think", pd.Series(dtype=str)) == "Scrappy Doo").sum())
            metric_panel("Scrappy Count", scrappy_count, "Fledgling with potential")
        with col5:
            garbage_count = int((display_scores.get("what_i_think", pd.Series(dtype=str)) == "This is Garbage").sum())
            metric_panel("Garbage Lab", garbage_count, "Kept for learning and filtering")
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

        st.markdown(
            f"""
            <div class="toolbar-note">
                <strong>{clean_text(research_lens, 'Overall Big Board')} lens:</strong>
                the cards below are the current front-office board after your filters. Use the full table when you want the stats-room version.
            </div>
            """,
            unsafe_allow_html=True,
        )
        card_frame = filtered.head(6)
        if not card_frame.empty:
            st.subheader("Front Office Board")
            card_cols = st.columns(3)
            for card_index, (_, card_row) in enumerate(card_frame.iterrows(), start=1):
                with card_cols[(card_index - 1) % 3]:
                    ticker_card(card_row, card_index)

        st.subheader("Stats Table")
        st.caption("Cleaner by default. Turn on Advanced columns in the sidebar when you want the full model guts.")
        core_columns = [
            "ticker",
            "company_name",
            "movement_grade",
            "movement_score",
            "what_i_think",
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
            "raw_movement_score",
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

        if "what_i_think" in display_scores.columns:
            st.subheader("Personality Label Mix")
            label_counts = display_scores["what_i_think"].value_counts().rename_axis("label").reset_index(name="count")
            st.bar_chart(label_counts.set_index("label"))

with mobile_tab:
    st.subheader("Mobile Lite")
    st.caption("A card-first view for phones and narrow screens. Same data, less table wrestling.")
    mobile_source = filtered if not filtered.empty else display_scores
    if mobile_source.empty:
        st.info("No scored tickers available yet.")
    else:
        mobile_limit = st.slider("Cards to show", 5, 100, min(25, len(mobile_source)), 5, key="mobile_limit")
        for rank, (_, row) in enumerate(mobile_source.head(mobile_limit).iterrows(), start=1):
            ticker = clean_text(row.get("ticker"), "???")
            company = clean_text(row.get("company_name"), "Unknown company")
            with st.container(border=True):
                top_left, top_right = st.columns([2, 1])
                with top_left:
                    st.markdown(f"### #{rank} {ticker}")
                    st.caption(company)
                    st.markdown(verdict_badge(row.get("what_i_think")), unsafe_allow_html=True)
                with top_right:
                    st.metric(clean_text(row.get("movement_grade"), "n/a"), f"{safe_number(row.get('movement_score')):.1f}")
                    st.caption(f"Price {money(row.get('price'))}")

                score_cols = st.columns(4)
                with score_cols[0]:
                    st.metric("Hume", f"{safe_number(row.get('hume_flow_potential_score')):.1f}")
                with score_cols[1]:
                    st.metric("Keynes", f"{safe_number(row.get('keynes_repricing_potential_score')):.1f}")
                with score_cols[2]:
                    st.metric("Austrian", f"{safe_number(row.get('austrian_mispricing_score')):.1f}")
                with score_cols[3]:
                    st.metric("Data", f"{safe_number(row.get('data_confidence_score')):.1f}")

                st.write(clean_text(row.get("ranking_note"), "No ranking note."))
                with st.expander("More details"):
                    st.write(f"**Risk:** {clean_text(row.get('risk_posture'), 'n/a')}")
                    st.write(f"**Flow:** {clean_text(row.get('flow_state'), 'n/a')}")
                    st.write(f"**Setup:** {clean_text(row.get('setup_type'), 'n/a')}")
                    st.write(f"**Event:** {clean_text(row.get('event_callouts'), 'No major event callout')}")
                    st.write(f"**Long-term:** {clean_text(row.get('long_term_investment_label'), 'n/a')} ({safe_number(row.get('long_term_investment_score')):.1f})")
                    st.write(clean_text(row.get("final_rank_interpretation"), "No final rank interpretation."))

with ticker_tab:
    ticker_source = filtered if not filtered.empty else display_scores
    if ticker_source.empty:
        st.info("No scored tickers available yet.")
    else:
        tickers = ticker_source["ticker"].astype(str).tolist()
        selected = st.selectbox("Ticker lens", tickers)
        score_row = theory_scores[theory_scores["ticker"].astype(str) == selected].iloc[0]

        st.markdown(
            f"""
            <div class="scout-card">
                <div class="scout-title">{selected} - {clean_text(score_row.get('company_name'), 'Unknown company')}</div>
                <div class="scout-subtitle">
                    {clean_text(score_row.get('sector'), 'Unknown sector')} | Price {money(score_row.get('price'))} | Market cap {money(score_row.get('market_cap'))}
                </div>
                <div>{verdict_badge(score_row.get('what_i_think'))}</div>
                <p>{scout_note(score_row)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
    st.subheader("Top 100 Research Batch")
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
