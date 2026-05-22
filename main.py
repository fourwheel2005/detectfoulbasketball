"""
main.py — AI Basketball Referee (Integrated Version)
=====================================================
Architecture:
    iPhone 15 Pro Max → MacBook (USB/WiFi) → OpenCV VideoCapture
       ↓
    [YOLO Person Model]  +  [YOLO Ball+Rim Model]  (dual YOLO)
       ↓                          ↓
    ByteTrack IDs         ball_box, rim_box (px)
       ↓                          ↓
    MediaPipe Pose (per-player crop → full-frame coords)
       ↓
    BasketballRef.process() → violations + info_texts
       ↓
    UI Display + Replay Video Logger (background thread)

Config:
    - ใส่ path ไฟล์โมเดลลูกบาสตรง BALL_MODEL_PATH
    - ถ้าไม่พบไฟล์ → ใช้ YOLO yolov8n.pt ตรวจ class 32 (sports ball COCO) แทน
"""

import cv2
import numpy as np
import mediapipe as mp
import threading
import time
import os
import json
import re
from datetime import datetime
from collections import deque
from ultralytics import YOLO

# ─── เชื่อมระบบกติกา ───────────────────────────────────────────────
from referee import BasketballRef, _is_pose_valid
from preprocessor import FramePreprocessor
from utils import FoulLogger, FoulEventLogger, evaluate_pose_quality

# ================================================================
#  CONFIG — ปรับค่าที่นี่ที่เดียว
# ================================================================
PERSON_MODEL_PATH = "yolov8n.pt"          # YOLO สำหรับตรวจคน
BALL_MODEL_PATH   = "trainmodel/best3.pt"  # ← ใส่ path ที่ได้จากเพื่อน

# Class IDs ใน Custom Ball Model (ตาม data.yaml)
BALL_CLASS_ID  = 0   # "basketball"
RIM_CLASS_ID   = 1   # "rim"
SBALL_CLASS_ID = 2   # "sports ball" (fallback)
BALL_CONF_MIN  = float(os.environ.get("BASKETBALL_BALL_CONF_MIN", "0.45"))
RIM_CONF_MIN   = float(os.environ.get("BASKETBALL_RIM_CONF_MIN", "0.55"))

# YOLO Fallback (ถ้าไม่มี best.pt) — class ใน COCO
COCO_BALL_CLASS = 32  # sports ball

# ══════════════════════════════════════════════════════════
#  SPEED OPTIMISATION CONFIG
# ══════════════════════════════════════════════════════════
# หัวใจของ FPS target: ลด imgsz + ลด MP complexity + skip YOLO ทุก N เฟรม
YOLO_IMGSZ     = 416    # ↓ จาก 640 → 416 (เร็วขึ้น ~30%)
YOLO_STRIDE    = 2      # รัน YOLO Person ทุก N เฟรม (ใช้ ByteTrack cache เฟรมที่แลก)
BALL_STRIDE    = 3      # รัน Ball Model ทุก N เฟรม (บอลเคลื่อนช้ากว่าคน)
CAM_WIDTH      = 960    # ↓ จาก 1280 (สมดุล YOLO + MP ลดลง)
CAM_HEIGHT     = 540

# MediaPipe Pose complexity: 0=เร็ว 2x (ปรับจาก 1)
# 0 ≈ 30ms/crop vs 1 ≈ 60ms/crop ที่ 4 player = ประหยัด ~120ms/frame
MP_MODEL_COMPLEXITY = 0

MAX_PLAYERS         = 4
ENABLE_HAND_REFINEMENT = os.environ.get("BASKETBALL_HAND_REFINEMENT", "1") != "0"
HAND_DEBUG_OVERLAY = os.environ.get("BASKETBALL_HAND_DEBUG", "0") == "1"
PIPELINE_TAG = os.environ.get(
    "BASKETBALL_PIPELINE_TAG",
    "hand_refinement_v1" if ENABLE_HAND_REFINEMENT else "baseline",
)
HAND_REFINEMENT_MAX_HANDS = 2
HAND_REFINEMENT_DIST_RATIO = 1.8
HAND_REFINEMENT_DIST_MIN = 140

REPLAY_BUFFER_LEN   = 90
POST_FOUL_FRAMES    = 30

# Preprocessing mode: "FAST" สำหรับ real-time (~7ms)
PREPROCESS_MODE = "FAST"
RUNTIME_STATUS_PATH = "logs/runtime_status.json"
RUNTIME_STATUS_INTERVAL = 10
RIM_MEMORY_FRAMES = 24  # ใช้ตำแหน่งห่วงล่าสุดต่อชั่วคราวเมื่อ YOLO rim หลุด
GT_NEAR_RIM_REFRESH_PAD = 2.2  # ลูกเข้าเขตห่วงแล้ว refresh ball/rim ทุกเฟรม
FOUL_ALERT_TTL_FRAMES = 75  # ค้างข้อความ foul บนจอ/replay ประมาณ 3-7 วินาทีตาม FPS
# (duplicate config removed — ค่าทั้งหมดถูกกำหนดใน SPEED OPTIMISATION CONFIG ด้านบนแล้ว)

# ================================================================
#  Replay Video Encoder (Background Thread)
# ================================================================
# แก้ไขบรรทัดนี้ รับค่า fps เข้ามาด้วย
def save_replay_video(frames: list, filepath: str, play_fps: float):
    """เซฟ Replay ในเบื้องหลัง เพื่อไม่ให้กล้องกระตุก"""
    if not frames:
        return
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    h, w = frames[0].shape[:2]
    safe_fps = max(5.0, min(float(play_fps or 10.0), 60.0))
    out = cv2.VideoWriter(filepath,
                          cv2.VideoWriter_fourcc(*"mp4v"),
                          safe_fps, (w, h))  # เปลี่ยน 30.0 เป็น play_fps
    if not out.isOpened():
        print(f"❌ [Replay] เปิด VideoWriter ไม่สำเร็จ → {filepath}")
        return
    for f in frames:
        out.write(f)
    out.release()
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        print(f"✅ [Replay] บันทึกเสร็จ → {filepath}")
    else:
        print(f"❌ [Replay] ไฟล์วิดีโอว่างหรือไม่ถูกสร้าง → {filepath}")


def sanitize_replay_label(label: str) -> str:
    """แปลงชื่อ foul ให้ปลอดภัยสำหรับใช้เป็นชื่อไฟล์ replay."""
    safe = str(label).upper().replace(" ", "-")
    safe = re.sub(r"[^A-Z0-9._()-]+", "-", safe)
    safe = re.sub(r"-{2,}", "-", safe).strip("-._")
    return safe[:80] or "FOUL"


def write_runtime_status(status: dict, filepath: str = RUNTIME_STATUS_PATH):
    """เขียนสถานะ runtime ให้ Streamlit UI อ่านแบบ lightweight"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    tmp_path = f"{filepath}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, filepath)


def draw_foul_alert_panel(frame, active_alerts: dict):
    """วาด foul alert แบบค้างหลายเฟรม เพื่อให้อ่านทันและติดใน replay."""
    if not active_alerts:
        return

    fh, fw = frame.shape[:2]
    alerts = sorted(
        active_alerts.values(),
        key=lambda item: item["ttl"],
        reverse=True,
    )[:4]
    panel_x, panel_y = 20, 58
    panel_w = min(620, fw - 40)
    panel_h = 58 + 52 * len(alerts)

    overlay = frame.copy()
    cv2.rectangle(
        overlay,
        (panel_x, panel_y),
        (panel_x + panel_w, panel_y + panel_h),
        (0, 0, 120),
        -1,
    )
    cv2.rectangle(
        overlay,
        (panel_x, panel_y),
        (panel_x + panel_w, panel_y + panel_h),
        (0, 0, 255),
        2,
    )
    cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

    cv2.putText(
        frame,
        "FOUL ALERT",
        (panel_x + 18, panel_y + 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    for idx, alert in enumerate(alerts):
        conf = float(alert.get("confidence", 0.0) or 0.0)
        reason = str(alert.get("reason", ""))
        suffix = f" {int(conf * 100)}%" if conf else ""
        text = f"P{alert['player_id']}  {alert['foul_type']}{suffix}"
        y = panel_y + 70 + idx * 52
        cv2.putText(
            frame,
            text[:48],
            (panel_x + 18, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )
        if reason:
            cv2.putText(
                frame,
                reason[:72],
                (panel_x + 18, y + 19),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                (210, 230, 230),
                1,
                cv2.LINE_AA,
            )


# ================================================================
#  ฟังก์ชันแปลง Landmark จาก Crop → Full Frame
# ================================================================
def landmarks_crop_to_full(pose_landmarks, crop_x1, crop_y1,
                            crop_w, crop_h) -> dict:
    """
    MediaPipe คืน landmark normalized [0,1] ในพื้นที่ Crop
    แปลงกลับเป็น pixel ของ Full Frame + เก็บ visibility
    Return: {idx: (full_x, full_y, visibility)}
    """
    result = {}
    for idx, lm in enumerate(pose_landmarks.landmark):
        fx  = int(lm.x * crop_w) + crop_x1
        fy  = int(lm.y * crop_h) + crop_y1
        vis = float(lm.visibility)   # 0.0 – 1.0
        result[idx] = (fx, fy, vis)
    return result


def hand_landmarks_crop_to_full(hand_result, crop_x1, crop_y1,
                                crop_w, crop_h) -> list:
    """แปลง MediaPipe Hands landmarks จาก crop กลับเป็นพิกัด full-frame."""
    if not hand_result.multi_hand_landmarks:
        return []

    handedness_list = hand_result.multi_handedness or []
    hands = []
    for idx, hand_lms in enumerate(hand_result.multi_hand_landmarks):
        label = "Unknown"
        if idx < len(handedness_list) and handedness_list[idx].classification:
            label = handedness_list[idx].classification[0].label
        points = {}
        for lm_idx, lm in enumerate(hand_lms.landmark):
            points[lm_idx] = (
                int(lm.x * crop_w) + crop_x1,
                int(lm.y * crop_h) + crop_y1,
            )
        hands.append({"label": label, "points": points})
    return hands


def should_refine_hands(landmarks_px: dict, mp_pose, ball_box,
                        shoulder_width: float, player_box: tuple) -> bool:
    """เปิด hand refinement เฉพาะผู้เล่นที่บอลอยู่ใกล้มือและใกล้ตัวจริง."""
    if ball_box is None:
        return False

    bx1, by1, bx2, by2 = ball_box
    ball_center = ((bx1 + bx2) / 2, (by1 + by2) / 2)
    px1, py1, px2, py2 = player_box
    box_pad = max(int(shoulder_width), 40)
    ball_near_player_box = (
        px1 - box_pad <= ball_center[0] <= px2 + box_pad and
        py1 - box_pad <= ball_center[1] <= py2 + box_pad
    )
    if not ball_near_player_box:
        return False

    hand_points = []
    for lm in (
        mp_pose.PoseLandmark.RIGHT_WRIST,
        mp_pose.PoseLandmark.LEFT_WRIST,
        mp_pose.PoseLandmark.RIGHT_INDEX,
        mp_pose.PoseLandmark.LEFT_INDEX,
        mp_pose.PoseLandmark.RIGHT_THUMB,
        mp_pose.PoseLandmark.LEFT_THUMB,
    ):
        pt = landmarks_px.get(lm.value)
        if pt is not None:
            hand_points.append(pt)
    if not hand_points:
        return False

    refine_threshold = max(
        shoulder_width * HAND_REFINEMENT_DIST_RATIO,
        HAND_REFINEMENT_DIST_MIN,
    )
    return min(
        ((pt[0] - ball_center[0]) ** 2 + (pt[1] - ball_center[1]) ** 2) ** 0.5
        for pt in hand_points
    ) <= refine_threshold


_HAND_DEBUG_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]


def draw_hand_refinement_overlay(frame, hand_landmarks_px: list):
    """วาด landmark มือเฉพาะตอน debug เพื่อใช้จูน ไม่รบกวนโหมดใช้งานจริง."""
    for hand in hand_landmarks_px:
        points = hand["points"]
        for start, end in _HAND_DEBUG_CONNECTIONS:
            p1, p2 = points.get(start), points.get(end)
            if p1 is None or p2 is None:
                continue
            cv2.line(frame, p1, p2, (255, 0, 255), 1)
        for idx, pt in points.items():
            color = (0, 255, 255) if idx in (4, 8, 12, 16, 20) else (255, 0, 255)
            radius = 4 if idx in (4, 8, 12, 16, 20) else 2
            cv2.circle(frame, pt, radius, color, -1)


# ════════════════════════════════════════════════════════════════
#  Skeleton Drawing (สีตาม visibility)
# ════════════════════════════════════════════════════════════════

_SKELETON_CONNECTIONS = [
    (0,1),(0,2),(1,3),(2,4),
    (11,12),
    (11,13),(13,15),(15,17),(15,19),
    (12,14),(14,16),(16,18),(16,20),
    (11,23),(12,24),(23,24),
    (23,25),(25,27),(27,31),
    (24,26),(26,28),(28,32),
]

def _vis_color(vis: float):
    if vis >= 0.70:   return (0, 230, 0)
    elif vis >= 0.40: return (0, 200, 255)
    else:             return (30, 30, 200)

def draw_skeleton(frame, landmarks_px: dict):
    """วาด Skeleton สีตาม visibility: เขียว=มั่น / เหลือง=พอใช้ / แดง=noise"""
    for (i, j) in _SKELETON_CONNECTIONS:
        p1, p2 = landmarks_px.get(i), landmarks_px.get(j)
        if p1 is None or p2 is None: continue
        vis = (p1[2] + p2[2]) / 2 if len(p1) > 2 else 1.0
        if vis < 0.20: continue
        cv2.line(frame, (p1[0],p1[1]), (p2[0],p2[1]),
                 _vis_color(vis), 2 if vis >= 0.5 else 1)
    for idx, pt in landmarks_px.items():
        vis = pt[2] if len(pt) > 2 else 1.0
        if vis < 0.20: continue
        r = 5 if vis >= 0.6 else 3
        cv2.circle(frame, (pt[0],pt[1]), r, _vis_color(vis), -1)
        cv2.circle(frame, (pt[0],pt[1]), r+1, (0,0,0), 1)



# ================================================================
#  หา Ball Box ที่อยู่ใกล้ผู้เล่นที่สุด
# ================================================================
def nearest_ball(player_cx: float, player_cy: float,
                 ball_boxes: list):
    """คืน ball_box ที่ใกล้ player center มากที่สุด (หรือ None)"""
    best_box  = None
    best_dist = float("inf")
    for bb in ball_boxes:
        bx = (bb[0] + bb[2]) / 2
        by = (bb[1] + bb[3]) / 2
        d  = ((bx - player_cx) ** 2 + (by - player_cy) ** 2) ** 0.5
        if d < best_dist:
            best_dist = d
            best_box  = tuple(int(v) for v in bb)
    return best_box


def ball_near_rim_zone(ball_box, rim_box, frame_w: int, frame_h: int) -> bool:
    """ตรวจว่าลูกเข้าเขตห่วงแล้วหรือยัง เพื่อ refresh ball/rim detection ถี่ขึ้น."""
    if ball_box is None or rim_box is None:
        return False
    bx = (ball_box[0] + ball_box[2]) / 2
    by = (ball_box[1] + ball_box[3]) / 2
    rx1, ry1, rx2, ry2 = rim_box
    rim_w = max(rx2 - rx1, 20)
    rim_h = max(ry2 - ry1, 20)
    pad_x = max(90, rim_w * GT_NEAR_RIM_REFRESH_PAD)
    pad_y = max(120, rim_h * (GT_NEAR_RIM_REFRESH_PAD + 1.0))
    return (
        max(0, rx1 - pad_x) <= bx <= min(frame_w, rx2 + pad_x) and
        max(0, ry1 - pad_y) <= by <= min(frame_h, ry2 + pad_y * 1.2)
    )


# ================================================================
#  MAIN
# ================================================================
def main():
    os.makedirs("logs/replays", exist_ok=True)
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    camera_index = int(os.environ.get("BASKETBALL_CAMERA", "1"))
    legacy_logger = FoulLogger("basketball_foul_logs.csv", cooldown_sec=3.0)
    event_logger = FoulEventLogger("logs/foul_events.csv")

    # ── โหลด YOLO Models ─────────────────────────────────────────
    print("🤖 โหลด YOLO Person Model...")
    person_model = YOLO(PERSON_MODEL_PATH).to('mps')

    ball_model     = None
    use_ball_model = False
    if os.path.exists(BALL_MODEL_PATH):
        print(f"🏀 โหลด Ball+Rim Model: {BALL_MODEL_PATH}")
        ball_model     = YOLO(BALL_MODEL_PATH).to('mps')
        use_ball_model = True
    else:
        print(f"⚠️  ไม่พบ {BALL_MODEL_PATH} → ใช้ YOLO COCO class 32 (sports ball) แทน")

    # ── MediaPipe Pose ────────────────────────────────────────────
    print("🧘 เตรียม MediaPipe Pose...")
    mp_pose_module = mp.solutions.pose
    mp_drawing     = mp.solutions.drawing_utils
    pose           = mp_pose_module.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        model_complexity=MP_MODEL_COMPLEXITY,
        enable_segmentation=False,
    )
    hands = None
    if ENABLE_HAND_REFINEMENT:
        print("✋ เตรียม MediaPipe Hands (conditional refinement)...")
        hands = mp.solutions.hands.Hands(
            # crop ในแต่ละ call อาจเป็นคนละผู้เล่น จึงใช้ image mode เพื่อไม่ให้ tracker
            # ของ Hands ลากสถานะข้ามคนโดยไม่ตั้งใจ
            static_image_mode=True,
            max_num_hands=HAND_REFINEMENT_MAX_HANDS,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    # ── Referee Engine ────────────────────────────────────────────
    print("⚖️  เตรียม BasketballRef (Rule Engine)...")
    ref = BasketballRef()

    # ── Preprocessor (FAST mode สำหรับ real-time) ─────────────────
    preprocessor = FramePreprocessor(mode=PREPROCESS_MODE)

    # ── กล้อง ─────────────────────────────────────────────────────
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print("❌ ไม่สามารถเปิดกล้องได้!")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # ลด latency
    print(f"✅ ระบบพร้อม! camera={camera_index} | {CAM_WIDTH}×{CAM_HEIGHT} | MP complexity={MP_MODEL_COMPLEXITY} | YOLO imgsz={YOLO_IMGSZ} | กด 'q' เพื่อออก")
    print(f"🧪 Pipeline tag: {PIPELINE_TAG} | hand_refinement={int(ENABLE_HAND_REFINEMENT)} | hand_debug={int(HAND_DEBUG_OVERLAY)}")


    # ── Replay Buffer ─────────────────────────────────────────────
    replay_buffer     = deque(maxlen=REPLAY_BUFFER_LEN)
    is_recording      = False
    recording_left    = 0
    recorded_foul_names = set() 
    recorded_foul_events = {}
    active_foul_alerts = {}

    prev_time   = time.time()
    frame_count = 0
    prev_ids    = set()

    # Frame-stride cache (ByteTrack + ball cache ระหว่าง skip)
    _cached_persons   = []
    _cached_balls     = []
    _cached_rims      = []
    _last_rim_box     = None
    _rim_lost_frames  = RIM_MEMORY_FRAMES + 1
    rim_memory_active = False
    rim_reliable_count = 0
    rim_reliable = False
    last_fps = 0.0

    # ─────────────────────────────────────────────────────────────
    #  Main Loop
    # ─────────────────────────────────────────────────────────────
    print("🔍 Methods in BasketballRef:", [m for m in dir(ref) if not m.startswith('__')])
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # ── Preprocessing: CLAHE + White Balance (~7ms) ──────────────
        frame = preprocessor.process(frame)

        frame_count += 1
        frame_h, frame_w = frame.shape[:2]

        any_violation = False
        frame_foul_names = set() 
        frame_foul_events = []
        pose_quality_samples = []
        low_vis_players = 0
        hand_refinement_runs = 0
        refined_hands_detected = 0

        # ──────────────────────────────────────────────────────────
        #  PHASE 1 — Person Detection + Tracking (YOLO + ByteTrack)
        # ──────────────────────────────────────────────────────────
        # ── YOLO stride: รัน Person YOLO ทุก YOLO_STRIDE เฟรม ──────────
        if frame_count % YOLO_STRIDE == 0:
            person_results = person_model.track(
                frame,
                imgsz=YOLO_IMGSZ,
                persist=True,
                tracker="bytetrack.yaml",
                classes=[0],
                verbose=False,
                device='mps'
            )
            _cached_persons = []
            if person_results[0].boxes is not None:
                b = person_results[0].boxes
                if b.id is not None:
                    for box, tid in zip(b.xyxy.cpu().numpy(),
                                        b.id.cpu().numpy()):
                        _cached_persons.append((int(tid), *box.astype(int)))

        persons  = sorted(_cached_persons, key=lambda p: p[0])[:MAX_PLAYERS]

        # Cleanup ผู้เล่นที่หายออกจากเฟรม
        cur_ids  = {p[0] for p in persons}
        gone_ids = prev_ids - cur_ids
        for gid in gone_ids:
            ref.cleanup_player(gid)
        prev_ids = cur_ids

        # ──────────────────────────────────────────────────────────
        #  PHASE 2 — Ball + Rim Detection
        # ──────────────────────────────────────────────────────────
        # ── Ball stride: รัน Ball Model ทุก BALL_STRIDE เฟรม ──────────
        # Goaltending ต้องการ trajectory ถี่กว่ากฎอื่น ถ้าลูกเข้าเขตห่วงแล้วให้ refresh ทุกเฟรม
        force_near_rim_refresh = (
            use_ball_model and ball_model is not None and
            rim_reliable and _last_rim_box is not None and
            any(ball_near_rim_zone(bb, _last_rim_box, frame_w, frame_h) for bb in _cached_balls)
        )
        if frame_count % BALL_STRIDE == 0 or force_near_rim_refresh:
            if use_ball_model and ball_model:
                ball_results = ball_model(frame, imgsz=YOLO_IMGSZ, verbose=False)
                _cached_balls, _cached_rims = [], []
                if ball_results[0].boxes is not None:
                    boxes = ball_results[0].boxes
                    for box, cls, conf in zip(
                        boxes.xyxy.cpu().numpy(),
                        boxes.cls.cpu().numpy(),
                        boxes.conf.cpu().numpy(),
                    ):
                        cls_id = int(cls)
                        conf = float(conf)
                        if cls_id in (BALL_CLASS_ID, SBALL_CLASS_ID) and conf >= BALL_CONF_MIN:
                            _cached_balls.append(box)
                        elif cls_id == RIM_CLASS_ID and conf >= RIM_CONF_MIN:
                            _cached_rims.append(box)
            else:
                fb = person_model(frame, imgsz=YOLO_IMGSZ,
                                  classes=[COCO_BALL_CLASS], verbose=False)
                _cached_balls = []
                if fb[0].boxes is not None:
                    for box in fb[0].boxes.xyxy.cpu().numpy():
                        _cached_balls.append(box)
                _cached_rims = []

        ball_boxes = _cached_balls
        rim_boxes  = _cached_rims

        # ── วาด Ball + Rim บนจอ ──────────────────────────────────
        for bb in ball_boxes:
            x1, y1, x2, y2 = map(int, bb)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 2)
            cv2.putText(frame, "Ball", (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)

        for rb in rim_boxes:
            rx1, ry1, rx2, ry2 = map(int, rb)
            rim_cy = (ry1 + ry2) // 2
            cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (0, 140, 255), 2)
            cv2.putText(frame, f"RIM y={rim_cy}", (rx1, ry1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 140, 255), 1)

        # Auto-calibrate goaltending เฉพาะเมื่อเคยเห็น rim จริงจาก model
        # ถ้า rim หลุดสั้นๆ ให้ใช้ตำแหน่งล่าสุดต่อเพื่อไม่ล้าง trajectory ของลูกเร็วเกินไป
        rim_for_gt = None
        rim_memory_active = False
        if rim_boxes:
            candidate_rim = max(rim_boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
            rim_jump_reset = False
            if _last_rim_box is not None:
                old_cx = (_last_rim_box[0] + _last_rim_box[2]) / 2
                old_cy = (_last_rim_box[1] + _last_rim_box[3]) / 2
                new_cx = (candidate_rim[0] + candidate_rim[2]) / 2
                new_cy = (candidate_rim[1] + candidate_rim[3]) / 2
                if ((new_cx - old_cx) ** 2 + (new_cy - old_cy) ** 2) ** 0.5 > max(120, frame_w * 0.18):
                    rim_jump_reset = True
            _last_rim_box = candidate_rim
            _rim_lost_frames = 0
            rim_reliable_count = 1 if rim_jump_reset else min(rim_reliable_count + 1, 12)
            rim_reliable = rim_reliable_count >= 3
            rim_for_gt = _last_rim_box
        elif _last_rim_box is not None and _rim_lost_frames < RIM_MEMORY_FRAMES:
            _rim_lost_frames += 1
            rim_for_gt = _last_rim_box
            rim_memory_active = True
            rim_reliable = rim_reliable_count >= 3 and _rim_lost_frames <= 8
        else:
            _rim_lost_frames += 1
            rim_reliable_count = 0
            rim_reliable = False

        if rim_for_gt is not None:
            rx1, ry1, rx2, ry2 = map(int, rim_for_gt)
            rim_cy = (ry1 + ry2) // 2
            rim_pad = max(80, int((rx2 - rx1) * 1.5))
            ref.set_rim_y(
                rim_cy,
                rim_x_range=(max(0, rx1 - rim_pad), min(frame_w, rx2 + rim_pad)),
                rim_reliable=rim_reliable,
            )
        else:
            ref.set_rim_y(None, rim_x_range=None, rim_reliable=False)

        # ──────────────────────────────────────────────────────────
        #  PHASE 3 — Per-Player: MediaPipe Pose → Referee
        # ──────────────────────────────────────────────────────────

        for (tid, px1, py1, px2, py2) in persons:

            # ── Crop ผู้เล่น (เพิ่ม padding เพื่อให้เห็นแขน) ──────
            PAD = 25
            cx1 = max(0, px1 - PAD)
            cy1 = max(0, py1 - PAD)
            cx2 = min(frame_w, px2 + PAD)
            cy2 = min(frame_h, py2 + PAD)
            crop_h = cy2 - cy1
            crop_w = cx2 - cx1
            crop = frame[cy1:cy2, cx1:cx2]
            if crop.size == 0:
                continue

            # ── MediaPipe Pose ─────────────────────────────────────
            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            pose_result = pose.process(crop_rgb)
            if not pose_result.pose_landmarks:
                # วาดกล่องคนสีเทา (ไม่พบ pose)
                cv2.rectangle(frame, (px1, py1), (px2, py2), (128, 128, 128), 1)
                continue

            # ── แปลง Landmark → Full Frame coords ─────────────────
            landmarks_px = landmarks_crop_to_full(
                pose_result.pose_landmarks,
                cx1, cy1, crop_w, crop_h
            )

            # ── Pose Validity Check ────────────────────────────────
            is_valid, reason = _is_pose_valid(landmarks_px, mp_pose_module)
            if not is_valid:
                cv2.rectangle(frame, (px1, py1), (px2, py2), (128, 128, 128), 1)
                if "vis" in reason.lower():
                    low_vis_players += 1
                    cv2.putText(frame, "Low vis",
                                (px1, py1-5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (80,80,200), 1)
                continue

            pose_quality = evaluate_pose_quality(landmarks_px, mp_pose_module)
            pose_quality_samples.append(pose_quality)

            # ── Draw Skeleton ─────────────────────────────────────────
            draw_skeleton(frame, landmarks_px)

            # ── หา Ball ที่ใกล้ผู้เล่นนี้มากที่สุด ─────────────────
            player_cx = (px1 + px2) / 2
            player_cy = (py1 + py2) / 2
            ball_box  = nearest_ball(player_cx, player_cy, ball_boxes)
            l_shoulder = landmarks_px[mp_pose_module.PoseLandmark.LEFT_SHOULDER.value]
            r_shoulder = landmarks_px[mp_pose_module.PoseLandmark.RIGHT_SHOULDER.value]
            shoulder_width = max(
                ((l_shoulder[0] - r_shoulder[0]) ** 2 +
                 (l_shoulder[1] - r_shoulder[1]) ** 2) ** 0.5,
                10.0,
            )

            hand_landmarks_px = []
            if (
                hands is not None and
                should_refine_hands(
                    landmarks_px,
                    mp_pose_module,
                    ball_box,
                    shoulder_width,
                    (px1, py1, px2, py2),
                )
            ):
                hand_refinement_runs += 1
                hand_result = hands.process(crop_rgb)
                hand_landmarks_px = hand_landmarks_crop_to_full(
                    hand_result, cx1, cy1, crop_w, crop_h
                )
                refined_hands_detected += len(hand_landmarks_px)
                if HAND_DEBUG_OVERLAY and hand_landmarks_px:
                    draw_hand_refinement_overlay(frame, hand_landmarks_px)
                    cv2.putText(
                        frame,
                        f"Hand refine: {len(hand_landmarks_px)}",
                        (px1, max(18, py1 - 44)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        (255, 0, 255),
                        1,
                    )

            # ── เรียก Referee Engine ────────────────────────────────
            violations, info_texts = ref.process(
                tid, landmarks_px, mp_pose_module,
                ball_box, frame_w, frame_h,
                hand_landmarks_px=hand_landmarks_px,
                fps=last_fps,
            )

            # ── วาด Bounding Box ผู้เล่น ────────────────────────────
            box_color = (0, 0, 255) if violations else (0, 220, 0)
            cv2.rectangle(frame, (px1, py1), (px2, py2), box_color, 2)
            cv2.putText(frame, f"P{tid}", (px1, py1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)
            cv2.putText(
                frame,
                f"Pose {pose_quality.percent()}% H{pose_quality.percent('hand_score')} F{pose_quality.percent('foot_score')}",
                (px1, py2 + 36),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (80, 220, 255),
                1,
            )

            # ── แสดง Violations ────────────────────────────────────
            y_offset = py1 - 28
            for v in violations:
                foul_text = getattr(v, "foul_type", str(v))
                confidence = float(getattr(v, "confidence", 0.0) or 0.0)
                reason = str(getattr(v, "reason", ""))
                display_text = f"!!! {foul_text} ({int(confidence * 100)}%)" if confidence else f"!!! {foul_text}"
                cv2.putText(frame, display_text, (px1, y_offset),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                y_offset -= 26
                any_violation = True   
                frame_foul_names.add(foul_text)
                frame_foul_events.append({
                    "player_id": tid,
                    "foul_type": foul_text,
                    "frame_index": frame_count,
                    "confidence": confidence,
                    "reason": reason,
                    "pose_score": pose_quality.overall_score,
                    "hand_score": pose_quality.hand_score,
                    "foot_score": pose_quality.foot_score,
                    "ball_velocity": getattr(v, "ball_velocity", ""),
                    "rim_reliable": rim_reliable,
                })
                active_foul_alerts[(tid, foul_text)] = {
                    "player_id": tid,
                    "foul_type": foul_text,
                    "confidence": confidence,
                    "reason": reason,
                    "ttl": FOUL_ALERT_TTL_FRAMES,
                    "frame_index": frame_count,
                }

            # ── แสดง Info (Steps etc.) ─────────────────────────────
            for info in info_texts:
                cv2.putText(frame, info, (px1, py2 + 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 220, 0), 1)

            # ── วาด Skeleton (optional, debug) ────────────────────
            # mp_drawing.draw_landmarks(
            #     frame, pose_result.pose_landmarks,
            #     mp_pose_module.POSE_CONNECTIONS,
            #     landmark_drawing_spec=mp_drawing.DrawingSpec(
            #         color=(0,255,0), thickness=1, circle_radius=2)
            # )

        # ──────────────────────────────────────────────────────────
        #  PHASE 4 — FPS + Replay Recording
        # ──────────────────────────────────────────────────────────
        curr_time = time.time()
        fps = 1.0 / max(curr_time - prev_time, 1e-9)
        last_fps = fps
        prev_time = curr_time
        cv2.putText(frame, f"FPS: {int(fps)}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

        if active_foul_alerts:
            draw_foul_alert_panel(frame, active_foul_alerts)
            expired_alerts = []
            for alert_key, alert in active_foul_alerts.items():
                alert["ttl"] -= 1
                if alert["ttl"] <= 0:
                    expired_alerts.append(alert_key)
            for alert_key in expired_alerts:
                active_foul_alerts.pop(alert_key, None)

        if frame_count % RUNTIME_STATUS_INTERVAL == 0:
            sample_count = len(pose_quality_samples)
            avg_pose = sum(q.overall_score for q in pose_quality_samples) / sample_count if sample_count else 0.0
            avg_hand = sum(q.hand_score for q in pose_quality_samples) / sample_count if sample_count else 0.0
            avg_foot = sum(q.foot_score for q in pose_quality_samples) / sample_count if sample_count else 0.0
            write_runtime_status({
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "session_id": session_id,
                "camera_id": camera_index,
                "frame_index": frame_count,
                "fps": round(float(fps), 1),
                "players_tracked": len(persons),
                "pose_players_valid": sample_count,
                "low_vis_players": low_vis_players,
                "ball_detected": bool(ball_boxes),
                "ball_count": len(ball_boxes),
                "rim_detected": bool(rim_boxes),
                "rim_count": len(rim_boxes),
                "rim_memory_active": bool(rim_memory_active),
                "rim_reliable": bool(rim_reliable),
                "rim_reliable_count": int(rim_reliable_count),
                "rim_lost_frames": int(_rim_lost_frames),
                "force_near_rim_refresh": bool(force_near_rim_refresh),
                "ball_conf_min": BALL_CONF_MIN,
                "rim_conf_min": RIM_CONF_MIN,
                "avg_pose_score": round(avg_pose, 3),
                "avg_hand_score": round(avg_hand, 3),
                "avg_foot_score": round(avg_foot, 3),
                "hand_refinement_runs": hand_refinement_runs,
                "refined_hands_detected": refined_hands_detected,
                "hand_refinement_enabled": bool(ENABLE_HAND_REFINEMENT),
                "hand_debug_overlay": bool(HAND_DEBUG_OVERLAY),
                "pipeline_tag": PIPELINE_TAG,
                "any_violation": bool(any_violation),
                "active_fouls": sorted(frame_foul_names),
                "displayed_foul_alerts": [
                    alert["foul_type"] for alert in active_foul_alerts.values()
                ],
            })

        # เริ่ม Record เมื่อมีฟาล์ว
        if any_violation and not is_recording:
            is_recording   = True
            recording_left = POST_FOUL_FRAMES
            recorded_foul_names = set() 
            recorded_foul_events = {}

        # REC indicator
        replay_buffer.append(frame.copy())
        if is_recording:
            recorded_foul_names.update(frame_foul_names)
            for event in frame_foul_events:
                event_key = (event["player_id"], event["foul_type"][:60])
                recorded_foul_events.setdefault(event_key, event)
            if frame_count % 10 < 5:
                fh, fw = frame.shape[:2]
                cv2.circle(frame, (fw - 50, 40), 10, (0, 0, 255), -1)
                cv2.putText(frame, "REC", (fw - 110, 45),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            recording_left -= 1
            if recording_left <= 0:
                is_recording   = False
                frames_to_save = list(replay_buffer)
                timestamp      = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                # Sanitize + join ชื่อ foul
                foul_label = "_".join(
                    sanitize_replay_label(v)
                    for v in sorted(recorded_foul_names)
                ) or "UNKNOWN"
                save_path = os.path.abspath(
                    f"logs/replays/foul_{timestamp}_{foul_label}.mp4"
                )
                threading.Thread(
                    target=save_replay_video,
                    args=(frames_to_save, save_path, fps), # เพิ่มตัวแปร fps ตรงนี้
                    daemon=False,
                ).start()
                for event in recorded_foul_events.values():
                    legacy_logger.log_foul(event["player_id"], event["foul_type"])
                    event_logger.log_event(
                        session_id=session_id,
                        frame_index=event["frame_index"],
                        player_id=event["player_id"],
                        foul_type=event["foul_type"],
                        replay_path=save_path,
                        camera_id=camera_index,
                        pipeline_tag=PIPELINE_TAG,
                        hand_refinement_enabled=ENABLE_HAND_REFINEMENT,
                        confidence=event.get("confidence", ""),
                        rule_reason=event.get("reason", ""),
                        pose_score=event.get("pose_score", ""),
                        hand_score=event.get("hand_score", ""),
                        foot_score=event.get("foot_score", ""),
                        ball_velocity=event.get("ball_velocity", ""),
                        rim_reliable=event.get("rim_reliable", ""),
                    )

        cv2.imshow("🏀 AI Referee", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # ── ปิดระบบ ───────────────────────────────────────────────────
    pose.close()
    if hands is not None:
        hands.close()
    cap.release()
    cv2.destroyAllWindows()
    print("👋 ปิดระบบเรียบร้อย")


if __name__ == "__main__":
    main()
