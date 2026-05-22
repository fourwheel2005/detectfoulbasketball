"""
pages/4_qa_review.py — Replay QA Review Queue
==============================================
Human review page for foul replay videos with pagination.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="QA Review — AI Referee",
    page_icon="✅",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Outfit:wght@400;600;700;800;900&display=swap');
:root {
    --primary:#F97316; --primary-dark:#EA580C; --accent:#FB923C;
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

.main .block-container{padding:2.2rem 2.7rem 3.2rem 2.7rem;max-width:1520px;}
[data-testid="stMetric"]{background:var(--bg-card)!important;border:1px solid var(--border)!important;border-radius:12px!important;padding:1.35rem 1.5rem!important;box-shadow:var(--shadow-sm)!important;}
[data-testid="stMetricLabel"]{color:var(--text-sub)!important;font-size:0.9rem!important;font-weight:700!important;text-transform:uppercase!important;letter-spacing:0.04em!important;}
[data-testid="stMetricValue"]{color:var(--primary)!important;font-size:2.25rem!important;font-weight:800!important;}
.stButton>button{background:linear-gradient(135deg,var(--primary) 0%,var(--primary-dark) 100%)!important;color:white!important;border:none!important;border-radius:8px!important;font-weight:700!important;font-size:1rem!important;padding:0.68rem 1.25rem!important;transition:all 0.25s ease!important;box-shadow:0 4px 14px rgba(249,115,22,0.3)!important;}
.stButton>button:hover{transform:translateY(-1px)!important;box-shadow:0 8px 24px rgba(249,115,22,0.42)!important;}
.page-title{font-family:'Outfit',sans-serif;font-size:2.55rem;font-weight:900;background:linear-gradient(135deg,#EA580C 0%,#F97316 60%,#FB923C 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:0.25rem;line-height:1.15;}
.page-subtitle{color:var(--text-sub);font-size:1.08rem;margin-bottom:1.7rem;}
.qa-card{background:var(--bg-card);border:1px solid var(--border);border-radius:14px;padding:1.35rem 1.5rem;margin-bottom:1.3rem;box-shadow:var(--shadow-sm);transition:box-shadow 0.2s;}
.qa-card:hover{box-shadow:var(--shadow-md);}
.qa-title{font-weight:800;color:var(--primary-dark);font-size:1.14rem;margin-bottom:0.4rem;}
.qa-meta{color:var(--text-sub);font-size:0.95rem;margin-bottom:0.8rem;line-height:1.5;}
.foul-badge{display:inline-block;background:#FFF7ED;color:var(--primary);border:1.5px solid #FED7AA;border-radius:6px;padding:4px 10px;font-size:0.9rem;font-weight:800;margin-right:5px;margin-bottom:5px;}
.status-pill{display:inline-block;border-radius:999px;padding:4px 11px;font-size:0.88rem;font-weight:800;}
.status-unreviewed{background:#F1F5F9;color:#64748B;border:1px solid #CBD5E1;}
.status-correct{background:#ECFDF5;color:#059669;border:1px solid #A7F3D0;}
.status-false-positive{background:#FEF2F2;color:#DC2626;border:1px solid #FECACA;}
.status-wrong-rule{background:#FFFBEB;color:#D97706;border:1px solid #FDE68A;}
.status-unclear{background:#F5F3FF;color:#7C3AED;border:1px solid #DDD6FE;}
.missing-video{background:#FEF2F2;border:1px solid #FECACA;border-radius:10px;padding:1rem;color:#DC2626;text-align:center;}
hr{border-color:var(--border)!important;margin:1.4rem 0!important;}
.stSelectbox>div>div,.stMultiSelect>div>div,.stTextInput>div>div,.stTextArea>div>div,.stNumberInput>div>div{background:var(--bg-card)!important;border-color:var(--border)!important;border-radius:8px!important;color:var(--text-main)!important;}
.stProgress>div>div>div{background:linear-gradient(90deg,var(--primary),var(--accent))!important;border-radius:99px!important;}
[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li,label{font-size:1rem!important;line-height:1.55!important;}
</style>
""", unsafe_allow_html=True)


PROJECT_ROOT = Path(__file__).parent.parent
EVENT_FILE = PROJECT_ROOT / "logs" / "foul_events.csv"
REVIEW_FILE = PROJECT_ROOT / "logs" / "review_labels.csv"

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
ACTIVE_RULES = ["DOUBLE DRIBBLE", "TRAVELING", "CARRYING", "GOALTENDING", "HELD BALL"]
HUMAN_LABEL_OPTIONS = ["NO FOUL", *ACTIVE_RULES, "UNCLEAR"]
DEPRECATED_RULES = ["PUSH FOUL", "ILLEGAL HANDS"]


def normalize_foul(foul_str: str) -> str:
    f = str(foul_str).upper()
    if "PUSH" in f:
        return "PUSH FOUL"
    if "ILLEGAL" in f:
        return "ILLEGAL HANDS"
    if "DOUBLE" in f:
        return "DOUBLE DRIBBLE"
    if "TRAVELING" in f:
        return "TRAVELING"
    if "CARRY" in f:
        return "CARRYING"
    if "GOALTENDING" in f or "GOAL" in f:
        return "GOALTENDING"
    if "HELD" in f or "JUMP" in f:
        return "HELD BALL"
    return str(foul_str)[:30]


def status_class(status: str) -> str:
    return str(status).lower().replace(" ", "-")


@st.cache_data(ttl=5)
def load_events() -> pd.DataFrame:
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
        "Event_ID", "Player_ID", "Foul_Type", "Replay_Path", "Camera_ID",
        "Pipeline_Tag", "Hand_Refinement_Enabled", "Confidence",
        "Rule_Reason", "Pose_Score", "Hand_Score", "Foot_Score",
        "Ball_Velocity", "Rim_Reliable",
    ]:
        if col not in df.columns:
            df[col] = ""
    df["Date_Time"] = pd.to_datetime(df.get("Date_Time"), errors="coerce")
    df["Foul_Label"] = df["Foul_Type"].apply(normalize_foul)
    df["Replay_Exists"] = df["Replay_Path"].apply(lambda p: Path(str(p)).exists())
    df["File_Size_KB"] = df["Replay_Path"].apply(
        lambda p: int(Path(str(p)).stat().st_size / 1024) if Path(str(p)).exists() else 0
    )
    return df


@st.cache_data(ttl=5)
def load_reviews() -> pd.DataFrame:
    if not REVIEW_FILE.exists():
        return pd.DataFrame(columns=REVIEW_COLUMNS)
    df = pd.read_csv(REVIEW_FILE)
    for col in REVIEW_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[REVIEW_COLUMNS]


def save_review(event_id: str, replay_path: str, predicted_rule: str, status: str, human_label: str, note: str):
    REVIEW_FILE.parent.mkdir(parents=True, exist_ok=True)
    reviews = load_reviews()
    reviews = reviews[reviews["Event_ID"].astype(str) != str(event_id)]
    row = {
        "Event_ID": event_id,
        "Replay_Path": replay_path,
        "Predicted_Rule": predicted_rule,
        "Review_Status": status,
        "Human_Label": human_label,
        "Reviewer_Note": note,
        "Reviewed_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    updated = pd.concat([reviews, pd.DataFrame([row])], ignore_index=True)
    updated.to_csv(REVIEW_FILE, index=False)
    load_reviews.clear()


def build_review_queue(events: pd.DataFrame, reviews: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return events.copy()

    queue = events.copy()
    event_reviews = reviews[reviews["Review_Status"] != "Missed Foul"].copy() if not reviews.empty else reviews
    if not event_reviews.empty:
        latest = event_reviews.drop_duplicates(subset=["Event_ID"], keep="last")
        queue = queue.merge(
            latest[["Event_ID", "Review_Status", "Human_Label", "Reviewer_Note", "Reviewed_At"]],
            on="Event_ID",
            how="left",
        )
    else:
        queue["Review_Status"] = "Unreviewed"
        queue["Human_Label"] = ""
        queue["Reviewer_Note"] = ""
        queue["Reviewed_At"] = ""

    queue["Review_Status"] = queue["Review_Status"].fillna("Unreviewed")
    queue["Human_Label"] = queue["Human_Label"].fillna("")
    queue["Reviewer_Note"] = queue["Reviewer_Note"].fillna("")
    queue["Reviewed_At"] = queue["Reviewed_At"].fillna("")
    return queue


def default_human_label(status: str, predicted_label: str, existing_label: str) -> str:
    if existing_label and existing_label != "nan":
        label = normalize_foul(existing_label)
        if label in HUMAN_LABEL_OPTIONS:
            return label
        return str(existing_label)
    if status == "False Positive":
        return "NO FOUL"
    if status == "Unclear":
        return "UNCLEAR"
    return predicted_label if predicted_label in HUMAN_LABEL_OPTIONS else "UNCLEAR"


st.markdown('<div class="page-title">✅ QA Review Queue</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">รีวิว replay video แบบเป็นคิว · แสดงทีละหน้าเพื่อให้ QA ครบและไม่โหลดหนักเกินไป</div>',
    unsafe_allow_html=True,
)

events_df = load_events()
reviews_df = load_reviews()
queue_df = build_review_queue(events_df, reviews_df)

if queue_df.empty:
    st.warning("ยังไม่มี `logs/foul_events.csv` หรือยังไม่มี event จากระบบ replay")
    st.stop()

with st.sidebar:
    st.markdown("### 🔍 QA Filters")

    status_filter = st.multiselect(
        "Review Status",
        options=REVIEW_STATUSES,
        default=["Unreviewed"],
        help="เริ่มจาก Unreviewed เพื่อไล่ QA ให้ครบก่อน",
    )

    foul_options = sorted(queue_df["Foul_Label"].dropna().unique().tolist())
    active_options = [f for f in ACTIVE_RULES if f in foul_options]
    default_fouls = active_options if active_options else foul_options
    foul_filter = st.multiselect(
        "Predicted Foul Type",
        options=foul_options,
        default=default_fouls,
    )
    pipeline_options = sorted(
        queue_df["Pipeline_Tag"].fillna("").replace("", "legacy").unique().tolist()
    )
    pipeline_filter = st.multiselect(
        "Pipeline Tag",
        options=pipeline_options,
        default=pipeline_options,
        help="ใช้แยก baseline กับรุ่น hand refinement เวลาเทียบก่อน/หลัง",
    )

    players = sorted(queue_df["Player_ID"].fillna("").astype(str).unique().tolist())
    player_filter = st.multiselect("Player ID", options=players, default=players)

    valid_dates = queue_df["Date_Time"].dropna().dt.date
    if not valid_dates.empty:
        min_date = valid_dates.min()
        max_date = valid_dates.max()
        date_range = st.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
    else:
        date_range = None

    sort_mode = st.selectbox(
        "Sort",
        ["Unreviewed first", "Newest first", "Oldest first", "Largest file first", "Missing video first"],
    )
    page_size = st.selectbox("Clips per page", [10, 20, 50], index=1)

    st.markdown("---")
    st.caption("Tip: ใช้ `Unreviewed first` + 20 clips/page เพื่อ QA ครบที่สุด")


filtered = queue_df.copy()
if status_filter:
    filtered = filtered[filtered["Review_Status"].isin(status_filter)]
if foul_filter:
    filtered = filtered[filtered["Foul_Label"].isin(foul_filter)]
if pipeline_filter:
    pipeline_series = filtered["Pipeline_Tag"].fillna("").replace("", "legacy")
    filtered = filtered[pipeline_series.isin(pipeline_filter)]
if player_filter:
    filtered = filtered[filtered["Player_ID"].fillna("").astype(str).isin(player_filter)]
if date_range and isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered = filtered[
        (filtered["Date_Time"].dt.date >= start_date)
        & (filtered["Date_Time"].dt.date <= end_date)
    ]

if sort_mode == "Unreviewed first":
    filtered["_status_rank"] = filtered["Review_Status"].apply(lambda s: 0 if s == "Unreviewed" else 1)
    filtered = filtered.sort_values(["_status_rank", "Date_Time"], ascending=[True, False])
elif sort_mode == "Newest first":
    filtered = filtered.sort_values("Date_Time", ascending=False)
elif sort_mode == "Oldest first":
    filtered = filtered.sort_values("Date_Time", ascending=True)
elif sort_mode == "Largest file first":
    filtered = filtered.sort_values("File_Size_KB", ascending=False)
elif sort_mode == "Missing video first":
    filtered = filtered.sort_values(["Replay_Exists", "Date_Time"], ascending=[True, False])

filtered = filtered.reset_index(drop=True)

total_events = len(queue_df)
reviewed_count = int((queue_df["Review_Status"] != "Unreviewed").sum())
unreviewed_count = total_events - reviewed_count
visible_count = len(filtered)
progress = reviewed_count / total_events if total_events else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Events", f"{total_events:,}")
k2.metric("Reviewed", f"{reviewed_count:,}", delta=f"{progress * 100:.1f}%")
k3.metric("Unreviewed", f"{unreviewed_count:,}")
k4.metric("Filtered Clips", f"{visible_count:,}")

st.progress(progress, text=f"QA Progress: {reviewed_count:,} / {total_events:,}")

target_rules = ["CARRYING", "HELD BALL"]
target_rows = []
queue_with_phase = queue_df.copy()
queue_with_phase["Pipeline_Tag"] = queue_with_phase["Pipeline_Tag"].fillna("").replace("", "legacy")
target_phases = sorted(queue_with_phase["Pipeline_Tag"].unique().tolist())
for phase in target_phases:
    for label in target_rules:
        target_slice = queue_with_phase[
            (queue_with_phase["Foul_Label"] == label) &
            (queue_with_phase["Pipeline_Tag"] == phase)
        ]
        reviewed_target = int((target_slice["Review_Status"] != "Unreviewed").sum())
        target_rows.append({
            "Pipeline Tag": phase,
            "Target Rule": label,
            "Events": int(len(target_slice)),
            "Reviewed": reviewed_target,
            "Need for 20": max(0, 20 - reviewed_target),
            "Need for 30": max(0, 30 - reviewed_target),
        })
target_df = pd.DataFrame(target_rows)
st.markdown("#### Hand-refinement QA target")
st.dataframe(target_df, use_container_width=True, hide_index=True)
st.caption("เป้าหมายขั้นต่ำคือรีวิวอย่างน้อย 20 เคสต่อกฎ และถ้าได้ 30 เคสจะนิ่งพอสำหรับจูน threshold รอบแรกมากกว่า")
st.markdown("---")

if filtered.empty:
    st.info("ไม่พบ replay ที่ตรงกับ filter ปัจจุบัน")
    st.stop()

total_pages = max(1, (visible_count + page_size - 1) // page_size)
if "qa_page" not in st.session_state:
    st.session_state.qa_page = 1
st.session_state.qa_page = min(max(1, int(st.session_state.qa_page)), total_pages)

page_col1, page_col2, page_col3, page_col4 = st.columns([1, 1, 2, 1])
with page_col1:
    if st.button("← Prev", disabled=st.session_state.qa_page <= 1, use_container_width=True):
        st.session_state.qa_page -= 1
        st.rerun()
with page_col2:
    if st.button("Next →", disabled=st.session_state.qa_page >= total_pages, use_container_width=True):
        st.session_state.qa_page += 1
        st.rerun()
with page_col3:
    selected_page = st.number_input(
        "Page",
        min_value=1,
        max_value=total_pages,
        value=st.session_state.qa_page,
        step=1,
        label_visibility="collapsed",
    )
    if selected_page != st.session_state.qa_page:
        st.session_state.qa_page = int(selected_page)
        st.rerun()
with page_col4:
    st.metric("Page", f"{st.session_state.qa_page}/{total_pages}")

start_idx = (st.session_state.qa_page - 1) * page_size
end_idx = min(start_idx + page_size, visible_count)
page_df = filtered.iloc[start_idx:end_idx]
st.caption(f"Showing {start_idx + 1:,}-{end_idx:,} of {visible_count:,} filtered clips")

for display_idx, row in page_df.iterrows():
    event_id = str(row.get("Event_ID", ""))
    replay_path = str(row.get("Replay_Path", ""))
    predicted_raw = str(row.get("Foul_Type", ""))
    predicted_label = str(row.get("Foul_Label", normalize_foul(predicted_raw)))
    current_status = str(row.get("Review_Status", "Unreviewed"))
    current_label = default_human_label(current_status, predicted_label, str(row.get("Human_Label", "")))
    current_note = str(row.get("Reviewer_Note", ""))
    replay_exists = bool(row.get("Replay_Exists", False))
    dt = row.get("Date_Time")
    dt_text = dt.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(dt) else "Unknown time"
    size_kb = int(row.get("File_Size_KB", 0))
    player_id = str(row.get("Player_ID", "?"))

    st.markdown('<div class="qa-card">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="qa-title">🎬 {dt_text}</div>
        <div class="qa-meta">
            Event: <strong>{event_id}</strong> · Player: <strong>{player_id}</strong> ·
            Camera: <strong>{row.get("Camera_ID", "—")}</strong> ·
            Pipeline: <strong>{row.get("Pipeline_Tag", "") or "legacy"}</strong> ·
            Size: <strong>{size_kb:,} KB</strong>
        </div>
        <span class="foul-badge">{predicted_raw}</span>
        <span class="status-pill status-{status_class(current_status)}">{current_status}</span>
        """,
        unsafe_allow_html=True,
    )

    video_col, review_col = st.columns([3, 2], gap="large")
    with video_col:
        if replay_exists:
            with open(replay_path, "rb") as vf:
                st.video(vf.read())
        else:
            st.markdown(
                f'<div class="missing-video">Replay file not found<br><code>{replay_path}</code></div>',
                unsafe_allow_html=True,
            )

    with review_col:
        status_index = REVIEW_STATUSES.index(current_status) if current_status in REVIEW_STATUSES else 0
        status = st.selectbox(
            "Review Status",
            REVIEW_STATUSES,
            index=status_index,
            key=f"qa_status_{event_id}",
        )

        label_options = HUMAN_LABEL_OPTIONS
        if current_label not in label_options:
            label_options = [current_label, *HUMAN_LABEL_OPTIONS]
        label_index = label_options.index(current_label) if current_label in label_options else 0
        human_label = st.selectbox(
            "Human Label",
            label_options,
            index=label_index,
            key=f"qa_label_{event_id}",
            help="False Positive ควรเลือก NO FOUL, Wrong Rule ให้เลือก foul จริง",
        )

        note = st.text_area(
            "Reviewer Note",
            value="" if current_note == "nan" else current_note,
            height=90,
            key=f"qa_note_{event_id}",
        )

        quick_col, save_col = st.columns(2)
        with quick_col:
            if st.button("Mark Correct", key=f"qa_correct_{event_id}", use_container_width=True):
                save_review(event_id, replay_path, predicted_raw, "Correct", predicted_label, note)
                st.success("Saved as Correct")
                st.rerun()
        with save_col:
            if st.button("Save Review", key=f"qa_save_{event_id}", use_container_width=True):
                save_review(event_id, replay_path, predicted_raw, status, human_label, note)
                st.success("Review saved")
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
