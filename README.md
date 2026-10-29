# BaanDee Living · ระบบเตือนสินค้าเสี่ยงขาดสต็อก

(ร่าง — ส่วนอธิบายปัญหา ผู้ใช้ แผนภาพข้อมูล และบทบาทสมาชิก จะเพิ่มทีหลัง)

## โครงสร้าง
| โฟลเดอร์ | หน้าที่ |
|---|---|
| `data/raw/` | ข้อมูลดิบจากอาจารย์ (ไม่แก้ไข) |
| `data/generated/` | ข้อมูลผู้ขายที่ทีมสร้าง (สมมติฐาน) |
| `data/cleaned/` | ผลลัพธ์จาก notebook: `stock_risk.csv`, บันทึกการแก้ข้อมูล, รายการที่กักไว้ |
| `notebooks/` | ทำความสะอาดข้อมูลและคำนวณความเสี่ยง |
| `backend/api.py` | ระบบหลังบ้าน (FastAPI) ส่งข้อมูลให้หน้าเว็บ และเก็บใบขอสั่งเติมใน SQLite |
| `frontend/` | หน้าเว็บ (Streamlit) |
| `tests/` | test 10 กรณี |

## ติดตั้ง (Windows, ทำครั้งเดียว)
```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

## รัน (เปิด PowerShell 2 หน้าต่าง ในโฟลเดอร์นี้)
หน้าต่างที่ 1 — ระบบหลังบ้าน:
```
.venv\Scripts\python -m uvicorn backend.api:app --port 8000
```
หน้าต่างที่ 2 — หน้าเว็บ:
```
.venv\Scripts\python -m streamlit run frontend/app.py
```
เปิด http://localhost:8501

## รัน test
```
.venv\Scripts\python -m pytest -v
```
