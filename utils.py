"""
utils.py — ฟังก์ชันและคลาสช่วยเหลือ
--------------------------------------
ประกอบด้วย:
  - get_dist()              : ระยะห่าง Euclidean
  - calculate_angle()       : มุมจาก 3 จุด
  - compute_iou()           : Intersection over Union
  - filter_duplicate_boxes(): กรอง Box ซ้อนทับ
  - filter_mirror_boxes()   : กรอง เงาในกระจก/สะท้อน  ← ใหม่
  - PlayerStabilityFilter   : กรอง ID กระพริบ
  - BallMotionTracker       : ติดตาม motion/เด้ง/หยุดของลูกบาส
  - PoseQuality             : ประเมินคุณภาพ pose แยกตามกลุ่ม keypoints
  - FoulLogger              : บันทึก CSV แบบเดิม
  - FoulEventLogger         : บันทึก event/replay สำหรับ QA review
  - AccuracyTracker         : รายงานความแม่นยำ
"""

import numpy as np
import time
import csv
import os
import uuid
from dataclasses import dataclass
from collections import defaultdict


# ─────────────────────────────────────────────────────
#  คณิตศาสตร์พื้นฐาน
# ─────────────────────────────────────────────────────

def get_dist(p1, p2) -> float:
    """ระยะทาง Euclidean ระหว่าง 2 จุด (pixel)"""
    return float(np.linalg.norm(np.array(p1[:2]) - np.array(p2[:2])))


def calculate_angle(a, b, c) -> float:
    """
    มุมที่จุด b (องศา 0–180)
    a, b, c: tuple (x, y) ของข้อต่อแต่ละจุด
    """
    a, b, c = np.array(a[:2]), np.array(b[:2]), np.array(c[:2])
    radians = (np.arctan2(c[1]-b[1], c[0]-b[0])
               - np.arctan2(a[1]-b[1], a[0]-b[0]))
    angle = abs(np.degrees(radians))
    return 360.0 - angle if angle > 180.0 else angle


# ─────────────────────────────────────────────────────
#  IoU และ Box Filtering
# ─────────────────────────────────────────────────────

def compute_iou(boxA, boxB) -> float:
    """IoU ของ 2 Bounding Box [x1, y1, x2, y2]"""
    xA = max(boxA[0], boxB[0]);  yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2]);  yB = min(boxA[3], boxB[3])
    inter = max(0, xB-xA) * max(0, yB-yA)
    if inter == 0:
        return 0.0
    aA = (boxA[2]-boxA[0]) * (boxA[3]-boxA[1])
    aB = (boxB[2]-boxB[0]) * (boxB[3]-boxB[1])
    return inter / (aA + aB - inter)


def filter_duplicate_boxes(boxes: list, ids: list,
                            iou_threshold: float = 0.4) -> tuple:
    """
    กรอง Box ซ้อนทับกัน เก็บ Box ใหญ่ไว้ (ตัวจริง)
    ตัด Box เล็กที่ซ้อนอยู่ทิ้ง (มือ/แขนลอย)
    """
    if len(boxes) == 0:
        return boxes, ids

    areas = [(b[2]-b[0])*(b[3]-b[1]) for b in boxes]
    order = sorted(range(len(areas)), key=lambda i: areas[i], reverse=True)
    keep = [];  suppressed = set()

    for i in order:
        if i in suppressed:
            continue
        keep.append(i)
        for j in order:
            if j == i or j in suppressed:
                continue
            if compute_iou(boxes[i], boxes[j]) > iou_threshold:
                suppressed.add(j)

    return [boxes[i] for i in keep], [ids[i] for i in keep]


def filter_mirror_boxes(boxes: list, ids: list,
                        frame_w: int,
                        size_ratio_thresh: float = 0.55,
                        brightness_thresh: float = 30.0,
                        frame_bgr=None) -> tuple:
    """
    กรองเงาในกระจก/ภาพสะท้อนออกจาก Person Detection

    หลักการ 3 ชั้น:
        1. Size Ratio  — เงาในกระจกมักมีขนาดเล็กกว่าตัวจริงมาก
                         Box ที่มี Area < size_ratio_thresh × Area ใหญ่สุด → ตัดทิ้ง
                         (ใช้ได้ดีเมื่อกระจกอยู่ข้าง/หลัง)

        2. Edge Bias   — กระจกมักอยู่ขอบซ้าย/ขวา
                         Box ที่ center_x อยู่ใน 15% ขอบซ้ายขวา
                         และมีขนาดเล็กกว่า 40% ของ Box ใหญ่สุด → ตัดทิ้ง

        3. Brightness  — เงาในกระจกมักมืดกว่าหรือ contrast ต่างกัน
                         (เฉพาะเมื่อส่ง frame_bgr มาด้วย)

    Parameters:
        boxes            : list ของ [x1,y1,x2,y2]
        ids              : list ของ Player ID
        frame_w          : ความกว้างของเฟรม (pixel)
        size_ratio_thresh: Box ที่เล็กกว่า ratio นี้ × Box ใหญ่สุด → ตัดทิ้ง
        brightness_thresh: ค่าต่างสว่าง (Mean BGR) ที่ถือว่า "ต่างกันมาก"
        frame_bgr        : numpy array ของ frame ต้นฉบับ (optional)

    Returns:
        (filtered_boxes, filtered_ids)
    """
    if len(boxes) <= 1:
        return boxes, ids  # คนเดียวไม่มีเงา

    areas    = [(b[2]-b[0])*(b[3]-b[1]) for b in boxes]
    max_area = max(areas)
    keep     = []

    for i, (box, area) in enumerate(zip(boxes, areas)):
        cx = (box[0] + box[2]) / 2  # Center X ของ Box

        # ── ชั้น 1: Size Ratio ──────────────────────────
        if max_area > 0 and (area / max_area) < size_ratio_thresh:
            # Box เล็กกว่า 55% ของ Box ใหญ่สุด → น่าจะเป็นเงา
            continue

        # ── ชั้น 2: Edge Bias ────────────────────────────
        edge_zone = frame_w * 0.15  # 15% ขอบซ้ายขวา
        is_edge   = (cx < edge_zone) or (cx > frame_w - edge_zone)
        is_small  = (area / max_area) < 0.40

        if is_edge and is_small:
            # อยู่ขอบและเล็กกว่า 40% → น่าจะเป็นเงาในกระจกข้างห้อง
            continue

        # ── ชั้น 3: Brightness (optional) ────────────────
        if frame_bgr is not None and brightness_thresh > 0:
            x1, y1, x2, y2 = map(int, box)
            x1 = max(0, x1);  y1 = max(0, y1)
            x2 = min(frame_bgr.shape[1], x2)
            y2 = min(frame_bgr.shape[0], y2)
            roi = frame_bgr[y1:y2, x1:x2]

            if roi.size > 0:
                # เปรียบสว่างเฉลี่ยกับ Box ที่ใหญ่ที่สุด
                big_idx = areas.index(max_area)
                bx1, by1, bx2, by2 = map(int, boxes[big_idx])
                bx1 = max(0, bx1);  by1 = max(0, by1)
                bx2 = min(frame_bgr.shape[1], bx2)
                by2 = min(frame_bgr.shape[0], by2)
                big_roi = frame_bgr[by1:by2, bx1:bx2]

                if big_roi.size > 0 and i != big_idx:
                    bright_diff = abs(float(roi.mean()) -
                                      float(big_roi.mean()))
                    if bright_diff > brightness_thresh and is_small:
                        continue  # สว่างต่างกันมากและเล็กกว่า → เงา

        keep.append(i)

    if len(keep) == 0:
        # ถ้ากรองหมดให้เก็บ Box ใหญ่สุดไว้
        keep = [areas.index(max_area)]

    return [boxes[i] for i in keep], [ids[i] for i in keep]


# ─────────────────────────────────────────────────────
#  PlayerStabilityFilter — กรอง ID กระพริบ
# ─────────────────────────────────────────────────────

class PlayerStabilityFilter:
    """
    กรอง Player ID ที่ปรากฏแล้วหายเร็ว (Noise)
    ID จริงปรากฏต่อเนื่อง ≥ MIN_FRAMES จึง Accept
    """

    MIN_FRAMES    = 8    # เฟรมขั้นต่ำก่อน Accept
    EXPIRE_FRAMES = 30   # ไม่เห็นกี่เฟรมถึงถือว่าออกไป

    def __init__(self):
        self._seen      : dict = {}
        self._last_seen : dict = {}
        self._active    : set  = set()
        self._frame     : int  = 0

    def update(self, current_ids: list) -> set:
        """
        อัปเดตด้วย ID ที่เห็นในเฟรมนี้
        Returns: set ของ ID ที่ "ยืนยันแล้ว" และอยู่ใน current_ids
        """
        self._frame += 1

        for pid in current_ids:
            self._seen[pid]      = self._seen.get(pid, 0) + 1
            self._last_seen[pid] = self._frame
            if self._seen[pid] >= self.MIN_FRAMES:
                self._active.add(pid)

        stale = [pid for pid, last in self._last_seen.items()
                 if self._frame - last > self.EXPIRE_FRAMES]
        for pid in stale:
            self._active.discard(pid)
            self._seen.pop(pid, None)
            self._last_seen.pop(pid, None)

        return self._active & set(current_ids)


# ─────────────────────────────────────────────────────
#  BallMotionTracker — ติดตามลูกบาสแบบกลาง
# ─────────────────────────────────────────────────────

@dataclass
class BallMotionState:
    """
    Snapshot การเคลื่อนที่ของลูกบาสใน 1 เฟรม

    center        : จุดกึ่งกลางลูกบาส หรือ None ถ้าไม่เจอ
    velocity      : ระยะที่ลูกเคลื่อนจากเฟรมก่อนหน้า (px/frame)
    delta_y       : การเปลี่ยนแกน Y จากเฟรมก่อนหน้า
    dribble_event : True เมื่อบอลเปลี่ยนทิศจากลงเป็นขึ้นชัดเจน
    is_still      : True เมื่อบอลเคลื่อนช้าพอจะถือว่า "พักในมือ"
    detected      : เฟรมนี้เจอลูกหรือไม่
    lost_frames   : จำนวนเฟรมต่อเนื่องที่ไม่เจอลูก
    in_lost_grace : ยังอยู่ในช่วงผ่อนผันหลังบอลหายชั่วคราว
    """
    center: tuple | None = None
    velocity: float = 0.0
    delta_y: float | None = None
    dribble_event: bool = False
    is_still: bool = False
    detected: bool = False
    lost_frames: int = 0
    in_lost_grace: bool = False


class BallMotionTracker:
    """
    ติดตาม motion ของลูกบาสแบบ reusable ให้ทุก foul rule ใช้ข้อมูลชุดเดียวกัน

    หลักการ:
      - dribble_event: บอลเคลื่อนลงเร็วในเฟรมก่อน แล้วเด้งขึ้นเร็วในเฟรมนี้
      - is_still: ความเร็วลูกต่ำกว่า threshold ที่ scale ตาม shoulder_width
      - lost grace: ลูกหายจาก detector สั้นๆ แต่ยังไม่ reset history ทันที
    """

    DRIBBLE_BOUNCE_THRESHOLD = 18  # px/frame
    BALL_STILL_RATIO = 0.08
    BALL_STILL_MIN = 6
    LOST_GRACE_FRAMES = 8

    def __init__(self):
        self._prev_center = None
        self._prev_delta_y = None
        self._lost_frames = 0

    def update(self, ball_center, shoulder_width: float = 100.0) -> BallMotionState:
        if ball_center is None:
            self._lost_frames += 1
            in_grace = self._lost_frames <= self.LOST_GRACE_FRAMES
            if not in_grace:
                self._prev_center = None
                self._prev_delta_y = None
            return BallMotionState(
                center=None,
                detected=False,
                lost_frames=self._lost_frames,
                in_lost_grace=in_grace,
            )

        ball_center = (float(ball_center[0]), float(ball_center[1]))
        self._lost_frames = 0

        if self._prev_center is None:
            self._prev_center = ball_center
            return BallMotionState(
                center=ball_center,
                detected=True,
                is_still=False,
            )

        velocity = get_dist(ball_center, self._prev_center)
        delta_y = ball_center[1] - self._prev_center[1]

        dribble_event = (
            self._prev_delta_y is not None and
            self._prev_delta_y > self.DRIBBLE_BOUNCE_THRESHOLD and
            delta_y < -self.DRIBBLE_BOUNCE_THRESHOLD
        )

        still_threshold = max(
            shoulder_width * self.BALL_STILL_RATIO,
            self.BALL_STILL_MIN,
        )
        is_still = velocity < still_threshold

        self._prev_center = ball_center
        self._prev_delta_y = delta_y

        return BallMotionState(
            center=ball_center,
            velocity=velocity,
            delta_y=delta_y,
            dribble_event=dribble_event,
            is_still=is_still,
            detected=True,
            lost_frames=0,
            in_lost_grace=False,
        )

    def reset(self):
        self._prev_center = None
        self._prev_delta_y = None
        self._lost_frames = 0


# ─────────────────────────────────────────────────────
#  PoseQuality — ประเมินคุณภาพ pose แยกตาม rule
# ─────────────────────────────────────────────────────

@dataclass
class PoseQuality:
    """
    ค่า visibility เฉลี่ยของ keypoint กลุ่มสำคัญ

    overall_score : ภาพรวม full-body
    core_score    : shoulder/hip ใช้ยืนยันว่า crop เป็นคนจริง
    hand_score    : wrist/index/thumb ใช้ Double Dribble, Carrying, Held Ball
    foot_score    : hip/knee/ankle ใช้ Traveling
    visible_ratio : สัดส่วน keypoints ที่ visibility ถึงขั้นต่ำ
    """
    overall_score: float = 0.0
    core_score: float = 0.0
    hand_score: float = 0.0
    foot_score: float = 0.0
    visible_ratio: float = 0.0

    def percent(self, score_name: str = "overall_score") -> int:
        return int(round(getattr(self, score_name) * 100))


def _visibility_of(landmarks_px: dict, landmark) -> float:
    pt = landmarks_px.get(landmark.value)
    if pt is None:
        return 0.0
    if len(pt) < 3:
        return 1.0
    return max(0.0, min(1.0, float(pt[2])))


def _mean_visibility(landmarks_px: dict, landmarks: list) -> float:
    if not landmarks:
        return 0.0
    return sum(_visibility_of(landmarks_px, lm) for lm in landmarks) / len(landmarks)


def evaluate_pose_quality(landmarks_px: dict, mp_pose, vis_min: float = 0.40) -> PoseQuality:
    """
    ประเมิน pose quality เพื่อให้ rule engine ใช้ตัดสินแบบ rule-specific
    ไม่ใช้ threshold เดียว reject ทุก rule เพราะแต่ละ foul ต้องใช้ keypoints คนละชุด
    """
    core = [
        mp_pose.PoseLandmark.LEFT_SHOULDER,
        mp_pose.PoseLandmark.RIGHT_SHOULDER,
        mp_pose.PoseLandmark.LEFT_HIP,
        mp_pose.PoseLandmark.RIGHT_HIP,
    ]
    hands = [
        mp_pose.PoseLandmark.LEFT_WRIST,
        mp_pose.PoseLandmark.RIGHT_WRIST,
        mp_pose.PoseLandmark.LEFT_INDEX,
        mp_pose.PoseLandmark.RIGHT_INDEX,
        mp_pose.PoseLandmark.LEFT_THUMB,
        mp_pose.PoseLandmark.RIGHT_THUMB,
    ]
    feet = [
        mp_pose.PoseLandmark.LEFT_HIP,
        mp_pose.PoseLandmark.RIGHT_HIP,
        mp_pose.PoseLandmark.LEFT_KNEE,
        mp_pose.PoseLandmark.RIGHT_KNEE,
        mp_pose.PoseLandmark.LEFT_ANKLE,
        mp_pose.PoseLandmark.RIGHT_ANKLE,
    ]
    all_rule_points = core + hands + feet

    visible = sum(1 for lm in all_rule_points if _visibility_of(landmarks_px, lm) >= vis_min)
    return PoseQuality(
        overall_score=_mean_visibility(landmarks_px, all_rule_points),
        core_score=_mean_visibility(landmarks_px, core),
        hand_score=_mean_visibility(landmarks_px, hands),
        foot_score=_mean_visibility(landmarks_px, feet),
        visible_ratio=visible / len(all_rule_points),
    )


# ─────────────────────────────────────────────────────
#  FoulLogger — บันทึก CSV
# ─────────────────────────────────────────────────────

class FoulLogger:
    """
    บันทึกฟาวล์ลง CSV พร้อม Cooldown ป้องกัน Log ซ้ำรัวๆ

    Usage:
        logger = FoulLogger("logs.csv", cooldown_sec=3.0)
        logger.log_foul(1, "TRAVELING")
    """

    CSV_HEADERS = ["Date_Time", "Player_ID", "Foul_Type"]

    def __init__(self, filename: str = "basketball_foul_logs.csv",
                 cooldown_sec: float = 3.0):
        self.filename     = filename
        self.cooldown_sec = cooldown_sec
        self._last_logged : dict = {}

        if not os.path.exists(self.filename):
            self._write_row(self.CSV_HEADERS, mode='w')

    def log_foul(self, player_id: int, foul_type: str) -> bool:
        """บันทึกถ้าพ้น Cooldown"""
        now = time.time()
        # ใช้ foul type ไม่เกิน 20 ตัวอักษรแรกเป็น key
        # กันกรณี velocity ต่างกันทุกเฟรมทำให้ key ต่างกันทุกเฟรม
        foul_key = foul_type[:20].strip()
        key = f"{player_id}_{foul_key}"

        if (key in self._last_logged and
                (now - self._last_logged[key]) < self.cooldown_sec):
            return False

        self._last_logged[key] = now
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
        self._write_row([ts, f"Player_{player_id}", foul_type])
        print(f"📝 [LOG] {ts} | Player {player_id} | {foul_type}")
        return True

    def _write_row(self, row: list, mode: str = 'a'):
        with open(self.filename, mode=mode, newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(row)


class FoulEventLogger:
    """
    บันทึก foul event แบบละเอียดแยกจาก log เดิม เพื่อใช้คำนวณ QA/Accuracy
    โดยไม่ทำให้ basketball_foul_logs.csv เก่าที่มี 3 คอลัมน์พัง
    """

    CSV_HEADERS = [
        "Event_ID",
        "Date_Time",
        "Session_ID",
        "Frame_Index",
        "Player_ID",
        "Foul_Type",
        "Replay_Path",
        "Camera_ID",
        "Pipeline_Tag",
        "Hand_Refinement_Enabled",
    ]

    def __init__(self, filename: str = "logs/foul_events.csv"):
        self.filename = filename
        parent = os.path.dirname(self.filename)
        if parent:
            os.makedirs(parent, exist_ok=True)
        if not os.path.exists(self.filename):
            self._write_row(self.CSV_HEADERS, mode="w")
        else:
            self._ensure_schema()

    def log_event(
        self,
        *,
        session_id: str,
        frame_index: int,
        player_id: int,
        foul_type: str,
        replay_path: str,
        camera_id: int | str = "",
        pipeline_tag: str = "",
        hand_refinement_enabled: bool | str = "",
    ) -> str:
        event_id = uuid.uuid4().hex[:12]
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self._write_row([
            event_id,
            ts,
            session_id,
            frame_index,
            f"Player_{player_id}",
            foul_type,
            replay_path,
            camera_id,
            pipeline_tag,
            int(bool(hand_refinement_enabled)) if hand_refinement_enabled != "" else "",
        ])
        return event_id

    def _write_row(self, row: list, mode: str = "a"):
        with open(self.filename, mode=mode, newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)

    def _ensure_schema(self):
        """ขยาย schema เดิมแบบ backward-compatible ก่อน append event รุ่นใหม่."""
        with open(self.filename, "r", newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        if not rows:
            self._write_row(self.CSV_HEADERS, mode="w")
            return
        header = rows[0]
        if header == self.CSV_HEADERS:
            return

        missing_headers = [col for col in self.CSV_HEADERS if col not in header]
        if not missing_headers:
            return

        expanded_rows = [header + missing_headers]
        for row in rows[1:]:
            expanded_rows.append(row + [""] * len(missing_headers))
        with open(self.filename, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(expanded_rows)

def is_point_near_box(px, py, box, margin=10):
    bx1, by1, bx2, by2 = box
    return (bx1 - margin <= px <= bx2 + margin) and (by1 - margin <= py <= by2 + margin)


#มีการใช้สูตรคณิตศาสตร์ในการคำนวณ
class EMAFilter:
    """ลดการสั่น (Jitter) ของพิกัดด้วย Exponential Moving Average"""
    def __init__(self, alpha=0.3):
        self.alpha = alpha
        self.val = None

    def update(self, new_val):
        if self.val is None:
            self.val = new_val
        else:
            self.val = self.alpha * new_val + (1 - self.alpha) * self.val
        return self.val

from collections import deque

class TemporalVoter:
    """ระบบ Voting ป้องกันการตัดสินพลาดชั่วขณะ (False Positive)"""
    def __init__(self, window_size=5, threshold=3):
        self.history = deque(maxlen=window_size)
        self.threshold = threshold

    def vote(self, detection_result):
        # detection_result เป็น True/False
        self.history.append(1 if detection_result else 0)
        # ถ้าผลรวมคะแนนโหวต >= เกณฑ์ที่ตั้งไว้ ถือว่าเกิดขึ้นจริง
        return sum(self.history) >= self.threshold


# ─────────────────────────────────────────────────────
#  AccuracyTracker — รายงานความแม่นยำ
# ─────────────────────────────────────────────────────

class AccuracyTracker:
    """
    ติดตาม Activation Rate ของแต่ละ Rule
    พิมพ์รายงานสรุปเมื่อ Session จบ
    """

    def __init__(self):
        self._stats : dict = defaultdict(
            lambda: {"total": 0, "detected": 0,
                     "consecutive": 0, "max_consecutive": 0}
        )
        self._session_start = time.time()
        self._total_frames  = 0

    def record(self, foul_type: str, detected: bool):
        s = self._stats[foul_type]
        s["total"] += 1
        if detected:
            s["detected"]        += 1
            s["consecutive"]     += 1
            s["max_consecutive"]  = max(s["max_consecutive"],
                                        s["consecutive"])
        else:
            s["consecutive"] = 0

    def tick_frame(self):
        self._total_frames += 1

    def print_report(self):
        elapsed = time.time() - self._session_start
        fps     = self._total_frames / elapsed if elapsed > 0 else 0

        print("\n" + "═"*60)
        print("  📊  AI BASKETBALL REFEREE — SESSION REPORT")
        print("═"*60)
        print(f"  Duration : {elapsed:.1f}s  "
              f"({self._total_frames} frames @ {fps:.1f} FPS)")
        print("─"*60)
        print(f"  {'Rule':<22} {'Checks':>7} {'Hits':>7} "
              f"{'Rate':>7} {'MaxStreak':>10}")
        print("─"*60)

        for foul_type, s in sorted(self._stats.items()):
            total  = s["total"]
            det    = s["detected"]
            rate   = (det/total*100) if total > 0 else 0.0
            streak = s["max_consecutive"]
            print(f"  {foul_type:<22} {total:>7} {det:>7} "
                  f"{rate:>6.1f}%  {streak:>9}")

        print("═"*60 + "\n")


        
