# สูตรคณิตศาสตร์ที่ใช้ในระบบตรวจจับ Foul บาสเกตบอล

> สรุปสำหรับใส่ในเล่มวิจัย — อธิบายสูตร, ที่มา, และเหตุผลที่เลือกใช้

---

## 1. Euclidean Distance (ระยะทางแบบยุคลิด)

### สูตร

$$d(P_1, P_2) = \sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}$$

### โค้ด (`utils.py`, บรรทัด 26–28)
```python
def get_dist(p1, p2) -> float:
    return float(np.linalg.norm(np.array(p1[:2]) - np.array(p2[:2])))
```

### ใช้ที่ไหนบ้าง
| Module | ใช้วัด |
|--------|--------|
| `double_dribble.py` | ระยะข้อมือ ↔ ลูกบาส (ตรวจว่าแตะบอลหรือไม่) |
| `carrying.py` | velocity ของลูกบาส (frame-to-frame) |
| `jump_ball.py` | velocity ข้อมือ + ระยะมือ ↔ หน้าอกคู่ต่อสู้ |
| `referee.py` | ระยะไหล่ (shoulder_width) ใช้เป็น dynamic scale |
| `goaltending.py` | ระยะมือ ↔ ลูกบาส |

### เหตุผลที่เลือกใช้
Euclidean Distance เป็นการวัดระยะทางตรงระหว่างสองจุดในระนาบ 2 มิติ (ระบบพิกัดภาพ) ซึ่งตรงกับความหมายทางกายภาพที่ต้องการ เช่น ระยะจากมือถึงลูกบาส หรือความเร็วของจุดบนร่างกาย (pixel/frame) เหมาะสมกว่า Manhattan Distance ที่วัดตามแกน X และ Y แยกกัน เพราะการเคลื่อนที่ของร่างกายเกิดขึ้นในทุกทิศทาง

---

## 2. Joint Angle (มุมที่ข้อต่อ)

### สูตร

มุมที่จุด **B** (ข้อศอก / เข่า / ข้อมือ) จากสามจุด A → B → C

$$\theta = \left| \arctan2(C_y - B_y,\ C_x - B_x) - \arctan2(A_y - B_y,\ A_x - B_x) \right|$$

ถ้า θ > 180° จะแปลงเป็น: θ = 360° − θ  (เพื่อให้ผลอยู่ในช่วง 0°–180°)

### โค้ด (`utils.py`, บรรทัด 31–40)
```python
def calculate_angle(a, b, c) -> float:
    a, b, c = np.array(a[:2]), np.array(b[:2]), np.array(c[:2])
    radians = (np.arctan2(c[1]-b[1], c[0]-b[0])
               - np.arctan2(a[1]-b[1], a[0]-b[0]))
    angle = abs(np.degrees(radians))
    return 360.0 - angle if angle > 180.0 else angle
```

### ใช้ที่ไหนบ้าง
| Module | จุด A | จุด B (vertex) | จุด C | ตรวจอะไร |
|--------|-------|----------------|-------|---------|
| `jump_ball.py` | Shoulder | Elbow | Wrist | Illegal Hands (ศอก > 155°) |

### เหตุผลที่เลือกใช้
**arctan2** ถูกเลือกแทน **arccos** (dot product) เพราะ:
1. arctan2 รับ (y, x) โดยตรง → คำนวณมุมได้ทุก quadrant อย่างถูกต้อง (−180° ถึง +180°)
2. arccos จาก dot product อาจเกิด domain error เมื่อค่าเกิน [−1, 1] เล็กน้อยเพราะ floating-point
3. ให้ผลที่สอดคล้องกับการมองด้วยตา: ข้อศอกกาง 155° หมายถึงแขนเกือบตรง

---

## 3. Intersection over Union — IoU

### สูตร

$$\text{IoU}(A, B) = \frac{|A \cap B|}{|A \cup B|} = \frac{\text{Area of Intersection}}{\text{Area of } A + \text{Area of } B - \text{Area of Intersection}}$$

พื้นที่ Intersection ของ Bounding Box:
$$x_{intersect} = \min(x_2^A, x_2^B) - \max(x_1^A, x_1^B)$$
$$y_{intersect} = \min(y_2^A, y_2^B) - \max(y_1^A, y_1^B)$$
$$\text{Intersection Area} = \max(0,\ x_{intersect}) \times \max(0,\ y_{intersect})$$

### โค้ด (`utils.py`, บรรทัด 47–56)
```python
def compute_iou(boxA, boxB) -> float:
    xA = max(boxA[0], boxB[0]);  yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2]);  yB = min(boxA[3], boxB[3])
    inter = max(0, xB-xA) * max(0, yB-yA)
    if inter == 0: return 0.0
    aA = (boxA[2]-boxA[0]) * (boxA[3]-boxA[1])
    aB = (boxB[2]-boxB[0]) * (boxB[3]-boxB[1])
    return inter / (aA + aB - inter)
```

### ใช้ที่ไหนบ้าง
`filter_duplicate_boxes()` ใช้ IoU เพื่อกรอง Bounding Box ที่ซ้อนทับกัน (Non-Maximum Suppression แบบ custom)

### เหตุผลที่เลือกใช้
IoU เป็นมาตรฐานอุตสาหกรรมสำหรับวัดความซ้อนทับของ Bounding Box ใน Object Detection มีคุณสมบัติ:
- ค่า 0 = ไม่ซ้อนทับเลย
- ค่า 1 = ซ้อนทับ 100%
- Invariant ต่อขนาด Box (normalized)

ใช้แทนการวัดระยะ center-to-center ซึ่งไม่คำนึงถึงขนาดของ Box และอาจ false-suppress boxes ที่อยู่ใกล้กันแต่ไม่ซ้อน

---

## 4. Polynomial Curve Fitting — Parabola (วิถีโค้งพาราโบลา)

### สูตร

Fit วิถีโค้ง Parabola จากข้อมูล Y ของลูกบาส:

$$y = at^2 + bt + c$$

หาสัมประสิทธิ์ด้วย **Least Squares Method**:

$$\min_{a,b,c} \sum_{t=0}^{N-1} \left[ y_t - (at^2 + bt + c) \right]^2$$

เงื่อนไขการตัดสิน Goaltending:
1. $a > 0.5$ → พาราโบลาหงาย (วิถีลูกบาสขึ้นแล้วลง)
2. $y_{N-1} > y_{N-2}$ → จุดล่าสุดกำลังลดลง (ขาลง)

### โค้ด (`goaltending.py`, บรรทัด 49–55)
```python
x_axis = np.arange(len(self._y_history))   # t = 0, 1, 2, ..., N-1
y_axis = np.array(self._y_history)          # Y pixel ของลูกบาส
a, b, c = np.polyfit(x_axis, y_axis, 2)    # Least Squares, deg=2

is_downward_arc = (a > 0.5) and (y_axis[-1] > y_axis[-2])
```

> **หมายเหตุพิกัด:** ใน OpenCV ค่า Y เพิ่มขึ้นเมื่อเลื่อนลงจอ ดังนั้นลูกบาสที่กำลังลงตะกร้าจะมีค่า y เพิ่มขึ้น → พาราโบลาหงาย → สัมประสิทธิ์ a > 0

### เหตุผลที่เลือกใช้
ทางฟิสิกส์ การเคลื่อนที่ของวัตถุภายใต้แรงโน้มถ่วง (projectile motion) เป็นไปตามสมการพาราโบลา วิธี Polynomial Fitting ด้วย Least Squares ช่วยให้:
1. ทนต่อ Noise ของ YOLO Detection (ไม่ตรวจ 2 เฟรมแล้วตัดสิน)
2. ระบุ **phase** ของบอล (ขาขึ้น vs ขาลง) ได้อย่างน่าเชื่อถือ
3. คำนวณจาก history 15 เฟรม → robust กว่าการดูจุดเดียว

---

## 5. Kalman Filter 1D (กรอง Noise ตำแหน่งข้อเท้า)

### สูตรหลัก

**State Model** (Constant Velocity):

$$\mathbf{x}_k = \begin{bmatrix} y_k \\ \dot{y}_k \end{bmatrix} \quad \Rightarrow \quad \mathbf{x}_{k+1} = \begin{bmatrix} 1 & 1 \\ 0 & 1 \end{bmatrix} \mathbf{x}_k + \mathbf{w}_k$$

**Prediction Step:**
$$\hat{\mathbf{x}}_{k|k-1} = F\hat{\mathbf{x}}_{k-1|k-1}$$
$$P_{k|k-1} = FP_{k-1|k-1}F^T + Q$$

**Update Step (Correction):**

Innovation: $\quad \tilde{y}_k = z_k - H\hat{\mathbf{x}}_{k|k-1}$

Kalman Gain: $\quad K_k = P_{k|k-1}H^T(HP_{k|k-1}H^T + R)^{-1}$

Update State: $\quad \hat{\mathbf{x}}_{k|k} = \hat{\mathbf{x}}_{k|k-1} + K_k\tilde{y}_k$

Update Covariance: $\quad P_{k|k} = (I - K_kH)P_{k|k-1}$

โดยที่:
- $F$ = Transition Matrix = $\begin{bmatrix}1&1\\0&1\end{bmatrix}$
- $H$ = Measurement Matrix = $\begin{bmatrix}1&0\end{bmatrix}$
- $Q$ = Process Noise Covariance = $10^{-4} I$
- $R$ = Measurement Noise = $10^{-2}$

### โค้ด (`traveling.py`, บรรทัด 7–26)
```python
class Kalman1D:
    def __init__(self):
        self.kf = cv2.KalmanFilter(2, 1)
        self.kf.transitionMatrix    = np.array([[1, 1], [0, 1]], np.float32)
        self.kf.measurementMatrix   = np.array([[1, 0]], np.float32)
        self.kf.processNoiseCov     = np.array([[1e-4, 0], [0, 1e-4]], np.float32)
        self.kf.measurementNoiseCov = np.array([[1e-2]], np.float32)
```

### ใช้ที่ไหนบ้าง
`traveling.py` — กรอง noise ของ Ankle Y coordinate ก่อนส่งเข้า FootStepTracker

### เหตุผลที่เลือกใช้
MediaPipe Pose landmark มี noise ตามธรรมชาติ (กระเด้ง 2–5 pixel ต่อเฟรม) ซึ่งหากนำ raw Y มานับก้าวโดยตรงจะเกิด False Positive สูง Kalman Filter แก้ปัญหานี้โดย:

1. **Predict**: ทำนายตำแหน่งถัดไปจากความเร็วปัจจุบัน
2. **Update**: ผสมค่าทำนายกับค่าวัดจริงตามน้ำหนัก (Kalman Gain)
3. ผลคือ trajectory ที่ smooth ขึ้นโดยยังคง responsiveness ต่อการเคลื่อนที่จริง

เหมาะกว่า Moving Average เพราะ Kalman ใช้ model ความเร็ว → ตอบสนองต่อการเปลี่ยนทิศทางเร็วกว่า

---

## 6. Exponential Moving Average — EMA (กรอง Jitter)

### สูตร

$$\text{EMA}_t = \alpha \cdot x_t + (1 - \alpha) \cdot \text{EMA}_{t-1}$$

โดยที่ $\alpha \in (0, 1)$ คือ **Smoothing Factor**:
- $\alpha$ สูง (→ 1): ตอบสนองเร็ว แต่ jittery มากขึ้น
- $\alpha$ ต่ำ (→ 0): smooth มาก แต่ตอบสนองช้า

ค่าที่ใช้ในระบบ: $\alpha = 0.3$

### โค้ด (`utils.py`, บรรทัด 266–277)
```python
class EMAFilter:
    def __init__(self, alpha=0.3):
        self.alpha = alpha
        self.val   = None

    def update(self, new_val):
        if self.val is None:
            self.val = new_val
        else:
            self.val = self.alpha * new_val + (1 - self.alpha) * self.val
        return self.val
```

### เหตุผลที่เลือกใช้
EMA คำนวณ O(1) ต่อ frame — เหมาะสำหรับ real-time processing ที่ทุก frame มีเวลาจำกัด น้ำหนักของข้อมูลเก่าลดลงแบบ exponential ซึ่งตรงกับสัญชาตญาณทางฟิสิกส์ (การเคลื่อนที่ล่าสุดสำคัญกว่า) และใช้ memory คงที่ O(1) ต่างจาก Moving Average ที่ต้องเก็บ window

---

## 7. Temporal Voting (การโหวตตามเวลา)

### สูตร

$$\text{Decision}_t = \begin{cases} \text{True} & \text{if } \sum_{i=t-W+1}^{t} v_i \geq \theta \\ \text{False} & \text{otherwise} \end{cases}$$

โดยที่:
- $W$ = window size = 5 frames
- $\theta$ = threshold = 4 votes
- $v_i \in \{0, 1\}$ = ผลการตรวจจับในแต่ละ frame

### โค้ด (`utils.py`, บรรทัด 281–291)
```python
class TemporalVoter:
    def __init__(self, window_size=5, threshold=3):
        self.history   = deque(maxlen=window_size)
        self.threshold = threshold

    def vote(self, detection_result):
        self.history.append(1 if detection_result else 0)
        return sum(self.history) >= self.threshold
```

ใช้ใน `traveling.py`: window=5, threshold=4 (ต้องผ่าน 4 จาก 5 frames)

### เหตุผลที่เลือกใช้
การตรวจจับด้วย Pose Estimation อาจเกิด false detection ชั่วขณะ (1–2 frames) เช่น landmark กระพริบ การ vote ป้องกัน false positive โดย:
- ต้องเห็น violation ติดต่อกัน/บ่อยพอในช่วงเวลาสั้น
- เทียบเท่ากับ "การยืนยันซ้ำ" ก่อนตัดสิน
- threshold 4/5 = ยืดหยุ่นกว่า AND-gate ล้วน (ต้อง 5/5) แต่เข้มงวดกว่า OR-gate (1/5)

---

## 8. Dynamic Scale Factor (การปรับ Threshold ตามขนาดตัว)

### สูตร

$$\text{threshold} = \max(w_s \times r,\ t_{\min})$$

โดยที่:
- $w_s$ = shoulder width (pixel) = $\|P_{LS} - P_{RS}\|_2$ (ระยะ Euclidean ระหว่างไหล่)
- $r$ = ratio constant (ต่างกันตาม detector)
- $t_{\min}$ = ค่าต่ำสุด (ป้องกันกรณีคนตัวเล็กมากจน threshold = 0)

### ตัวอย่างในระบบ

| Detector | สูตร | ค่า r | ค่า t_min |
|----------|------|-------|---------|
| Traveling — lift threshold | $\max(w_s \times 0.18,\ 12)$ | 0.18 | 12 px |
| Carrying — Y buffer | $\max(w_s \times 0.15,\ 10)$ | 0.15 | 10 px |
| Carrying — ball stillness | $\max(w_s \times 0.08,\ 6)$ | 0.08 | 6 px |

### โค้ดตัวอย่าง (`traveling.py`, บรรทัด 127)
```python
lift_threshold = max(shoulder_width * self.LIFT_RATIO, self.LIFT_MIN)
# = max(shoulder_width × 0.18, 12)
```

### เหตุผลที่เลือกใช้
ระบบถ่ายภาพแบบ monocular (กล้องเดียว) ไม่สามารถวัดระยะทางจริง (เมตร) ได้โดยตรง ขนาดของ landmark ในพิกัดภาพ (pixel) ขึ้นอยู่กับ:
- ระยะห่างระหว่างผู้เล่นกับกล้อง
- ความสูงของผู้เล่น

การใช้ **shoulder_width** เป็น reference scale ทำให้ threshold ปรับตามตัวผู้เล่นโดยอัตโนมัติ เช่น ผู้เล่นอยู่ใกล้กล้องมาก → ไหล่กว้างในภาพ → threshold สูงตาม → ไม่ตรวจเกินจริง

---

## 9. Aspect Ratio Check (ตรวจสัดส่วนกรอบตัว)

### สูตร

$$\text{aspect\_ratio} = \frac{h}{w} = \frac{\max(y) - \min(y)}{\max(x) - \min(x)}$$

เงื่อนไข Pose Valid:

$$\frac{h}{w} < 0.5 \Rightarrow \text{Reject (likely arm/hand, not full body)}$$

### โค้ด (`referee.py`, บรรทัด 64–70)
```python
xs = [v[0] for v in landmarks_px.values()]
ys = [v[1] for v in landmarks_px.values()]
w  = max(xs) - min(xs)
h  = max(ys) - min(ys)

if w > 0 and h > 0 and (h / w) < 0.5:
    return False, "Aspect ratio invalid (likely arm/hand)"
```

### เหตุผลที่เลือกใช้
YOLO บางครั้งตรวจพบ "คน" จากมือหรือแขนที่ลอยอยู่ในเฟรม Pose Landmark ของแขนจะมีแนวนอน (กว้างกว่าสูง) → h/w < 0.5 ซึ่งไม่ใช่ลักษณะร่างกายคนยืน/เดิน การ reject ด้วย aspect ratio ช่วยกรอง false detection ก่อนเข้า Rule Engine ทุกตัว

---

## สรุปภาพรวม — สูตรคณิตศาสตร์ทั้งหมด

| # | สูตร | โมดูล | วัตถุประสงค์ |
|---|------|-------|-------------|
| 1 | Euclidean Distance | utils.py | วัดระยะทาง landmark, ball, velocity |
| 2 | arctan2 (Joint Angle) | utils.py | มุมข้อศอกสำหรับ Illegal Hands |
| 3 | IoU (Intersection over Union) | utils.py | กรอง Bounding Box ซ้อนทับ |
| 4 | Polynomial Curve Fitting (deg=2) | goaltending.py | ตรวจวิถีพาราโบลาลูกบาส |
| 5 | Kalman Filter 1D | traveling.py | กรอง noise ตำแหน่งข้อเท้า |
| 6 | Exponential Moving Average (EMA) | utils.py | กรอง Jitter Landmark |
| 7 | Temporal Voting (Majority Vote) | utils.py + traveling.py | กัน False Positive ชั่วขณะ |
| 8 | Dynamic Scale Factor | traveling.py, carrying.py | ปรับ threshold ตามขนาดตัว |
| 9 | Aspect Ratio | referee.py | กรอง False Detection (มือ/แขน) |

### หลักการออกแบบที่ใช้สูตรเหล่านี้ร่วมกัน

ระบบออกแบบตามหลัก **Defense in Depth** โดยสูตรแต่ละตัวแก้ปัญหาคนละชั้น:

```
Raw Pixels
    ↓ [Aspect Ratio]      — กรอง detection ที่ไม่ใช่คน
    ↓ [Kalman / EMA]      — กรอง noise จาก landmark
    ↓ [Euclidean / arctan2] — วัด feature ทางกายภาพ
    ↓ [Dynamic Scale]     — normalize ตามขนาดตัว
    ↓ [IoU / Curve Fitting] — ตรวจ pattern เฉพาะ foul
    ↓ [Temporal Vote]     — ยืนยันก่อนแจ้งเตือน
    ↓ VIOLATION OUTPUT
```
