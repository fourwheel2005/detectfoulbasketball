import cv2
import numpy as np
from collections import deque
from utils import TemporalVoter


class Kalman1D:
    """ Wrapper สำหรับ cv2.KalmanFilter แบบ 1 มิติ (แกน Y) """
    def __init__(self):
        self.kf = cv2.KalmanFilter(2, 1)
        self.kf.transitionMatrix   = np.array([[1, 1], [0, 1]], np.float32)
        self.kf.measurementMatrix  = np.array([[1, 0]], np.float32)
        self.kf.processNoiseCov    = np.array([[1e-4, 0], [0, 1e-4]], np.float32)
        self.kf.measurementNoiseCov = np.array([[1e-2]], np.float32)
        self.kf.errorCovPost       = np.eye(2, dtype=np.float32)
        self.is_initialized = False

    def update(self, measurement):
        self.kf.predict()
        if not self.is_initialized:
            self.kf.statePost = np.array([[measurement], [0]], np.float32)
            self.is_initialized = True
            return measurement
        meas_array = np.array([[measurement]], np.float32)
        self.kf.correct(meas_array)
        return self.kf.statePost[0, 0]


class FootStepTracker:
    """
    ตรวจก้าวเดียวสำหรับเท้าหนึ่งข้าง (State Machine)

    ใน Image Coordinates (OpenCV):
        Y สูง (ตัวเลขมาก) = เท้าอยู่บนพื้น (ต่ำบนจอ)
        Y ต่ำ (ตัวเลขน้อย) = เท้าลอยอยู่ (สูงบนจอ)

    States:
        GROUNDED → เท้าอยู่บนพื้น
        LIFTED   → เท้าลอยอยู่กลางอากาศ

    นับก้าวเมื่อ: LIFTED → GROUNDED (เท้ากระทบพื้น)
    """

    def __init__(self):
        self._y_history: deque = deque(maxlen=4)
        self._state: str = "GROUNDED"
        self._cooldown_left: int = 0

    def update(self, y: float, lift_threshold: float,
               cooldown_frames: int = 0) -> bool:
        """Returns True ถ้าเพิ่งตรวจพบว่าเท้ากระทบพื้น (= 1 ก้าว)"""
        self._y_history.append(y)

        if self._cooldown_left > 0:
            self._cooldown_left -= 1
            return False

        if len(self._y_history) < 3:
            return False

        h = list(self._y_history)

        if self._state == "GROUNDED":
            # เท้าถูกยก: Y ลดลงมากกว่า threshold (ลอยขึ้นในจอ)
            if h[-3] - h[-1] > lift_threshold:
                self._state = "LIFTED"

        elif self._state == "LIFTED":
            # เท้ากระทบพื้น: Y เพิ่มขึ้น (ลงมาในจอ)
            if h[-1] - h[-2] > lift_threshold * 0.4:
                self._state = "GROUNDED"
                self._cooldown_left = cooldown_frames
                return True  # ← นับ 1 ก้าว!

        return False

    def reset(self):
        self._state = "GROUNDED"
        self._cooldown_left = 0
        self._y_history.clear()


class TravelingDetector:
    """
    ตรวจ Traveling ด้วย Foot-Strike Detection (กฎ NBA)

    กฎ NBA:
      - Gather Step: เฟรมแรกหลังหยิบบอลไม่นับ
      - หลัง Gather: อนุญาต 2 ก้าว → ก้าวที่ 3 = TRAVELING
      - Jump Stop (ทั้ง 2 เท้าลงภายใน JSYNC_FRAMES): นับเป็น 1 ก้าว

    วิธีนับก้าว:
      - ตรวจ foot-strike: FootStepTracker เปลี่ยนจาก LIFTED → GROUNDED
      - แต่ละ foot-strike = 1 ก้าว
    """

    MAX_STEPS    = 2     # ก้าวสูงสุด (NBA)
    LIFT_RATIO   = 0.18  # สัดส่วน shoulder_width สำหรับ lift threshold
    LIFT_MIN     = 14    # ค่าต่ำสุด (px) กัน ankle jitter ตอนผู้เล่นอยู่ไกล
    LIFT_MAX     = 42    # ค่าสูงสุด (px) กัน threshold ใหญ่เกินเมื่อผู้เล่นอยู่ใกล้กล้อง
    GATHER_FRAMES = 10   # Grace period หลังหยิบบอล (gather step)
    JSYNC_FRAMES  = 2    # เฟรム tolerance สำหรับ jump stop (นับครั้งเดียว)
    STEP_COOLDOWN_FRAMES = 7   # debounce หลังนับ foot-strike แล้ว
    LOST_HOLDING_GRACE_FRAMES = 20  # กัน ball/holding detection หายชั่วคราว
    ANKLE_VIS_MIN = 0.50  # visibility ขั้นต่ำของ ankle
    POSSESSION_CONFIRM_FRAMES = 2  # ต้องถือบอลต่อเนื่องเล็กน้อยก่อนเริ่มนับก้าว
    HELD_BALL_PAUSE_FRAMES = 12

    def __init__(self):
        self.steps: int = 0
        self.kf_l  = Kalman1D()
        self.kf_r  = Kalman1D()
        self.voter = TemporalVoter(window_size=5, threshold=4)

        self._step_l = FootStepTracker()
        self._step_r = FootStepTracker()

        self._gather_left: int = 0
        self._last_step_frame: int = -10   # กัน jump stop นับ 2 ก้าว
        self._frame_n: int = 0
        self.is_holding_prev: bool = False
        self._lost_holding_frames: int = self.LOST_HOLDING_GRACE_FRAMES
        self._holding_confirm_frames: int = 0
        self._held_ball_pause_left: int = 0

    def check(self, landmarks_px, mp_pose, is_holding, shoulder_width, frame_h,
              dribble_event: bool = False, ball_motion=None, fps: float = 0.0,
              held_ball_candidate: bool = False):
        """
        ตรวจจับ Traveling

        Returns: (is_violation: bool, message: str)
        """
        self._frame_n += 1

        fps = float(fps or 0.0)
        if fps > 0:
            gather_frames = max(4, int(round(fps * 0.35)))
            cooldown_frames = max(3, int(round(fps * 0.22)))
            lost_grace_frames = max(6, int(round(fps * 0.65)))
            held_pause_frames = max(4, int(round(fps * 0.45)))
        else:
            gather_frames = self.GATHER_FRAMES
            cooldown_frames = self.STEP_COOLDOWN_FRAMES
            lost_grace_frames = self.LOST_HOLDING_GRACE_FRAMES
            held_pause_frames = self.HELD_BALL_PAUSE_FRAMES

        if held_ball_candidate:
            self._held_ball_pause_left = max(self._held_ball_pause_left, held_pause_frames)

        if self._held_ball_pause_left > 0:
            self._held_ball_pause_left -= 1
            self._step_l.reset()
            self._step_r.reset()
            return False, f"Steps: {self.steps} [held-ball pause]"

        l_ankle = landmarks_px.get(mp_pose.PoseLandmark.LEFT_ANKLE.value)
        r_ankle = landmarks_px.get(mp_pose.PoseLandmark.RIGHT_ANKLE.value)

        if l_ankle is None or r_ankle is None:
            return False, f"Steps: {self.steps}"

        if len(l_ankle) >= 3 and len(r_ankle) >= 3:
            if l_ankle[2] < self.ANKLE_VIS_MIN or r_ankle[2] < self.ANKLE_VIS_MIN:
                return False, f"Steps: {self.steps} [low ankle vis]"

        # ผ่าน Kalman Filter เพื่อลด noise
        l_y = self.kf_l.update(l_ankle[1])
        r_y = self.kf_r.update(r_ankle[1])

        # Dynamic lift threshold ปรับตามขนาดตัว พร้อม clamp กัน sensitivity แกว่งตามระยะกล้อง
        lift_threshold = min(
            max(shoulder_width * self.LIFT_RATIO, self.LIFT_MIN),
            self.LIFT_MAX,
        )

        # ถ้าลูกเด้งกลับขึ้นชัดเจน แปลว่ากำลัง dribble อยู่จริง
        # ให้คง possession state ไว้ แต่ไม่เอา ankle movement เฟรมนี้ไปนับก้าว
        ball_in_grace = bool(getattr(ball_motion, "in_lost_grace", False))
        if dribble_event or ball_in_grace:
            self._gather_left = max(self._gather_left, 1)
            self._step_l.reset()
            self._step_r.reset()
            self.is_holding_prev = is_holding
            if is_holding:
                self._lost_holding_frames = 0
                self._holding_confirm_frames = min(
                    self._holding_confirm_frames + 1,
                    self.POSSESSION_CONFIRM_FRAMES,
                )
            reason = "dribble" if dribble_event else "ball grace"
            return False, f"Steps: {self.steps} [{reason} th={lift_threshold:.1f}]"

        # ── Possession grace: ball/holding อาจหายชั่วคราวจาก occlusion ──
        if is_holding:
            self._holding_confirm_frames = min(
                self._holding_confirm_frames + 1,
                self.POSSESSION_CONFIRM_FRAMES,
            )
            possession_confirmed = self._holding_confirm_frames >= self.POSSESSION_CONFIRM_FRAMES
            possession_started = (
                self._lost_holding_frames >= self.LOST_HOLDING_GRACE_FRAMES
                and possession_confirmed
            )
            self._lost_holding_frames = 0
        else:
            self._holding_confirm_frames = 0
            self._lost_holding_frames += 1
            if self._lost_holding_frames < lost_grace_frames:
                self._step_l.update(l_y, lift_threshold, cooldown_frames)
                self._step_r.update(r_y, lift_threshold, cooldown_frames)
                return False, f"Steps: {self.steps} [holding grace]"
            else:
                self.steps = 0
                self._gather_left = 0
                self._step_l.reset()
                self._step_r.reset()
                self._last_step_frame = -10
                self.voter.history.clear()
                self.is_holding_prev = False
                return False, f"Steps: {self.steps}"

        if not possession_confirmed:
            self._step_l.update(l_y, lift_threshold, cooldown_frames)
            self._step_r.update(r_y, lift_threshold, cooldown_frames)
            return False, (
                f"Steps: {self.steps} [possession confirm "
                f"{self._holding_confirm_frames}/{self.POSSESSION_CONFIRM_FRAMES}]"
            )

        # ── Gather Step: Reset เมื่อเพิ่งหยิบบอลจริง หลังหมด grace ──
        if is_holding and (not self.is_holding_prev or possession_started):
            self.steps = 0
            self._gather_left = gather_frames
            self._step_l.reset()
            self._step_r.reset()
            self._last_step_frame = -10
            self.voter.history.clear()

        self.is_holding_prev = is_holding

        if not is_holding:
            return False, f"Steps: {self.steps}"

        # ── Gather Period: อัปเดต Kalman แต่ไม่นับก้าว ──
        if self._gather_left > 0:
            self._gather_left -= 1
            self._step_l.update(l_y, lift_threshold, cooldown_frames)
            self._step_r.update(r_y, lift_threshold, cooldown_frames)
            return False, f"Steps: {self.steps} [gather {self._gather_left} th={lift_threshold:.1f}]"

        # ── นับก้าวจริง ──
        step_l = self._step_l.update(l_y, lift_threshold, cooldown_frames)
        step_r = self._step_r.update(r_y, lift_threshold, cooldown_frames)

        if step_l:
            # Jump stop check: ถ้า 2 เท้าลงพร้อมกัน ≤ JSYNC_FRAMES → นับ 1 ก้าว
            if self._frame_n - self._last_step_frame > self.JSYNC_FRAMES:
                self.steps += 1
            self._last_step_frame = self._frame_n

        if step_r:
            if self._frame_n - self._last_step_frame > self.JSYNC_FRAMES:
                self.steps += 1
            self._last_step_frame = self._frame_n

        # ── ตัดสิน Violation ──
        is_foul_raw = self.steps > self.MAX_STEPS
        is_foul_confirmed = self.voter.vote(is_foul_raw)
        voter_score = sum(self.voter.history)

        if is_foul_confirmed:
            return True, f"TRAVELING ({self.steps} steps)"

        return False, (
            f"Steps: {self.steps} L={int(step_l)} R={int(step_r)} "
            f"th={lift_threshold:.1f} vote={voter_score}/{self.voter.threshold}"
        )
