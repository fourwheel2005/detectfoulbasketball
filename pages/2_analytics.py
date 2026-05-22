"""
pages/2_analytics.py — Analytics Summary
========================================
สรุป KPI และ QA metrics สำหรับระบบตรวจจับฟาวล์
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import uuid

from ui_theme import (
    inject_global_css,
    render_page_header,
    render_section_label,
    render_footer,
    normalize_foul,
    rule_status,
    pct_value,
    fmt_pct,
    ACTIVE_RULES,
    DEPRECATED_RULES,
)

# ── Page Config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Analytics — AI Referee",
    page_icon="📊",
    layout="wide",
)

# ── Apply Global Theme ──────────────────────────────────────────────────
inject_global_css()

# ── Data Loading ──────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
LOG_FILE     = PROJECT_ROOT / "basketball_foul_logs.csv"
EVENT_FILE   = PROJECT_ROOT / "logs" / "foul_events.csv"
REVIEW_FILE  = PROJECT_ROOT / "logs" / "review_labels.csv"


@st.cache_data(ttl=5)
def load_data():
    if not LOG_FILE.exists():
        return pd.DataFrame(columns=["Date_Time", "Player_ID", "Foul_Type"])
    df = pd.read_csv(LOG_FILE)
    df["Date_Time"] = pd.to_datetime(df["Date_Time"])
    df["Date"]      = df["Date_Time"].dt.date
    df["Hour"]      = df["Date_Time"].dt.hour
    # Normalize Foul_Type to short labels
    df["Foul_Label"] = df["Foul_Type"].apply(normalize_foul)
    df["Rule_Status"] = df["Foul_Label"].apply(rule_status)
    return df


@st.cache_data(ttl=5)
def load_event_data():
    if not EVENT_FILE.exists():
        return pd.DataFrame(columns=[
            "Event_ID", "Date_Time", "Session_ID", "Frame_Index",
            "Player_ID", "Foul_Type", "Replay_Path", "Camera_ID",
            "Pipeline_Tag", "Hand_Refinement_Enabled", "Confidence",
            "Rule_Reason", "Pose_Score", "Hand_Score", "Foot_Score",
            "Ball_Velocity", "Rim_Reliable",
        ])
    df = pd.read_csv(EVENT_FILE)
    for col in [
        "Pipeline_Tag", "Hand_Refinement_Enabled", "Confidence",
        "Rule_Reason", "Pose_Score", "Hand_Score", "Foot_Score",
        "Ball_Velocity", "Rim_Reliable",
    ]:
        if col not in df.columns:
            df[col] = ""
    if "Date_Time" in df.columns:
        df["Date_Time"] = pd.to_datetime(df["Date_Time"], errors="coerce")
    if "Foul_Type" in df.columns:
        df["Foul_Label"] = df["Foul_Type"].apply(normalize_foul)
        df["Rule_Status"] = df["Foul_Label"].apply(rule_status)
    return df


@st.cache_data(ttl=5)
def load_review_data():
    if not REVIEW_FILE.exists():
        return pd.DataFrame(columns=[
            "Event_ID", "Replay_Path", "Predicted_Rule", "Review_Status",
            "Human_Label", "Reviewer_Note", "Reviewed_At", "Pipeline_Tag",
        ])
    df = pd.read_csv(REVIEW_FILE)
    if "Pipeline_Tag" not in df.columns:
        df["Pipeline_Tag"] = ""
    return df


def save_missed_foul(human_label: str, pipeline_tag: str, note: str = ""):
    REVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "Event_ID", "Replay_Path", "Predicted_Rule", "Review_Status",
        "Human_Label", "Reviewer_Note", "Reviewed_At", "Pipeline_Tag",
    ]
    reviews = load_review_data()
    for col in columns:
        if col not in reviews.columns:
            reviews[col] = ""

    row = {
        "Event_ID": f"missed_{uuid.uuid4().hex[:12]}",
        "Replay_Path": "",
        "Predicted_Rule": "",
        "Review_Status": "Missed Foul",
        "Human_Label": human_label,
        "Reviewer_Note": note,
        "Reviewed_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Pipeline_Tag": pipeline_tag,
    }
    updated = pd.concat([reviews[columns], pd.DataFrame([row])], ignore_index=True)
    updated.to_csv(REVIEW_FILE, index=False)
    load_review_data.clear()


# ═════════════════════════════════════════════════════════════════════════
#  UI LAYOUT
# ═════════════════════════════════════════════════════════════════════════

render_page_header(
    "📊 Analytics Summary",
    "วิเคราะห์สถิติการทำฟาวล์จากระบบ AI Referee · อัปเดตทุก 5 วินาที",
)

# ── Load Data ─────────────────────────────────────────────────────────────
df_raw = load_data()
event_raw = load_event_data()
review_raw = load_review_data()

if df_raw.empty:
    st.warning("⚠️ ยังไม่พบข้อมูล Foul ใน `basketball_foul_logs.csv` — กรุณารันระบบเพื่อเก็บข้อมูลก่อน")
    st.stop()

# ── Sidebar Filters ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Filters")

    all_fouls   = sorted(df_raw["Foul_Label"].unique().tolist())
    active_fouls = [f for f in ACTIVE_RULES if f in all_fouls]
    deprecated_fouls = [f for f in DEPRECATED_RULES if f in all_fouls]
    all_players = sorted(df_raw["Player_ID"].unique().tolist(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0))
    all_dates   = sorted(df_raw["Date"].unique().tolist())

    rule_scope = st.radio(
        "Rule Scope",
        options=["Current active rules", "All historical logs", "Deprecated only"],
        index=0,
        help="Current active rules จะซ่อน Push/Illegal Hands จากระบบเก่าโดยไม่แก้ CSV ต้นฉบับ",
    )

    if rule_scope == "Current active rules":
        foul_options = active_fouls
        default_fouls = active_fouls
    elif rule_scope == "Deprecated only":
        foul_options = deprecated_fouls
        default_fouls = deprecated_fouls
    else:
        foul_options = all_fouls
        default_fouls = all_fouls

    selected_fouls = st.multiselect(
        "Foul Type",
        options=foul_options,
        default=default_fouls,
    )
    selected_players = st.multiselect(
        "Player ID",
        options=all_players,
        default=all_players,
    )

    if len(all_dates) > 1:
        date_range = st.date_input(
            "Date Range",
            value=(all_dates[0], all_dates[-1]),
            min_value=all_dates[0],
            max_value=all_dates[-1],
        )
    else:
        date_range = (all_dates[0], all_dates[-1])

    st.markdown("---")
    csv_data = df_raw.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Export CSV",
        data=csv_data,
        file_name=f"foul_log_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ── Apply Filters ─────────────────────────────────────────────────────────
df = df_raw.copy()
if rule_scope == "Current active rules":
    df = df[df["Rule_Status"] == "Active"]
elif rule_scope == "Deprecated only":
    df = df[df["Rule_Status"] == "Deprecated"]
if selected_fouls:
    df = df[df["Foul_Label"].isin(selected_fouls)]
if selected_players:
    df = df[df["Player_ID"].isin(selected_players)]
try:
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        df = df[(df["Date"] >= date_range[0]) & (df["Date"] <= date_range[1])]
except Exception:
    pass

if df.empty:
    st.warning("ไม่พบข้อมูลที่ตรงกับ Filter ที่เลือก")
    if rule_scope == "Current active rules":
        st.info("ถ้ายังเห็นค่านี้ แปลว่ายังไม่มี log จากกฎ active รุ่นใหม่ หรือยังไม่ได้รันระบบหลังอัปเดตล่าสุด")
    st.stop()

# ── KPI Cards ─────────────────────────────────────────────────────────────
render_section_label("📈", "Overview Metrics")

k1, k2, k3, k4 = st.columns(4, gap="medium")

with k1:
    st.metric("🚨 Total Fouls", f"{len(df):,}")
with k2:
    top_type = df["Foul_Label"].value_counts().idxmax()
    top_type_count = df["Foul_Label"].value_counts().max()
    st.metric("🏆 Most Common Foul", top_type, delta=f"{top_type_count} ครั้ง")
with k3:
    top_player = df["Player_ID"].value_counts().idxmax()
    top_player_count = df["Player_ID"].value_counts().max()
    st.metric("👤 Most Fouled Player", top_player, delta=f"{top_player_count} ครั้ง")
with k4:
    unique_players = df["Player_ID"].nunique()
    st.metric("🧑‍🤝‍🧑 Players Detected", unique_players)

deprecated_count = int((df_raw["Rule_Status"] == "Deprecated").sum())
active_count = int((df_raw["Rule_Status"] == "Active").sum())
if deprecated_count:
    st.caption(
        f"Dashboard นี้กำลังใช้โหมด `{rule_scope}` · "
        f"Active logs: {active_count:,} · Deprecated legacy logs: {deprecated_count:,} "
        "(Push/Illegal Hands ถูกเก็บไว้เป็นประวัติ แต่ไม่รวมในค่าเริ่มต้น)"
    )

st.markdown("---")

# ── QA / Review Accuracy ───────────────────────────────────────────────────
render_section_label("✅", "QA Review Accuracy")

with st.expander("➕ บันทึก Missed Foul (FN)", expanded=False):
    st.caption(
        "ใช้เมื่อดูคลิปหรือระหว่างเทสแล้วพบว่าเกิด foul จริง แต่ AI ไม่สร้าง event/replay "
        "รายการนี้จะถูกนับเป็น FN เพื่อคำนวณ Recall และ F1-score"
    )
    missed_rule = st.selectbox(
        "Actual Foul Type",
        options=ACTIVE_RULES,
        key="qa_missed_rule",
    )
    pipeline_options = sorted(
        set(event_raw.get("Pipeline_Tag", pd.Series(dtype=str)).fillna("").replace("", "legacy").tolist())
        | {"baseline", "hand_refinement_v1"}
    )
    missed_pipeline = st.selectbox(
        "Pipeline Tag",
        options=pipeline_options,
        index=pipeline_options.index("hand_refinement_v1") if "hand_refinement_v1" in pipeline_options else 0,
        help="ต้องระบุ phase เพื่อให้ FN ถูกนำไปเทียบ baseline vs hand refinement ได้ถูกต้อง",
        key="qa_missed_pipeline",
    )
    missed_note = st.text_area(
        "Note",
        placeholder="เช่น นาทีที่เกิดเหตุ, สถานการณ์, หรือเหตุผลที่ AI วิเคราะห์พลาด",
        key="qa_missed_note",
    )
    if st.button("Save Missed Foul", use_container_width=True):
        save_missed_foul(missed_rule, missed_pipeline, missed_note.strip())
        st.success("บันทึก Missed Foul แล้ว")
        st.rerun()

qa_df = event_raw.copy()
if "Foul_Label" not in qa_df.columns and "Foul_Type" in qa_df.columns:
    qa_df["Foul_Label"] = qa_df["Foul_Type"].apply(normalize_foul)

missed_df = pd.DataFrame(columns=review_raw.columns)
if not review_raw.empty and "Review_Status" in review_raw.columns:
    missed_df = review_raw[review_raw["Review_Status"] == "Missed Foul"].copy()

if not qa_df.empty and not review_raw.empty:
    event_reviews = review_raw[review_raw["Review_Status"] != "Missed Foul"].copy()
    latest_reviews = (
        event_reviews.drop_duplicates(subset=["Event_ID"], keep="last")
        if "Event_ID" in event_reviews.columns else event_reviews
    )
    if not latest_reviews.empty:
        qa_df = qa_df.merge(
            latest_reviews[["Event_ID", "Review_Status", "Human_Label"]],
            on="Event_ID",
            how="left",
        )
    else:
        qa_df["Review_Status"] = "Unreviewed"
        qa_df["Human_Label"] = ""
elif not qa_df.empty:
    qa_df["Review_Status"] = "Unreviewed"
    qa_df["Human_Label"] = ""

if not qa_df.empty:
    qa_df["Review_Status"] = qa_df["Review_Status"].fillna("Unreviewed")
    qa_df["Human_Label"] = qa_df["Human_Label"].fillna("")
    qa_df["Pipeline_Tag"] = qa_df.get("Pipeline_Tag", "").fillna("").replace("", "legacy")
if not missed_df.empty:
    missed_df["Pipeline_Tag"] = missed_df.get("Pipeline_Tag", "").fillna("").replace("", "legacy")

reviewed_df = (
    qa_df[qa_df["Review_Status"] != "Unreviewed"]
    if not qa_df.empty and "Review_Status" in qa_df.columns
    else pd.DataFrame()
)
scored_df = (
    qa_df[qa_df["Review_Status"].isin(["Correct", "False Positive", "Wrong Rule"])]
    if not qa_df.empty and "Review_Status" in qa_df.columns
    else pd.DataFrame()
)

tp_count = int((scored_df["Review_Status"] == "Correct").sum()) if not scored_df.empty else 0
fp_count = int(scored_df["Review_Status"].isin(["False Positive", "Wrong Rule"]).sum()) if not scored_df.empty else 0
wrong_rule_fn_count = int((scored_df["Review_Status"] == "Wrong Rule").sum()) if not scored_df.empty else 0
fn_count = int(len(missed_df) + wrong_rule_fn_count)
reviewed_total = int(len(reviewed_df) + len(missed_df))

precision = pct_value(tp_count, tp_count + fp_count)
recall = pct_value(tp_count, tp_count + fn_count)
if precision is not None and recall is not None and (precision + recall) > 0:
    f1_score = 2 * precision * recall / (precision + recall)
else:
    f1_score = None

# ── QA Metric Cards ──────────────────────────────────────────────────────
with st.container():
    q1, q2, q3, q4 = st.columns(4, gap="medium")
    q1.metric("Events Logged", f"{len(qa_df):,}")
    q2.metric("Reviewed Samples", f"{reviewed_total:,}")
    q3.metric("TP / FP / FN", f"{tp_count:,} / {fp_count:,} / {fn_count:,}")
    q4.metric("Accuracy", "—")

    q5, q6, q7 = st.columns(3, gap="medium")
    q5.metric("Precision", fmt_pct(precision))
    q6.metric("Recall", fmt_pct(recall))
    q7.metric("F1-score", fmt_pct(f1_score))

st.caption(
    "สูตรที่ใช้: Precision = TP/(TP+FP), Recall = TP/(TP+FN), "
    "F1 = 2PR/(P+R). `Wrong Rule` ถูกนับเป็น FP ของกฎที่ AI วิเคราะห์ผิด "
    "และเป็น FN ของกฎจริงตามหลัก multi-class evaluation. "
    "Accuracy ยังไม่คำนวณ เพราะระบบยังไม่มี TN จาก no-foul sample จริง"
)

st.markdown("---")

# ── Per-rule Breakdown ────────────────────────────────────────────────────
if event_raw.empty and missed_df.empty:
    st.info("ยังไม่มี `logs/foul_events.csv` หรือ Missed Foul review จึงยังคำนวณ QA metrics ไม่ได้")
else:
    render_section_label("📋", "Per-rule Breakdown")

    rule_rows = []
    labels = sorted(set(ACTIVE_RULES) | set(qa_df.get("Foul_Label", pd.Series(dtype=str)).dropna().tolist()))
    for label in labels:
        rule_events = qa_df[qa_df["Foul_Label"] == label] if not qa_df.empty and "Foul_Label" in qa_df.columns else pd.DataFrame()
        rule_scored = rule_events[rule_events["Review_Status"].isin(["Correct", "False Positive", "Wrong Rule"])] if not rule_events.empty else pd.DataFrame()
        rule_tp = int((rule_scored["Review_Status"] == "Correct").sum()) if not rule_scored.empty else 0
        rule_fp = int(rule_scored["Review_Status"].isin(["False Positive", "Wrong Rule"]).sum()) if not rule_scored.empty else 0

        wrong_rule_fn = 0
        if not scored_df.empty and "Human_Label" in scored_df.columns:
            human_labels = scored_df["Human_Label"].fillna("").apply(normalize_foul)
            wrong_rule_fn = int(((scored_df["Review_Status"] == "Wrong Rule") & (human_labels == label)).sum())
        missed_rule_fn = 0
        if not missed_df.empty and "Human_Label" in missed_df.columns:
            missed_labels = missed_df["Human_Label"].fillna("").apply(normalize_foul)
            missed_rule_fn = int((missed_labels == label).sum())
        rule_fn = wrong_rule_fn + missed_rule_fn

        rule_precision = pct_value(rule_tp, rule_tp + rule_fp)
        rule_recall = pct_value(rule_tp, rule_tp + rule_fn)
        if rule_precision is not None and rule_recall is not None and (rule_precision + rule_recall) > 0:
            rule_f1 = 2 * rule_precision * rule_recall / (rule_precision + rule_recall)
        else:
            rule_f1 = None

        rule_rows.append({
            "Foul_Label": label,
            "Events": int(len(rule_events)),
            "Reviewed": int((rule_events["Review_Status"] != "Unreviewed").sum()) if not rule_events.empty else 0,
            "TP": rule_tp,
            "FP": rule_fp,
            "FN": rule_fn,
            "Precision_%": round(rule_precision, 1) if rule_precision is not None else None,
            "Recall_%": round(rule_recall, 1) if rule_recall is not None else None,
            "F1_%": round(rule_f1, 1) if rule_f1 is not None else None,
        })

    per_rule = pd.DataFrame(rule_rows)
    st.dataframe(per_rule, use_container_width=True, height=280, hide_index=True)

    # ── Pipeline Tag Comparison ──────────────────────────────────────────
    phase_rows = []
    phase_labels = sorted(set(qa_df.get("Pipeline_Tag", pd.Series(dtype=str)).dropna().tolist()))
    for phase in phase_labels:
        phase_scored = scored_df[scored_df["Pipeline_Tag"] == phase] if not scored_df.empty else pd.DataFrame()
        phase_missed = missed_df[missed_df["Pipeline_Tag"] == phase] if not missed_df.empty else pd.DataFrame()
        phase_tp = int((phase_scored["Review_Status"] == "Correct").sum()) if not phase_scored.empty else 0
        phase_fp = int(phase_scored["Review_Status"].isin(["False Positive", "Wrong Rule"]).sum()) if not phase_scored.empty else 0
        phase_fn = int((phase_scored["Review_Status"] == "Wrong Rule").sum()) if not phase_scored.empty else 0
        phase_fn += int(len(phase_missed))
        phase_precision = pct_value(phase_tp, phase_tp + phase_fp)
        phase_recall = pct_value(phase_tp, phase_tp + phase_fn)
        if phase_precision is not None and phase_recall is not None and (phase_precision + phase_recall) > 0:
            phase_f1 = 2 * phase_precision * phase_recall / (phase_precision + phase_recall)
        else:
            phase_f1 = None
        phase_rows.append({
            "Pipeline_Tag": phase,
            "TP": phase_tp,
            "FP": phase_fp,
            "FN": phase_fn,
            "Precision_%": round(phase_precision, 1) if phase_precision is not None else None,
            "Recall_%": round(phase_recall, 1) if phase_recall is not None else None,
            "F1_%": round(phase_f1, 1) if phase_f1 is not None else None,
        })
    if phase_rows:
        st.markdown("")
        render_section_label("🔄", "Before / After by Pipeline Tag")
        st.dataframe(pd.DataFrame(phase_rows), use_container_width=True, hide_index=True)

# ── Footer ────────────────────────────────────────────────────────────────
render_footer()
