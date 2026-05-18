"""
pages/3_system_info.py — Architecture + Foul Rules + Tech Stack
===============================================================
"""

import streamlit as st

st.set_page_config(
    page_title="System Info — AI Referee",
    page_icon="ℹ️",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Outfit:wght@400;600;700;800;900&display=swap');
:root{--primary:#F97316;--primary-dark:#EA580C;--accent:#FB923C;
    --bg-page:#F8FAFC;--bg-soft:#F1F5F9;--bg-card:#FFFFFF;--bg-card2:#F8FAFC;
    --border:#E2E8F0;--border-accent:rgba(249,115,22,0.3);
    --text-main:#0F172A;--text-body:#334155;--text-sub:#64748B;--text-muted:#94A3B8;
    --success:#10B981;--danger:#EF4444;--warning:#F59E0B;
    --shadow-sm:0 1px 3px rgba(0,0,0,0.06);--shadow-md:0 4px 16px rgba(0,0,0,0.08);}
html,body,[class*="css"],[data-testid="stAppViewContainer"],.stApp{font-family:'Inter',sans-serif!important;background-color:var(--bg-page)!important;color:var(--text-main)!important;font-size:17px!important;}
#MainMenu,footer,header{visibility:hidden;}.stDeployButton{display:none;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#FFFFFF 0%,#FFF7ED 60%,#FFF1E6 100%)!important;border-right:1px solid var(--border)!important;box-shadow:4px 0 20px rgba(0,0,0,0.04)!important;}
[data-testid="stSidebar"] *{color:var(--text-body)!important;}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,[data-testid="stSidebar"] strong{color:var(--text-main)!important;}
[data-testid="stSidebarNav"] a,[data-testid="stSidebarNav"] a span,[data-testid="stSidebarNavItems"] a,[data-testid="stSidebarNavItems"] span,section[data-testid="stSidebar"] a,section[data-testid="stSidebar"] a span,section[data-testid="stSidebar"] a p{color:var(--text-body)!important;font-weight:600!important;text-decoration:none!important;}
[data-testid="stSidebarNav"] a:hover,[data-testid="stSidebarNavItems"] a:hover,section[data-testid="stSidebar"] a:hover{background:rgba(249,115,22,0.1)!important;color:var(--primary-dark)!important;border-radius:8px!important;}
[data-testid="stSidebarNav"] a[aria-selected="true"],[data-testid="stSidebarNavItems"] a[aria-selected="true"]{background:rgba(249,115,22,0.15)!important;color:var(--primary-dark)!important;border-radius:8px!important;font-weight:700!important;}

.main .block-container{padding:2.2rem 2.7rem 3.2rem 2.7rem;max-width:1460px;}
.page-title{font-family:'Outfit',sans-serif;font-size:2.55rem;font-weight:900;background:linear-gradient(135deg,#EA580C 0%,#F97316 60%,#FB923C 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:0.25rem;line-height:1.15;}
.page-subtitle{color:var(--text-sub);font-size:1.08rem;margin-bottom:1.7rem;}
hr{border-color:var(--border)!important;margin:1.4rem 0!important;}

/* Rule cards */
.rule-card{
    background:var(--bg-card);
    border:1px solid var(--border);
    border-radius:14px;
    padding:1.3rem 1.4rem;
    height:100%;
    box-shadow:var(--shadow-sm);
    transition:transform 0.2s ease, box-shadow 0.2s ease;
}
.rule-card:hover{transform:translateY(-3px);box-shadow:var(--shadow-md);}
.rule-icon{font-size:2.2rem;margin-bottom:0.6rem;}
.rule-name{font-weight:800;font-size:1.18rem;color:var(--primary-dark);margin-bottom:0.35rem;}
.rule-desc{color:var(--text-sub);font-size:0.98rem;line-height:1.65;margin-bottom:0.9rem;}
.rule-how{font-size:0.92rem;color:#92400E;background:#FFF7ED;border:1px solid #FED7AA;border-radius:6px;padding:8px 11px;}

/* Tech Stack cards */
.tech-card{
    background:var(--bg-card);
    border:1px solid var(--border);
    border-radius:12px;
    padding:1.2rem 1.3rem;
    text-align:center;
    box-shadow:var(--shadow-sm);
    transition:transform 0.2s ease, box-shadow 0.2s ease;
}
.tech-card:hover{transform:translateY(-3px);box-shadow:var(--shadow-md);}
.tech-icon{font-size:2rem;margin-bottom:0.4rem;}
.tech-name{font-weight:700;font-size:1.12rem;color:var(--text-main);}
.tech-role{color:var(--text-sub);font-size:0.92rem;margin-top:0.25rem;}

/* Architecture Flow */
.arch-step{
    display:flex; align-items:flex-start; gap:1rem;
    background:var(--bg-card);
    border:1px solid var(--border);
    border-radius:10px;
    padding:0.9rem 1.1rem;
    margin-bottom:0.7rem;
    box-shadow:var(--shadow-sm);
    transition:border-color 0.2s, transform 0.2s;
}
.arch-step:hover{border-color:var(--border-accent);transform:translateX(3px);}
.arch-num{
    min-width:32px; height:32px;
    background:linear-gradient(135deg,var(--primary),var(--primary-dark));
    border-radius:50%;
    display:flex; align-items:center; justify-content:center;
    font-weight:800; font-size:1rem; color:white;
    flex-shrink:0;
}
.arch-content{}
.arch-title{font-weight:700;font-size:1.08rem;color:var(--text-main);margin-bottom:0.25rem;}
.arch-detail{font-size:0.96rem;color:var(--text-sub);line-height:1.5;}
.arch-arrow{text-align:center;color:var(--border-accent);font-size:1.4rem;margin:-0.2rem 0;}

/* Section label */
.section-label{font-size:1.34rem;font-weight:750;color:var(--text-body);margin:1.6rem 0 1rem 0;}

/* Accuracy badge */
.badge{display:inline-block;border-radius:6px;padding:4px 11px;font-size:0.9rem;font-weight:700;margin-right:5px;}
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li,label{font-size:1rem!important;line-height:1.55!important;}
.badge-green{background:#ECFDF5;color:#059669;border:1px solid #A7F3D0;}
.badge-orange{background:#FFF7ED;color:#EA580C;border:1px solid #FED7AA;}
.badge-blue{background:#EFF6FF;color:#2563EB;border:1px solid #BFDBFE;}
</style>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════
#  HEADER
# ═════════════════════════════════════════════════════════════════════════
st.markdown('<div class="page-title">ℹ️ System Info</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">สถาปัตยกรรมระบบ · กฎที่เปิดใช้งานปัจจุบัน · เทคโนโลยีที่ใช้</div>', unsafe_allow_html=True)
st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════
#  ARCHITECTURE FLOW
# ═════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">🏗️ System Architecture</div>', unsafe_allow_html=True)

arch_col, spacer = st.columns([2, 1])

with arch_col:
    steps = [
        ("📷", "Camera Input", "iPhone / MacBook Camera → OpenCV VideoCapture (1280×720 @ ~30fps)"),
        ("🤖", "Person Detection + Tracking (YOLOv8 + ByteTrack)", "ตรวจจับนักกีฬา → กำหนด Track ID ต่อเนื่อง (ไม่เกิน 4 คน)"),
        ("🏀", "Ball + Rim Detection (Custom YOLOv8)", "ตรวจจับลูกบาสและห่วง → ระบุ class: basketball / rim / sports ball"),
        ("🧘", "MediaPipe Pose (per player crop)", "วิเคราะห์ 33 Landmark ของร่างกาย → แปลงเป็น pixel coordinates เต็มเฟรม"),
        ("⚖️", "Rule Engine (BasketballRef)", "ประมวลผลกฎที่เปิดใช้งาน per-player per-frame"),
        ("🚨", "Violation Output", "แสดงบน OpenCV window + บันทึก CSV + event log + Replay Video (.mp4)"),
    ]

    for i, (icon, title, detail) in enumerate(steps):
        st.markdown(f"""
        <div class="arch-step">
            <div class="arch-num">{i+1}</div>
            <div class="arch-content">
                <div class="arch-title">{icon} {title}</div>
                <div class="arch-detail">{detail}</div>
            </div>
        </div>
        {"" if i == len(steps)-1 else '<div class="arch-arrow">↓</div>'}
        """, unsafe_allow_html=True)

with spacer:
    st.markdown("""
    <div style="background:var(--bg-card2);border:1px solid var(--border);border-radius:14px;padding:1.5rem;text-align:center;margin-top:0.5rem;">
        <div style="font-size:2.5rem;margin-bottom:0.8rem;">⚡</div>
        <div style="font-weight:800;font-size:1.1rem;color:#FF6B00;margin-bottom:0.3rem;">Real-time</div>
        <div style="color:#8888AA;font-size:0.96rem;">ตรวจสอบทุก Frame<br>ด้วย Apple MPS (GPU)</div>
        <hr style="border-color:rgba(255,107,0,0.2);margin:1rem 0;">
        <div style="font-size:2.5rem;margin-bottom:0.8rem;">🎥</div>
        <div style="font-weight:800;font-size:1.1rem;color:#FF6B00;margin-bottom:0.3rem;">Auto Replay</div>
        <div style="color:#8888AA;font-size:0.96rem;">บันทึก 3 วินาทีก่อน<br>+ 1 วินาทีหลัง Foul</div>
        <hr style="border-color:rgba(255,107,0,0.2);margin:1rem 0;">
        <div style="font-size:2.5rem;margin-bottom:0.8rem;">📊</div>
        <div style="font-weight:800;font-size:1.1rem;color:#FF6B00;margin-bottom:0.3rem;">Auto Logging</div>
        <div style="color:#8888AA;font-size:0.96rem;">บันทึก CSV ทุก Foul<br>เพื่อวิเคราะห์สถิติ</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════
#  FOUL RULE CARDS
# ═════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">📋 Active Detection Rules</div>', unsafe_allow_html=True)

rules = [
    {
        "icon": "🔄",
        "name": "Double Dribble",
        "desc": "ผู้เล่นหยุดเลี้ยงลูกแล้วเริ่มเลี้ยงใหม่ หรือเลี้ยงด้วยสองมือพร้อมกัน",
        "how": "🔬 State Machine: IDLE → DRIBBLING → HOLDING → DRIBBLING_AGAIN",
        "color": "#FFB347",
    },
    {
        "icon": "🚶",
        "name": "Traveling",
        "desc": "เดินหรือวิ่งขณะถือลูก โดยไม่เลี้ยง เกิน 2 ก้าวที่อนุญาต",
        "how": "🔬 Step Counter: Peak Detection บน ankle Y + Rolling Average + Dynamic Threshold",
        "color": "#7C4DFF",
    },
    {
        "icon": "🤲",
        "name": "Carrying",
        "desc": "วางมือใต้ลูกบาส (palm facing up) ขณะเลี้ยง — ผิดกฎ NBA/FIBA",
        "how": "🔬 Wrist vs Index Y position + Velocity confirm buffer (ป้องกัน false positive)",
        "color": "#00BCD4",
    },
    {
        "icon": "🏹",
        "name": "Goaltending",
        "desc": "แตะลูกขณะลูกกำลังลงสู่ตะกร้า หรืออยู่เหนือระนาบห่วง",
        "how": "🔬 Parabolic Trajectory Analysis: ตรวจวิถีลูก + ตำแหน่ง Rim Y จาก YOLO",
        "color": "#E91E63",
    },
    {
        "icon": "🤝",
        "name": "Held Ball / Jump Ball",
        "desc": "ผู้เล่นฝ่ายตรงข้ามจับหรือควบคุมบอลพร้อมกันจนไม่มีฝ่ายใดครอบครองบอลได้ชัดเจน",
        "how": "🔬 Two-player hand proximity to ball + ball stillness + confirm frames",
        "color": "#00E676",
    },
]

col1, col2, col3 = st.columns(3)
cols = [col1, col2, col3]

for i, rule in enumerate(rules):
    with cols[i % 3]:
        st.markdown(f"""
        <div class="rule-card" style="border-top:3px solid {rule['color']};">
            <div class="rule-icon">{rule['icon']}</div>
            <div class="rule-name" style="color:{rule['color']};">{rule['name']}</div>
            <div class="rule-desc">{rule['desc']}</div>
            <div class="rule-how">{rule['how']}</div>
        </div>
        <br>
        """, unsafe_allow_html=True)

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════
#  TECH STACK
# ═════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">🛠️ Tech Stack</div>', unsafe_allow_html=True)

techs = [
    ("🤖", "YOLOv8", "Object Detection\nPerson + Ball + Rim"),
    ("🔁", "ByteTrack", "Multi-Object Tracking\nPlayer ID tracking"),
    ("🧘", "MediaPipe", "Pose Estimation\n33 body landmarks"),
    ("👁️", "OpenCV", "Video Processing\nCamera + Drawing"),
    ("🐍", "Python", "Core Language\nv3.9+"),
    ("⚡", "Apple MPS", "GPU Acceleration\nMacBook inference"),
    ("📊", "Streamlit", "Web UI Framework\nThis dashboard"),
    ("📈", "Plotly", "Interactive Charts\nAnalytics visuals"),
]

t_cols = st.columns(4)
for i, (icon, name, role) in enumerate(techs):
    with t_cols[i % 4]:
        st.markdown(f"""
        <div class="tech-card">
            <div class="tech-icon">{icon}</div>
            <div class="tech-name">{name}</div>
            <div class="tech-role">{role.replace(chr(10), "<br>")}</div>
        </div>
        <br>
        """, unsafe_allow_html=True)

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════
#  MODEL INFO
# ═════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">📦 Model Files</div>', unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)

with m1:
    st.markdown("""
    <div class="arch-step" style="flex-direction:column; gap:0.5rem;">
        <div style="font-weight:700; color:#FF6B00;">🤖 yolov8n.pt</div>
        <div style="font-size:0.96rem; color:#8888AA;">Person Detection Model<br>COCO Pretrained · class 0 (person) · class 32 (sports ball fallback)</div>
        <div>
            <span class="badge badge-green">✓ Loaded</span>
            <span class="badge badge-blue">COCO 80 classes</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with m2:
    st.markdown("""
    <div class="arch-step" style="flex-direction:column; gap:0.5rem;">
        <div style="font-weight:700; color:#FF6B00;">🏀 trainmodel/best.pt</div>
        <div style="font-size:0.96rem; color:#8888AA;">Custom Ball + Rim Model<br>class 0: basketball · class 1: rim · class 2: sports ball</div>
        <div>
            <span class="badge badge-orange">Custom Trained</span>
            <span class="badge badge-blue">3 classes</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown("""
    <div class="arch-step" style="flex-direction:column; gap:0.5rem;">
        <div style="font-weight:700; color:#FF6B00;">🧘 MediaPipe Pose</div>
        <div style="font-size:0.96rem; color:#8888AA;">Body Pose Estimation<br>complexity=1 · 33 landmarks · full-body tracking</div>
        <div>
            <span class="badge badge-green">✓ Realtime</span>
            <span class="badge badge-blue">33 landmarks</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ═════════════════════════════════════════════════════════════════════════
#  SYSTEM REQUIREMENTS
# ═════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">💻 System Requirements</div>', unsafe_allow_html=True)

req_col1, req_col2 = st.columns(2)

with req_col1:
    st.markdown("""
    <div class="arch-step" style="flex-direction:column; gap:0.4rem;">
        <div style="font-weight:700; color:#FF6B00; margin-bottom:0.3rem;">🖥️ Hardware</div>
        <div style="font-size:0.98rem; color:#8888AA; line-height:2;">
            • MacBook (Apple Silicon — M1/M2/M3/M4 สำหรับ MPS GPU)<br>
            • RAM ≥ 8 GB แนะนำ 16 GB<br>
            • กล้อง iPhone หรือ Built-in Webcam<br>
            • USB / Wi-Fi สำหรับ iPhone Camera (DroidCam / Continuity Camera)
        </div>
    </div>
    """, unsafe_allow_html=True)

with req_col2:
    st.markdown("""
    <div class="arch-step" style="flex-direction:column; gap:0.4rem;">
        <div style="font-weight:700; color:#FF6B00; margin-bottom:0.3rem;">🐍 Software</div>
        <div style="font-size:0.98rem; color:#8888AA; line-height:2;">
            • Python 3.9+ (แนะนำ 3.11)<br>
            • ultralytics (YOLOv8)<br>
            • mediapipe · opencv-python · streamlit<br>
            • plotly · pandas · numpy
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div style="background:rgba(255,107,0,0.06);border:1px solid rgba(255,107,0,0.2);border-radius:10px;padding:1rem 1.3rem;margin-top:0.5rem;font-size:0.98rem;color:#8888AA;">
    💡 <strong style="color:#FF6B00;">วิธีรันระบบ</strong> &nbsp;→&nbsp;
    เปิด Terminal แล้วพิมพ์: &nbsp;
    <code style="background:rgba(0,0,0,0.4);padding:2px 8px;border-radius:4px;color:#FFB347;">streamlit run app_ui.py</code>
    &nbsp; จากนั้นไปที่หน้า <strong style="color:#FF6B00;">🎥 Live Demo</strong> แล้วกด Start System
</div>
""", unsafe_allow_html=True)
