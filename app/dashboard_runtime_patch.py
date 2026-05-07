"""Hosted runtime patch for Mystery Machine.

This keeps Streamlit Cloud on the latest dashboard behavior even when the
checked-in dashboard source lags behind the local working copy.
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
section[data-testid="stSidebar"] [data-baseweb="slider"],
input,
textarea,
[data-baseweb="select"] > div {
    background: #ffffff !important;
    color: #0f172a !important;
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
.cfe-hero {
    background: linear-gradient(135deg, #0f172a, #1e293b) !important;
    border: 1px solid #334155 !important;
    color: #f8fafc !important;
}
.cfe-hero,
.cfe-hero * {
    color: #f8fafc !important;
    text-shadow: none !important;
}
.draft-grade,
.draft-grade * {
    color: #ffffff !important;
}
.draft-grade {
    min-width: 2.35rem !important;
    min-height: 1.45rem !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    line-height: 1 !important;
    white-space: nowrap !important;
}
.native-grade {
    margin-left: 0 !important;
    width: 100% !important;
}
.draft-native-head,
.draft-native-head * {
    color: #111827 !important;
    line-height: 1.2 !important;
    white-space: nowrap !important;
    text-shadow: none !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff !important;
    border: 2px solid #c7d4e8 !important;
    border-radius: 8px !important;
    box-shadow: 0 12px 28px rgba(15, 23, 42, .10) !important;
    padding: .78rem .9rem .9rem .9rem !important;
}
.draft-card-content {
    margin-top: .35rem !important;
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
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"],
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] * {
    color: #ffffff !important;
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
</style>
"""


SCOUT_FUNCTIONS = r'''
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
        ("Data", clamp_score(row.get("data_confidence_score")), "Evidence"),
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
        power_bar("Move", row.get("movement_score"), grade),
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

    return f"""
    <div class="scout-console">
        <div class="scout-console-hero">
            <div>
                <div class="scout-kicker">Mystery Machine Scout Console</div>
                <div class="scout-console-title">{html.escape(ticker)} <span>{html.escape(company)}</span></div>
                <div class="scout-console-subtitle">{html.escape(sector)} | Price {money(row.get('price'))} | Market cap {money(row.get('market_cap'))}</div>
                <div class="scout-console-badges">{verdict_badge(row.get('what_i_think'))}</div>
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


def compact_scout_card(row: pd.Series) -> None:
    """Render a condensed ticker scout view for front-office popovers."""
    render_scout_console(row, compact=True)


@st.dialog("Front Office Scout Card", width="large")
def front_office_scout_dialog(row_data: dict[str, Any]) -> None:
    """Show a compact scout-card popout from a front-office tile."""
    row = pd.Series(row_data)
    compact_scout_card(row)
    st.caption("Use the Scout Card tab when you want the full 250-name research board and factor stack.")


'''


def replace_between(source: str, start_marker: str, end_marker: str, replacement: str) -> str:
    """Replace text between two markers when both exist."""
    start = source.find(start_marker)
    if start == -1:
        return source
    end = source.find(end_marker, start)
    if end == -1:
        return source
    return source[:start] + replacement + source[end:]


def patched_dashboard_source() -> str:
    """Return dashboard source with hosted UI and Scout-console changes."""
    source = SOURCE_PATH.read_text(encoding="utf-8")

    source = source.replace("import html\n", "import html\nimport math\n", 1)
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

    source = replace_between(
        source,
        "\ndef ticker_card(row: pd.Series, rank: int) -> None:",
        "\nBOARD_LABELS = {",
        "\n" + SCOUT_FUNCTIONS + "BOARD_LABELS = {",
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
    source = source.replace("sidebar when you want the full model guts", "Filters & Lenses when you want the full model guts")

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

    ticker_start = source.find("\nwith ticker_tab:\n")
    data_start = source.find("\nwith data_tab:\n", ticker_start)
    if ticker_start != -1 and data_start != -1:
        source = (
            source[:ticker_start]
            + '''
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
'''
            + source[data_start:]
        )

    return source


code = compile(patched_dashboard_source(), str(SOURCE_PATH), "exec")
exec(code, globals())
