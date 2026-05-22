"""
ui_theme.py — Centralized UI Theme & Shared Helpers
====================================================
ทุกหน้า Streamlit import จากไฟล์นี้:
    from ui_theme import inject_global_css, render_page_header, ...
"""

import streamlit as st

# ═════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═════════════════════════════════════════════════════════════════════════

ACTIVE_RULES = [
    "DOUBLE DRIBBLE",
    "TRAVELING",
    "CARRYING",
    "GOALTENDING",
    "HELD BALL",
]

DEPRECATED_RULES = [
    "PUSH FOUL",
    "ILLEGAL HANDS",
]

ACTIVE_RULES_SET = set(ACTIVE_RULES)
DEPRECATED_RULES_SET = set(DEPRECATED_RULES)

REVIEW_COLUMNS = [
    "Event_ID",
    "Replay_Path",
    "Predicted_Rule",
    "Review_Status",
    "Human_Label",
    "Reviewer_Note",
    "Reviewed_At",
]

REVIEW_STATUSES = ["Unreviewed", "Correct", "False Positive", "Wrong Rule", "Unclear"]
HUMAN_LABEL_OPTIONS = ["NO FOUL", *ACTIVE_RULES, "UNCLEAR"]


# ═════════════════════════════════════════════════════════════════════════
#  SHARED HELPER FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════

def normalize_foul(foul_str: str) -> str:
    """Normalize raw foul type string to a standard short label."""
    f = str(foul_str).upper()
    if "PUSH"        in f: return "PUSH FOUL"
    if "ILLEGAL"     in f: return "ILLEGAL HANDS"
    if "DOUBLE"      in f: return "DOUBLE DRIBBLE"
    if "TRAVELING"   in f: return "TRAVELING"
    if "CARRY"       in f: return "CARRYING"
    if "GOALTENDING" in f or "GOAL" in f: return "GOALTENDING"
    if "HELD" in f or "JUMP" in f: return "HELD BALL"
    return str(foul_str)[:30]


# Alias for backward compatibility
foul_short_name = normalize_foul


def rule_status(foul_label: str) -> str:
    """Return 'Active', 'Deprecated', or 'Unknown' for a given foul label."""
    if foul_label in DEPRECATED_RULES_SET:
        return "Deprecated"
    if foul_label in ACTIVE_RULES_SET:
        return "Active"
    return "Unknown"


def get_foul_color(foul_type: str) -> str:
    """Return a color hex string for each foul type."""
    f = foul_type.upper()
    if "PUSH"        in f: return "#F97316"
    if "ILLEGAL"     in f: return "#EF4444"
    if "DOUBLE"      in f: return "#F59E0B"
    if "TRAVELING"   in f: return "#8B5CF6"
    if "CARRY"       in f: return "#06B6D4"
    if "GOALTENDING" in f: return "#EC4899"
    if "HELD" in f or "JUMP" in f: return "#10B981"
    return "#F97316"


def pct(value) -> str:
    """Format a 0‑1 float as percentage string."""
    try:
        return f"{float(value) * 100:.0f}%"
    except Exception:
        return "—"


def bool_status(value) -> str:
    if value is None:
        return "—"
    return "YES" if bool(value) else "NO"


def pct_value(numerator: int, denominator: int):
    if denominator <= 0:
        return None
    return numerator / denominator * 100


def fmt_pct(value):
    return f"{value:.1f}%" if value is not None else "—"


def status_class(status: str) -> str:
    return str(status).lower().replace(" ", "-")


# ═════════════════════════════════════════════════════════════════════════
#  GLOBAL CSS
# ═════════════════════════════════════════════════════════════════════════

_GLOBAL_CSS = """
<style>
    /* ── Import Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Outfit:wght@400;600;700;800;900&display=swap');

    /* ── Root Design Tokens ── */
    :root {
        --primary:       #F97316;
        --primary-light: #FED7AA;
        --primary-dark:  #EA580C;
        --accent:        #FB923C;
        --accent2:       #FDBA74;

        --bg-page:       #FFFFFF;
        --bg-soft:       #F8FAFC;
        --bg-card:       #FFFFFF;
        --bg-card2:      #FAFAFA;

        --border:        #E8ECF1;
        --border-accent: rgba(249, 115, 22, 0.25);

        --text-main:     #0F172A;
        --text-body:     #334155;
        --text-sub:      #64748B;
        --text-muted:    #94A3B8;

        --success:       #10B981;
        --danger:        #EF4444;
        --warning:       #F59E0B;
        --info:          #3B82F6;

        --shadow-xs:     0 1px 2px rgba(0,0,0,0.04);
        --shadow-sm:     0 1px 4px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
        --shadow-md:     0 4px 20px rgba(0,0,0,0.07), 0 2px 6px rgba(0,0,0,0.04);
        --shadow-lg:     0 12px 40px rgba(0,0,0,0.09), 0 4px 12px rgba(0,0,0,0.05);
        --shadow-orange: 0 8px 32px rgba(249,115,22,0.16);

        --radius-sm:     8px;
        --radius-md:     12px;
        --radius-lg:     16px;
        --radius-xl:     20px;
        --radius-2xl:    24px;
    }

    /* ── Base Typography ── */
    html, body, [class*="css"], .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"],
    [data-testid="stMainBlockContainer"],
    [data-testid="stVerticalBlock"],
    .main, .main > div,
    section.main > div {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: #FFFFFF !important;
        color: var(--text-main) !important;
        font-size: 18px !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    /* Force white on absolute outermost wrappers */
    .stApp > header + div,
    .stApp [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stBottom"],
    [data-testid="stStatusWidget"],
    .stApp > div:first-child,
    .appview-container,
    .stAppViewContainer {
        background-color: #FFFFFF !important;
    }

    /* ── Hide Streamlit Branding (keep sidebar toggle working) ── */
    #MainMenu, footer { visibility: hidden; }
    .stDeployButton { display: none !important; }
    .viewerBadge_container__1QSob { display: none; }
    [data-testid="stToolbar"] { display: none !important; }
    /* Make header bar transparent & minimal — sidebar toggle still works */
    [data-testid="stHeader"] {
        background: transparent !important;
        border: none !important;
        height: 2.5rem !important;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #FFFCF9 50%, #FFF8F3 100%) !important;
        border-right: 1px solid var(--border) !important;
        box-shadow: 2px 0 16px rgba(0,0,0,0.03) !important;
    }
    [data-testid="stSidebar"] * {
        color: var(--text-body) !important;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] strong {
        color: var(--text-main) !important;
    }
    /* ── Sidebar Nav Links (Streamlit default nav + our custom st.page_link nav) ── */
    [data-testid="stSidebarNav"] a,
    [data-testid="stSidebarNav"] a span,
    [data-testid="stSidebarNav"] li,
    [data-testid="stSidebarNavItems"] a,
    [data-testid="stSidebarNavItems"] span,
    section[data-testid="stSidebar"] a,
    section[data-testid="stSidebar"] a span,
    section[data-testid="stSidebar"] a p {
        color: var(--text-body) !important;
        font-weight: 600 !important;
        text-decoration: none !important;
    }
    [data-testid="stSidebarNav"] a:hover,
    [data-testid="stSidebarNavItems"] a:hover,
    section[data-testid="stSidebar"] a:hover {
        background: rgba(249,115,22,0.08) !important;
        color: var(--primary-dark) !important;
        border-radius: var(--radius-sm) !important;
    }
    [data-testid="stSidebarNav"] a[aria-selected="true"],
    [data-testid="stSidebarNavItems"] a[aria-selected="true"] {
        background: rgba(249,115,22,0.12) !important;
        color: var(--primary-dark) !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 700 !important;
    }
    [data-testid="stSidebarNav"] svg,
    [data-testid="stSidebarNavItems"] svg {
        fill: var(--text-sub) !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        font-weight: 500;
        color: var(--text-body) !important;
        padding: 6px 0;
    }

    /* ── Main Container ── */
    .main .block-container {
        padding: 2.2rem 3rem 3.5rem 3rem;
        max-width: 1480px;
    }

    /* ── Markdown text size ── */
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    label {
        font-size: 1.05rem !important;
        line-height: 1.6 !important;
    }

    /* ── Metric / KPI Cards ── */
    [data-testid="stMetric"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
        padding: 1.4rem 1.5rem !important;
        box-shadow: var(--shadow-sm) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease !important;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-3px) !important;
        box-shadow: var(--shadow-md) !important;
        border-color: var(--border-accent) !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--text-sub) !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.04em !important;
    }
    [data-testid="stMetricValue"] {
        color: var(--primary) !important;
        font-size: 2.4rem !important;
        font-weight: 800 !important;
    }
    [data-testid="stMetricDelta"] svg { display: none; }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
        color: white !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        padding: 0.7rem 1.8rem !important;
        transition: all 0.25s ease !important;
        box-shadow: 0 4px 14px rgba(249,115,22,0.3) !important;
        letter-spacing: 0.02em !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(249,115,22,0.4) !important;
        background: linear-gradient(135deg, #FB923C 0%, var(--primary) 100%) !important;
    }
    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* Stop Button (red variant) */
    .stop-btn > button {
        background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%) !important;
        box-shadow: 0 4px 14px rgba(239,68,68,0.3) !important;
    }
    .stop-btn > button:hover {
        box-shadow: 0 8px 24px rgba(239,68,68,0.4) !important;
    }

    /* ── UI Card ── */
    .ui-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.5rem 1.8rem;
        margin-bottom: 1.2rem;
        box-shadow: var(--shadow-sm);
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }
    .ui-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
        border-color: var(--border-accent);
    }

    /* ── Status Badges ── */
    .status-active {
        display: inline-flex; align-items: center; gap: 8px;
        background: #ECFDF5;
        color: var(--success);
        border: 1.5px solid #6EE7B7;
        border-radius: 24px;
        padding: 7px 18px;
        font-weight: 700; font-size: 1rem;
        animation: pulse-green 2s ease-in-out infinite;
    }
    .status-stopped {
        display: inline-flex; align-items: center; gap: 8px;
        background: var(--bg-soft);
        color: var(--text-sub);
        border: 1.5px solid var(--border);
        border-radius: 24px;
        padding: 7px 18px;
        font-weight: 700; font-size: 1rem;
    }
    .dot-green  { width: 10px; height: 10px; border-radius: 50%; background: var(--success); }
    .dot-gray   { width: 10px; height: 10px; border-radius: 50%; background: var(--text-muted); }

    @keyframes pulse-green {
        0%,100% { box-shadow: 0 0 0 0 rgba(16,185,129,0.3); }
        50%     { box-shadow: 0 0 0 8px rgba(16,185,129,0); }
    }

    /* ── Foul Alert Row ── */
    .foul-row {
        display: flex; align-items: center; gap: 14px;
        padding: 14px 20px;
        border-radius: var(--radius-sm);
        margin-bottom: 8px;
        background: #FFFBF7;
        border-left: 4px solid var(--primary);
        font-size: 1.02rem;
        transition: background 0.15s, transform 0.15s;
    }
    .foul-row:hover {
        background: #FFF3E8;
        transform: translateX(3px);
    }
    .foul-time   { color: var(--text-sub); font-size: 0.95rem; min-width: 88px; font-variant-numeric: tabular-nums; }
    .foul-player { color: var(--primary-dark); font-weight: 700; min-width: 85px; }
    .foul-type   { color: var(--text-body); font-weight: 600; }

    /* ── Foul Badge ── */
    .foul-badge {
        display: inline-block;
        background: #FFF7ED;
        color: var(--primary);
        border: 1.5px solid #FED7AA;
        border-radius: 6px;
        padding: 4px 12px;
        font-size: 0.92rem;
        font-weight: 800;
        margin-right: 6px;
        margin-bottom: 5px;
    }

    /* ── Rule Cards ── */
    .rule-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 1.3rem 1.5rem;
        height: 100%;
        box-shadow: var(--shadow-sm);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .rule-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-md);
    }
    .rule-card h4 { color: var(--primary); margin-bottom: 0.4rem; font-size: 1.05rem; }
    .rule-card p  { color: var(--text-sub); font-size: 0.88rem; line-height: 1.6; margin: 0; }

    /* ── Replay Card ── */
    .replay-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 1.2rem 1.4rem;
        margin-bottom: 1rem;
        box-shadow: var(--shadow-sm);
        transition: box-shadow 0.2s;
    }
    .replay-card:hover { box-shadow: var(--shadow-md); }
    .replay-title { font-weight: 700; font-size: 1.06rem; color: var(--primary-dark); margin-bottom: 0.6rem; }

    /* ── QA Card ── */
    .qa-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.5rem 1.7rem;
        margin-bottom: 1.5rem;
        box-shadow: var(--shadow-sm);
        transition: box-shadow 0.2s;
    }
    .qa-card:hover { box-shadow: var(--shadow-md); }
    .qa-title { font-weight: 800; color: var(--primary-dark); font-size: 1.16rem; margin-bottom: 0.5rem; }
    .qa-meta  { color: var(--text-sub); font-size: 0.98rem; margin-bottom: 0.8rem; line-height: 1.55; }

    /* ── Status Pills (QA) ── */
    .status-pill         { display: inline-block; border-radius: 999px; padding: 4px 12px; font-size: 0.9rem; font-weight: 800; }
    .status-unreviewed   { background: #F1F5F9; color: #64748B; border: 1px solid #CBD5E1; }
    .status-correct      { background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }
    .status-false-positive { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; }
    .status-wrong-rule   { background: #FFFBEB; color: #D97706; border: 1px solid #FDE68A; }
    .status-unclear      { background: #F5F3FF; color: #7C3AED; border: 1px solid #DDD6FE; }
    .missing-video       { background: #FEF2F2; border: 1px solid #FECACA; border-radius: var(--radius-md); padding: 1.2rem; color: #DC2626; text-align: center; }

    /* ── Page Title ── */
    .page-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.8rem;
        font-weight: 900;
        background: linear-gradient(135deg, #EA580C 0%, #F97316 55%, #FB923C 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.25rem;
        line-height: 1.15;
    }
    .page-subtitle {
        color: var(--text-sub);
        font-size: 1.1rem;
        margin-bottom: 1.8rem;
        font-weight: 400;
        line-height: 1.5;
    }

    /* ── Section Label ── */
    .section-label {
        font-size: 1.3rem;
        font-weight: 750;
        color: var(--text-body);
        margin: 1.8rem 0 1rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* ── Sidebar Logo Area ── */
    .sidebar-logo {
        text-align: center;
        padding: 1.4rem 0 1.8rem 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 1.2rem;
    }
    .sidebar-logo .logo-emoji { font-size: 3.4rem; line-height: 1; }
    .sidebar-logo .logo-title {
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
        font-size: 1.18rem;
        color: var(--text-main);
        margin-top: 0.55rem;
    }
    .sidebar-logo .logo-sub {
        color: var(--text-sub);
        font-size: 0.82rem;
        margin-top: 0.15rem;
    }

    /* ── Divider ── */
    hr {
        border-color: var(--border) !important;
        margin: 1.6rem 0 !important;
    }

    /* ── DataFrame — Force Light Headers ── */
    .stDataFrame {
        border-radius: var(--radius-md);
        overflow: hidden;
        box-shadow: var(--shadow-sm);
    }
    /* Override dark header background */
    .stDataFrame [data-testid="stDataFrameResizable"],
    .stDataFrame thead tr,
    .stDataFrame thead th,
    .stDataFrame [class*="glideDataEditor"] [class*="header"],
    [data-testid="stDataFrame"] [data-testid="glide-cell-header"],
    .dvn-scroller .header-row,
    .gdg-header,
    [data-testid="stDataFrame"] canvas + div {
        background-color: var(--bg-soft) !important;
        color: var(--text-main) !important;
    }
    /* Force the glide data grid to use light colors */
    [data-testid="stDataFrame"] {
        --gdg-bg-header: #F1F5F9 !important;
        --gdg-bg-header-has-focus: #E8ECF1 !important;
        --gdg-bg-header-hovered: #E8ECF1 !important;
        --gdg-text-header: #0F172A !important;
        --gdg-bg-cell: #FFFFFF !important;
        --gdg-text-dark: #334155 !important;
        --gdg-text-medium: #64748B !important;
        --gdg-text-light: #94A3B8 !important;
        --gdg-border-color: #E8ECF1 !important;
        --gdg-bg-search-result: rgba(249,115,22,0.12) !important;
        --gdg-accent-color: #F97316 !important;
        --gdg-accent-light: rgba(249,115,22,0.15) !important;
        --gdg-bg-bubble: #F1F5F9 !important;
        --gdg-bg-bubble-selected: #FFF7ED !important;
    }

    /* ── Selectbox / Inputs ── */
    .stSelectbox > div > div,
    .stTextInput > div > div,
    .stTextArea > div > div,
    .stMultiSelect > div > div,
    .stNumberInput > div > div {
        background: var(--bg-card) !important;
        border-color: var(--border) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--text-main) !important;
    }
    .stSelectbox > div > div:focus-within,
    .stTextInput > div > div:focus-within,
    .stTextArea > div > div:focus-within {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(249,115,22,0.12) !important;
    }

    /* ── MultiSelect Tags — Soft Orange ── */
    .stMultiSelect [data-baseweb="tag"] {
        background-color: #FFF7ED !important;
        border: 1.5px solid #FED7AA !important;
        border-radius: 6px !important;
        color: var(--primary-dark) !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
    }
    .stMultiSelect [data-baseweb="tag"] span {
        color: var(--primary-dark) !important;
    }
    .stMultiSelect [data-baseweb="tag"] [role="presentation"] {
        color: var(--primary) !important;
    }
    /* Tag close button */
    .stMultiSelect [data-baseweb="tag"] svg,
    .stMultiSelect [data-baseweb="tag"] button {
        color: var(--primary) !important;
        fill: var(--primary) !important;
    }

    /* ── Plotly chart ── */
    .js-plotly-plot .plotly { background: transparent !important; }

    /* ── Alerts ── */
    .stAlert {
        border-radius: var(--radius-sm) !important;
        border-left-width: 4px !important;
    }

    /* ── Progress Bar ── */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, var(--primary), var(--accent)) !important;
        border-radius: 99px !important;
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        font-weight: 600 !important;
        color: var(--text-body) !important;
        background: var(--bg-soft) !important;
        border-radius: var(--radius-sm) !important;
    }

    /* ── Form Labels ── */
    .stSelectbox label,
    .stTextInput label,
    .stTextArea label,
    .stMultiSelect label,
    .stNumberInput label,
    .stRadio label,
    .stCheckbox label {
        color: var(--text-body) !important;
        font-weight: 600 !important;
    }
</style>
"""


def inject_global_css():
    """Inject the global CSS into the current Streamlit page. Call once at the top of every page."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════
#  REUSABLE UI COMPONENTS
# ═════════════════════════════════════════════════════════════════════════

def render_sidebar_logo():
    """Render the branded sidebar logo block."""
    st.markdown("""
    <div class="sidebar-logo">
        <div class="logo-emoji">🏀</div>
        <div class="logo-title">AI Basketball Referee</div>
        <div class="logo-sub">Foul Detection System</div>
    </div>
    """, unsafe_allow_html=True)


def render_page_header(title: str, subtitle: str):
    """Render a styled page title + subtitle."""
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)
    render_top_nav()


def render_top_nav():
    """Render visible page links in the main content area as a fallback navbar."""
    nav_cols = st.columns(len(_NAV_PAGES))
    for col, (label, page, icon) in zip(nav_cols, _NAV_PAGES):
        with col:
            st.page_link(page, label=label, icon=icon)
    st.markdown("<br>", unsafe_allow_html=True)


def render_section_label(icon: str, text: str):
    """Render a styled section label with icon."""
    st.markdown(
        f'<div class="section-label">{icon} {text}</div>',
        unsafe_allow_html=True,
    )


def render_footer():
    """Render a consistent footer across all pages."""
    st.markdown("""
    <div style="
        text-align: center;
        color: #94A3B8;
        font-size: 0.82rem;
        padding: 2rem 0 0.5rem 0;
        border-top: 1px solid #E8ECF1;
        margin-top: 1.5rem;
    ">
        Built with ❤️ using &nbsp;<strong style="color:#F97316;">YOLOv8</strong>
        &nbsp;·&nbsp; <strong style="color:#F97316;">MediaPipe Pose</strong>
        &nbsp;·&nbsp; <strong style="color:#F97316;">ByteTrack</strong>
        &nbsp;·&nbsp; <strong style="color:#F97316;">Streamlit</strong>
    </div>
    """, unsafe_allow_html=True)


def render_empty_state(icon: str, message: str):
    """Render a friendly empty-state card."""
    st.markdown(f"""
    <div class="ui-card" style="text-align:center; padding:3rem 2rem; color:#94A3B8;">
        <div style="font-size:2.8rem; margin-bottom:0.8rem; line-height:1;">{icon}</div>
        <div style="font-size:1.05rem; line-height:1.6;">{message}</div>
    </div>
    """, unsafe_allow_html=True)


# ── Navigation pages definition ──
_NAV_PAGES = [
    ("Home",               "app_ui.py",             "🏠"),
    ("Live Demo",          "pages/1_live_demo.py",  "🎥"),
    ("Analytics Summary",  "pages/2_analytics.py",  "📊"),
    ("QA Review",          "pages/4_qa_review.py",  "✅"),
]


def render_sidebar_nav():
    """Render the sidebar logo + navigation links. Call inside `with st.sidebar:` on every page."""
    render_sidebar_logo()
    st.markdown("### Navigation")
    for label, page, icon in _NAV_PAGES:
        st.page_link(page, label=label, icon=icon)
