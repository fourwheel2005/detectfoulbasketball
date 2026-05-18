# AI Basketball Referee System Flowcharts

เอกสารนี้สรุป Flowchart ของระบบ AI Basketball Referee ทั้งหมด เพื่อใช้เป็นต้นแบบในการวาด diagram ลงรายงาน, resume, presentation หรือเอกสารโปรเจค

ระบบนี้แบ่งเป็น 6 ส่วนหลัก:

1. Real-time video pipeline
2. Detection layer: person, ball, rim, pose
3. Rule engine: foul detection
4. Pose quality and false-positive guard
5. Replay, event logging, QA review
6. Streamlit UI and analytics

---

## 1. High-Level System Architecture

ภาพรวมระบบตั้งแต่กล้องจนถึง UI และ replay

```mermaid
flowchart TD
    A["Camera Input<br/>MacBook / iPhone Camera"] --> B["OpenCV VideoCapture"]
    B --> C["Frame Preprocessor<br/>CLAHE + White Balance"]
    C --> D["YOLO Person Detection<br/>yolov8n.pt + ByteTrack"]
    C --> E["YOLO Ball/Rim Detection<br/>trainmodel/best.pt"]
    D --> F["Player Crop per Track ID"]
    F --> G["MediaPipe Pose Estimation<br/>33 Body Landmarks"]
    G --> H["Pose Quality Evaluation<br/>Pose / Hand / Foot Score"]
    E --> I["Ball Center + Rim Position"]
    H --> J["BasketballRef Rule Engine"]
    I --> J
    J --> K["Violation Output<br/>Traveling / Carrying / etc."]
    K --> L["OpenCV Overlay"]
    K --> M["Replay Recorder"]
    K --> N["CSV + Event Logs"]
    H --> O["Runtime Status JSON"]
    O --> P["Streamlit Live Demo<br/>Field Test Health"]
    M --> P
    N --> Q["Streamlit Analytics<br/>QA Review + Precision"]
    P --> R["Human Review"]
    R --> Q
```

### อธิบายภาพรวม

- `OpenCV VideoCapture` รับภาพจากกล้องจริง
- `FramePreprocessor` ปรับภาพก่อนส่งเข้า model เพื่อลดผลกระทบจากแสง
- `YOLO Person + ByteTrack` ตรวจจับคนและรักษา Player ID
- `YOLO Ball/Rim` ตรวจจับลูกบาสและห่วง
- `MediaPipe Pose` หา keypoints ของผู้เล่นแต่ละคน
- `Pose Quality` เช็กว่า keypoints ชัดพอสำหรับแต่ละ rule หรือไม่
- `BasketballRef` คือ rule engine กลางที่รวมกติกาทั้งหมด
- `Replay Recorder` บันทึกวิดีโอเมื่อพบ foul
- `Streamlit UI` ใช้ดู live status, replay, analytics และ QA review

---

## 2. Real-Time Main Loop Flow

Flow หลักของ `main.py` ในแต่ละ frame

```mermaid
flowchart TD
    A["Start main.py"] --> B["Load Models<br/>Person YOLO + Ball/Rim YOLO + MediaPipe"]
    B --> C["Open Camera"]
    C --> D{"Read frame success?"}
    D -- No --> Z["Release camera<br/>Close windows"]
    D -- Yes --> E["Preprocess frame"]
    E --> F["Update frame_count"]
    F --> G{"frame_count % YOLO_STRIDE == 0?"}
    G -- Yes --> H["Run Person YOLO + ByteTrack"]
    G -- No --> I["Use cached persons"]
    H --> J["Update person cache"]
    I --> K["Active players"]
    J --> K
    K --> L{"frame_count % BALL_STRIDE == 0?"}
    L -- Yes --> M["Run Ball/Rim YOLO"]
    L -- No --> N["Use cached ball/rim boxes"]
    M --> O["Update ball/rim cache"]
    N --> P["Current ball/rim boxes"]
    O --> P
    P --> Q["Set rim position for Goaltending<br/>Disable if rim not detected"]
    Q --> R["For each player"]
    R --> S["Crop player region"]
    S --> T["Run MediaPipe Pose"]
    T --> U{"Pose exists?"}
    U -- No --> R
    U -- Yes --> V["Convert landmarks to full-frame pixels"]
    V --> W["Basic pose validity check"]
    W --> X{"Valid pose?"}
    X -- No --> Y["Draw Low vis / skip player this frame"]
    Y --> R
    X -- Yes --> AA["Evaluate Pose Quality"]
    AA --> AB["Find nearest ball"]
    AB --> AC["Call BasketballRef.process()"]
    AC --> AD["Draw skeleton, pose score, violations"]
    AD --> R
    R --> AE["Calculate FPS"]
    AE --> AF["Write runtime_status.json every 10 frames"]
    AF --> AG{"Any violation?"}
    AG -- Yes --> AH["Start / continue replay recording"]
    AG -- No --> AI["Show frame"]
    AH --> AJ["Save replay + write logs"]
    AJ --> AI
    AI --> AK{"Press q?"}
    AK -- No --> D
    AK -- Yes --> Z
```

### จุดสำคัญของ main loop

- Person detection ใช้ stride เพื่อลดภาระ CPU/GPU
- Ball/Rim detection ใช้ cache ระหว่าง frame ที่ไม่ได้รัน model
- ถ้าไม่เห็น rim ระบบจะ disable goaltending เพื่อลด false positive
- ถ้า pose ไม่ชัด ระบบจะเขียน `Low vis` แล้ว skip player เฟรมนั้น
- Runtime status ถูกเขียนออกไปที่ `logs/runtime_status.json` เพื่อให้ UI อ่าน

---

## 3. Detection Layer Flow

แยก layer การตรวจจับวัตถุและร่างกาย

```mermaid
flowchart LR
    A["Input Frame"] --> B["Preprocessor"]
    B --> C["Person YOLO"]
    B --> D["Ball/Rim YOLO"]
    C --> E["ByteTrack Player ID"]
    E --> F["Player Boxes<br/>P0, P1, P2..."]
    F --> G["Crop each player"]
    G --> H["MediaPipe Pose"]
    H --> I["Landmarks in crop coordinates"]
    I --> J["Convert to full-frame pixel coordinates"]
    D --> K["Ball boxes"]
    D --> L["Rim boxes"]
    K --> M["Ball center"]
    L --> N["Rim y + rim x-range"]
    J --> O["Rule Engine Input"]
    M --> O
    N --> O
```

### ข้อมูลที่ส่งเข้า rule engine

| Data | Source | ใช้ทำอะไร |
|---|---|---|
| Player ID | ByteTrack | แยก detector state รายคน |
| Landmarks pixel | MediaPipe Pose | ตรวจมือ เท้า ไหล่ สะโพก |
| Ball box / center | Ball YOLO | ตรวจ dribble, holding, carrying |
| Rim y / x-range | Rim YOLO | ตรวจ goaltending |
| Frame size | OpenCV | ใช้ scale และ boundary |

---

## 4. Pose Quality Gate Flow

ระบบนี้ไม่ได้เชื่อ pose ทุกจุดเท่ากัน แต่แยก score ตาม rule

```mermaid
flowchart TD
    A["MediaPipe Landmarks"] --> B["evaluate_pose_quality()"]
    B --> C["Core Score<br/>Shoulder + Hip"]
    B --> D["Hand Score<br/>Wrist + Index + Thumb"]
    B --> E["Foot Score<br/>Hip + Knee + Ankle"]
    B --> F["Overall Pose Score"]
    C --> G{"Core OK?"}
    D --> H{"Hand OK?"}
    E --> I{"Foot OK?"}
    H -- Yes --> J["Allow Double Dribble"]
    H -- Yes --> K["Allow Carrying"]
    H -- Yes --> L["Allow Goaltending hand check"]
    H -- No --> M["Skip hand-based rules<br/>Add PoseQ hand low info"]
    I -- Yes --> N["Allow Traveling"]
    I -- No --> O["Skip Traveling<br/>Add PoseQ foot low info"]
    G --> P["Used for stable player validation"]
```

### แนวคิดแบบ Senior AI Engineer

- ไม่ควรใช้ bounding box อย่างเดียว เพราะไม่รู้ตำแหน่งมือ/เท้า
- ไม่ควรใช้ pose แบบผ่าน/ไม่ผ่านทั้งระบบ เพราะแต่ละ rule ใช้ keypoints ไม่เหมือนกัน
- Traveling ต้องการ `foot_score`
- Carrying, Double Dribble, Held Ball ต้องการ `hand_score`
- Held Ball ต้องการ hand score ของผู้เล่นทั้งสองคน
- ถ้า keypoints ไม่ชัด ระบบควร skip rule นั้น ไม่ควรเดา

---

## 5. BasketballRef Rule Engine Flow

Flow ของ `referee.py`

```mermaid
flowchart TD
    A["BasketballRef.process(player_id, landmarks, ball_box)"] --> B["Get player detectors"]
    B --> C["Calculate shoulder_width"]
    C --> D["Evaluate Pose Quality"]
    D --> E["Calculate ball_center"]
    E --> F["Check ball possession / holding"]
    F --> G["Update BallMotionTracker"]
    G --> H{"Hand pose OK?"}
    G --> I{"Foot pose OK?"}
    H -- Yes --> J["DoubleDribbleDetector.check()"]
    H -- Yes --> K["CarryingDetector.check()"]
    H -- Yes --> L["GoaltendingDetector.check()"]
    H -- No --> M["Skip hand-based rules"]
    I -- Yes --> N["TravelingDetector.check()"]
    I -- No --> O["Skip Traveling"]
    G --> P["Find nearest opponent"]
    P --> Q{"Both players hand pose OK?"}
    Q -- Yes --> R["JumpBallDetector.check()<br/>Held Ball situation"]
    Q -- No --> S["Skip Held Ball check"]
    J --> T["Collect violations"]
    K --> T
    L --> T
    N --> T
    R --> T
    M --> U["Collect info_texts"]
    O --> U
    T --> V["Return violations + info_texts"]
    U --> V
```

### Detector state ต่อผู้เล่น

แต่ละ `player_id` มี detector ของตัวเอง:

```text
dd   = DoubleDribbleDetector
tr   = TravelingDetector
ca   = CarryingDetector
gt   = GoaltendingDetector
jb   = JumpBallDetector
ball = BallMotionTracker
```

การแยก state รายคนช่วยให้ผู้เล่นหลายคนไม่แชร์สถานะผิดกัน

---

## 6. Ball Motion Tracker Flow

`BallMotionTracker` เป็นข้อมูลกลางที่ช่วยลด false positive

```mermaid
flowchart TD
    A["Ball center from YOLO"] --> B{"Ball detected?"}
    B -- No --> C["Increase lost_frames"]
    C --> D{"Still in lost grace?"}
    D -- Yes --> E["Keep previous motion state"]
    D -- No --> F["Reset previous center/delta"]
    B -- Yes --> G["Calculate velocity"]
    G --> H["Calculate delta_y"]
    H --> I{"Previous delta_y was down<br/>and current delta_y is up?"}
    I -- Yes --> J["dribble_event = True"]
    I -- No --> K["dribble_event = False"]
    G --> L{"Velocity below still threshold?"}
    L -- Yes --> M["is_still = True"]
    L -- No --> N["is_still = False"]
    J --> O["BallMotionState"]
    K --> O
    M --> O
    N --> O
```

### ใช้ใน rule ไหน

| Field | ใช้กับ | เหตุผล |
|---|---|---|
| `dribble_event` | Traveling | ลด false positive ตอนกำลังเลี้ยงบอลจริง |
| `is_still` | Held Ball | ลูกต้องนิ่งหรือชะลอจริง |
| `velocity` | Carrying / Double Dribble | แยก holding, pass, shot, dribble |
| `lost_frames` | Stability | กันลูกหาย 1-2 เฟรมแล้ว state พัง |

---

## 7. Traveling Flow

ตรวจ Traveling จาก foot-strike + holding + dribble guard

```mermaid
flowchart TD
    A["TravelingDetector.check()"] --> B{"Foot pose OK?"}
    B -- No --> C["Skip Traveling"]
    B -- Yes --> D["Get left/right ankle"]
    D --> E{"Ankle visibility OK?"}
    E -- No --> F["Return Steps with low ankle vis"]
    E -- Yes --> G["Kalman smooth ankle Y"]
    G --> H{"dribble_event?"}
    H -- Yes --> I["Reset foot trackers<br/>Do not count step"]
    H -- No --> J{"is_holding?"}
    J -- No --> K["Use holding grace or reset steps"]
    J -- Yes --> L{"New possession?"}
    L -- Yes --> M["Start gather frames"]
    L -- No --> N["Track foot strike"]
    M --> O["Update trackers but do not count"]
    N --> P{"Foot lifted then grounded?"}
    P -- Yes --> Q["steps += 1"]
    P -- No --> R["Keep steps"]
    Q --> S{"steps > 2 and confirmed by voter?"}
    S -- Yes --> T["TRAVELING"]
    S -- No --> U["Return step info"]
```

### Key idea

- ไม่ได้นับจาก bounding box
- ใช้ข้อเท้าและ state machine ของเท้า
- ถ้ามี `dribble_event` จะไม่เอาการขยับเท้าเฟรมนั้นไปนับก้าว
- มี gather frame และ holding grace เพื่อกันระบบตัดสินเร็วเกินไป

---

## 8. Double Dribble Flow

ตรวจ Double Dribble ด้วย state machine

```mermaid
flowchart TD
    A["DoubleDribbleDetector.check()"] --> B{"Ball detected?"}
    B -- No --> C["Increase ball lost frames"]
    C --> D{"Timeout?"}
    D -- Yes --> E["Reset to IDLE"]
    D -- No --> F["Keep state"]
    B -- Yes --> G["Calculate ball velocity + dribble_event"]
    G --> H["Get wrist positions"]
    H --> I{"Touching ball?"}
    I -- No --> J["Increase no_touch_frames"]
    I -- Yes --> K["Reset no_touch_frames"]
    K --> L{"Current state"}
    L -- IDLE --> M{"Touch or dribble_event?"}
    M -- Yes --> N["State = DRIBBLING"]
    L -- DRIBBLING --> O{"Holding confirmed?"}
    O -- Yes --> P["State = HOLDING"]
    L -- HOLDING --> Q{"Dribble again after holding?"}
    Q -- Yes --> R["DOUBLE DRIBBLE"]
    Q -- No --> S{"Fast ball far from hands?"}
    S -- Yes --> E
```

### Key idea

- ต้องเคย dribble ก่อน
- ต้องมี holding confirmed หลายเฟรม
- ถ้าหลัง holding แล้วเริ่ม dribble ใหม่ จึงเป็น double dribble
- ถ้าบอลเร็วและห่างมือมาก ถือว่าอาจเป็น pass/shot แล้ว reset

---

## 9. Carrying Flow

ตรวจ Carrying / Palming จากมือรองบอล + บอลนิ่ง

```mermaid
flowchart TD
    A["CarryingDetector.check()"] --> B{"is_holding?"}
    B -- No --> C["Reset consecutive frames"]
    B -- Yes --> D{"ball_center exists?"}
    D -- No --> C
    D -- Yes --> E["Calculate ball velocity"]
    E --> F{"Ball is still?"}
    F -- No --> C
    F -- Yes --> G["Find nearest hand to ball"]
    G --> H{"Hand near ball?"}
    H -- No --> C
    H -- Yes --> I{"Wrist lower than index?"}
    I -- No --> C
    I -- Yes --> J{"Ball above wrist?"}
    J -- No --> C
    J -- Yes --> K["consecutive += 1"]
    K --> L{"consecutive >= CONFIRM_FRAMES?"}
    L -- Yes --> M["CARRYING (L/R)"]
    L -- No --> N["Wait for confirmation"]
```

### Key idea

- Carrying ไม่ใช่แค่มืออยู่ใต้บอลในเฟรมเดียว
- ต้องใกล้บอลจริง
- บอลต้องช้าหรือหยุดในมือ
- ต้องเกิดหลายเฟรมติดกัน

---

## 10. Goaltending Flow

ตรวจ Goaltending เฉพาะเมื่อเห็น rim จริง

```mermaid
flowchart TD
    A["GoaltendingDetector.check()"] --> B{"Rim detected?"}
    B -- No --> C["Disable Goaltending<br/>Return no foul"]
    B -- Yes --> D["Track ball y-history"]
    D --> E{"Ball above/near rim plane?"}
    E -- No --> F["No foul"]
    E -- Yes --> G{"Ball moving downward?"}
    G -- No --> F
    G -- Yes --> H{"Hand near ball?"}
    H -- No --> F
    H -- Yes --> I["GOALTENDING"]
```

### Key idea

- ถ้า `best.pt` ยังตรวจ rim ไม่ดี ระบบจะไม่เดา goaltending
- วิธีนี้ลด false positive ตอนทดสอบในห้องหรือสนามที่ไม่เห็นห่วง

---

## 11. Held Ball / Jump Ball Flow

ตรวจสถานการณ์ลูกยึดตามกติกา

```mermaid
flowchart TD
    A["JumpBallDetector.check()"] --> B{"Ball center exists?"}
    B -- No --> C["Reset confirm"]
    B -- Yes --> D{"Opponent landmarks exist?"}
    D -- No --> C
    D -- Yes --> E["Get hand points<br/>wrists/index/thumbs"]
    E --> F{"Both players have hand points?"}
    F -- No --> C
    F -- Yes --> G["Calculate dynamic hand-ball threshold"]
    G --> H["Count my hand points near ball"]
    G --> I["Count opponent hand points near ball"]
    H --> J{"Both players on ball?"}
    I --> J
    J -- No --> C
    J -- Yes --> K{"Ball is still?"}
    K -- No --> C
    K -- Yes --> L["confirm_count += 1"]
    L --> M{"confirm_count >= CONFIRM_FRAMES?"}
    M -- Yes --> N["HELD BALL / JUMP BALL"]
    M -- No --> O["Show debug info"]
```

### Key idea

- ไม่ใช่ Push Foul
- ไม่ใช่ Illegal Hands
- ต้องมีผู้เล่นสองฝ่ายจับบอลหรือควบคุมบอลพร้อมกัน
- บอลต้องนิ่งหรือชะลอจริง
- ต้องยืนยันหลายเฟรม

---

## 12. Replay + Event Logging Flow

เมื่อตรวจพบ foul ระบบจะบันทึก replay และ log

```mermaid
flowchart TD
    A["Violation detected"] --> B{"Already recording?"}
    B -- No --> C["Start replay recording"]
    B -- Yes --> D["Continue current recording"]
    C --> E["Collect pre-foul frames from replay_buffer"]
    D --> F["Collect foul names and player ids"]
    E --> F
    F --> G["Record post-foul frames"]
    G --> H{"recording_left <= 0?"}
    H -- No --> G
    H -- Yes --> I["Create replay filename"]
    I --> J["Save MP4 in logs/replays"]
    J --> K["Write basketball_foul_logs.csv"]
    J --> L["Write logs/foul_events.csv"]
    L --> M["Event_ID + Replay_Path"]
    M --> N["Available for QA Review in UI"]
```

### ไฟล์ log ที่เกี่ยวข้อง

| File | Purpose |
|---|---|
| `basketball_foul_logs.csv` | log แบบเดิม ใช้ feed/analytics พื้นฐาน |
| `logs/foul_events.csv` | event log รุ่นใหม่ มี Event_ID + Replay_Path |
| `logs/review_labels.csv` | human QA review |
| `logs/runtime_status.json` | field test health แบบ real-time |
| `logs/replays/*.mp4` | replay video เมื่อเกิด foul |

---

## 13. QA Review + Accuracy Flow

ระบบไม่เรียก confidence ว่า accuracy แต่ใช้ human review เพื่อคำนวณ precision

```mermaid
flowchart TD
    A["Replay saved"] --> B["foul_events.csv has Event_ID"]
    B --> C["Live Demo shows replay"]
    C --> D["Human reviewer opens QA Review"]
    D --> E{"Review status"}
    E -- Correct --> F["True Positive"]
    E -- False Positive --> G["False Positive"]
    E -- Wrong Rule --> H["Wrong Classification"]
    E -- Unclear --> I["Exclude or inspect later"]
    F --> J["review_labels.csv"]
    G --> J
    H --> J
    I --> J
    J --> K["Analytics Dashboard"]
    K --> L["Review Precision"]
    K --> M["Per-rule QA summary"]
```

### Metric ที่ใช้ตอนนี้

```text
Review Precision = Correct / (Correct + False Positive + Wrong Rule)
```

หมายเหตุ:

- ยังไม่ใช่ Recall
- Recall ต้องมีการบันทึกจังหวะที่ AI พลาดไม่จับ foul
- ดังนั้นระบบปัจจุบันใช้ `Review Precision` ซึ่งถูกต้องกว่า `Accuracy %`

---

## 14. Runtime Status / Field Test Health Flow

ใช้ดูความพร้อมตอนเทสสนามจริง

```mermaid
flowchart TD
    A["main.py running"] --> B["Collect runtime metrics every 10 frames"]
    B --> C["FPS"]
    B --> D["Players tracked"]
    B --> E["Ball detected / count"]
    B --> F["Rim detected / count"]
    B --> G["Pose Q / Hand Q / Foot Q"]
    B --> H["Low vis players"]
    C --> I["Write logs/runtime_status.json"]
    D --> I
    E --> I
    F --> I
    G --> I
    H --> I
    I --> J["pages/1_live_demo.py reads JSON"]
    J --> K["Field Test Health cards"]
```

### วิธีอ่านค่าตอนเทสจริง

| UI Field | แปลว่า | ถ้าค่าต่ำควรทำอะไร |
|---|---|---|
| `FPS` | ความลื่นของระบบ | ลด imgsz หรือจำนวนผู้เล่น |
| `Players` | จำนวนผู้เล่นที่ YOLO track ได้ | ปรับมุมกล้องให้เห็นคนเต็มตัว |
| `Ball` | เห็นลูกบาสหรือไม่ | ขยับกล้อง / ปรับ model / ลดแสงสะท้อน |
| `Rim` | เห็นห่วงหรือไม่ | ถ้าไม่เห็น Goaltending จะถูก disable |
| `Pose Q` | คุณภาพ pose รวม | ถอยกล้องให้เห็นเต็มตัว |
| `Hand Q` | มือ/นิ้วชัดไหม | สำคัญกับ Carrying, Double Dribble, Held Ball |
| `Foot Q` | เท้า/เข่า/สะโพกชัดไหม | สำคัญกับ Traveling |
| `Low Vis` | จำนวนผู้เล่นที่ pose ไม่ชัด | ปรับมุมกล้องหรือแสง |

---

## 15. Streamlit UI Flow

Flow ของหน้า UI ในโฟลเดอร์ `pages`

```mermaid
flowchart TD
    A["Streamlit app_ui.py"] --> B["Sidebar Navigation"]
    B --> C["pages/1_live_demo.py"]
    B --> D["pages/2_analytics.py"]
    B --> E["pages/3_system_info.py"]
    C --> F["Start/Stop main.py subprocess"]
    C --> G["Read runtime_status.json"]
    C --> H["Read basketball_foul_logs.csv"]
    C --> I["Read replay videos"]
    C --> J["QA Review replay"]
    J --> K["Write review_labels.csv"]
    D --> L["Read foul logs"]
    D --> M["Filter active/deprecated rules"]
    D --> N["Read foul_events.csv + review_labels.csv"]
    N --> O["Calculate Review Precision"]
    E --> P["Explain architecture + active rules"]
```

### Page responsibility

| Page | Responsibility |
|---|---|
| `pages/1_live_demo.py` | Start/stop system, Field Test Health, live foul feed, replay, QA review |
| `pages/2_analytics.py` | charts, active/deprecated filters, review precision |
| `pages/3_system_info.py` | architecture, rules, tech stack |

---

## 16. Data/File Flow

แสดงว่าแต่ละไฟล์ข้อมูลถูกสร้างและถูกอ่านตรงไหน

```mermaid
flowchart LR
    A["main.py"] --> B["logs/runtime_status.json"]
    A --> C["basketball_foul_logs.csv"]
    A --> D["logs/foul_events.csv"]
    A --> E["logs/replays/*.mp4"]
    F["pages/1_live_demo.py"] --> G["logs/review_labels.csv"]
    B --> F
    C --> F
    D --> F
    E --> F
    C --> H["pages/2_analytics.py"]
    D --> H
    G --> H
```

### สรุปข้อมูลแต่ละไฟล์

```text
basketball_foul_logs.csv
  - log ง่าย ๆ สำหรับ foul feed และสถิติเบื้องต้น

logs/foul_events.csv
  - event-level log
  - ผูก foul กับ replay path
  - ใช้กับ QA review

logs/review_labels.csv
  - มนุษย์รีวิวว่า event ถูกหรือผิด
  - ใช้คำนวณ Review Precision

logs/runtime_status.json
  - ค่าสุขภาพระบบแบบ real-time
  - ใช้ใน Live Demo / Field Test Health

logs/replays/*.mp4
  - วิดีโอ replay หลังเกิด foul
```

---

## 17. Field Test Checklist Flow

Flow สำหรับใช้เช็กก่อนเริ่มทดสอบสนามจริง

```mermaid
flowchart TD
    A["Start Field Test"] --> B["Open Streamlit Live Demo"]
    B --> C["Select camera"]
    C --> D["Start System"]
    D --> E["Check Field Test Health"]
    E --> F{"FPS stable?"}
    F -- No --> G["Reduce load<br/>lower imgsz / fewer players"]
    F -- Yes --> H{"Ball detected often?"}
    H -- No --> I["Adjust camera angle / lighting"]
    H -- Yes --> J{"Pose Q acceptable?"}
    J -- No --> K["Move camera back<br/>show full body"]
    J -- Yes --> L{"Hand Q acceptable?"}
    L -- No --> M["Improve hand visibility<br/>avoid occlusion"]
    L -- Yes --> N{"Foot Q acceptable?"}
    N -- No --> O["Show ankles/feet in frame"]
    N -- Yes --> P["Run foul scenarios"]
    P --> Q["Review replays"]
    Q --> R["Label Correct / False Positive / Wrong Rule"]
    R --> S["Analyze Review Precision"]
```

### Threshold แนะนำตอนเทส

```text
Pose Q >= 60%    = ใช้ได้
Hand Q >= 45%    = เริ่มเชื่อ hand-based rules ได้
Foot Q >= 50%    = เริ่มเชื่อ Traveling ได้
Ball = YES บ่อย  = ball detection ใช้ได้
Rim = YES เฉพาะเมื่อต้องทดสอบ Goaltending
```

---

## 18. Suggested Presentation Diagram

ถ้าจะวาดในสไลด์หรือ resume ให้ใช้ diagram แบบย่ออันนี้

```mermaid
flowchart LR
    A["Camera"] --> B["OpenCV + Preprocessing"]
    B --> C["YOLO<br/>Person + Ball + Rim"]
    C --> D["ByteTrack<br/>Player ID"]
    D --> E["MediaPipe Pose"]
    E --> F["Pose Quality Gate"]
    C --> G["Ball Motion Tracker"]
    F --> H["Rule Engine"]
    G --> H
    H --> I["Foul Detection"]
    I --> J["Replay + Event Log"]
    J --> K["Streamlit UI"]
    K --> L["QA Review + Analytics"]
```

### Resume wording

```text
Built a real-time AI basketball referee pipeline using YOLOv8, ByteTrack,
MediaPipe Pose, OpenCV, and Streamlit. Designed a rule-based foul engine with
pose-quality gating, ball-motion tracking, replay-linked event logging, and
human QA review for precision analysis.
```

---

## 19. Current Active Rules Summary

```mermaid
flowchart TD
    A["BasketballRef"] --> B["Double Dribble"]
    A --> C["Traveling"]
    A --> D["Carrying"]
    A --> E["Goaltending"]
    A --> F["Held Ball / Jump Ball"]
    B --> G["Hand Q + Ball Motion + State Machine"]
    C --> H["Foot Q + Foot Strike + Holding + Dribble Event"]
    D --> I["Hand Q + Palm-up + Ball Still"]
    E --> J["Hand Q + Ball Trajectory + Real Rim Detection"]
    F --> K["Two-player Hand Q + Ball Still"]
```

### Deprecated / Removed

```text
Contact Foul / 3D-CNN
Push Foul
Illegal Hands
```

ข้อมูลเก่าจาก deprecated rules ยังอาจอยู่ใน `basketball_foul_logs.csv` แต่ UI แยก active/deprecated แล้ว

---

## 20. How To Draw This Manually

ถ้าจะเอาไปวาดเองใน diagrams.net, Figma, Canva หรือ PowerPoint แนะนำใช้ 5 กล่องหลัก:

```text
1. Input
   Camera / Frame

2. Perception
   Preprocessor / YOLO / MediaPipe / Pose Quality

3. Reasoning
   BasketballRef / Rule Detectors / BallMotionTracker

4. Evidence
   Replay / Logs / Event_ID / Runtime Status

5. User Interface
   Live Demo / QA Review / Analytics
```

Flow ที่ควรวาด:

```text
Camera
  -> Preprocess
  -> YOLO + Pose
  -> Pose Quality + Ball Motion
  -> Rule Engine
  -> Violation
  -> Replay + Logs
  -> UI + Human Review
  -> Analytics
```

สีที่แนะนำ:

```text
Input         = Gray / Blue
AI Models     = Purple
Rule Engine   = Orange
Safety Gates  = Yellow
Logging       = Green
UI/Analytics  = Cyan
Violation     = Red
```

---

## 21. Final End-to-End Flow

Flow รวมแบบเข้าใจง่ายที่สุด

```mermaid
flowchart TD
    A["Camera frame"] --> B["Clean frame with preprocessor"]
    B --> C["Detect players, ball, rim"]
    C --> D["Track player IDs"]
    D --> E["Estimate pose for each player"]
    E --> F["Score pose quality"]
    F --> G{"Quality good enough for each rule?"}
    G -- No --> H["Skip unsafe rule<br/>avoid false positive"]
    G -- Yes --> I["Run BasketballRef detectors"]
    I --> J{"Violation found?"}
    J -- No --> K["Show normal overlay"]
    J -- Yes --> L["Show violation overlay"]
    L --> M["Save replay"]
    L --> N["Write event logs"]
    N --> O["Show in Streamlit UI"]
    M --> O
    O --> P["Human QA review"]
    P --> Q["Analytics precision report"]
```

