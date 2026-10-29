"""
backend/api.py — ระบบหลังบ้าน (API) ที่หน้าเว็บส่งคำถามมาหา

หน้าที่:
1. อ่านผลความเสี่ยงจาก data/cleaned/stock_risk.csv (ผลจาก notebook) แล้วส่งให้หน้าเว็บ
2. เก็บใบขอสั่งเติมในฐานข้อมูล SQLite (data/app.db) ปิดโปรแกรมแล้วข้อมูลไม่หาย
3. ตรวจข้อมูลที่ส่งเข้ามาอีกชั้น (จำนวนต้องมากกว่า 0, รหัสสินค้าต้องมีจริง)

วิธีรัน (จากโฟลเดอร์หลักของโปรเจกต์):
    uvicorn backend.api:app --port 8000

ช่องรับคำถาม 5 ช่อง (ตรงกับสัญญาข้อมูล):
    GET  /risk-list                รายการสินค้าทั้งหมดพร้อมความเสี่ยง
    GET  /product?product_id=...   สินค้า 1 ตัว (ไม่พบ → 404)
    POST /restock-request          สร้างใบขอสั่งเติม
    GET  /restock-requests         ใบขอสั่งเติมทั้งหมด
    POST /restock-request/update   แก้ใบขอสั่งเติม (ไม่พบ → 404)
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
RISK_CSV = Path(os.getenv("RISK_CSV", ROOT / "data/cleaned/stock_risk.csv"))
DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data/app.db"))
STATUSES = ("รออนุมัติ", "อนุมัติแล้ว", "ยกเลิก")

app = FastAPI(title="BaanDee Stock Risk API")


# ----------------------------------------------------------------------
# ข้อมูลความเสี่ยง (อ่านอย่างเดียว)
# ----------------------------------------------------------------------
def load_risk() -> list[dict]:
    df = pd.read_csv(RISK_CSV)
    df = df.astype(object).where(df.notna(), None)  # ช่องว่างใน CSV → null
    return df.to_dict(orient="records")


@app.get("/risk-list")
def risk_list():
    return load_risk()


@app.get("/product")
def product(product_id: str):
    for row in load_risk():
        if row["product_id"] == product_id.strip().upper():
            return row
    raise HTTPException(404, detail="ไม่พบสินค้านี้")


# ----------------------------------------------------------------------
# ใบขอสั่งเติม (สร้าง / ดู / แก้ไข)
# ----------------------------------------------------------------------
def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS restock_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            quantity   INTEGER NOT NULL CHECK (quantity > 0),
            status     TEXT NOT NULL,
            note       TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
    return conn


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def check_quantity(quantity: int) -> None:
    if quantity <= 0:
        raise HTTPException(400, detail="จำนวนที่สั่งต้องมากกว่า 0")


class NewRequest(BaseModel):
    product_id: str
    quantity: int
    note: str = ""


class UpdateRequest(BaseModel):
    request_id: int
    quantity: int | None = None
    status: str | None = None
    note: str | None = None


@app.post("/restock-request")
def create_request(body: NewRequest):
    check_quantity(body.quantity)
    if not any(r["product_id"] == body.product_id for r in load_risk()):
        raise HTTPException(404, detail=f"ไม่พบสินค้า {body.product_id}")
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO restock_requests (product_id, quantity, status, note, created_at, updated_at) "
            "VALUES (?, ?, 'รออนุมัติ', ?, ?, ?)",
            (body.product_id, body.quantity, body.note.strip(), now(), now()),
        )
        row = conn.execute("SELECT * FROM restock_requests WHERE request_id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.get("/restock-requests")
def list_requests():
    with db() as conn:
        rows = conn.execute("SELECT * FROM restock_requests ORDER BY request_id").fetchall()
    return [dict(r) for r in rows]


@app.post("/restock-request/update")
def update_request(body: UpdateRequest):
    if body.quantity is not None:
        check_quantity(body.quantity)
    if body.status is not None and body.status not in STATUSES:
        raise HTTPException(400, detail=f"สถานะต้องเป็น {', '.join(STATUSES)}")
    with db() as conn:
        row = conn.execute("SELECT * FROM restock_requests WHERE request_id = ?", (body.request_id,)).fetchone()
        if row is None:
            raise HTTPException(404, detail="ไม่พบใบสั่งเติมนี้")
        new = dict(row)
        for key in ("quantity", "status", "note"):
            value = getattr(body, key)
            if value is not None:
                new[key] = value
        new["updated_at"] = now()
        conn.execute(
            "UPDATE restock_requests SET quantity = ?, status = ?, note = ?, updated_at = ? WHERE request_id = ?",
            (new["quantity"], new["status"], new["note"], new["updated_at"], body.request_id),
        )
    return new
