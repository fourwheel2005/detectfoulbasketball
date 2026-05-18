"""
fouls/carrying.py — ตรวจจับ Carrying (Palming)
-----------------------------------------------
Logic:
    1. เลือกมือที่เกี่ยวข้องกับบอลจริงที่สุดจากระยะ ball-center ↔ wrist/index/thumb
    2. ข้อมือ (Wrist) อยู่ต่ำกว่านิ้วชี้ (Index Finger) + Dynamic Buffer
       → มือรองบอล / palm-up cue
    3. บอลอยู่เหนือมือและอยู่ใกล้มือพอ
    4. บอลเคลื่อนที่ช้าพอเมื่อเทียบกับขนาดตัวและยังอยู่ใกล้มือ
       → บอล "หยุดในมือ" (comes to rest) ตามกฎจริง
    ต้องเกิดทุกเงื่อนไขพร้อมกัน CONFIRM_FRAMES เฟรมติดต่อกัน = Carrying
"""
from utils import get_dist


class CarryingDetector:
    """
    ตรวจจับ Carrying โดยเปรียบเทียบตำแหน่ง Y ของ Wrist vs Index Finger

    ถ้า wrist_y > index_y + dynamic_buffer → มืออยู่ใต้บอล / palm-up cue
    (Y มากกว่า = ต่ำกว่าในพิกัดภาพ)
    """

    Y_BUFFER_RATIO  = 0.12  # สัดส่วนของ shoulder_width ที่ข้อมือต้องต่ำกว่านิ้ว
    Y_BUFFER_MIN    = 10    # ค่าขั้นต่ำ (px) ป้องกันคนตัวเล็กมากจนค่าเป็น 0
    CONFIRM_FRAMES  = 4     # ต้องเกิดต่อเนื่องกี่เฟรมถึง Confirm
    MISS_GRACE_FRAMES = 2   # ยอมให้หลุดสั้นๆ จาก pose/ball jitter โดยไม่ reset ทันที
    COOLDOWN_FRAMES = 25    # กันแจ้งซ้ำต่อเนื่องหลัง Confirm

    BALL_REST_RATIO = 0.14   # บอลต้องเคลื่อนช้าพอเมื่อพักในมือ
    BALL_REST_MIN   = 12     # ค่าต่ำสุด (px/frame) กัน YOLO jitter / กล้องสั่น
    BALL_HAND_RATIO   = 1.55  # ระยะ ball ↔ hand ต้องไม่เกิน shoulder_width * ratio
    BALL_HAND_MIN     = 90    # ระยะขั้นต่ำ (px) สำหรับมุมกล้องใกล้
    BALL_ABOVE_RATIO  = 0.06  # บอลควรอยู่สูงกว่าข้อมืออย่างน้อยสัดส่วนนี้

    def __init__(self):
        self._consecutive = 0
        self._prev_ball_center = None  # สำหรับคำนวณ ball velocity
        self._cooldown_left = 0
        self._miss_frames = 0

    def check(self, landmarks_px: dict, mp_pose, is_holding: bool,
              shoulder_width: float = 100.0, ball_center=None,
              hand_landmarks_px=None) -> tuple:
        """
        Parameters:
            landmarks_px  : dict {landmark_id: (x, y)} — Pixel
            mp_pose       : mediapipe.solutions.pose
            is_holding    : bool — ผู้เล่นถือบอลอยู่หรือไม่
            shoulder_width: float — ความกว้างไหล่ (px)
            ball_center   : tuple (x, y) หรือ None — จุดกึ่งกลางบอล

        Returns:
            (is_violation: bool, message: str)
        """
        if self._cooldown_left > 0:
            self._cooldown_left -= 1
            return False, ""

        if ball_center is None:
            self._soft_reset()
            self._prev_ball_center = None
            return False, "Carry: no ball"

        # ── ตรวจ Ball Velocity (กฎต้องการ "comes to rest") ──
        ball_rest_threshold = max(
            shoulder_width * self.BALL_REST_RATIO, self.BALL_REST_MIN
        )
        if self._prev_ball_center is None:
            self._prev_ball_center = ball_center
            return False, "Carry: warmup"

        ball_vel = get_dist(ball_center, self._prev_ball_center)
        ball_is_resting = ball_vel < ball_rest_threshold
        self._prev_ball_center = ball_center

        # ── คำนวณ Dynamic Y Buffer ──
        y_buffer = max(shoulder_width * self.Y_BUFFER_RATIO, self.Y_BUFFER_MIN)
        ball_hand_threshold = max(
            shoulder_width * self.BALL_HAND_RATIO, self.BALL_HAND_MIN
        )
        ball_above_buffer = max(
            shoulder_width * self.BALL_ABOVE_RATIO, self.Y_BUFFER_MIN * 0.5
        )

        # ── ดึงพิกัดมือจาก Pose + hand refinement (ถ้ามี) ──
        hands = []
        for side, wrist_lm, index_lm, thumb_lm in (
            (
                "R",
                mp_pose.PoseLandmark.RIGHT_WRIST,
                mp_pose.PoseLandmark.RIGHT_INDEX,
                mp_pose.PoseLandmark.RIGHT_THUMB,
            ),
            (
                "L",
                mp_pose.PoseLandmark.LEFT_WRIST,
                mp_pose.PoseLandmark.LEFT_INDEX,
                mp_pose.PoseLandmark.LEFT_THUMB,
            ),
        ):
            wrist = landmarks_px.get(wrist_lm.value)
            index = landmarks_px.get(index_lm.value)
            thumb = landmarks_px.get(thumb_lm.value)
            if wrist is None or (index is None and thumb is None):
                continue

            wrist_ball_dist = get_dist(wrist, ball_center)
            finger_dists = []
            if index is not None:
                finger_dists.append(get_dist(index, ball_center))
            if thumb is not None:
                finger_dists.append(get_dist(thumb, ball_center))
            hands.append((min([wrist_ball_dist, *finger_dists]), side, wrist, index, thumb))

        for hand in hand_landmarks_px or []:
            points = hand["points"]
            wrist = points.get(0)
            fingertips = [points.get(idx) for idx in (4, 8, 12, 16, 20)]
            fingertips = [pt for pt in fingertips if pt is not None]
            if wrist is None or not fingertips:
                continue

            nearest_dist = min(
                [get_dist(wrist, ball_center)] +
                [get_dist(pt, ball_center) for pt in fingertips]
            )
            highest_tip = min(fingertips, key=lambda pt: pt[1])
            nearest_tip = min(fingertips, key=lambda pt: get_dist(pt, ball_center))
            side = min(
                (
                    (get_dist(wrist, pose_wrist), pose_side)
                    for pose_side, pose_wrist in (
                        ("R", landmarks_px.get(mp_pose.PoseLandmark.RIGHT_WRIST.value)),
                        ("L", landmarks_px.get(mp_pose.PoseLandmark.LEFT_WRIST.value)),
                    )
                    if pose_wrist is not None
                ),
                default=(0, hand.get("label", "H")[:1].upper()),
                key=lambda item: item[0],
            )[1]
            hands.append((
                nearest_dist,
                side,
                wrist,
                highest_tip,
                nearest_tip,
            ))

        if not hands:
            self._soft_reset()
            return False, "Carry: no hand points"

        _, side, wrist, index, thumb = min(hands, key=lambda item: item[0])

        hand_points = [pt for pt in (wrist, index, thumb) if pt is not None]
        hand_near_ball = (
            min(get_dist(pt, ball_center) for pt in hand_points) < ball_hand_threshold
        )

        # ข้อมืออยู่ต่ำกว่านิ้ว/นิ้วโป้ง + บอลอยู่เหนือข้อมือ = มือรองบอล
        finger_y_values = [pt[1] for pt in (index, thumb) if pt is not None]
        highest_finger_y = min(finger_y_values)
        palm_up = wrist[1] > (highest_finger_y + y_buffer)
        ball_above_hand = ball_center[1] < (wrist[1] - ball_above_buffer)

        possession_signal = is_holding or hand_near_ball

        # ต้องเป็นมือที่เกี่ยวกับบอลจริง + มือรองบอล + บอลพักในมือ
        candidate = (
            possession_signal and
            hand_near_ball and
            palm_up and
            ball_above_hand and
            ball_is_resting
        )

        if candidate:
            self._consecutive += 1
            self._miss_frames = 0
        else:
            self._miss_frames += 1
            if self._miss_frames > self.MISS_GRACE_FRAMES:
                self._consecutive = max(0, self._consecutive - 1)

        # ต้องเกิดต่อเนื่อง CONFIRM_FRAMES เฟรม
        if self._consecutive >= self.CONFIRM_FRAMES:
            self._consecutive = 0
            self._miss_frames = 0
            self._cooldown_left = self.COOLDOWN_FRAMES
            return True, f"CARRYING ({side})"

        return False, (
            f"Carry: side={side} hold={int(is_holding)} near={int(hand_near_ball)} "
            f"palm={int(palm_up)} above={int(ball_above_hand)} "
            f"rest={int(ball_is_resting)} v={ball_vel:.1f}/{ball_rest_threshold:.1f} "
            f"conf={self._consecutive}/{self.CONFIRM_FRAMES}"
        )

    def _soft_reset(self):
        self._consecutive = 0
        self._miss_frames = 0
