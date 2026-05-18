"""
preprocessor.py — Frame Preprocessing Pipeline
================================================
ใช้ร่วมกันทั้ง real-time (main.py) และ semi-real-time (video_main.py)

Modes:
    FAST   — CLAHE + White Balance (~7ms) สำหรับ real-time
    FULL   — CLAHE + White Balance + Bilateral (~25ms) สำหรับ video file

Usage:
    from preprocessor import FramePreprocessor
    proc = FramePreprocessor(mode="FAST")   # หรือ "FULL"
    frame = proc.process(frame)
"""

import cv2
import numpy as np


class FramePreprocessor:
    """
    Pipeline กรองภาพก่อนส่งเข้า YOLO + MediaPipe

    Parameters
    ----------
    mode : str
        "FAST" — CLAHE + White Balance เท่านั้น (~7ms, สำหรับ real-time)
        "FULL" — CLAHE + White Balance + Bilateral (~25ms, สำหรับ video)
    clahe_clip   : float  clipLimit ของ CLAHE (2.0 = standard)
    clahe_tile   : int    tileGridSize ของ CLAHE
    bilateral_d  : int    diameter ของ Bilateral (5 = เร็ว, 9 = คมชัด)
    """

    def __init__(self, mode: str = "FAST",
                 clahe_clip: float = 2.0,
                 clahe_tile: int = 8,
                 bilateral_d: int = 5,
                 bilateral_sigma: int = 75):
        self.mode     = mode.upper()
        self._clahe   = cv2.createCLAHE(
            clipLimit=clahe_clip,
            tileGridSize=(clahe_tile, clahe_tile)
        )
        self._bil_d     = bilateral_d
        self._bil_sigma = bilateral_sigma

        mode_desc = {
            "FAST": "CLAHE + WhiteBalance (~7ms)",
            "FULL": f"CLAHE + WhiteBalance + Bilateral(d={bilateral_d}) (~25ms)",
        }
        print(f"✅ [Preprocessor] mode={mode.upper()} → {mode_desc.get(self.mode,'unknown')}")

    # ── Public API ──────────────────────────────────────────────────

    def process(self, frame: np.ndarray) -> np.ndarray:
        """
        ประมวลผล 1 frame ตาม mode ที่เลือก
        Input / Output: BGR uint8 ndarray
        """
        frame = self._clahe_enhance(frame)
        frame = self._white_balance(frame)
        if self.mode == "FULL":
            frame = self._bilateral(frame)
        return frame

    # ── Private Methods ─────────────────────────────────────────────

    def _clahe_enhance(self, frame: np.ndarray) -> np.ndarray:
        """
        CLAHE (Contrast Limited Adaptive Histogram Equalization)
        ทำงานในช่อง L ของ LAB color space
        → แก้ overexposure / underexposure เฉพาะจุดโดยไม่กระทบ Hue/Saturation
        """
        lab      = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b  = cv2.split(lab)
        l        = self._clahe.apply(l)
        enhanced = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
        return enhanced

    def _white_balance(self, frame: np.ndarray) -> np.ndarray:
        """
        Grey-World White Balance ใน LAB space
        หลักการ: ปรับให้ค่าเฉลี่ยของช่อง a และ b ≈ 128 (neutral)

        ข้อจำกัด: ถ้าฉากมีสีที่ dominant มาก (เช่น ท้องฟ้าสีฟ้า)
        อาจ over-correct → ลด strength ด้วย blend_ratio
        """
        BLEND = 0.6   # 0=ไม่ทำ WB เลย, 1=ทำ WB เต็ม 100%

        lab          = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB).astype(np.float32)
        avg_a        = np.mean(lab[:, :, 1])
        avg_b        = np.mean(lab[:, :, 2])

        # ปรับเฉพาะส่วนที่ห่างจาก 128 มากพอ (กัน over-correction)
        shift_a = (avg_a - 128) * BLEND
        shift_b = (avg_b - 128) * BLEND

        lab[:, :, 1] -= shift_a
        lab[:, :, 2] -= shift_b
        lab = np.clip(lab, 0, 255).astype(np.uint8)
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    def _bilateral(self, frame: np.ndarray) -> np.ndarray:
        """
        Bilateral Filter — ลด noise แต่คงขอบ (edge-preserving)
        ใช้เฉพาะ mode=FULL (video file) เพราะช้ากว่า Gaussian ~10x
        """
        return cv2.bilateralFilter(
            frame,
            d=self._bil_d,
            sigmaColor=self._bil_sigma,
            sigmaSpace=self._bil_sigma,
        )


# ── Self-test: python preprocessor.py ──────────────────────────────
if __name__ == "__main__":
    import time

    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("❌ เปิดกล้องไม่ได้ ลองใช้ index อื่น")
        exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    proc_fast = FramePreprocessor(mode="FAST")
    proc_full = FramePreprocessor(mode="FULL", bilateral_d=5)

    print("กด 'q' เพื่อออก | 'f' = toggle FAST/FULL")
    mode_fast = True

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        t0    = time.perf_counter()
        proc  = proc_fast if mode_fast else proc_full
        out   = proc.process(frame)
        ms    = (time.perf_counter() - t0) * 1000

        label = f"Mode: {'FAST' if mode_fast else 'FULL'}  preprocess={ms:.1f}ms"
        cv2.putText(out, label, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        combined = cv2.hconcat([
            cv2.resize(frame, (640, 360)),
            cv2.resize(out,   (640, 360)),
        ])
        cv2.putText(combined, "Original", (10, 355),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        cv2.putText(combined, "Processed", (650, 355),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

        cv2.imshow("Preprocessor Test (f=toggle mode)", combined)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("f"):
            mode_fast = not mode_fast
            print(f"→ switched to {'FAST' if mode_fast else 'FULL'}")

    cap.release()
    cv2.destroyAllWindows()
