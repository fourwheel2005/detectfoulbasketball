"""
referee.py — ศูนย์กลางการตัดสิน (Orchestrator)
------------------------------------------------
กฎทั้งหมดที่ตรวจสอบ:
    Rule 1 — Double Dribble   (State Machine)
    Rule 2 — Traveling        (Peak Detection + Rolling Average)
    Rule 3 — Carrying         (Wrist vs Index Y + Confirm Buffer)
    Rule 4 — Goaltending      (Parabolic Trajectory Analysis)
    Rule 5 — Held Ball / Jump Ball Situation
"""

from utils import (
    get_dist,
    AccuracyTracker,
    BallMotionTracker,
    evaluate_pose_quality,
)
from fouls.double_dribble import DoubleDribbleDetector
from fouls.traveling      import TravelingDetector
from fouls.carrying       import CarryingDetector
from fouls.goaltending    import GoaltendingDetector
from fouls.jump_ball      import JumpBallDetector

# ─────────────────────────────────────────────────────
#  Pose Validity Check (Module-level function)
# ─────────────────────────────────────────────────────

_MAX_MISSING     = 2    # ขาด Landmark หลักได้สูงสุดกี่จุด
VIS_THRESHOLD    = 0.40  # Landmark ที่ visibility < ค่านี้ ถือว่า "มองไม่เห็น"
VIS_CRITICAL_MIN = 0.55  # Landmark หลัก (Shoulder, Hip) ต้องสูงกว่านี้


def _is_pose_valid(landmarks_px: dict, mp_pose) -> tuple:
    """
    ตรวจสอบว่า Pose มี Landmark สำคัญครบและ visibility สูงพอ

    Conditions:
        1. Landmark หลัก 5 จุด ต้องขาดไม่เกิน _MAX_MISSING จุด
        2. Landmark หลัก (Shoulder, Hip) ต้องมี visibility >= VIS_CRITICAL_MIN
        3. Aspect Ratio ต้องสูงกว่ากว้าง (คนยืน/เดิน)

    Note: landmarks_px[idx] = (x, y, visibility)
    Returns:
        (is_valid: bool, reason: str)
    """
    critical = [
        mp_pose.PoseLandmark.LEFT_SHOULDER,
        mp_pose.PoseLandmark.RIGHT_SHOULDER,
        mp_pose.PoseLandmark.LEFT_HIP,
        mp_pose.PoseLandmark.RIGHT_HIP,
    ]
    required = [mp_pose.PoseLandmark.NOSE] + critical

    # ── ตรวจว่ามี Landmark ครบไหม ─────────────────────────
    missing = [lm for lm in required if lm.value not in landmarks_px]
    if len(missing) > _MAX_MISSING:
        return False, f"Pose incomplete ({len(missing)} key points missing)"

    # ── ตรวจ Visibility ของ Landmark หลัก ────────────────
    # landmarks_px[idx] = (x, y, visibility)  ← index [2]
    low_vis = []
    for lm in critical:
        pt = landmarks_px.get(lm.value)
        if pt is not None and len(pt) >= 3 and pt[2] < VIS_CRITICAL_MIN:
            low_vis.append(lm.name)
    if len(low_vis) > 1:          # ยอมให้ 1 จุดมองไม่ชัดได้ (เช่น ถูกบัง)
        return False, f"Low visibility: {low_vis}"

    # ── ตรวจ Aspect Ratio ─────────────────────────────────
    xs = [v[0] for v in landmarks_px.values()]
    ys = [v[1] for v in landmarks_px.values()]
    w  = max(xs) - min(xs)
    h  = max(ys) - min(ys)

    if w > 0 and h > 0 and (h / w) < 0.5:
        return False, "Aspect ratio invalid (likely arm/hand)"

    return True, ""


# ─────────────────────────────────────────────────────
#  BasketballRef — Main Orchestrator
# ─────────────────────────────────────────────────────

class BasketballRef:
    """
    จัดการ Detector ของแต่ละผู้เล่น (แยกกันตาม Player ID)
    และรวบรวม Violations + Info Texts ส่งกลับให้ main.py

    Attributes:
        HOLDING_DIST (int) : ระยะ (px) ที่ถือว่า "ถือบอล"
        _players     (dict): {player_id: {detector_key: DetectorInstance}}
        _latest_landmarks  : {player_id: landmarks_px} — ใช้หา opponent
        _latest_ball_motion: {player_id: BallMotionState} — ใช้แชร์ motion ของบอล
    """

    HOLDING_DIST = 120  # px
    HAND_RULE_VIS_MIN = 0.45
    CARRYING_HAND_VIS_MIN = 0.35
    JUMP_BALL_HAND_VIS_MIN = 0.30
    FOOT_RULE_VIS_MIN = 0.50
    CORE_RULE_VIS_MIN = 0.45

    def __init__(self):
        self._players           : dict = {}
        self._latest_landmarks  : dict = {}
        self._latest_hand_landmarks: dict = {}
        self._latest_ball_motion: dict = {}
        self.accuracy           = AccuracyTracker()
        self._rim_y_px          = None  # อัปเดตผ่าน set_rim_y()

    def set_rim_y(self, rim_y_px: int | None, rim_x_range=None):
        """
        อัปเดตตำแหน่ง Y ของห่วงบาส (pixel) ให้กับ GoaltendingDetector ทุก Player
        เรียกจาก main.py เมื่อ YOLO ตรวจเจอ Rim ใหม่แต่ละเฟรม
        """
        self._rim_y_px = rim_y_px
        for detectors in self._players.values():
            if "gt" in detectors:
                detectors["gt"].rim_y_px = rim_y_px
                detectors["gt"].rim_x_range = rim_x_range

    # ─── Public API ───────────────────────────────────

   # ไฟล์ referee.py (ตัดมาเฉพาะส่วนฟังก์ชัน process เพื่ออัปเดต)
    def process(self, p_id, landmarks_px, mp_pose, ball_box, frame_w, frame_h,
                hand_landmarks_px=None):
        detectors = self._get_detectors(p_id)
        violations = []
        info_texts = []
        hand_landmarks_px = hand_landmarks_px or []

        # 📌 1. Dynamic Scale: หาความกว้างไหล่ (Shoulder Width) เพื่อใช้เป็นเกณฑ์วัด
        l_shoulder = landmarks_px[mp_pose.PoseLandmark.LEFT_SHOULDER]
        r_shoulder = landmarks_px[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        from utils import get_dist, is_point_near_box
        shoulder_width = get_dist(l_shoulder, r_shoulder)
        if shoulder_width < 10: shoulder_width = 10 # ป้องกันค่า 0

        pose_quality = evaluate_pose_quality(landmarks_px, mp_pose)
        hand_pose_ok = pose_quality.hand_score >= self.HAND_RULE_VIS_MIN
        foot_pose_ok = pose_quality.foot_score >= self.FOOT_RULE_VIS_MIN
        core_pose_ok = pose_quality.core_score >= self.CORE_RULE_VIS_MIN

        # 📌 2. Dynamic Possession: เช็คการครองบอลจาก Bounding Box และปลายนิ้ว
        is_holding = False
        ball_center = None
        if ball_box is not None:
            bx1, by1, bx2, by2 = ball_box
            ball_center = ((bx1+bx2)/2, (by1+by2)/2)
            
            # Margin แปรผันตามขนาดตัว (ไหล่) และใช้ wrist/index/thumb
            # เพราะ Carrying มักมีนิ้วโดนลูกบัง ทำให้ index อย่างเดียวไม่ stable
            margin = int(max(shoulder_width * 0.25, 18))
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
            for hand in hand_landmarks_px:
                hand_points.extend(hand["points"].values())

            ball_radius_hint = max((bx2 - bx1), (by2 - by1)) * 0.75
            center_threshold = max(shoulder_width * 0.55, ball_radius_hint, 55)
            for pt in hand_points:
                if (
                    is_point_near_box(pt[0], pt[1], ball_box, margin) or
                    get_dist((pt[0], pt[1]), ball_center) <= center_threshold
                ):
                    is_holding = True
                    break

        ball_motion = detectors["ball"].update(ball_center, shoulder_width)
        self._latest_ball_motion[p_id] = ball_motion
        self._latest_landmarks[p_id] = landmarks_px
        self._latest_hand_landmarks[p_id] = hand_landmarks_px

        # --- Check Rules ---
        held_ball_candidate = False
        
        # Double Dribble — ต้องเห็นมือดีพอ เพราะ rule ใช้ wrist ↔ ball distance
        if hand_pose_ok:
            is_dd, msg_dd = detectors["dd"].check(
                landmarks_px, mp_pose, ball_center,
                hand_landmarks_px=hand_landmarks_px,
            )
            if is_dd: violations.append(msg_dd)
        else:
            info_texts.append(f"PoseQ hand low: {pose_quality.percent('hand_score')}%")

        # Held Ball / Jump Ball Situation
        # ตรวจให้เร็วกว่า Traveling เพื่อกันเคสแย่งบอลแล้วระบบนับก้าวผิดเป็น Traveling
        opponent_lm = self._find_nearest_opponent(p_id, landmarks_px)
        opponent_id = self._find_nearest_opponent_id(p_id, landmarks_px)
        opponent_hand_ok = False
        if opponent_lm is not None:
            opponent_quality = evaluate_pose_quality(opponent_lm, mp_pose)
            opponent_hand_ok = opponent_quality.hand_score >= self.JUMP_BALL_HAND_VIS_MIN
        elif ball_center is not None:
            info_texts.append("HeldBall skip: no nearby opponent")

        if pose_quality.hand_score >= self.JUMP_BALL_HAND_VIS_MIN and opponent_hand_ok and core_pose_ok:
            is_jb, msg_jb = detectors["jb"].check(
                landmarks_px, mp_pose, opponent_lm,
                ball_center=ball_center,
                ball_motion=ball_motion,
                hand_landmarks_px=hand_landmarks_px,
                opponent_hand_landmarks_px=self._latest_hand_landmarks.get(opponent_id, []),
            )
            if is_jb:
                held_ball_candidate = True
                violations.append(msg_jb)
            elif msg_jb:
                held_ball_candidate = msg_jb.startswith("HeldBall candidate")
                info_texts.append(msg_jb)
        elif ball_center is not None and opponent_lm is not None:
            info_texts.append(
                f"HeldBall skip: handQ {pose_quality.percent('hand_score')}%"
            )

        # 📌 3. Traveling (ส่ง shoulder_width ไปคำนวณ Dynamic Threshold ด้วย)
        if held_ball_candidate:
            info_texts.append("Steps paused [held ball candidate]")
        elif foot_pose_ok:
            is_tr, msg_tr = detectors["tr"].check(
                landmarks_px, mp_pose, is_holding, shoulder_width, frame_h,
                dribble_event=ball_motion.dribble_event,
            )
            if is_tr: violations.append(msg_tr)
            elif "Steps" in msg_tr: info_texts.append(msg_tr)
        else:
            info_texts.append(f"PoseQ foot low: {pose_quality.percent('foot_score')}%")

        # Carrying (ใช้ threshold มือเฉพาะ rule นี้ เพราะต้องดูมือเดียวที่เกี่ยวกับบอล)
        if pose_quality.hand_score >= self.CARRYING_HAND_VIS_MIN:
            is_ca, msg_ca = detectors["ca"].check(
                landmarks_px, mp_pose, is_holding, shoulder_width, ball_center,
                hand_landmarks_px=hand_landmarks_px,
            )
            if is_ca: violations.append(msg_ca)
            elif msg_ca: info_texts.append(msg_ca)

        # Goaltending (ตรวจวิถีลูกและมือขณะกำลังลงตะกร้า)
        if ball_center is not None and hand_pose_ok:
            hands_pos = []
            for wrist_lm in [mp_pose.PoseLandmark.RIGHT_WRIST, mp_pose.PoseLandmark.LEFT_WRIST]:
                pt = landmarks_px.get(wrist_lm.value)
                if pt:
                    hands_pos.append((pt[0], pt[1]))
            is_gt, msg_gt = detectors["gt"].check(ball_center, hands_pos, frame_h)
            if is_gt: violations.append(msg_gt)
            elif msg_gt: info_texts.append(msg_gt)

        return violations, info_texts

    def cleanup_player(self, player_id: int):
        """
        เรียกเมื่อ Player ID หายออกจากเฟรม
        - Reset JumpBallDetector state
        - ลบ landmarks ออกจาก cache

        ควรเรียกจาก main.py เมื่อ valid_ids ลดลง
        """
      #  if player_id in self._players:
         #   self._players[player_id]["jb"].reset()
        if player_id in self._players and "ball" in self._players[player_id]:
            self._players[player_id]["ball"].reset()
        self._latest_landmarks.pop(player_id, None)
        self._latest_hand_landmarks.pop(player_id, None)
        self._latest_ball_motion.pop(player_id, None)

    # ─── Private Helpers ──────────────────────────────

    def _get_detectors(self, player_id: int) -> dict:
        """สร้างหรือดึงชุด Detector สำหรับผู้เล่นแต่ละคน"""
        if player_id not in self._players:
            detectors = {
                "dd": DoubleDribbleDetector(),
                "tr": TravelingDetector(),
                "ca": CarryingDetector(),
                "gt": GoaltendingDetector(),
                "jb": JumpBallDetector(),
                "ball": BallMotionTracker(),
            }
            self._players[player_id] = detectors
            
        return self._players[player_id]

    def _check_holding(self, landmarks_px: dict, mp_pose,
                       ball_center) -> bool:
        """
        ตรวจสอบว่าผู้เล่นถือบอลหรือไม่
        เช็คระยะห่างระหว่างข้อมือกับจุดกึ่งกลางบอล
        """
        if ball_center is None:
            return False

        r_key = mp_pose.PoseLandmark.RIGHT_WRIST.value
        l_key = mp_pose.PoseLandmark.LEFT_WRIST.value

        r_wrist = landmarks_px.get(r_key)
        l_wrist = landmarks_px.get(l_key)

        if r_wrist is None or l_wrist is None:
            return False

        return (get_dist(r_wrist, ball_center) < self.HOLDING_DIST or
                get_dist(l_wrist, ball_center) < self.HOLDING_DIST)

    def _find_nearest_opponent(self, player_id: int,
                                my_landmarks: dict):
        """
        ค้นหาผู้เล่นที่อยู่ใกล้ที่สุดเพื่อใช้เป็น opponent
        สำหรับ JumpBallDetector ตรวจ Held Ball / Jump Ball Situation

        ใช้ torso center จาก shoulder/hip แทน hip จุดเดียว
        และใช้ threshold แบบ dynamic ตามขนาดตัวเพื่อรองรับภาพ outdoor / resolution สูง
        """
        my_center = self._torso_center(my_landmarks)
        if my_center is None:
            return None

        nearest_lm   = None
        nearest_dist = float('inf')

        for pid, lm in self._latest_landmarks.items():
            if pid == player_id:
                continue

            opp_center = self._torso_center(lm)
            if opp_center is None:
                continue

            d = get_dist(my_center, opp_center)
            if d < nearest_dist:
                nearest_dist = d
                nearest_lm   = lm

        max_distance = max(450.0, self._shoulder_width_from_landmarks(my_landmarks) * 3.5)
        return nearest_lm if nearest_dist <= max_distance else None

    def _find_nearest_opponent_id(self, player_id: int,
                                  my_landmarks: dict):
        my_center = self._torso_center(my_landmarks)
        if my_center is None:
            return None

        nearest_id = None
        nearest_dist = float("inf")
        for pid, lm in self._latest_landmarks.items():
            if pid == player_id:
                continue
            opp_center = self._torso_center(lm)
            if opp_center is None:
                continue
            d = get_dist(my_center, opp_center)
            if d < nearest_dist:
                nearest_dist = d
                nearest_id = pid

        max_distance = max(450.0, self._shoulder_width_from_landmarks(my_landmarks) * 3.5)
        return nearest_id if nearest_dist <= max_distance else None

    def _torso_center(self, landmarks_px: dict):
        points = []
        for idx in (11, 12, 23, 24):
            pt = landmarks_px.get(idx)
            if pt is not None:
                points.append(pt)
        if not points:
            return None
        return (
            sum(pt[0] for pt in points) / len(points),
            sum(pt[1] for pt in points) / len(points),
        )

    def _shoulder_width_from_landmarks(self, landmarks_px: dict) -> float:
        l_shoulder = landmarks_px.get(11)
        r_shoulder = landmarks_px.get(12)
        if l_shoulder is None or r_shoulder is None:
            return 120.0
        return max(get_dist(l_shoulder, r_shoulder), 10.0)
