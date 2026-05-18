"""
fouls/double_dribble.py — ตรวจจับ Double Dribble
--------------------------------------------------
ปัญหาของเวอร์ชันเดิม:
  1. ใช้ landmarks.x / landmarks.y แบบ Normalized (0–1)
     แต่ ball_center เป็น Pixel → ระยะห่างผิดพลาด 100%
  2. State Machine ไม่ Reset เมื่อผู้เล่นชู้ต/ส่งบอล

การแก้ไข:
  - รับ landmarks_px (Pixel) แบบเดียวกับไฟล์อื่นๆ
  - ยืนยันการ HOLD หลายเฟรมก่อนถือว่า "หยุดเลี้ยง"
  - เพิ่ม Timeout/ball-lost grace เพื่อกัน detection หายชั่วคราว
  - ใช้ทิศทางการเด้งของบอลช่วยยืนยันการเริ่ม dribble ใหม่
"""

from utils import get_dist


class DoubleDribbleDetector:
    """
    ตรวจจับ Double Dribble ด้วย State Machine

    States:
        IDLE      → ยังไม่แตะบอล (เริ่มต้น / หลัง Reset)
        DRIBBLING → เลี้ยงบอลด้วยมือเดียว
        HOLDING   → จับบอลค้างหลังเคยเลี้ยง (หยุดเลี้ยงแล้ว)
        VIOLATION → ตรวจพบฟาวล์ (รอ Reset)

    Transitions:
        IDLE      + touch_one  → DRIBBLING
        DRIBBLING + holding_confirmed → HOLDING
        HOLDING   + dribble_event     → VIOLATION  ← Double Dribble!
        any       + no touch (timeout) → IDLE
    """

    HOLD_THRESHOLD   = 110   # ระยะ (px) ที่ถือว่า "จับบอล" ด้วยมือนั้น
    DRIBBLE_THRESHOLD = 140  # ระยะ (px) ที่ถือว่า "แตะบอล" ขณะเลี้ยง
    TIMEOUT_FRAMES   = 45    # เฟรมที่ไม่แตะบอลแล้ว Reset State
    VIOLATION_COOLDOWN = 30  # เฟรมที่ค้าง VIOLATION ก่อน Auto Reset
    HOLD_CONFIRM_FRAMES = 12  # ต้องถือบอลต่อเนื่องก่อนนับว่า gather/หยุดเลี้ยง
    BALL_LOST_GRACE_FRAMES = 8  # กัน ball detection หายสั้นๆ แล้ว state หลุด
    DRIBBLE_BOUNCE_THRESHOLD = 18  # px/frame — บอลเปลี่ยนทิศจากลงเป็นขึ้น
    PASS_RESET_DISTANCE = 260  # px — บอลห่างมือมากพร้อมความเร็วสูง = น่าจะ pass/shot

    def __init__(self):
        self.state = "IDLE"
        self._no_touch_frames = 0
        self._violation_frames = 0
        self._prev_ball_center = None   # สำหรับเช็ค ball velocity
        self._prev_delta_y = None
        self._hold_frames = 0
        self._lost_ball_frames = 0

    # ── ค่า Threshold อื่นๆ ──
    BALL_FAST_THRESHOLD = 35  # px/frame — บอลเคลื่อนเร็วมาก = น่าจะถูกส่ง/ชูตแล้ว

    def check(self, landmarks_px: dict, mp_pose, ball_center,
              hand_landmarks_px=None) -> tuple:
        """
        ตรวจสอบ Double Dribble ใน 1 เฟรม

        Parameters:
            landmarks_px : dict {landmark_id: (x, y)} — Pixel coordinates
            mp_pose      : mediapipe.solutions.pose module
            ball_center  : tuple (x, y) หรือ None

        Returns:
            (is_violation: bool, message: str)
        """
        if ball_center is None:
            self._lost_ball_frames += 1
            if self._lost_ball_frames >= self.BALL_LOST_GRACE_FRAMES:
                self._no_touch_frames += 1
                self._hold_frames = 0
                if self._no_touch_frames >= self.TIMEOUT_FRAMES:
                    self.reset()
            return False, f"State: {self.state}"
        self._lost_ball_frames = 0

        # ── Ball Velocity Auto-Reset: ถ้าบอลเคลื่อนเร็วมาก → น่าจะถูกส่ง/ชูต ──
        ball_vel = 0.0
        dribble_event = False
        if self._prev_ball_center is not None:
            ball_vel = get_dist(ball_center, self._prev_ball_center)
            delta_y = ball_center[1] - self._prev_ball_center[1]
            if (
                self._prev_delta_y is not None
                and self._prev_delta_y > self.DRIBBLE_BOUNCE_THRESHOLD
                and delta_y < -self.DRIBBLE_BOUNCE_THRESHOLD
            ):
                dribble_event = True
            self._prev_delta_y = delta_y
        self._prev_ball_center = ball_center

        # ── VIOLATION Auto Reset: ค้างสถานะครบกำหนดแล้ว Reset ──
        if self.state == "VIOLATION":
            self._violation_frames += 1
            if self._violation_frames >= self.VIOLATION_COOLDOWN:
                self.state = "IDLE"
                self._violation_frames = 0
            return False, f"State: {self.state}"

        # ดึงพิกัด Pixel ของข้อมือ (ไม่ต้องแปลงอีก เพราะ landmarks_px เป็น Pixel แล้ว)
        r_wrist = landmarks_px.get(mp_pose.PoseLandmark.RIGHT_WRIST.value)
        l_wrist = landmarks_px.get(mp_pose.PoseLandmark.LEFT_WRIST.value)
        if r_wrist is None or l_wrist is None:
            return False, f"State: {self.state}"

        dist_r = get_dist(r_wrist, ball_center)
        dist_l = get_dist(l_wrist, ball_center)
        min_dist = min(dist_r, dist_l)
        refined_dists = []
        for hand in hand_landmarks_px or []:
            for idx in (0, 4, 8, 12, 16, 20):
                pt = hand["points"].get(idx)
                if pt is not None:
                    refined_dists.append(get_dist(pt, ball_center))
        min_touch_dist = min([min_dist, *refined_dists]) if refined_dists else min_dist

        # ─── จำแนกสถานะการสัมผัสบอล ───
        touching_right = dist_r < self.DRIBBLE_THRESHOLD
        touching_left  = dist_l < self.DRIBBLE_THRESHOLD
        holding_right = dist_r < self.HOLD_THRESHOLD
        holding_left  = dist_l < self.HOLD_THRESHOLD
        holding_both  = holding_right and holding_left
        holding_one   = holding_right or holding_left
        touching_any   = touching_right or touching_left or min_touch_dist < self.DRIBBLE_THRESHOLD

        if self.state == "HOLDING" and ball_vel > self.BALL_FAST_THRESHOLD and min_dist > self.PASS_RESET_DISTANCE:
            self.reset()
            return False, f"State: {self.state}"

        # ─── Timeout: ถ้าไม่แตะบอลนานเกิน Threshold → Reset ───
        if not touching_any:
            self._no_touch_frames += 1
            self._hold_frames = 0
            if self._no_touch_frames >= self.TIMEOUT_FRAMES:
                self.reset()
            return False, f"State: {self.state}"
        else:
            self._no_touch_frames = 0

        if holding_both or (holding_one and ball_vel < self.BALL_FAST_THRESHOLD * 0.5):
            self._hold_frames += 1
        else:
            self._hold_frames = 0

        holding_confirmed = self._hold_frames >= self.HOLD_CONFIRM_FRAMES

        # ─── State Machine ───
        violation = False

        if self.state == "HOLDING":
            if dribble_event or (touching_any and not holding_confirmed and ball_vel > self.BALL_FAST_THRESHOLD):
                # เคยหยุดเลี้ยงแล้วบอลกลับมาเด้ง/แตะมือเดียวอีกครั้ง = Double Dribble
                violation = True
                self.state = "VIOLATION"
                self._violation_frames = 0

        elif self.state == "DRIBBLING":
            if holding_confirmed:
                self.state = "HOLDING"

        elif self.state == "IDLE":
            if dribble_event or touching_any:
                self.state = "DRIBBLING"

        if violation:
            return True, "DOUBLE DRIBBLE"

        return False, f"State: {self.state}"

    def reset(self):
        """รีเซ็ตสถานะ (เรียกเมื่อ Shot หรือ Pass ออกไป)"""
        self.state = "IDLE"
        self._no_touch_frames = 0
        self._violation_frames = 0
        self._hold_frames = 0
        self._lost_ball_frames = 0
        self._prev_ball_center = None
        self._prev_delta_y = None
