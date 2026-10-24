# Crowd Runner (Python midterm)

เกมคนวิ่งผ่านประตู `+ - × ÷` เลียนแบบเกมโฆษณา ทำด้วย Pygame

## รันเกม

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## ปุ่ม

| ปุ่ม | ทำอะไร |
|---|---|
| ขึ้น/ลง (W/S) + Space หรือ คลิก | เลือกด่านแล้วเริ่มเล่น |
| A, D หรือ ลูกศรซ้าย/ขวา | เลื่อนกลุ่มคน |
| R | เล่นด่านเดิมอีกครั้ง (หน้าจบ) |
| M | กลับเมนูเลือกด่าน (หน้าจบ) |
| U | ปลดล็อกทุกด่านชั่วคราว ไว้ทดสอบ/โชว์ (ในเมนู กดอีกครั้งเพื่อปิด, ไม่บันทึก) |

## ทดสอบ

```bash
python -m pytest        # หรือ python tests/test_logic.py
```

## ด่านและคะแนน

- ด่านอยู่ใน `levels/level1.json` ถึง `level5.json` เพิ่มไฟล์ใหม่แล้วจะขึ้นในเมนูเอง (เรียงตามเลข)
- ดาว: ชนะ = 1 ดาว, เหลือคน >= 25% ของจำนวนสูงสุดที่เป็นไปได้ = 2 ดาว, >= 50% = 3 ดาว
- high score บันทึกใน `highscores.json` (แต่ละเครื่องแยกกัน ไม่เข้า git)
- กติกาด่าน (test ตรวจให้): สิ่งกีดขวางกว้างไม่เกิน 150 (ครึ่งถนน) และเลือกประตูดีที่สุดแล้วต้องชนะได้

## โครงสร้าง

| ไฟล์ | หน้าที่ | เจ้าของ |
|---|---|---|
| `main.py` | game loop, state machine | A |
| `camera.py` | แปลง (x, z) -> จอ | A |
| `config.py` | ค่าคงที่ทั้งหมด | ทุกคน (แก้ระวัง) |
| `crowd.py` `gate.py` `obstacle.py` `enemy.py` | gameplay | B |
| `level.py` `levels/*.json` `ui.py` `scores.py` `tests/` `assets/` | ด่าน, UI, ดาว/high score, ทดสอบ | C |

คู่มือทำงานร่วมกันอยู่ใน `GUIDE_TH.md`
"# Crowd_runner_fish.ver" 
"# Crowd_runner_fish.ver" 
"# Crowd_runner_fish.ver" 
"# Hello" 
"# Hello" 
"# Hello" 
"# Hello" 
"# 2-bosses" 
"# 2-bosses" 
"# 2-bosses" 
