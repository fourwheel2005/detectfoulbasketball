"""
app_ui.py — AI Basketball Referee: Main Streamlit Entry Point
=============================================================
รัน: streamlit run app_ui.py
"""

import streamlit as st
from ui_theme import inject_global_css, render_sidebar_nav, render_top_nav, render_footer

# ── Page Config ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🏀 AI Basketball Referee",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Apply Global Theme ──────────────────────────────────────────────────
inject_global_css()

# ── Sidebar ──────────────────────────────────────────────────────────────
with st.sidebar:
    render_sidebar_nav()

# ── Hero Section ─────────────────────────────────────────────────────────
st.markdown("""
<div style="
    background: linear-gradient(135deg, #FFFFFF 0%, #FFF9F5 40%, #FFF4ED 100%);
    border: 1px solid #F3D8C2;
    border-radius: 24px;
    padding: 3rem 2.5rem;
    margin-bottom: 2.2rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 4px 24px rgba(249,115,22,0.08);
">
    <div style="position:absolute;top:-20px;right:-20px;font-size:9rem;opacity:0.06;line-height:1;">🏀</div>
    <div style="
        font-family:'Outfit',sans-serif;
        font-size:3rem;
        font-weight:900;
        background:linear-gradient(135deg,#EA580C 0%,#F97316 60%,#FB923C 100%);
        -webkit-background-clip:text;
        -webkit-text-fill-color:transparent;
        background-clip:text;
        line-height:1.15;
        margin-bottom:0.7rem;
    ">🏀 AI Basketball Referee</div>
    <div style="font-size:1.1rem;color:#64748B;margin-bottom:1.6rem;font-weight:400;max-width:620px;line-height:1.65;">
        ระบบตรวจจับการทำฟาวล์บาสเกตบอลด้วย AI แบบ Real-time<br>
        ขับเคลื่อนด้วย YOLOv8 · MediaPipe Pose · ByteTrack
    </div>
    <div style="display:flex;gap:0.8rem;flex-wrap:wrap;">
        <span style="background:#FFF7ED;color:#EA580C;border:1.5px solid #FED7AA;border-radius:99px;padding:6px 16px;font-size:0.88rem;font-weight:700;">⚡ Real-time Detection</span>
        <span style="background:#ECFDF5;color:#059669;border:1.5px solid #A7F3D0;border-radius:99px;padding:6px 16px;font-size:0.88rem;font-weight:700;">🎥 Auto Replay</span>
        <span style="background:#F5F3FF;color:#7C3AED;border:1.5px solid #DDD6FE;border-radius:99px;padding:6px 16px;font-size:0.88rem;font-weight:700;">✅ QA Review</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Navigation ───────────────────────────────────────────────────────────
st.markdown("### เลือกหน้าการทำงาน")
render_top_nav()

col1, col2 = st.columns(2, gap="large")

nav_cards = [
    (col1, "🎥", "#FFF9F5", "#F3D8C2", "#EA580C", "Live Demo",
     "เปิด/ปิดระบบ · ดู Foul แบบ Real-time · เล่น Replay"),
    (col2, "✅", "#F0FDF9", "#BBE9D8", "#059669", "QA Review",
     "รีวิว replay ทีละหน้า · บันทึก Human Label · ลดคลิปหลุด"),
]

for col, icon, bg, border, color, title, desc in nav_cards:
    with col:
        st.markdown(f"""
        <div style="
            background: {bg};
            border: 1.5px solid {border};
            border-radius: 20px;
            padding: 2rem 1.5rem 1.6rem 1.5rem;
            text-align: center;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        " onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='0 12px 32px rgba(0,0,0,0.08)'"
           onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 2px 8px rgba(0,0,0,0.04)'">
            <div style="font-size:2.8rem;margin-bottom:0.8rem;line-height:1;">{icon}</div>
            <div style="font-family:'Outfit',sans-serif;font-weight:800;font-size:1.15rem;color:{color};margin-bottom:0.5rem;">{title}</div>
            <div style="color:#64748B;font-size:0.88rem;line-height:1.55;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)
        if title == "Live Demo":
            if st.button("🎥 ไปหน้า Live Demo", key="home_live_demo", use_container_width=True):
                st.switch_page("pages/1_live_demo.py")
        elif title == "QA Review":
            if st.button("✅ ไปหน้า QA Review", key="home_qa_review", use_container_width=True):
                st.switch_page("pages/4_qa_review.py")

st.markdown("<br>", unsafe_allow_html=True)

# ── How-to Section ────────────────────────────────────────────────────────
st.markdown("""
<div style="
    background: white;
    border: 1px solid #E8ECF1;
    border-radius: 20px;
    padding: 1.8rem 2.2rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    margin-bottom: 1.5rem;
">
    <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:1.2rem;">
        <span style="font-size:1.15rem;">🛠️</span>
        <span style="font-family:'Outfit',sans-serif;font-weight:800;font-size:1.08rem;color:#0F172A;">วิธีใช้งาน</span>
    </div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1.2rem;text-align:center;">
        <div>
            <div style="font-size:1.8rem;margin-bottom:0.4rem;">1️⃣</div>
            <div style="font-weight:700;font-size:0.92rem;color:#0F172A;">เลือก Camera</div>
            <div style="color:#64748B;font-size:0.82rem;margin-top:0.25rem;">Built-in หรือ iPhone</div>
        </div>
        <div>
            <div style="font-size:1.8rem;margin-bottom:0.4rem;">2️⃣</div>
            <div style="font-weight:700;font-size:0.92rem;color:#0F172A;">กด Start System</div>
            <div style="color:#64748B;font-size:0.82rem;margin-top:0.25rem;">เปิดหน้าต่าง OpenCV</div>
        </div>
        <div>
            <div style="font-size:1.8rem;margin-bottom:0.4rem;">3️⃣</div>
            <div style="font-weight:700;font-size:0.92rem;color:#0F172A;">เล่นบาสเกตบอล</div>
            <div style="color:#64748B;font-size:0.82rem;margin-top:0.25rem;">AI ตรวจจับ Foul อัตโนมัติ</div>
        </div>
        <div>
            <div style="font-size:1.8rem;margin-bottom:0.4rem;">4️⃣</div>
            <div style="font-weight:700;font-size:0.92rem;color:#0F172A;">ดู Foul Feed</div>
            <div style="color:#64748B;font-size:0.82rem;margin-top:0.25rem;">Auto-refresh ทุก 2 วินาที</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────
render_footer()
