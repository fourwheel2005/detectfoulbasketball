# System Flowcharts — AI Basketball Foul Detection

> Flowchart ทั้งหมดของระบบ วิเคราะห์จากซอร์สโค้ดจริง  
> เรนเดอร์ด้วย Mermaid (VS Code: ติดตั้ง "Markdown Preview Mermaid Support")

---

## Flowchart 1: Main System Pipeline (ภาพรวมทั้งระบบ)

```mermaid
flowchart TD
    A([🎥 Camera Input\niPhone / MacBook]) --> B

    B["YOLOv8n Person Detection\n+ ByteTrack Tracking\nclass=0 person"]
    B --> C{พบผู้เล่นไหม?}
    C -- ไม่พบ --> B
    C -- พบ --> D

    D["เรียงตาม Track ID\nจำกัด MAX_PLAYERS = 4"]
    D --> E

    E["YOLOv8 Ball + Rim Detection\n(Custom best.pt)"]
    E --> F{พบ best.pt?}
    F -- ไม่พบ --> G["Fallback:\nYOLOv8 COCO class 32\nsports ball"]
    F -- พบ --> H["ตรวจ class 0: basketball\nclass 1: rim\nclass 2: sports ball"]
    G --> I
    H --> I

    I["อัปเดต rim_y_px\nให้ GoaltendingDetector"]
    I --> J

    J[/"Loop ทุกผู้เล่น (tid, x1,y1,x2,y2)"/]
    J --> K

    K["Crop ผู้เล่น\n+ Padding 25px"]
    K --> L["MediaPipe Pose\n33 Landmarks → Pixel Coords"]
    L --> M{Pose พบ\nLandmarks?}
    M -- ไม่พบ --> N["วาดกล่องสีเทา\nข้ามผู้เล่นนี้"]
    N --> J

    M -- พบ --> O["Pose Validity Check\n_is_pose_valid()"]
    O --> P{Valid?}
    P -- ไม่ผ่าน --> N
    P -- ผ่าน --> Q

    Q["หา Ball ที่ใกล้ผู้เล่นนี้\nnearest_ball()"]
    Q --> R["BasketballRef.process()\nเรียก 5 Detectors"]

    R --> S["Double Dribble\nDetector"]
    R --> T["Traveling\nDetector"]
    R --> U["Carrying\nDetector"]
    R --> V["Goaltending\nDetector"]
    R --> W["Jump Ball Foul\nDetector"]

    S & T & U & V & W --> X{มี\nViolation?}

    X -- ไม่มี --> Y["วาดกล่องสีเขียว\nแสดง Info Steps"]
    X -- มี --> Z["วาดกล่องสีแดง\nแสดง !!! Foul Name"]

    Z --> AA["🚨 Trigger\nReplay Recording"]
    AA --> AB["บันทึก CSV\nFoulLogger.log_foul()"]

    Y & Z --> AC
    J -- ครบทุกคน --> AC

    AC["แสดง FPS\nบนหน้าจอ"]
    AC --> AD["cv2.imshow\nAI Referee Window"]
    AD --> AE{กด q?}
    AE -- ไม่ --> B
    AE -- ใช่ --> AF([🔴 ปิดระบบ])
```

---

## Flowchart 2: Pose Validity Check

```mermaid
flowchart TD
    A([เริ่ม: landmarks_px]) --> B

    B["ตรวจ Key Landmarks 5 จุด\nNose, L/R Shoulder, L/R Hip"]
    B --> C["นับจุดที่หายไป\nmissing = จุดที่ไม่มีใน dict"]

    C --> D{missing > 2?}
    D -- ใช่ --> E(["❌ Reject\nPose incomplete"])

    D -- ไม่ --> F

    F["คำนวณ Bounding Box\nของ Landmarks ทั้งหมด\nw = max(x) - min(x)\nh = max(y) - min(y)"]

    F --> G{"h/w < 0.5?\n(แนวนอน = แขน/มือ)"}
    G -- ใช่ --> H(["❌ Reject\nAspect ratio invalid"])
    G -- ไม่ --> I(["✅ Valid Pose\nส่งต่อให้ Detectors"])
```

---

## Flowchart 3: Double Dribble State Machine

```mermaid
flowchart TD
    A([เริ่ม: frame ใหม่]) --> B{ball_center\nมีค่าไหม?}
    B -- ไม่มี --> Z(["return False"])
    B -- มี --> C

    C{"State == HOLDING?\nและ ball เคลื่อน\n> 30px/frame?"}
    C -- ใช่ --> D["Auto Reset → IDLE\n(บอลถูกส่ง/ชู้ตแล้ว)"]
    D --> E
    C -- ไม่ --> E

    E{"State == VIOLATION?"}
    E -- ใช่ --> F["violation_frames++"]
    F --> G{violation_frames\n>= 30?}
    G -- ใช่ --> H["Reset → IDLE"]
    G -- ไม่ --> I(["return False\n'State: VIOLATION'"])

    E -- ไม่ --> J

    J["คำนวณ dist_R, dist_L\n= Euclidean(wrist, ball_center)"]
    J --> K["touching_right = dist_R < 140px\ntouching_left  = dist_L < 140px\ntouching_both  = R AND L\ntouching_any   = R OR L"]

    K --> L{touching_any?}
    L -- ไม่ --> M["no_touch_frames++"]
    M --> N{no_touch_frames\n>= 45?}
    N -- ใช่ --> O["Reset → IDLE"]
    N -- ไม่ --> P(["return False"])
    O --> P

    L -- ใช่ --> Q["no_touch_frames = 0"]
    Q --> R{touching_both?}

    R -- ใช่ --> S["State = HOLDING\n(จับสองมือแล้ว)"]
    S --> Z

    R -- ไม่ --> T{State == HOLDING?}
    T -- ใช่ --> U["State = VIOLATION\n⚠️ DOUBLE DRIBBLE!"]
    U --> V(["return True\n'DOUBLE DRIBBLE'"])

    T -- ไม่ --> W{State == IDLE?}
    W -- ใช่ --> X["State = DRIBBLING"]
    W -- ไม่ --> Z
    X --> Z
```

---

## Flowchart 4: Traveling Detection

```mermaid
flowchart TD
    A([เริ่ม: frame ใหม่]) --> B["frame_n++"]
    B --> C{L/R Ankle\nมีค่าไหม?}
    C -- ไม่ --> Z(["return False\n'Steps: N'"])
    C -- มี --> D

    D["Kalman Filter 1D\nl_y = kf_l.update(ankle_L_y)\nr_y = kf_r.update(ankle_R_y)"]

    D --> E["Dynamic Lift Threshold\n= max(shoulder_width × 0.18, 12px)"]

    E --> F{"is_holding\nเพิ่งเปลี่ยน\nFalse → True?"}
    F -- ใช่ --> G["Gather Step Reset\nsteps = 0\ngather_left = 10\nReset FootStepTrackers"]
    G --> H
    F -- ไม่ --> H

    H{is_holding?}
    H -- ไม่ --> Z

    H -- ใช่ --> I{gather_left > 0?}
    I -- ใช่ --> J["gather_left--\nอัปเดต Kalman แต่ไม่นับก้าว"]
    J --> K(["return False\n'Steps: N [gather]'"])

    I -- ไม่ --> L

    L["FootStepTracker L: update(l_y, threshold)\nFootStepTracker R: update(r_y, threshold)"]

    L --> M{step_L เกิดขึ้น?\n(LIFTED → GROUNDED)}
    M -- ใช่ --> N{"frame_n - last_step\n> 2? (Jump Stop Check)"}
    N -- ใช่ --> O["steps += 1"]
    N -- ไม่ --> P["(Jump Stop: นับรวมกัน)"]
    O & P --> Q["last_step_frame = frame_n"]

    Q --> R{step_R เกิดขึ้น?}
    M -- ไม่ --> R

    R -- ใช่ --> S{"frame_n - last_step\n> 2?"}
    S -- ใช่ --> T["steps += 1"]
    S -- ไม่ --> U["(Jump Stop)"]
    T & U --> V["last_step_frame = frame_n"]

    R -- ไม่ --> V

    V --> W{steps > 2?}
    W -- ไม่ --> Z
    W -- ใช่ --> X["TemporalVoter.vote(True)\n(window=5, need 4/5)"]
    X --> Y{Vote\nConfirmed?}
    Y -- ไม่ --> Z
    Y -- ใช่ --> AA(["return True\n'TRAVELING (N steps)'"])
```

---

## Flowchart 5: Carrying Detection

```mermaid
flowchart TD
    A([เริ่ม: frame ใหม่]) --> B{is_holding?}
    B -- ไม่ --> C["consecutive = 0\nprev_ball = None"]
    C --> Z(["return False"])

    B -- ใช่ --> D

    D["คำนวณ Ball Velocity\n= Euclidean(ball_center, prev_ball)"]
    D --> E["ball_still_threshold\n= max(shoulder_w × 0.08, 6px)"]
    E --> F{"ball_vel <\nball_still_threshold?"}
    F -- ใช่ --> G["ball_is_still = True"]
    F -- ไม่ --> H["ball_is_still = False"]
    G & H --> I

    I["Dynamic Y Buffer\n= max(shoulder_w × 0.15, 10px)"]
    I --> J

    J["ตรวจมือขวา:\nr_carry = wrist_R_y > index_R_y + buffer\nตรวจมือซ้าย:\nl_carry = wrist_L_y > index_L_y + buffer"]

    J --> K{"(r_carry OR l_carry)\nAND ball_is_still?"}

    K -- ใช่ --> L["consecutive++"]
    K -- ไม่ --> M["consecutive = 0"]

    L --> N{consecutive\n>= 5 frames?}
    N -- ใช่ --> O(["return True\n'CARRYING'"])
    N -- ไม่ --> Z
    M --> Z
```

---

## Flowchart 6: Goaltending Detection

```mermaid
flowchart TD
    A([เริ่ม: frame ใหม่]) --> B{ball_center\nมีค่าไหม?}
    B -- ไม่ --> C["Clear y_history"]
    C --> Z(["return False"])

    B -- มี --> D

    D["rim_y = rim_y_px\n(จาก YOLO หรือ fallback 42% height)"]
    D --> E["y_history.append(ball_y)\n(deque maxlen=15)"]

    E --> F{len(y_history)\n>= 8?}
    F -- ไม่ --> Z

    F -- ใช่ --> G{ball_y < rim_y?\n(บอลอยู่เหนือห่วง)}
    G -- ไม่ --> Z

    G -- ใช่ --> H

    H["np.polyfit(t, y_values, deg=2)\n→ สัมประสิทธิ์ (a, b, c)\ny = at² + bt + c"]

    H --> I{"a > 0.5?\n(พาราโบลาหงาย)\nAND y[-1] > y[-2]?\n(กำลังลง)"}
    I -- ไม่ --> Z

    I -- ใช่ --> J{มี hands_positions?}
    J -- ไม่ --> Z

    J -- ใช่ --> K["วัดระยะทุกมือ:\ndist = hypot(hand_x - ball_x,\n             hand_y - ball_y)"]
    K --> L{dist < 80px\nสำหรับมือใดมือหนึ่ง?}

    L -- ไม่ --> Z
    L -- ใช่ --> M["Clear y_history\n(ป้องกัน duplicate alert)"]
    M --> N(["return True\n'GOALTENDING ⚠️'"])
```

---

## Flowchart 7: Jump Ball Foul — Phase Detection

```mermaid
flowchart TD
    A([เริ่ม: frame ใหม่]) --> B{All Landmarks\nครบไหม?\nAnkle L/R, Hip L/R}
    B -- ไม่ --> Z(["return ไม่เปลี่ยน Phase"])

    B -- ใช่ --> C{Phase == IDLE?}
    C -- ใช่ --> D["เก็บ Baseline:\nl_ankle_baseline.append(ankle_L_y)\nr_ankle_baseline.append(ankle_R_y)\nhip_baseline.append(hip_y)"]
    D --> E
    C -- ไม่ --> E

    E{len(baseline)\n>= 20 frames?}
    E -- ไม่ --> Z

    E -- ใช่ --> F

    F["คำนวณ Baseline averages\nbase_l = mean(l_ankle_baseline)\nbase_r = mean(r_ankle_baseline)\nbase_hip = mean(hip_baseline)"]

    F --> G["คำนวณ Lift:\nlift_l = base_l - ankle_L_y\nlift_r = base_r - ankle_R_y\nhip_lift = base_hip - hip_y"]

    G --> H{"lift_l > 60px\nAND lift_r > 60px?\n(ทั้งสองเท้าลอย)"}
    H -- ไม่ --> I{"Phase ==\nAIRBORNE?"}
    I -- ใช่ --> J["Phase = LANDING"]
    I -- ไม่ --> K{"Phase ==\nLANDING?"}
    K -- ใช่ --> L["Phase = IDLE\nairborne_cnt = 0"]
    K -- ไม่ --> Z
    J & L --> Z

    H -- ใช่ --> M{"hip_lift > 36px?\n(60 × 0.6)"}
    M -- ไม่ --> I

    M -- ใช่ --> N["airborne_cnt++"]
    N --> O{airborne_cnt\n>= 5 frames?}
    O -- ไม่ --> Z
    O -- ใช่ --> P{"Phase !=\nAIRBORNE?"}
    P -- ใช่ --> Q["jump_count++"]
    Q --> R["Phase = AIRBORNE"]
    P -- ไม่ --> R
    R --> Z
```

---

## Flowchart 8: Jump Ball Foul — Foul Detection (Airborne Phase)

```mermaid
flowchart TD
    A([เริ่ม: AIRBORNE Phase]) --> B

    B["ลด push_cd_frames\n(Cooldown counter)"]

    B --> C{Wrist L/R\nมีค่าไหม?}
    C -- ใช่ --> D["ตรวจ Push Foul"]
    C -- ไม่ --> G

    subgraph PUSH["Push Foul Check"]
        D --> D1{push_cd_frames > 0?\nยังอยู่ใน Cooldown}
        D1 -- ใช่ --> D2(["Skip Push Check"])
        D1 -- ไม่ --> D3["คำนวณ Wrist Velocity:\nvel_R = dist(wrist_R, prev_wrist_R)\nvel_L = dist(wrist_L, prev_wrist_L)\nmax_vel = max(vel_R, vel_L)"]
        D3 --> D4{max_vel > 80px/frame?}
        D4 -- ใช่ --> D5["push_cd = 30 frames\npush_confirm++"]
        D4 -- ไม่ --> D6{"ระยะมือ ↔\nหน้าอกคู่ต่อสู้\n< 80px?"}
        D6 -- ใช่ --> D5
        D6 -- ไม่ --> D7["push_confirm = 0"]
        D5 --> D8{push_confirm\n>= 3 frames?}
        D8 -- ใช่ --> D9(["✅ PUSH FOUL"])
        D8 -- ไม่ --> D2
    end

    G["ตรวจ Illegal Hands"]

    subgraph ELBOW["Illegal Hands Check"]
        G --> G1{"Shoulder/Elbow/Wrist\nครบทุกจุดไหม?"}
        G1 -- ไม่ --> G8(["Skip"])
        G1 -- ใช่ --> G2["คำนวณ Elbow Angle:\nangle_R = arctan2(Shoulder→Elbow→Wrist)\nangle_L = arctan2(...)"]
        G2 --> G3["max_angle = max(angle_R, angle_L)"]
        G3 --> G4{max_angle > 155°?}
        G4 -- ไม่ --> G5["elbow_confirm = 0"]
        G4 -- ใช่ --> G6{"ข้อมืออยู่สูงกว่า\nหน้าอก?\nwrist_y < shoulder_y + 50"}
        G6 -- ไม่ --> G5
        G6 -- ใช่ --> G7["elbow_confirm++"]
        G7 --> G8b{elbow_confirm\n>= 3 frames?}
        G8b -- ใช่ --> G9(["✅ ILLEGAL HANDS"])
        G8b -- ไม่ --> G8
    end

    B --> G
```

---

## Flowchart 9: Replay Recording System

```mermaid
flowchart TD
    A([ทุก Frame]) --> B["replay_buffer.append(frame)\n(deque maxlen=90 frames = 3 วินาที)"]

    B --> C{any_violation\nในเฟรมนี้?}
    C -- ไม่ --> D{is_recording?}
    C -- ใช่ --> E{is_recording\nอยู่แล้วไหม?}

    E -- ไม่ --> F["เริ่ม Recording:\nis_recording = True\nrecording_left = 30 frames\nrecorded_foul_names = set()"]
    F --> G
    E -- ใช่ --> G

    G["recorded_foul_names\n.update(frame_foul_names)"]
    G --> H["แสดง 🔴 REC indicator\n(กระพริบทุก 10 frames)"]
    H --> I["recording_left -= 1"]
    I --> J{recording_left <= 0?}

    J -- ไม่ --> K(["ถ่ายต่อไป"])
    J -- ใช่ --> L

    L["is_recording = False\nframes_to_save = list(replay_buffer)\n(90 + 30 = ~4 วินาที)"]

    L --> M["สร้างชื่อไฟล์:\nfoul_{timestamp}_{FOUL_LABEL}.mp4"]

    M --> N["🧵 Background Thread\nsave_replay_video(frames, path, fps)"]

    N --> O["cv2.VideoWriter\ncodec: mp4v\nbันทึกทุก frame"]
    O --> P(["💾 บันทึกไฟล์\nlogs/replays/"])

    D -- ไม่ --> Q(["ไปเฟรมถัดไป"])
    D -- ใช่ --> G
```

---

## Flowchart 10: UI System (Streamlit)

```mermaid
flowchart TD
    A([ผู้ใช้เปิด Browser]) --> B["app_ui.py\nHome Page"]

    B --> C{เลือกหน้า\nจาก Sidebar}

    C --> D["🎥 Live Demo\n1_live_demo.py"]
    C --> E["📊 Analytics\n2_analytics.py"]
    C --> F["ℹ️ System Info\n3_system_info.py"]

    subgraph LIVE["Live Demo"]
        D --> D1{กด\n▶ Start System?}
        D1 -- ใช่ --> D2["subprocess.Popen\npython main.py"]
        D2 --> D3["OpenCV Window\nเปิดแยก"]
        D3 --> D4["Auto-refresh 2 วินาที\nอ่าน CSV ล่าสุด"]
        D4 --> D5["แสดง Foul Feed\n+ KPI Cards"]
        D5 --> D6["แสดง Replay Videos\nจาก logs/replays/"]
        D1 -- ไม่ --> D7{กด\n⏹ Stop?}
        D7 -- ใช่ --> D8["process.terminate()\nปิด OpenCV"]
    end

    subgraph ANALYTICS["Analytics Dashboard"]
        E --> E1["โหลด basketball_foul_logs.csv\n@st.cache_data(ttl=5)"]
        E1 --> E2["Sidebar Filters:\nFoul Type / Player / Date"]
        E2 --> E3["KPI Cards:\nTotal / Top Foul / Top Player"]
        E3 --> E4["Bar Chart (Foul Type)"]
        E4 --> E5["Pie Chart (Distribution)"]
        E5 --> E6["Timeline Chart (per minute)"]
        E6 --> E7["Player Comparison\nStacked Bar"]
        E7 --> E8["Hourly Heatmap"]
        E8 --> E9["Log Table + Export CSV"]
    end

    subgraph INFO["System Info"]
        F --> F1["Architecture Flow\n6 ขั้นตอน"]
        F1 --> F2["Foul Rule Cards\n6 ประเภท + วิธีตรวจ"]
        F2 --> F3["Tech Stack Cards\nYOLO / MediaPipe / etc."]
        F3 --> F4["Model Info\nbest.pt / yolov8n.pt"]
    end
```

---

## สรุป Flowchart ทั้งหมด

| # | Flowchart | ครอบคลุม |
|---|-----------|---------|
| 1 | **Main System Pipeline** | ภาพรวมทั้งระบบตั้งแต่กล้องถึง output |
| 2 | **Pose Validity Check** | กรอง detection ที่ไม่ใช่คน |
| 3 | **Double Dribble** | State Machine 4 สถานะ + auto-reset |
| 4 | **Traveling** | Kalman → FootStepTracker → TemporalVoter |
| 5 | **Carrying** | Palm position + Ball velocity check |
| 6 | **Goaltending** | Parabola fitting + Hand contact |
| 7 | **Jump Ball — Phase** | Baseline adaptive + IDLE/RISING/AIRBORNE/LANDING |
| 8 | **Jump Ball — Foul** | Push velocity + Elbow angle (Airborne only) |
| 9 | **Replay Recording** | Buffer → trigger → background save thread |
| 10 | **UI System** | Streamlit 3 หน้า + subprocess control |
