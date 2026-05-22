# AI Basketball Referee System

ระบบตรวจจับเหตุการณ์ผิดกติกาในกีฬาบาสเกตบอลจากวิดีโอแบบ real-time โดยใช้กล้องเดี่ยวร่วมกับ
YOLOv8, MediaPipe Pose และ rule-based decision engine

## ความสามารถหลัก

ระบบปัจจุบันตรวจจับเหตุการณ์ได้ 5 ประเภท:

1. Traveling
2. Double Dribble
3. Carrying
4. Held Ball / Jump Ball
5. Goaltending

ระบบยังมีความสามารถสนับสนุนเพิ่มเติม:

- ตรวจจับผู้เล่น ลูกบาส และห่วงด้วย YOLOv8
- ติดตามผู้เล่นด้วย Track ID
- วิเคราะห์ท่าทางผู้เล่นด้วย MediaPipe Pose
- ปรับปรุงตำแหน่งมือด้วย hand refinement สำหรับกฎที่ต้องใช้รายละเอียดบริเวณมือ
- บันทึก foul events และ replay videos ระหว่างการรัน
- แสดงผลผ่าน Streamlit UI สำหรับ Live Demo, Analytics Summary และ QA Review

## โครงสร้างไฟล์หลัก

```text
.
|-- main.py
|-- referee.py
|-- preprocessor.py
|-- utils.py
|-- app_ui.py
|-- fouls/
|   |-- carrying.py
|   |-- double_dribble.py
|   |-- goaltending.py
|   |-- jump_ball.py
|   `-- traveling.py
|-- pages/
|   |-- 1_live_demo.py
|   |-- 2_analytics.py
|   `-- 4_qa_review.py
|-- trainmodel/
|   `-- best3.pt
`-- yolov8n.pt
```

## ไฟล์โมเดลที่ต้องใช้

- `yolov8n.pt` สำหรับตรวจจับผู้เล่น
- `trainmodel/best3.pt` สำหรับตรวจจับลูกบาสและห่วง

## การติดตั้ง

แนะนำให้ใช้ Python 3.11

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## วิธีรันระบบหลัก

```bash
python main.py
```

## วิธีรันหน้า UI

```bash
streamlit run app_ui.py
```

## หมายเหตุเรื่องไฟล์ที่ไม่รวมใน GitHub

ไฟล์ต่อไปนี้ไม่รวมอยู่ใน repository สำหรับส่งงาน เนื่องจากมีขนาดใหญ่และไม่จำเป็นต่อการรันระบบหลัก:

- dataset และไฟล์ preprocessing
- replay videos
- runtime logs
- virtual environment
- model checkpoints รุ่นเก่า

ไฟล์เหล่านี้ควรเก็บแยกภายนอก GitHub หากต้องการใช้สำหรับการฝึกโมเดลหรือการทดลองเพิ่มเติม

## แนวทางการประเมินผล

ระบบรองรับการทำ QA review จาก replay events เพื่อวัดผลการตรวจจับในเชิง:

- Precision
- Recall
- F1-score
- Accuracy

โดยการประเมินที่น่าเชื่อถือควรใช้ผลตรวจทานจากมนุษย์ประกอบกับเหตุการณ์ที่ระบบตรวจจับได้จริง
