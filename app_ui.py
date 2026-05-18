"""
app_ui.py — AI Basketball Referee: Main Streamlit Entry Point
=============================================================
รัน: streamlit run app_ui.py
"""

import streamlit as st

# ── Page Config ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🏀 AI Basketball Referee",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ───────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Import Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Outfit:wght@400;600;700;800;900&display=swap');

    /* ── Root Variables ── */
    :root {
        --primary:      #F97316;
        --primary-light:#FED7AA;
        --primary-dark: #EA580C;
        --accent:       #FB923C;
        --accent2:      #FDBA74;
        --bg-page:      #F8FAFC;
        --bg-soft:      #F1F5F9;
        --bg-card:      #FFFFFF;
        --bg-card2:     #F8FAFC;
        --border:       #E2E8F0;
        --border-accent:rgba(249,115,22,0.3);
        --text-main:    #0F172A;
        --text-body:    #334155;
        --text-sub:     #64748B;
        --text-muted:   #94A3B8;
        --success:      #10B981;
        --danger:       #EF4444;
        --warning:      #F59E0B;
        --info:         #3B82F6;
        --shadow-sm:    0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
        --shadow-md:    0 4px 16px rgba(0,0,0,0.08), 0 2px 6px rgba(0,0,0,0.04);
        --shadow-lg:    0 10px 40px rgba(0,0,0,0.10), 0 4px 12px rgba(0,0,0,0.06);
        --shadow-orange:0 8px 32px rgba(249,115,22,0.18);
        --radius-sm:    8px;
        --radius-md:    12px;
        --radius-lg:    16px;
        --radius-xl:    20px;
    }

    /* ── Base ── */
    html, body, [class*="css"], [data-testid="stAppViewContainer"], .stApp {
        font-family: 'Inter', sans-serif !important;
        background-color: var(--bg-page) !important;
        color: var(--text-main) !important;
    }

    /* ── Hide Streamlit branding ── */
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }
    .viewerBadge_container__1QSob { display: none; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #FFF7ED 60%, #FFF1E6 100%) !important;
        border-right: 1px solid var(--border) !important;
        box-shadow: 4px 0 20px rgba(0,0,0,0.04) !important;
    }

    /* ── Sidebar: all text dark ── */
    [data-testid="stSidebar"] * {
        color: var(--text-body) !important;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] strong {
        color: var(--text-main) !important;
    }

    /* ── Sidebar Nav Links ── */
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
        background: rgba(249,115,22,0.1) !important;
        color: var(--primary-dark) !important;
        border-radius: 8px !important;
    }
    [data-testid="stSidebarNav"] a[aria-selected="true"],
    [data-testid="stSidebarNavItems"] a[aria-selected="true"] {
        background: rgba(249,115,22,0.15) !important;
        color: var(--primary-dark) !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
    }
    /* nav item icons */
    [data-testid="stSidebarNav"] svg,
    [data-testid="stSidebarNavItems"] svg {
        fill: var(--text-sub) !important;
    }

    [data-testid="stSidebar"] .stRadio label {
        font-weight: 500;
        color: var(--text-body) !important;
        padding: 6px 0;
    }


    /* ── Main container ── */
    .main .block-container {
        padding: 2rem 2.5rem 3rem 2.5rem;
        max-width: 1400px;
    }

    /* ── Metric / KPI Cards ── */
    [data-testid="stMetric"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-md) !important;
        padding: 1.2rem 1.4rem !important;
        box-shadow: var(--shadow-sm) !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
    }
    [data-testid="stMetric"]:hover {
        transform: translateY(-3px) !important;
        box-shadow: var(--shadow-md) !important;
        border-color: var(--border-accent) !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--text-sub) !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
    }
    [data-testid="stMetricValue"] {
        color: var(--primary) !important;
        font-size: 2rem !important;
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
        font-size: 0.95rem !important;
        padding: 0.65rem 1.8rem !important;
        transition: all 0.25s ease !important;
        box-shadow: 0 4px 14px rgba(249,115,22,0.35) !important;
        letter-spacing: 0.02em !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(249,115,22,0.45) !important;
        background: linear-gradient(135deg, #FB923C 0%, var(--primary) 100%) !important;
    }
    .stButton > button:active { transform: translateY(0) !important; }

    /* Stop Button (secondary) */
    .stop-btn > button {
        background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%) !important;
        box-shadow: 0 4px 14px rgba(239,68,68,0.35) !important;
    }
    .stop-btn > button:hover {
        box-shadow: 0 8px 24px rgba(239,68,68,0.45) !important;
    }

    /* ── Cards ── */
    .ui-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 1.4rem 1.6rem;
        margin-bottom: 1rem;
        box-shadow: var(--shadow-sm);
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }
    .ui-card:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
        border-color: var(--border-accent);
    }

    /* ── Status Badge ── */
    .status-active {
        display: inline-flex; align-items: center; gap: 8px;
        background: #ECFDF5;
        color: var(--success);
        border: 1.5px solid #6EE7B7;
        border-radius: 20px;
        padding: 6px 16px;
        font-weight: 700; font-size: 0.88rem;
        animation: pulse-green 2s ease-in-out infinite;
    }
    .status-stopped {
        display: inline-flex; align-items: center; gap: 8px;
        background: var(--bg-soft);
        color: var(--text-sub);
        border: 1.5px solid var(--border);
        border-radius: 20px;
        padding: 6px 16px;
        font-weight: 700; font-size: 0.88rem;
    }
    .dot-green  { width: 9px; height: 9px; border-radius: 50%; background: var(--success); }
    .dot-gray   { width: 9px; height: 9px; border-radius: 50%; background: var(--text-muted); }

    @keyframes pulse-green {
        0%,100% { box-shadow: 0 0 0 0 rgba(16,185,129,0.35); }
        50%      { box-shadow: 0 0 0 7px rgba(16,185,129,0); }
    }

    /* ── Foul Alert Row ── */
    .foul-row {
        display: flex; align-items: center; gap: 12px;
        padding: 10px 16px;
        border-radius: var(--radius-sm);
        margin-bottom: 6px;
        background: #FFF7ED;
        border-left: 3px solid var(--primary);
        font-size: 0.87rem;
        transition: background 0.15s, transform 0.15s;
    }
    .foul-row:hover {
        background: #FFEDD5;
        transform: translateX(2px);
    }
    .foul-time   { color: var(--text-sub); font-size: 0.78rem; min-width: 75px; }
    .foul-player { color: var(--primary-dark); font-weight: 700; min-width: 80px; }
    .foul-type   { color: var(--text-body); font-weight: 600; }

    /* ── Rule Cards (System Info) ── */
    .rule-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 1.2rem 1.4rem;
        height: 100%;
        box-shadow: var(--shadow-sm);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .rule-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-md);
    }
    .rule-card h4 { color: var(--primary); margin-bottom: 0.4rem; font-size: 1rem; }
    .rule-card p  { color: var(--text-sub); font-size: 0.84rem; line-height: 1.55; margin: 0; }

    /* ── Page Title ── */
    .page-title {
        font-family: 'Outfit', sans-serif;
        font-size: 2.2rem;
        font-weight: 900;
        background: linear-gradient(135deg, #EA580C 0%, #F97316 50%, #FB923C 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.2rem;
        line-height: 1.2;
    }
    .page-subtitle {
        color: var(--text-sub);
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
        font-weight: 400;
    }

    /* ── Divider ── */
    hr { border-color: var(--border) !important; margin: 1.4rem 0 !important; }

    /* ── Dataframe ── */
    .stDataFrame { border-radius: var(--radius-md); overflow: hidden; box-shadow: var(--shadow-sm); }

    /* ── Selectbox / Input ── */
    .stSelectbox > div > div, .stTextInput > div > div, .stTextArea > div > div, .stMultiSelect > div > div {
        background: var(--bg-card) !important;
        border-color: var(--border) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--text-main) !important;
    }
    .stSelectbox > div > div:focus-within,
    .stTextInput > div > div:focus-within {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(249,115,22,0.15) !important;
    }

    /* ── Sidebar Logo Area ── */
    .sidebar-logo {
        text-align: center;
        padding: 1.2rem 0 1.6rem 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 1rem;
    }
    .sidebar-logo .logo-emoji { font-size: 3.2rem; line-height: 1; }
    .sidebar-logo .logo-title {
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
        font-size: 1.15rem;
        color: var(--text-main);
        margin-top: 0.5rem;
    }
    .sidebar-logo .logo-sub {
        color: var(--text-sub);
        font-size: 0.78rem;
        margin-top: 0.15rem;
    }

    /* ── Section label ── */
    .section-label {
        font-size: 1.1rem;
        font-weight: 700;
        color: var(--text-body);
        margin: 1.4rem 0 0.8rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* ── Plotly chart background ── */
    .js-plotly-plot .plotly { background: transparent !important; }

    /* ── Info/Warning alerts ── */
    .stAlert {
        border-radius: var(--radius-sm) !important;
        border-left-width: 4px !important;
    }

    /* ── Progress bar ── */
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
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <div class="logo-emoji">🏀</div>
        <div class="logo-title">AI Basketball Referee</div>
        <div class="logo-sub">Foul Detection System</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Navigation")

# ── Hero Section ─────────────────────────────────────────────────────────
st.markdown("""
<div style="
    background: linear-gradient(135deg, #FFF7ED 0%, #FFEDD5 50%, #FEF3C7 100%);
    border: 1px solid #FED7AA;
    border-radius: 20px;
    padding: 2.5rem 2rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 4px 24px rgba(249,115,22,0.1);
">
    <div style="position:absolute;top:-20px;right:-20px;font-size:8rem;opacity:0.08;line-height:1;">🏀</div>
    <div style="
        font-family:'Outfit',sans-serif;
        font-size:2.8rem;
        font-weight:900;
        background:linear-gradient(135deg,#EA580C 0%,#F97316 60%,#FB923C 100%);
        -webkit-background-clip:text;
        -webkit-text-fill-color:transparent;
        background-clip:text;
        line-height:1.15;
        margin-bottom:0.6rem;
    ">🏀 AI Basketball Referee</div>
    <div style="font-size:1.05rem;color:#64748B;margin-bottom:1.5rem;font-weight:400;max-width:600px;line-height:1.6;">
        ระบบตรวจจับการทำฟาวล์บาสเกตบอลด้วย AI แบบ Real-time<br>
        ขับเคลื่อนด้วย YOLOv8 · MediaPipe Pose · ByteTrack
    </div>
    <div style="display:flex;gap:0.75rem;flex-wrap:wrap;">
        <span style="background:#FFF7ED;color:#EA580C;border:1.5px solid #FED7AA;border-radius:99px;padding:5px 14px;font-size:0.82rem;font-weight:700;">⚡ Real-time Detection</span>
        <span style="background:#ECFDF5;color:#059669;border:1.5px solid #A7F3D0;border-radius:99px;padding:5px 14px;font-size:0.82rem;font-weight:700;">🎥 Auto Replay</span>
        <span style="background:#EFF6FF;color:#2563EB;border:1.5px solid #BFDBFE;border-radius:99px;padding:5px 14px;font-size:0.82rem;font-weight:700;">📊 Analytics Dashboard</span>
        <span style="background:#F5F3FF;color:#7C3AED;border:1.5px solid #DDD6FE;border-radius:99px;padding:5px 14px;font-size:0.82rem;font-weight:700;">✅ QA Review</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Navigation Cards ──────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

nav_cards = [
    ("col1", "🎥", "#FFF7ED", "#FED7AA", "#EA580C", "Live Demo", "เปิด/ปิดระบบ · ดู Foul แบบ Real-time · เล่น Replay"),
    ("col2", "📊", "#EFF6FF", "#BFDBFE", "#2563EB", "Analytics", "สถิติ Foul · Precision/Recall/F1 · Export ข้อมูล"),
    ("col3", "✅", "#ECFDF5", "#A7F3D0", "#059669", "QA Review", "รีวิว replay ทีละหน้า · บันทึก Human Label · ลดคลิปหลุด"),
    ("col4", "ℹ️", "#F5F3FF", "#DDD6FE", "#7C3AED", "System Info", "สถาปัตยกรรม · กฎ Foul รุ่นปัจจุบัน · Tech Stack"),
]

for (col_id, icon, bg, border, color, title, desc), col in zip(nav_cards, [col1, col2, col3, col4]):
    with col:
        st.markdown(f"""
        <div style="
            background:{bg};
            border:1.5px solid {border};
            border-radius:16px;
            padding:1.8rem 1rem 1.4rem 1rem;
            text-align:center;
            cursor:pointer;
            transition:transform 0.2s, box-shadow 0.2s;
            box-shadow:0 2px 8px rgba(0,0,0,0.05);
        " onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='0 12px 32px rgba(0,0,0,0.1)'"
           onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 2px 8px rgba(0,0,0,0.05)'">
            <div style="font-size:2.6rem;margin-bottom:0.7rem;line-height:1;">{icon}</div>
            <div style="font-family:'Outfit',sans-serif;font-weight:800;font-size:1.1rem;color:{color};margin-bottom:0.4rem;">{title}</div>
            <div style="color:#64748B;font-size:0.82rem;line-height:1.5;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Stats Overview ────────────────────────────────────────────────────────
st.markdown("""
<div style="
    background:white;
    border:1px solid #E2E8F0;
    border-radius:16px;
    padding:1.5rem 2rem;
    box-shadow:0 2px 8px rgba(0,0,0,0.05);
    margin-bottom:1.5rem;
">
    <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:1rem;">
        <span style="font-size:1.1rem;">🛠️</span>
        <span style="font-family:'Outfit',sans-serif;font-weight:800;font-size:1rem;color:#0F172A;">วิธีใช้งาน</span>
    </div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;text-align:center;">
        <div>
            <div style="font-size:1.6rem;margin-bottom:0.3rem;">1️⃣</div>
            <div style="font-weight:700;font-size:0.88rem;color:#0F172A;">เลือก Camera</div>
            <div style="color:#64748B;font-size:0.78rem;margin-top:0.2rem;">Built-in หรือ iPhone</div>
        </div>
        <div>
            <div style="font-size:1.6rem;margin-bottom:0.3rem;">2️⃣</div>
            <div style="font-weight:700;font-size:0.88rem;color:#0F172A;">กด Start System</div>
            <div style="color:#64748B;font-size:0.78rem;margin-top:0.2rem;">เปิดหน้าต่าง OpenCV</div>
        </div>
        <div>
            <div style="font-size:1.6rem;margin-bottom:0.3rem;">3️⃣</div>
            <div style="font-weight:700;font-size:0.88rem;color:#0F172A;">เล่นบาสเกตบอล</div>
            <div style="color:#64748B;font-size:0.78rem;margin-top:0.2rem;">AI ตรวจจับ Foul อัตโนมัติ</div>
        </div>
        <div>
            <div style="font-size:1.6rem;margin-bottom:0.3rem;">4️⃣</div>
            <div style="font-weight:700;font-size:0.88rem;color:#0F172A;">ดู Foul Feed</div>
            <div style="color:#64748B;font-size:0.78rem;margin-top:0.2rem;">Auto-refresh ทุก 2 วินาที</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;color:#94A3B8;font-size:0.78rem;padding:1.5rem 0 0.5rem 0;border-top:1px solid #F1F5F9;margin-top:1rem;">
    Built with ❤️ using &nbsp;<strong style="color:#F97316;">YOLOv8</strong> &nbsp;·&nbsp; <strong style="color:#F97316;">MediaPipe Pose</strong> &nbsp;·&nbsp; <strong style="color:#F97316;">ByteTrack</strong> &nbsp;·&nbsp; <strong style="color:#F97316;">Streamlit</strong>
</div>
""", unsafe_allow_html=True)
