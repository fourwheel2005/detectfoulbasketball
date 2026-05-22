import numpy as np
from collections import deque
import math

class GoaltendingDetector:
    def __init__(self):
        self.HISTORY_LEN = 15
        self.MIN_SAMPLES = 6
        self.rim_y_px  = None       # ต้องมาจาก YOLO rim detection เท่านั้น
        self.rim_x_range = None      # (x1, x2) px ถ้าต้องการตรวจ cylinder (optional)
        self.rim_reliable = False
        self.HAND_BALL_THRESHOLD_PX = 110
        self.RIM_VERTICAL_MARGIN_PX = 25
        self.RIM_MISSING_CLEAR_FRAMES = 12
        self._y_history = deque(maxlen=self.HISTORY_LEN)
        self._rim_missing_frames = 0

    def check(self, ball_center, hands_positions, frame_h, rim_y_px=None,
              rim_reliable: bool | None = None, ball_in_flight: bool = False):
        """
        hands_positions: list ของ (x, y) ของมือผู้เล่นทุกคนในเฟรม
        rim_y_px: pixel Y ของห่วงบาส

        Tip (Calibration):
            ดู frame แล้วสังเกตว่าห่วงอยู่ที่ Y = ? px แล้วใส่ค่าตรงๆ:
            detector.rim_y_px = 280  # หรือส่งผ่าน rim_y_px parameter
        """
        if ball_center is None:
            self._y_history.clear()
            return False, "GT: no ball"

        reliable = self.rim_reliable if rim_reliable is None else bool(rim_reliable)

        # ต้องเห็นห่วงจริงและ reliable ก่อนเท่านั้น ไม่ใช้ fallback ในห้อง/ฉากไม่มีห่วง
        rim_y = rim_y_px if rim_y_px is not None else self.rim_y_px
        if rim_y is None:
            self._rim_missing_frames += 1
            if self._rim_missing_frames >= self.RIM_MISSING_CLEAR_FRAMES:
                self._y_history.clear()
            return False, f"GT: no rim {self._rim_missing_frames}/{self.RIM_MISSING_CLEAR_FRAMES}"
        if not reliable:
            self._y_history.clear()
            return False, "GT skip: rim unreliable"
        if not ball_in_flight:
            self._y_history.clear()
            return False, "GT skip: ball not in flight"
        self._rim_missing_frames = 0

        y = ball_center[1]
        self._y_history.append(y)

        if len(self._y_history) < self.MIN_SAMPLES:
            return False, f"GT: samples {len(self._y_history)}/{self.MIN_SAMPLES}"

        # 1. บอลต้องอยู่เหนือหรือใกล้ plane ของห่วง
        # ใช้ margin เล็กน้อยเพราะ ball bbox center / rim bbox center มี jitter ตามมุมกล้อง
        if y >= rim_y + self.RIM_VERTICAL_MARGIN_PX:
            return False, f"GT: below rim y={int(y)} rim={int(rim_y)}"

        # 1b. Cylinder check (optional): บอลต้องอยู่แนวเดียวกับห่วงด้วย
        if self.rim_x_range is not None:
            x1, x2 = self.rim_x_range
            if ball_center[0] < x1 or ball_center[0] > x2:
                return False, f"GT: out cylinder x={int(ball_center[0])} range={int(x1)}-{int(x2)}"

        # 2. สร้างสมการ Parabola (y = ax^2 + bx + c) จากประวัติ Y
        # เนื่องจากพิกัด Y ของจอคอม ยิ่งลงล่างยิ่งค่าบวก กราฟลูกบาสตกพื้นจะเป็นตัว U หงาย (a > 0)
        x_axis = np.arange(len(self._y_history))
        y_axis = np.array(self._y_history)
        a, b, c = np.polyfit(x_axis, y_axis, 2)

        # Hybrid trajectory:
        # - parabola_ok ใช้รูปวิถีโดยรวม
        # - downward_trend ใช้ delta หลายเฟรมล่าสุดเพื่อทน noise จาก YOLO/camera shake
        recent = y_axis[-min(5, len(y_axis)):]
        deltas = np.diff(recent)
        downward_steps = int(np.sum(deltas > 2.0))
        downward_total = float(recent[-1] - recent[0]) if len(recent) >= 2 else 0.0
        parabola_ok = (a > 0.25) and (y_axis[-1] > y_axis[-2])
        downward_trend = downward_steps >= 2 and downward_total > 6.0
        is_downward_arc = parabola_ok or downward_trend

        if not is_downward_arc:
            return False, (
                f"GT: not downward a={a:.2f} "
                f"steps={downward_steps} total={downward_total:.1f}"
            )

        # 3. เช็คว่ามี "มือ" เข้าใกล้ลูกบาสในระยะที่กำหนดหรือไม่ (ป้องกันนกบินผ่าน)
        is_touched = False
        if hands_positions:
            for hand_x, hand_y in hands_positions:
                dist = math.hypot(hand_x - ball_center[0], hand_y - ball_center[1])
                if dist < self.HAND_BALL_THRESHOLD_PX:
                    is_touched = True
                    break

        if is_downward_arc and is_touched:
            # ล้างประวัติเพื่อไม่ให้เตือนซ้ำรัวๆ
            self._y_history.clear() 
            return True, "GOALTENDING ⚠️"

        return False, (
            f"GT candidate: above rim + downward "
            f"hand={int(is_touched)} a={a:.2f} steps={downward_steps}"
        )
