"""
pages/1_live_demo.py — Live Camera Control + Foul Alert Feed + Replay Gallery
=============================================================================
"""

import streamlit as st
import pandas as pd
import subprocess
import os
import time
import sys
import json
from datetime import datetime
from pathlib import Path

# ── Inherit global CSS from app_ui.py ───────────────────────────────────
st.set_page_config(
    page_title="Live Demo — AI Referee",
    page_icon="🎥",
    layout="wide",
)

# ── Inject CSS (same global styles) ─────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Outfit:wght@400;600;700;800;900&display=swap');
:root {
    --primary:#F97316; --primary-dark:#EA580C; --accent:#FB923C; --accent2:#FDBA74;
    --bg-page:#F8FAFC; --bg-soft:#F1F5F9; --bg-card:#FFFFFF; --bg-card2:#F8FAFC;
    --border:#E2E8F0; --border-accent:rgba(249,115,22,0.3);
    --text-main:#0F172A; --text-body:#334155; --text-sub:#64748B; --text-muted:#94A3B8;
    --success:#10B981; --danger:#EF4444; --warning:#F59E0B;
    --shadow-sm:0 1px 3px rgba(0,0,0,0.06); --shadow-md:0 4px 16px rgba(0,0,0,0.08);
}
html,body,[class*="css"],[data-testid="stAppViewContainer"],.stApp{font-family:'Inter',sans-serif!important;background-color:var(--bg-page)!important;color:var(--text-main)!important;font-size:17px!important;}
#MainMenu,footer,header{visibility:hidden;} .stDeployButton{display:none;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#FFFFFF 0%,#FFF7ED 60%,#FFF1E6 100%)!important;border-right:1px solid var(--border)!important;box-shadow:4px 0 20px rgba(0,0,0,0.04)!important;}
[data-testid="stSidebar"] *{color:var(--text-body)!important;}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3,[data-testid="stSidebar"] strong{color:var(--text-main)!important;}
[data-testid="stSidebarNav"] a,[data-testid="stSidebarNav"] a span,[data-testid="stSidebarNavItems"] a,[data-testid="stSidebarNavItems"] span,section[data-testid="stSidebar"] a,section[data-testid="stSidebar"] a span,section[data-testid="stSidebar"] a p{color:var(--text-body)!important;font-weight:600!important;text-decoration:none!important;}
[data-testid="stSidebarNav"] a:hover,[data-testid="stSidebarNavItems"] a:hover,section[data-testid="stSidebar"] a:hover{background:rgba(249,115,22,0.1)!important;color:var(--primary-dark)!important;border-radius:8px!important;}
[data-testid="stSidebarNav"] a[aria-selected="true"],[data-testid="stSidebarNavItems"] a[aria-selected="true"]{background:rgba(249,115,22,0.15)!important;color:var(--primary-dark)!important;border-radius:8px!important;font-weight:700!important;}

.main .block-container{padding:2.2rem 2.7rem 3.2rem 2.7rem;max-width:1460px;}
[data-testid="stMetric"]{background:var(--bg-card)!important;border:1px solid var(--border)!important;border-radius:12px!important;padding:1.35rem 1.5rem!important;box-shadow:var(--shadow-sm)!important;transition:transform 0.2s ease,box-shadow 0.2s ease,border-color 0.2s ease!important;}
[data-testid="stMetric"]:hover{transform:translateY(-3px)!important;box-shadow:var(--shadow-md)!important;border-color:var(--border-accent)!important;}
[data-testid="stMetricLabel"]{color:var(--text-sub)!important;font-size:0.9rem!important;font-weight:700!important;text-transform:uppercase!important;letter-spacing:0.04em!important;}
[data-testid="stMetricValue"]{color:var(--primary)!important;font-size:2.25rem!important;font-weight:800!important;}
.stButton>button{background:linear-gradient(135deg,var(--primary) 0%,var(--primary-dark) 100%)!important;color:white!important;border:none!important;border-radius:8px!important;font-weight:700!important;font-size:1.05rem!important;padding:0.75rem 1.9rem!important;transition:all 0.25s ease!important;box-shadow:0 4px 14px rgba(249,115,22,0.35)!important;letter-spacing:0.02em!important;}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 8px 24px rgba(249,115,22,0.45)!important;}
.stop-btn>button{background:linear-gradient(135deg,#EF4444 0%,#DC2626 100%)!important;box-shadow:0 4px 14px rgba(239,68,68,0.35)!important;}
.ui-card{background:var(--bg-card);border:1px solid var(--border);border-radius:16px;padding:1.4rem 1.6rem;margin-bottom:1rem;box-shadow:var(--shadow-sm);transition:transform 0.2s,box-shadow 0.2s,border-color 0.2s;}
.ui-card:hover{transform:translateY(-2px);box-shadow:var(--shadow-md);border-color:var(--border-accent);}
.status-active{display:inline-flex;align-items:center;gap:8px;background:#ECFDF5;color:var(--success);border:1.5px solid #6EE7B7;border-radius:20px;padding:7px 17px;font-weight:700;font-size:1rem;animation:pulse-green 2s ease-in-out infinite;}
.status-stopped{display:inline-flex;align-items:center;gap:8px;background:var(--bg-soft);color:var(--text-sub);border:1.5px solid var(--border);border-radius:20px;padding:7px 17px;font-weight:700;font-size:1rem;}
.dot-green{width:9px;height:9px;border-radius:50%;background:var(--success);}
.dot-gray{width:9px;height:9px;border-radius:50%;background:var(--text-muted);}
@keyframes pulse-green{0%,100%{box-shadow:0 0 0 0 rgba(16,185,129,0.35);}50%{box-shadow:0 0 0 7px rgba(16,185,129,0);}}
.foul-row{display:flex;align-items:center;gap:14px;padding:13px 18px;border-radius:8px;margin-bottom:8px;background:#FFF7ED;border-left:4px solid var(--primary);font-size:1rem;transition:background 0.15s,transform 0.15s;}
.foul-row:hover{background:#FFEDD5;transform:translateX(2px);}
.foul-time{color:var(--text-sub);font-size:0.92rem;min-width:84px;}
.foul-player{color:var(--primary-dark);font-weight:700;min-width:80px;}
.foul-type{color:var(--text-body);font-weight:600;}
.page-title{font-family:'Outfit',sans-serif;font-size:2.55rem;font-weight:900;background:linear-gradient(135deg,#EA580C 0%,#F97316 60%,#FB923C 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:0.25rem;line-height:1.15;}
.page-subtitle{color:var(--text-sub);font-size:1.08rem;margin-bottom:1.7rem;}
hr{border-color:var(--border)!important;margin:1.4rem 0!important;}
.stSelectbox>div>div,.stTextInput>div>div,.stTextArea>div>div{background:var(--bg-card)!important;border-color:var(--border)!important;border-radius:8px!important;color:var(--text-main)!important;}
.replay-card{background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:1.15rem 1.3rem;margin-bottom:0.9rem;box-shadow:var(--shadow-sm);}
.replay-title{font-weight:700;font-size:1.04rem;color:var(--primary-dark);margin-bottom:0.6rem;}
.foul-badge{display:inline-block;background:#FFF7ED;color:var(--primary);border:1.5px solid #FED7AA;border-radius:6px;padding:4px 10px;font-size:0.88rem;font-weight:700;margin-right:5px;}
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li,label{font-size:1rem!important;line-height:1.55!important;}
</style>
""", unsafe_allow_html=True)

# ── Project Root ─────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
LOG_FILE     = PROJECT_ROOT / "basketball_foul_logs.csv"
EVENT_FILE   = PROJECT_ROOT / "logs" / "foul_events.csv"
REVIEW_FILE  = PROJECT_ROOT / "logs" / "review_labels.csv"
RUNTIME_STATUS_FILE = PROJECT_ROOT / "logs" / "runtime_status.json"
REPLAY_DIR   = PROJECT_ROOT / "logs" / "replays"
MAIN_PY      = PROJECT_ROOT / "main.py"
REVIEW_COLUMNS = [
    "Event_ID",
    "Replay_Path",
    "Predicted_Rule",
    "Review_Status",
    "Human_Label",
    "Reviewer_Note",
    "Reviewed_At",
]
ACTIVE_RULES = {
    "DOUBLE DRIBBLE",
    "TRAVELING",
    "CARRYING",
    "GOALTENDING",
    "HELD BALL",
}
DEPRECATED_RULES = {
    "PUSH FOUL",
    "ILLEGAL HANDS",
}

# ── Session State Init ───────────────────────────────────────────────────
if "process" not in st.session_state:
    st.session_state.process       = None
if "system_active" not in st.session_state:
    st.session_state.system_active = False
if "session_start_time" not in st.session_state:
    st.session_state.session_start_time = None
if "camera_index" not in st.session_state:
    st.session_state.camera_index  = 1
if "last_log_count" not in st.session_state:
    st.session_state.last_log_count = 0

# ── Helpers ──────────────────────────────────────────────────────────────
def is_process_running():
    """ตรวจสอบว่า subprocess ยังรันอยู่หรือไม่"""
    p = st.session_state.process
    if p is None:
        return False
    return p.poll() is None


def start_system(camera_idx: int):
    """รัน main.py เป็น subprocess"""
    env = os.environ.copy()
    env["BASKETBALL_CAMERA"] = str(camera_idx)
    process = subprocess.Popen(
        [sys.executable, str(MAIN_PY)],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    st.session_state.process            = process
    st.session_state.system_active      = True
    st.session_state.session_start_time = datetime.now()


def stop_system():
    """ปิด subprocess"""
    p = st.session_state.process
    if p and p.poll() is None:
        p.terminate()
        try:
            p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p.kill()
    st.session_state.process       = None
    st.session_state.system_active = False


def load_recent_fouls(n: int = 20):
    """โหลด Foul ล่าสุดจาก CSV"""
    if not LOG_FILE.exists():
        return pd.DataFrame(columns=["Date_Time", "Player_ID", "Foul_Type"])
    try:
        df = pd.read_csv(LOG_FILE)
        df["Date_Time"] = pd.to_datetime(df["Date_Time"])
        df["Foul_Label"] = df["Foul_Type"].apply(foul_short_name)
        df["Rule_Status"] = df["Foul_Label"].apply(rule_status)
        return df.sort_values("Date_Time", ascending=False).head(n).reset_index(drop=True)
    except Exception:
        return pd.DataFrame(columns=["Date_Time", "Player_ID", "Foul_Type"])


def load_foul_events():
    """โหลด event log ใหม่ที่ผูก foul กับ replay path"""
    if not EVENT_FILE.exists():
        return pd.DataFrame(columns=[
            "Event_ID", "Date_Time", "Session_ID", "Frame_Index",
            "Player_ID", "Foul_Type", "Replay_Path", "Camera_ID",
        ])
    try:
        return pd.read_csv(EVENT_FILE)
    except Exception:
        return pd.DataFrame(columns=[
            "Event_ID", "Date_Time", "Session_ID", "Frame_Index",
            "Player_ID", "Foul_Type", "Replay_Path", "Camera_ID",
        ])


def load_review_labels():
    """โหลดผล human review สำหรับ accuracy/QA"""
    if not REVIEW_FILE.exists():
        return pd.DataFrame(columns=REVIEW_COLUMNS)
    try:
        return pd.read_csv(REVIEW_FILE)
    except Exception:
        return pd.DataFrame(columns=REVIEW_COLUMNS)


def load_runtime_status():
    """โหลดสถานะ runtime ล่าสุดจาก main.py สำหรับ field test health"""
    if not RUNTIME_STATUS_FILE.exists():
        return {}
    try:
        with open(RUNTIME_STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_review_label(event_id, replay_path, predicted_rule, status, human_label, note):
    """บันทึกหรืออัปเดตผล review ของ event เดิม"""
    REVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)
    reviews = load_review_labels()
    new_row = {
        "Event_ID": event_id,
        "Replay_Path": replay_path,
        "Predicted_Rule": predicted_rule,
        "Review_Status": status,
        "Human_Label": human_label,
        "Reviewer_Note": note,
        "Reviewed_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    reviews = reviews[reviews["Event_ID"].astype(str) != str(event_id)]
    reviews = pd.concat([reviews, pd.DataFrame([new_row])], ignore_index=True)
    reviews.to_csv(REVIEW_FILE, index=False)


def load_session_fouls():
    """โหลด Foul ที่เกิดในเซสชันนี้"""
    if not LOG_FILE.exists() or st.session_state.session_start_time is None:
        return pd.DataFrame()
    try:
        df = pd.read_csv(LOG_FILE)
        df["Date_Time"] = pd.to_datetime(df["Date_Time"])
        df["Foul_Label"] = df["Foul_Type"].apply(foul_short_name)
        df["Rule_Status"] = df["Foul_Label"].apply(rule_status)
        mask = df["Date_Time"] >= st.session_state.session_start_time
        return df[mask]
    except Exception:
        return pd.DataFrame()


def get_foul_color(foul_type: str) -> str:
    """คืนสีตามประเภท Foul"""
    foul_type_upper = foul_type.upper()
    if "PUSH"        in foul_type_upper: return "#FF6B00"
    if "ILLEGAL"     in foul_type_upper: return "#FF3D57"
    if "DOUBLE"      in foul_type_upper: return "#FFB347"
    if "TRAVELING"   in foul_type_upper: return "#7C4DFF"
    if "CARRY"       in foul_type_upper: return "#00BCD4"
    if "GOALTENDING" in foul_type_upper: return "#E91E63"
    if "HELD" in foul_type_upper or "JUMP" in foul_type_upper: return "#00E676"
    return "#FF6B00"


def get_replay_videos():
    """ดึงรายการไฟล์วิดีโอ Replay"""
    if not REPLAY_DIR.exists():
        return []
    videos = sorted(REPLAY_DIR.glob("*.mp4"), key=os.path.getmtime, reverse=True)
    return videos[:10]  # แสดง 10 ล่าสุด


def foul_short_name(foul_type: str) -> str:
    """ชื่อย่อของ Foul"""
    f = foul_type.upper()
    if "PUSH"        in f: return "PUSH FOUL"
    if "ILLEGAL"     in f: return "ILLEGAL HANDS"
    if "DOUBLE"      in f: return "DOUBLE DRIBBLE"
    if "TRAVELING"   in f: return "TRAVELING"
    if "CARRY"       in f: return "CARRYING"
    if "GOALTENDING" in f: return "GOALTENDING"
    if "HELD" in f or "JUMP" in f: return "HELD BALL"
    return foul_type[:20]


def rule_status(foul_label: str) -> str:
    if foul_label in DEPRECATED_RULES:
        return "Deprecated"
    if foul_label in ACTIVE_RULES:
        return "Active"
    return "Unknown"


def pct(value) -> str:
    try:
        return f"{float(value) * 100:.0f}%"
    except Exception:
        return "—"


def bool_status(value) -> str:
    if value is None:
        return "—"
    return "YES" if bool(value) else "NO"


# ═════════════════════════════════════════════════════════════════════════
#  UI LAYOUT
# ═════════════════════════════════════════════════════════════════════════

st.markdown('<div class="page-title">🎥 Live Demo</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">ควบคุมระบบตรวจจับ Foul แบบ Real-time · ดู Foul Alert และ Replay Video</div>', unsafe_allow_html=True)

# ── Sync process state ────────────────────────────────────────────────────
if st.session_state.system_active and not is_process_running():
    st.session_state.system_active = False
    st.session_state.process       = None

# ── Top Row: Status + Controls ────────────────────────────────────────────
ctrl_col, status_col, cam_col = st.columns([2, 2, 3])

with status_col:
    if st.session_state.system_active:
        st.markdown("""
        <div class="status-active">
            <span class="dot-green"></span> SYSTEM ACTIVE
        </div>
        """, unsafe_allow_html=True)
        if st.session_state.session_start_time:
            elapsed = datetime.now() - st.session_state.session_start_time
            mins, secs = divmod(int(elapsed.total_seconds()), 60)
            st.caption(f"⏱ รันมา {mins:02d}:{secs:02d} นาที")
    else:
        st.markdown("""
        <div class="status-stopped">
            <span class="dot-gray"></span> SYSTEM STOPPED
        </div>
        """, unsafe_allow_html=True)
        st.caption("กด Start เพื่อเริ่มระบบ")

with cam_col:
    cam_options = {
        "📷 Built-in Camera (index 0)": 0,
        "📱 External / iPhone (index 1)": 1,
    }
    selected_cam_label = st.selectbox(
        "Camera Source",
        options=list(cam_options.keys()),
        index=0,
        disabled=st.session_state.system_active,
        label_visibility="collapsed",
    )
    st.session_state.camera_index = cam_options[selected_cam_label]

with ctrl_col:
    if not st.session_state.system_active:
        if st.button("▶  Start System", key="btn_start", use_container_width=True):
            start_system(st.session_state.camera_index)
            st.rerun()
    else:
        st.markdown('<div class="stop-btn">', unsafe_allow_html=True)
        if st.button("⏹  Stop System", key="btn_stop", use_container_width=True):
            stop_system()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

runtime_status = load_runtime_status()
st.markdown("### 🧪 Field Test Health")
health_cols = st.columns(6)
with health_cols[0]:
    st.metric("FPS", runtime_status.get("fps", "—"))
with health_cols[1]:
    st.metric("Players", runtime_status.get("players_tracked", "—"))
with health_cols[2]:
    st.metric("Ball", bool_status(runtime_status.get("ball_detected")))
with health_cols[3]:
    st.metric("Rim", bool_status(runtime_status.get("rim_detected")))
with health_cols[4]:
    st.metric("Hand Q", pct(runtime_status.get("avg_hand_score")))
with health_cols[5]:
    st.metric("Foot Q", pct(runtime_status.get("avg_foot_score")))

pose_cols = st.columns(4)
with pose_cols[0]:
    st.metric("Pose Q", pct(runtime_status.get("avg_pose_score")))
with pose_cols[1]:
    st.metric("Valid Pose", runtime_status.get("pose_players_valid", "—"))
with pose_cols[2]:
    st.metric("Low Vis", runtime_status.get("low_vis_players", "—"))
with pose_cols[3]:
    st.metric("Frame", runtime_status.get("frame_index", "—"))

last_updated = runtime_status.get("last_updated")
if last_updated:
    st.caption(
        f"Runtime status updated: {last_updated} · "
        f"Ball boxes: {runtime_status.get('ball_count', 0)} · "
        f"Rim boxes: {runtime_status.get('rim_count', 0)}"
    )
else:
    st.info("ยังไม่มี runtime status — กด Start System แล้วรอไม่กี่เฟรมเพื่อเริ่มดู Field Test Health")

st.markdown("---")

show_deprecated_logs = st.toggle(
    "Show deprecated legacy logs",
    value=False,
    help="เปิดเพื่อดู log เก่าจาก Push Foul / Illegal Hands ที่ถูกถอดออกจาก rule engine แล้ว",
)

# ── KPI Row (Session Stats) ───────────────────────────────────────────────
session_df = load_session_fouls()
total_log_df = load_recent_fouls(n=99999)
if not show_deprecated_logs:
    if not session_df.empty and "Rule_Status" in session_df.columns:
        session_df = session_df[session_df["Rule_Status"] == "Active"]
    if not total_log_df.empty and "Rule_Status" in total_log_df.columns:
        total_log_df = total_log_df[total_log_df["Rule_Status"] == "Active"]

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    session_count = len(session_df) if not session_df.empty else 0
    st.metric("🚨 Fouls This Session", session_count)

with kpi2:
    total_count = len(total_log_df) if not total_log_df.empty else 0
    st.metric("📋 Active Logged Fouls" if not show_deprecated_logs else "📋 Total Logged Fouls", total_count)

with kpi3:
    if not session_df.empty and "Foul_Type" in session_df.columns:
        top_foul_raw = session_df["Foul_Type"].value_counts().idxmax()
        top_foul = foul_short_name(top_foul_raw)
    else:
        top_foul = "—"
    st.metric("🔝 Top Foul (Session)", top_foul)

with kpi4:
    if not session_df.empty and "Player_ID" in session_df.columns:
        top_player = session_df["Player_ID"].value_counts().idxmax()
    else:
        top_player = "—"
    st.metric("👤 Most Fouled Player", top_player)

st.markdown("---")

# ── Two Column: Feed Left | Replay Right ─────────────────────────────────
feed_col, replay_col = st.columns([3, 2], gap="large")

# ── LEFT: Live Foul Alert Feed ────────────────────────────────────────────
with feed_col:
    feed_header_col, refresh_col = st.columns([4, 1])
    with feed_header_col:
        st.markdown("### 🚨 Live Foul Alert Feed")
    with refresh_col:
        if st.button("🔄", key="manual_refresh", help="Refresh feed"):
            st.rerun()

    recent_df = load_recent_fouls(n=25)
    if not show_deprecated_logs and not recent_df.empty and "Rule_Status" in recent_df.columns:
        recent_df = recent_df[recent_df["Rule_Status"] == "Active"]

    if recent_df.empty:
        st.markdown("""
        <div class="ui-card" style="text-align:center; padding:2.5rem; color:#8888AA;">
            <div style="font-size:2.5rem; margin-bottom:0.8rem;">🏀</div>
            <div>ยังไม่มีข้อมูล Foul<br>กด Start System และเล่นบาส!</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        with st.container(height=520):
            for _, row in recent_df.iterrows():
                try:
                    dt_str = row["Date_Time"].strftime("%H:%M:%S")
                except Exception:
                    dt_str = str(row["Date_Time"])[:8]

                foul_raw  = str(row.get("Foul_Type", "Unknown"))
                player_id = str(row.get("Player_ID", "?"))
                color      = get_foul_color(foul_raw)
                short_name = foul_short_name(foul_raw)

                st.markdown(f"""
                <div class="foul-row" style="border-left-color:{color};">
                    <span class="foul-time">{dt_str}</span>
                    <span class="foul-player">{player_id}</span>
                    <span class="foul-type">{short_name}</span>
                </div>
                """, unsafe_allow_html=True)

    # Auto-refresh every 2 seconds when system is active
    if st.session_state.system_active:
        time.sleep(2)
        st.rerun()

# ── RIGHT: Replay Videos ──────────────────────────────────────────────────
with replay_col:
    st.markdown("### 📼 Replay Videos")

    videos = get_replay_videos()
    event_df = load_foul_events()
    review_df = load_review_labels()

    if not videos:
        st.markdown("""
        <div class="ui-card" style="text-align:center; padding:2.5rem; color:#8888AA;">
            <div style="font-size:2.5rem; margin-bottom:0.8rem;">🎬</div>
            <div>ยังไม่มีวิดีโอ Replay<br>วิดีโอจะถูกบันทึกเมื่อเกิด Foul</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for video_path in videos:
            filename = video_path.stem  # e.g. foul_2026-03-24_15-32_PUSH-FOUL
            parts = filename.split("_")

            # Parse foul types from filename
            foul_labels = ""
            for part in parts:
                if any(k in part.upper() for k in ["PUSH", "ILLEGAL", "DOUBLE", "TRAVELING", "CARRY", "GOAL", "HELD", "JUMP"]):
                    foul_labels += f'<span class="foul-badge">{part.replace("-", " ")}</span>'

            # Date from filename
            date_part = ""
            for p in parts:
                if "-" in p and p[0].isdigit():
                    date_part = p[:10]
                    break

            mtime = datetime.fromtimestamp(os.path.getmtime(video_path))
            size_kb = video_path.stat().st_size // 1024

            st.markdown(f"""
            <div class="replay-card">
                <div class="replay-title">🎬 {mtime.strftime("%Y-%m-%d %H:%M:%S")}</div>
                <div style="margin-bottom:0.5rem;">{foul_labels if foul_labels else '<span class="foul-badge">FOUL</span>'}</div>
                <div style="color:#8888AA; font-size:0.92rem;">📁 {size_kb} KB</div>
            </div>
            """, unsafe_allow_html=True)

            with open(video_path, "rb") as vf:
                video_bytes = vf.read()
            st.video(video_bytes)

            video_abs = str(video_path.resolve())
            related_events = pd.DataFrame()
            if not event_df.empty and "Replay_Path" in event_df.columns:
                related_events = event_df[event_df["Replay_Path"].astype(str) == video_abs]

            if related_events.empty:
                st.caption("ยังไม่มี event id สำหรับ replay นี้ จึงยังไม่ใช้คำนวณ accuracy แบบเต็ม")
            else:
                with st.expander("QA Review", expanded=False):
                    for _, event in related_events.iterrows():
                        event_id = str(event["Event_ID"])
                        predicted = str(event["Foul_Type"])
                        existing = review_df[review_df["Event_ID"].astype(str) == event_id]
                        default_status = "Unreviewed"
                        default_label = foul_short_name(predicted)
                        default_note = ""
                        if not existing.empty:
                            latest = existing.iloc[-1]
                            default_status = str(latest.get("Review_Status", default_status))
                            default_label = str(latest.get("Human_Label", default_label))
                            default_note = str(latest.get("Reviewer_Note", ""))

                        st.caption(f"{event_id} · {event.get('Player_ID', '?')} · {foul_short_name(predicted)}")
                        status = st.selectbox(
                            "Review Status",
                            ["Unreviewed", "Correct", "False Positive", "Wrong Rule", "Unclear"],
                            index=["Unreviewed", "Correct", "False Positive", "Wrong Rule", "Unclear"].index(default_status)
                            if default_status in ["Unreviewed", "Correct", "False Positive", "Wrong Rule", "Unclear"] else 0,
                            key=f"status_{event_id}",
                        )
                        human_label = st.text_input(
                            "Human Label",
                            value=default_label,
                            key=f"human_label_{event_id}",
                        )
                        note = st.text_area(
                            "Reviewer Note",
                            value=default_note if default_note != "nan" else "",
                            height=70,
                            key=f"note_{event_id}",
                        )
                        if st.button("Save Review", key=f"save_review_{event_id}", use_container_width=True):
                            save_review_label(event_id, video_abs, predicted, status, human_label, note)
                            st.success("บันทึก review แล้ว")
                            st.rerun()

# ── Bottom: System Info Banner ────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div class="ui-card" style="display:flex; align-items:center; gap:2rem; flex-wrap:wrap; padding:1rem 1.5rem;">
    <div style="font-size:1.5rem;">💡</div>
    <div>
        <div style="font-weight:700; margin-bottom:0.2rem;">วิธีใช้งาน</div>
        <div style="color:#8888AA; font-size:0.98rem;">
            1. เลือก Camera Source → 2. กด <strong style="color:#FF6B00;">▶ Start System</strong> → 3. ระบบเปิดหน้าต่าง OpenCV → 4. เล่นบาสให้ AI ตรวจ → 5. Foul จะแสดงที่นี่ auto-refresh ทุก 2 วินาที
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
