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

from ui_theme import (
    inject_global_css,
    render_page_header,
    render_section_label,
    render_empty_state,
    render_footer,
    normalize_foul,
    foul_short_name,
    rule_status,
    get_foul_color,
    pct,
    bool_status,
    ACTIVE_RULES,
    ACTIVE_RULES_SET,
    DEPRECATED_RULES_SET,
    REVIEW_COLUMNS,
)

# ── Page Config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Live Demo — AI Referee",
    page_icon="🎥",
    layout="wide",
)

# ── Apply Global Theme ──────────────────────────────────────────────────
inject_global_css()

# ── Project Root ─────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
LOG_FILE     = PROJECT_ROOT / "basketball_foul_logs.csv"
EVENT_FILE   = PROJECT_ROOT / "logs" / "foul_events.csv"
REVIEW_FILE  = PROJECT_ROOT / "logs" / "review_labels.csv"
RUNTIME_STATUS_FILE = PROJECT_ROOT / "logs" / "runtime_status.json"
REPLAY_DIR   = PROJECT_ROOT / "logs" / "replays"
MAIN_PY      = PROJECT_ROOT / "main.py"

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
    columns = [
        "Event_ID", "Date_Time", "Session_ID", "Frame_Index",
        "Player_ID", "Foul_Type", "Replay_Path", "Camera_ID",
        "Pipeline_Tag", "Hand_Refinement_Enabled", "Confidence",
        "Rule_Reason", "Pose_Score", "Hand_Score", "Foot_Score",
        "Ball_Velocity", "Rim_Reliable",
    ]
    if not EVENT_FILE.exists():
        return pd.DataFrame(columns=columns)
    try:
        df = pd.read_csv(EVENT_FILE)
        for col in columns:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception:
        return pd.DataFrame(columns=columns)


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


def get_replay_videos():
    """ดึงรายการไฟล์วิดีโอ Replay"""
    if not REPLAY_DIR.exists():
        return []
    videos = sorted(REPLAY_DIR.glob("*.mp4"), key=os.path.getmtime, reverse=True)
    return videos[:10]  # แสดง 10 ล่าสุด


# ═════════════════════════════════════════════════════════════════════════
#  UI LAYOUT
# ═════════════════════════════════════════════════════════════════════════

render_page_header(
    "🎥 Live Demo",
    "ควบคุมระบบตรวจจับ Foul แบบ Real-time · ดู Foul Alert และ Replay Video",
)

# ── Sync process state ────────────────────────────────────────────────────
if st.session_state.system_active and not is_process_running():
    st.session_state.system_active = False
    st.session_state.process       = None

# ── Top Row: Controls + Status + Camera ───────────────────────────────────
ctrl_col, status_col, cam_col = st.columns([2, 2, 3], gap="medium")

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

st.markdown("---")

# ── Field Test Health ─────────────────────────────────────────────────────
runtime_status = load_runtime_status()
render_section_label("🧪", "Field Test Health")

with st.container():
    row1_cols = st.columns(4, gap="medium")
    with row1_cols[0]:
        st.metric("FPS", runtime_status.get("fps", "—"))
    with row1_cols[1]:
        st.metric("Players Tracked", runtime_status.get("players_tracked", "—"))
    with row1_cols[2]:
        st.metric("Ball Detected", bool_status(runtime_status.get("ball_detected")))
    with row1_cols[3]:
        st.metric("Rim Detected", bool_status(runtime_status.get("rim_detected")))

    row2_cols = st.columns(4, gap="medium")
    with row2_cols[0]:
        st.metric("Pose Quality", pct(runtime_status.get("avg_pose_score")))
    with row2_cols[1]:
        st.metric("Hand Quality", pct(runtime_status.get("avg_hand_score")))
    with row2_cols[2]:
        st.metric("Foot Quality", pct(runtime_status.get("avg_foot_score")))
    with row2_cols[3]:
        st.metric("Frame Index", runtime_status.get("frame_index", "—"))

    last_updated = runtime_status.get("last_updated")
    if last_updated:
        st.caption(
            f"Runtime status updated: {last_updated} · "
            f"Pose valid: {runtime_status.get('pose_players_valid', '—')} · "
            f"Low vis: {runtime_status.get('low_vis_players', '—')} · "
            f"Ball boxes: {runtime_status.get('ball_count', 0)} · "
            f"Rim boxes: {runtime_status.get('rim_count', 0)}"
        )
    else:
        st.info("ยังไม่มี runtime status — กด Start System แล้วรอไม่กี่เฟรมเพื่อเริ่มดู Field Test Health")

st.markdown("---")

# ── Toggle deprecated logs ────────────────────────────────────────────────
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

kpi1, kpi2, kpi3, kpi4 = st.columns(4, gap="medium")

with kpi1:
    session_count = len(session_df) if not session_df.empty else 0
    st.metric("🚨 Fouls This Session", session_count)

with kpi2:
    total_count = len(total_log_df) if not total_log_df.empty else 0
    label = "📋 Active Logged Fouls" if not show_deprecated_logs else "📋 Total Logged Fouls"
    st.metric(label, total_count)

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
        render_section_label("🚨", "Live Foul Alert Feed")
    with refresh_col:
        if st.button("🔄", key="manual_refresh", help="Refresh feed"):
            st.rerun()

    recent_df = load_recent_fouls(n=25)
    if not show_deprecated_logs and not recent_df.empty and "Rule_Status" in recent_df.columns:
        recent_df = recent_df[recent_df["Rule_Status"] == "Active"]

    if recent_df.empty:
        render_empty_state("🏀", "ยังไม่มีข้อมูล Foul<br>กด Start System และเล่นบาส!")
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
    render_section_label("📼", "Replay Videos")

    videos = get_replay_videos()
    event_df = load_foul_events()
    review_df = load_review_labels()

    if not videos:
        render_empty_state("🎬", "ยังไม่มีวิดีโอ Replay<br>วิดีโอจะถูกบันทึกเมื่อเกิด Foul")
    else:
        for video_path in videos:
            filename = video_path.stem
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
                <div style="color:#94A3B8; font-size:0.92rem;">📁 {size_kb} KB</div>
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

                        conf = event.get("Confidence", "")
                        reason = event.get("Rule_Reason", "")
                        conf_text = ""
                        try:
                            if str(conf).strip() not in ("", "nan"):
                                conf_text = f" · conf {float(conf) * 100:.0f}%"
                        except (TypeError, ValueError):
                            conf_text = ""
                        st.caption(f"{event_id} · {event.get('Player_ID', '?')} · {foul_short_name(predicted)}{conf_text}")
                        if str(reason).strip() not in ("", "nan"):
                            st.caption(f"Reason: {str(reason)[:160]}")
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
