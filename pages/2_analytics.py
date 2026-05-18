"""
pages/2_analytics.py — Full Analytics Dashboard
================================================
สถิติ Foul แบบครบ: KPI Cards, Charts, Table, Export
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime
import uuid

# ── Page Config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Analytics — AI Referee",
    page_icon="📊",
    layout="wide",
)

# ── CSS ───────────────────────────────────────────────────────────────────
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
[data-testid="stMetric"]{background:var(--bg-card)!important;border:1px solid var(--border)!important;border-radius:12px!important;padding:1.35rem 1.5rem!important;box-shadow:var(--shadow-sm)!important;transition:transform 0.2s ease,box-shadow 0.2s ease,border-color 0.2s ease!important;}
[data-testid="stMetric"]:hover{transform:translateY(-3px)!important;box-shadow:var(--shadow-md)!important;border-color:var(--border-accent)!important;}
[data-testid="stMetricLabel"]{color:var(--text-sub)!important;font-size:0.9rem!important;font-weight:700!important;text-transform:uppercase!important;letter-spacing:0.04em!important;}
[data-testid="stMetricValue"]{color:var(--primary)!important;font-size:2.25rem!important;font-weight:800!important;}
.stButton>button{background:linear-gradient(135deg,var(--primary) 0%,var(--primary-dark) 100%)!important;color:white!important;border:none!important;border-radius:8px!important;font-weight:700!important;padding:0.65rem 1.8rem!important;transition:all 0.25s ease!important;box-shadow:0 4px 14px rgba(249,115,22,0.35)!important;}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 8px 24px rgba(249,115,22,0.45)!important;}
.ui-card{background:var(--bg-card);border:1px solid var(--border);border-radius:16px;padding:1.4rem 1.6rem;margin-bottom:1rem;box-shadow:var(--shadow-sm);}
.page-title{font-family:'Outfit',sans-serif;font-size:2.55rem;font-weight:900;background:linear-gradient(135deg,#EA580C 0%,#F97316 60%,#FB923C 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:0.25rem;line-height:1.15;}
.page-subtitle{color:var(--text-sub);font-size:1.08rem;margin-bottom:1.7rem;}
hr{border-color:var(--border)!important;margin:1.4rem 0!important;}
.stSelectbox>div>div,.stMultiSelect>div>div{background:var(--bg-card)!important;border-color:var(--border)!important;border-radius:8px!important;color:var(--text-main)!important;}
.section-label{font-size:1.28rem;font-weight:750;color:var(--text-body);margin:1.6rem 0 0.95rem 0;}
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li,label{font-size:1rem!important;line-height:1.55!important;}
</style>
""", unsafe_allow_html=True)

# ── Plotly dark theme ─────────────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(248,250,252,0.8)",
    font=dict(family="Inter", color="#334155"),
    title_font=dict(family="Outfit", size=15, color="#0F172A"),
    legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#E2E8F0", borderwidth=1),
    margin=dict(l=10, r=10, t=40, b=10),
    xaxis=dict(gridcolor="#F1F5F9", linecolor="#E2E8F0", tickfont=dict(color="#64748B")),
    yaxis=dict(gridcolor="#F1F5F9", linecolor="#E2E8F0", tickfont=dict(color="#64748B")),
)

FOUL_COLORS = {
    "PUSH FOUL":      "#F97316",
    "ILLEGAL HANDS":  "#EF4444",
    "DOUBLE DRIBBLE": "#F59E0B",
    "TRAVELING":      "#8B5CF6",
    "CARRYING":       "#06B6D4",
    "GOALTENDING":    "#EC4899",
    "HELD BALL":      "#10B981",
}

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
            "Pipeline_Tag", "Hand_Refinement_Enabled",
        ])
    df = pd.read_csv(EVENT_FILE)
    for col in ["Pipeline_Tag", "Hand_Refinement_Enabled"]:
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


def pct_value(numerator: int, denominator: int):
    if denominator <= 0:
        return None
    return numerator / denominator * 100


def fmt_pct(value):
    return f"{value:.1f}%" if value is not None else "—"


def normalize_foul(foul_str: str) -> str:
    f = str(foul_str).upper()
    if "PUSH"        in f: return "PUSH FOUL"
    if "ILLEGAL"     in f: return "ILLEGAL HANDS"
    if "DOUBLE"      in f: return "DOUBLE DRIBBLE"
    if "TRAVELING"   in f: return "TRAVELING"
    if "CARRY"       in f: return "CARRYING"
    if "GOALTENDING" in f: return "GOALTENDING"
    if "HELD" in f or "JUMP" in f: return "HELD BALL"
    return foul_str[:30]


def rule_status(foul_label: str) -> str:
    if foul_label in DEPRECATED_RULES:
        return "Deprecated"
    if foul_label in ACTIVE_RULES:
        return "Active"
    return "Unknown"


# ═════════════════════════════════════════════════════════════════════════
#  UI LAYOUT
# ═════════════════════════════════════════════════════════════════════════

st.markdown('<div class="page-title">📊 Analytics Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">วิเคราะห์สถิติการทำฟาวล์จากระบบ AI Referee · อัปเดตทุก 5 วินาที</div>', unsafe_allow_html=True)

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
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
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
k1, k2, k3, k4 = st.columns(4)

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

st.markdown("---")

deprecated_count = int((df_raw["Rule_Status"] == "Deprecated").sum())
active_count = int((df_raw["Rule_Status"] == "Active").sum())
if deprecated_count:
    st.caption(
        f"Dashboard นี้กำลังใช้โหมด `{rule_scope}` · "
        f"Active logs: {active_count:,} · Deprecated legacy logs: {deprecated_count:,} "
        "(Push/Illegal Hands ถูกเก็บไว้เป็นประวัติ แต่ไม่รวมในค่าเริ่มต้น)"
    )

# ── QA / Review Accuracy ───────────────────────────────────────────────────
st.markdown('<div class="section-label">✅ QA Review Accuracy</div>', unsafe_allow_html=True)

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

q1, q2, q3, q4 = st.columns(4)
q1.metric("Events Logged", f"{len(qa_df):,}")
q2.metric("Reviewed Samples", f"{reviewed_total:,}")
q3.metric("TP / FP / FN", f"{tp_count:,} / {fp_count:,} / {fn_count:,}")
q4.metric("Accuracy", "—")

q5, q6, q7 = st.columns(3)
q5.metric("Precision", fmt_pct(precision))
q6.metric("Recall", fmt_pct(recall))
q7.metric("F1-score", fmt_pct(f1_score))

st.caption(
    "สูตรที่ใช้: Precision = TP/(TP+FP), Recall = TP/(TP+FN), "
    "F1 = 2PR/(P+R). `Wrong Rule` ถูกนับเป็น FP ของกฎที่ AI วิเคราะห์ผิด "
    "และเป็น FN ของกฎจริงตามหลัก multi-class evaluation. "
    "Accuracy ยังไม่คำนวณ เพราะระบบยังไม่มี TN จาก no-foul sample จริง"
)

if event_raw.empty and missed_df.empty:
    st.info("ยังไม่มี `logs/foul_events.csv` หรือ Missed Foul review จึงยังคำนวณ QA metrics ไม่ได้")
else:
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
    st.dataframe(per_rule, use_container_width=True, height=260)

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
        st.markdown("##### Before / After by Pipeline Tag")
        st.dataframe(pd.DataFrame(phase_rows), use_container_width=True, hide_index=True)

st.markdown("---")

# ── Row 1: Bar Chart + Pie Chart ──────────────────────────────────────────
chart_col1, chart_col2 = st.columns([3, 2], gap="large")

with chart_col1:
    st.markdown('<div class="section-label">📊 Fouls by Type</div>', unsafe_allow_html=True)

    foul_counts = df["Foul_Label"].value_counts().reset_index()
    foul_counts.columns = ["Foul Type", "Count"]
    color_seq = [FOUL_COLORS.get(ft, "#FF6B00") for ft in foul_counts["Foul Type"]]

    fig_bar = go.Figure(go.Bar(
        x=foul_counts["Foul Type"],
        y=foul_counts["Count"],
        marker=dict(
            color=color_seq,
            line=dict(color="rgba(255,255,255,0.1)", width=1),
        ),
        hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>",
        text=foul_counts["Count"],
        textposition="outside",
        textfont=dict(color="#F0F0F8", size=13),
    ))
    fig_bar.update_layout(**PLOTLY_LAYOUT, title="จำนวน Foul แต่ละประเภท")
    fig_bar.update_yaxes(title_text="จำนวนครั้ง")
    st.plotly_chart(fig_bar, use_container_width=True)

with chart_col2:
    st.markdown('<div class="section-label"> Foul Distribution</div>', unsafe_allow_html=True)

    fig_pie = go.Figure(go.Pie(
        labels=foul_counts["Foul Type"],
        values=foul_counts["Count"],
        marker=dict(colors=color_seq, line=dict(color="#0A0A0F", width=2)),
        hole=0.4,
        hovertemplate="<b>%{label}</b><br>%{value} ครั้ง (%{percent})<extra></extra>",
        textfont=dict(size=12),
    ))
    fig_pie.update_layout(
        **{**PLOTLY_LAYOUT, "showlegend": True},
        title="สัดส่วน Foul",
        annotations=[dict(text="Foul<br>Types", x=0.5, y=0.5, font_size=14, showarrow=False, font_color="#8888AA")],
    )
    st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")

# ── Row 2: Timeline Chart ─────────────────────────────────────────────────
st.markdown('<div class="section-label">📈 Foul Timeline</div>', unsafe_allow_html=True)

# Group by minute + foul label
df_time = df.copy()
df_time["Minute"] = df_time["Date_Time"].dt.floor("1min")
timeline = df_time.groupby(["Minute", "Foul_Label"]).size().reset_index(name="Count")

if not timeline.empty:
    fig_timeline = px.line(
        timeline,
        x="Minute",
        y="Count",
        color="Foul_Label",
        color_discrete_map=FOUL_COLORS,
        markers=True,
        labels={"Minute": "เวลา", "Count": "จำนวน Foul", "Foul_Label": "ประเภท"},
    )
    fig_timeline.update_traces(line=dict(width=2.5), marker=dict(size=7))
    fig_timeline.update_layout(**PLOTLY_LAYOUT, title="Foul ตามช่วงเวลา (ทุก 1 นาที)")
    st.plotly_chart(fig_timeline, use_container_width=True)

st.markdown("---")

# ── Row 3: Player Comparison + Hourly Heatmap ────────────────────────────
player_col, heat_col = st.columns([3, 2], gap="large")

with player_col:
    st.markdown('<div class="section-label">👥 Player Comparison</div>', unsafe_allow_html=True)

    player_foul = (
        df.groupby(["Player_ID", "Foul_Label"])
        .size()
        .reset_index(name="Count")
    )

    fig_player = px.bar(
        player_foul,
        x="Player_ID",
        y="Count",
        color="Foul_Label",
        color_discrete_map=FOUL_COLORS,
        barmode="stack",
        labels={"Player_ID": "Player", "Count": "จำนวน Foul", "Foul_Label": "ประเภท"},
        text_auto=True,
    )
    fig_player.update_layout(**PLOTLY_LAYOUT, title="Foul แยกตามผู้เล่น")
    fig_player.update_traces(textfont=dict(size=10), textposition="inside")
    st.plotly_chart(fig_player, use_container_width=True)

with heat_col:
    st.markdown('<div class="section-label">⏰ Fouls by Hour</div>', unsafe_allow_html=True)

    hourly = df.groupby("Hour").size().reset_index(name="Count")

    fig_hour = go.Figure(go.Bar(
        x=hourly["Hour"],
        y=hourly["Count"],
        marker=dict(
            color=hourly["Count"],
            colorscale=[[0, "#1A1A26"], [0.5, "#CC5500"], [1, "#FF6B00"]],
            showscale=False,
            line=dict(color="rgba(255,255,255,0.08)", width=1),
        ),
        hovertemplate="ชั่วโมง %{x}:00<br>%{y} Fouls<extra></extra>",
        text=hourly["Count"],
        textposition="outside",
        textfont=dict(color="#F0F0F8"),
    ))
    fig_hour.update_layout(**PLOTLY_LAYOUT, title="Foul แต่ละชั่วโมงของวัน")
    fig_hour.update_xaxes(title_text="ชั่วโมง (0-23)", tickmode="linear", dtick=2)
    fig_hour.update_yaxes(title_text="จำนวน Foul")
    st.plotly_chart(fig_hour, use_container_width=True)

st.markdown("---")

# ── Row 4: Log Table ──────────────────────────────────────────────────────
st.markdown('<div class="section-label">📋 Foul Log (Raw Data)</div>', unsafe_allow_html=True)

table_col, filter_col = st.columns([5, 1])
with filter_col:
    sort_by = st.selectbox("Sort by", ["Newest", "Oldest"], label_visibility="collapsed")

display_df = df[["Date_Time", "Player_ID", "Foul_Label", "Rule_Status", "Foul_Type"]].copy()
display_df.columns = ["Date & Time", "Player", "Foul Type", "Rule Status", "Raw Detail"]
display_df["Date & Time"] = display_df["Date & Time"].dt.strftime("%Y-%m-%d %H:%M:%S")

if sort_by == "Newest":
    display_df = display_df.sort_values("Date & Time", ascending=False)
else:
    display_df = display_df.sort_values("Date & Time", ascending=True)

st.dataframe(
    display_df.reset_index(drop=True),
    use_container_width=True,
    height=350,
    column_config={
        "Foul Type": st.column_config.TextColumn("Foul Type", width="medium"),
        "Rule Status": st.column_config.TextColumn("Rule Status", width="small"),
        "Raw Detail": st.column_config.TextColumn("Detail", width="large"),
    },
)

st.caption(f"แสดง {len(display_df):,} รายการ (filtered จาก {len(df_raw):,} รายการทั้งหมด)")
