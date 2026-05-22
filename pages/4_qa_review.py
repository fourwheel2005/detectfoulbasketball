"""
pages/4_qa_review.py — Replay QA Review Queue
==============================================
Human review page for foul replay videos with pagination.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from ui_theme import (
    inject_global_css,
    render_page_header,
    render_section_label,
    render_footer,
    normalize_foul,
    status_class,
    ACTIVE_RULES,
    DEPRECATED_RULES,
    REVIEW_COLUMNS,
    REVIEW_STATUSES,
    HUMAN_LABEL_OPTIONS,
)

# ── Page Config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QA Review — AI Referee",
    page_icon="✅",
    layout="wide",
)

# ── Apply Global Theme ──────────────────────────────────────────────────
inject_global_css()

# ── Project Paths ─────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
EVENT_FILE = PROJECT_ROOT / "logs" / "foul_events.csv"
REVIEW_FILE = PROJECT_ROOT / "logs" / "review_labels.csv"


# ── Data Loading ──────────────────────────────────────────────────────────
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


# ═════════════════════════════════════════════════════════════════════════
#  UI LAYOUT
# ═════════════════════════════════════════════════════════════════════════

render_page_header(
    "✅ QA Review Queue",
    "รีวิว replay video แบบเป็นคิว · แสดงทีละหน้าเพื่อให้ QA ครบและไม่โหลดหนักเกินไป",
)

events_df = load_events()
reviews_df = load_reviews()
queue_df = build_review_queue(events_df, reviews_df)

if queue_df.empty:
    st.warning("ยังไม่มี `logs/foul_events.csv` หรือยังไม่มี event จากระบบ replay")
    st.stop()

# ── Sidebar Filters ───────────────────────────────────────────────────────
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

# ── Apply Filters ─────────────────────────────────────────────────────────
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

# ── KPI + Progress ────────────────────────────────────────────────────────
total_events = len(queue_df)
reviewed_count = int((queue_df["Review_Status"] != "Unreviewed").sum())
unreviewed_count = total_events - reviewed_count
visible_count = len(filtered)
progress = reviewed_count / total_events if total_events else 0

k1, k2, k3, k4 = st.columns(4, gap="medium")
k1.metric("Total Events", f"{total_events:,}")
k2.metric("Reviewed", f"{reviewed_count:,}", delta=f"{progress * 100:.1f}%")
k3.metric("Unreviewed", f"{unreviewed_count:,}")
k4.metric("Filtered Clips", f"{visible_count:,}")

st.progress(progress, text=f"QA Progress: {reviewed_count:,} / {total_events:,}")

# ── Hand-refinement QA Target ─────────────────────────────────────────────
with st.expander("📊 Hand-refinement QA Target", expanded=False):
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
    st.dataframe(target_df, use_container_width=True, hide_index=True)
    st.caption("เป้าหมายขั้นต่ำคือรีวิวอย่างน้อย 20 เคสต่อกฎ และถ้าได้ 30 เคสจะนิ่งพอสำหรับจูน threshold รอบแรกมากกว่า")

st.markdown("---")

# ── Check Empty State ─────────────────────────────────────────────────────
if filtered.empty:
    st.info("ไม่พบ replay ที่ตรงกับ filter ปัจจุบัน")
    st.stop()

# ── Pagination ────────────────────────────────────────────────────────────
total_pages = max(1, (visible_count + page_size - 1) // page_size)
if "qa_page" not in st.session_state:
    st.session_state.qa_page = 1
st.session_state.qa_page = min(max(1, int(st.session_state.qa_page)), total_pages)

page_col1, page_col2, page_col3, page_col4 = st.columns([1, 1, 2, 1], gap="medium")
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

# ── Review Cards ──────────────────────────────────────────────────────────
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

    # Card header as single HTML block (no split divs)
    st.markdown(
        f"""
        <div style="
            background: #FFFFFF;
            border: 1px solid #E8ECF1;
            border-radius: 16px;
            padding: 1.5rem 1.7rem 1rem 1.7rem;
            margin-bottom: 0.3rem;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        ">
            <div style="font-weight:800; color:#EA580C; font-size:1.16rem; margin-bottom:0.5rem;">🎬 {dt_text}</div>
            <div style="color:#64748B; font-size:0.98rem; margin-bottom:0.8rem; line-height:1.55;">
                Event: <strong>{event_id}</strong> · Player: <strong>{player_id}</strong> ·
                Camera: <strong>{row.get("Camera_ID", "—")}</strong> ·
                Pipeline: <strong>{row.get("Pipeline_Tag", "") or "legacy"}</strong> ·
                Size: <strong>{size_kb:,} KB</strong>
            </div>
            <span class="foul-badge">{predicted_raw}</span>
            <span class="status-pill status-{status_class(current_status)}">{current_status}</span>
        </div>
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

        label_options = list(HUMAN_LABEL_OPTIONS)
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

        quick_col, save_col = st.columns(2, gap="small")
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

    st.markdown("---")

# ── Footer ────────────────────────────────────────────────────────────────
render_footer()
