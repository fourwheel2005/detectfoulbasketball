"""
fouls/jump_ball.py — ตรวจจับ Held Ball / Jump Ball Situation
--------------------------------------------------------------
ตามกติกา Jump Ball / Held Ball:
    ผู้เล่นฝ่ายตรงข้าม 1 คนหรือมากกว่า ใช้มือเดียวหรือสองมือจับบอลไว้อย่างมั่นคงพร้อมกัน
    จนไม่มีผู้เล่นคนใดครอบครองบอลได้ชัดเจน

ไฟล์นี้จึงไม่ตรวจ PUSH FOUL / ILLEGAL HANDS แล้ว
แต่ตรวจสถานการณ์ "ลูกยึด" เพื่อให้ระบบแจ้ง JUMP BALL SITUATION แทน
"""

from utils import get_dist


class JumpBallDetector:
    """
    ตรวจจับ Held Ball / Jump Ball Situation จาก Pose + Ball Motion

    เงื่อนไขหลัก:
        1. มี opponent อยู่ใกล้พอ (หาโดย referee.py)
        2. มือของผู้เล่นทั้งสองคนอยู่ใกล้ลูกพร้อมกัน
        3. บอลเคลื่อนช้าหรือไม่ใช่จังหวะ dribble/pass/shot
        4. สถานการณ์ค้างต่อเนื่อง CONFIRM_FRAMES เฟรม

    หมายเหตุ:
        ชื่อ class ยังเป็น JumpBallDetector เพื่อคง compatibility กับ referee.py
    """

    CONFIRM_FRAMES = 6
    COOLDOWN_FRAMES = 45
    HAND_BALL_RATIO = 1.20
    HAND_BALL_MIN = 85
    STRONG_HAND_CONFIRM = 2
    WEAK_HAND_CONFIRM = 1
    CONTESTED_BALL_SPEED_RATIO = 0.18
    CONTESTED_BALL_SPEED_MIN = 18

    def __init__(self):
        self._confirm_count = 0
        self._cooldown_left = 0

    def check(self, landmarks_px: dict, mp_pose, opponent_landmarks: dict = None,
              ball_center=None, ball_motion=None, hand_landmarks_px=None,
              opponent_hand_landmarks_px=None) -> tuple:
        """
        Returns:
            (is_situation: bool, message: str)
        """
        if self._cooldown_left > 0:
            self._cooldown_left -= 1
            return False, ""

        if ball_center is None or opponent_landmarks is None:
            self._confirm_count = 0
            return False, ""

        my_hand_points = self._hand_points(landmarks_px, mp_pose, hand_landmarks_px)
        opp_hand_points = self._hand_points(
            opponent_landmarks, mp_pose, opponent_hand_landmarks_px
        )
        if not my_hand_points or not opp_hand_points:
            self._confirm_count = 0
            return False, ""

        threshold = self._hand_ball_threshold(landmarks_px, opponent_landmarks, mp_pose)

        my_near_count = self._count_points_near_ball(my_hand_points, ball_center, threshold)
        opp_near_count = self._count_points_near_ball(opp_hand_points, ball_center, threshold)

        strong_contest = (
            my_near_count >= self.STRONG_HAND_CONFIRM and
            opp_near_count >= self.STRONG_HAND_CONFIRM
        )
        weak_contest = (
            my_near_count >= self.WEAK_HAND_CONFIRM and
            opp_near_count >= self.WEAK_HAND_CONFIRM and
            self._ball_between_players(landmarks_px, opponent_landmarks, mp_pose, ball_center)
        )
        both_players_on_ball = strong_contest or weak_contest

        ball_is_still = bool(getattr(ball_motion, "is_still", False))
        ball_velocity = float(getattr(ball_motion, "velocity", 0.0))
        dribble_event = bool(getattr(ball_motion, "dribble_event", False))
        stable_threshold = max(
            self._max_shoulder_width(landmarks_px, opponent_landmarks, mp_pose) * self.CONTESTED_BALL_SPEED_RATIO,
            self.CONTESTED_BALL_SPEED_MIN,
        )
        ball_is_contested_stable = (
            ball_is_still or
            (ball_velocity <= stable_threshold and not dribble_event)
        )

        if both_players_on_ball and ball_is_contested_stable:
            self._confirm_count += 1
        else:
            self._confirm_count = 0

        if self._confirm_count >= self.CONFIRM_FRAMES:
            self._confirm_count = 0
            self._cooldown_left = self.COOLDOWN_FRAMES
            return True, "HELD BALL / JUMP BALL"

        return False, self._status_message(
            my_near_count,
            opp_near_count,
            ball_is_contested_stable,
            ball_velocity,
            stable_threshold,
            both_players_on_ball,
        )

    def reset(self):
        self._confirm_count = 0
        self._cooldown_left = 0

    # ─── Helpers ───────────────────────────────────────────

    def _hand_points(self, landmarks_px: dict, mp_pose, hand_landmarks_px=None) -> list:
        points = []
        for lm in (
            mp_pose.PoseLandmark.LEFT_WRIST,
            mp_pose.PoseLandmark.RIGHT_WRIST,
            mp_pose.PoseLandmark.LEFT_INDEX,
            mp_pose.PoseLandmark.RIGHT_INDEX,
            mp_pose.PoseLandmark.LEFT_THUMB,
            mp_pose.PoseLandmark.RIGHT_THUMB,
        ):
            pt = landmarks_px.get(lm.value)
            if pt is not None:
                points.append(pt)
        for hand in hand_landmarks_px or []:
            points.extend(hand["points"].values())
        return points

    def _shoulder_width(self, landmarks_px: dict, mp_pose) -> float:
        l_shoulder = landmarks_px.get(mp_pose.PoseLandmark.LEFT_SHOULDER.value)
        r_shoulder = landmarks_px.get(mp_pose.PoseLandmark.RIGHT_SHOULDER.value)
        if l_shoulder is None or r_shoulder is None:
            return 100.0
        return max(get_dist(l_shoulder, r_shoulder), 10.0)

    def _max_shoulder_width(self, my_lm: dict, opp_lm: dict, mp_pose) -> float:
        return max(self._shoulder_width(my_lm, mp_pose), self._shoulder_width(opp_lm, mp_pose))

    def _hand_ball_threshold(self, my_lm: dict, opp_lm: dict, mp_pose) -> float:
        my_width = self._shoulder_width(my_lm, mp_pose)
        opp_width = self._shoulder_width(opp_lm, mp_pose)
        scale = max(my_width, opp_width)
        return max(scale * self.HAND_BALL_RATIO, self.HAND_BALL_MIN)

    def _count_points_near_ball(self, points: list, ball_center, threshold: float) -> int:
        return sum(1 for pt in points if get_dist(pt, ball_center) <= threshold)

    def _torso_center(self, landmarks_px: dict, mp_pose):
        points = []
        for lm in (
            mp_pose.PoseLandmark.LEFT_SHOULDER,
            mp_pose.PoseLandmark.RIGHT_SHOULDER,
            mp_pose.PoseLandmark.LEFT_HIP,
            mp_pose.PoseLandmark.RIGHT_HIP,
        ):
            pt = landmarks_px.get(lm.value)
            if pt is not None:
                points.append(pt)
        if not points:
            return None
        return (
            sum(pt[0] for pt in points) / len(points),
            sum(pt[1] for pt in points) / len(points),
        )

    def _ball_between_players(self, my_lm: dict, opp_lm: dict, mp_pose, ball_center) -> bool:
        my_center = self._torso_center(my_lm, mp_pose)
        opp_center = self._torso_center(opp_lm, mp_pose)
        if my_center is None or opp_center is None:
            return True

        shoulder_scale = self._max_shoulder_width(my_lm, opp_lm, mp_pose)
        min_x = min(my_center[0], opp_center[0]) - shoulder_scale * 0.75
        max_x = max(my_center[0], opp_center[0]) + shoulder_scale * 0.75
        min_y = min(my_center[1], opp_center[1]) - shoulder_scale * 1.6
        max_y = max(my_center[1], opp_center[1]) + shoulder_scale * 1.6
        return min_x <= ball_center[0] <= max_x and min_y <= ball_center[1] <= max_y

    def _status_message(
        self,
        my_count: int,
        opp_count: int,
        ball_is_contested_stable: bool,
        ball_velocity: float,
        stable_threshold: float,
        both_players_on_ball: bool,
    ) -> str:
        if my_count or opp_count:
            stable = "stable" if ball_is_contested_stable else "moving"
            prefix = "HeldBall candidate" if both_players_on_ball and ball_is_contested_stable else "HeldBall"
            return (
                f"{prefix}: my={my_count} opp={opp_count} "
                f"ball={stable} v={ball_velocity:.1f}/{stable_threshold:.1f} "
                f"confirm={self._confirm_count}/{self.CONFIRM_FRAMES}"
            )
        return ""
