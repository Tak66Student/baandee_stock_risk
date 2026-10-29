"""
api_client.py — "คนเดินเรื่อง" ระหว่างหน้าเว็บกับระบบหลังบ้าน (backend/api.py)

หน้าเว็บ (app.py) ไม่คุยกับระบบหลังบ้านเอง แต่เรียกฟังก์ชันในไฟล์นี้
ทุกฟังก์ชันคืนค่าเป็น Result ที่บอกว่าเกิดอะไรขึ้น 1 ใน 4 แบบ:

    "success"     ได้ข้อมูลครบ
    "not_found"   ถามไปแล้ว แต่ไม่มีข้อมูลตัวนั้น (เช่น รหัสสินค้าผิด)
    "unavailable" ติดต่อระบบหลังบ้านไม่ได้ (ปิดอยู่ / ตอบช้าเกินไป)
    "error"       ระบบหลังบ้านตอบมา แต่ข้อมูลที่ส่งไปไม่ผ่าน หรือตอบผิดรูปแบบ

มี 2 โหมด:
    real = ส่งคำถามไปที่ระบบหลังบ้านจริง (FastAPI ในเครื่อง)
    mock = ใช้ข้อมูลตัวอย่างจาก mock_data.py ไว้ทดลองหน้าเว็บโดยไม่ต้องเปิดระบบหลังบ้าน
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

import mock_data

TIMEOUT_SECONDS = 8  # รอระบบหลังบ้านตอบได้นานสุดกี่วินาที ก่อนถือว่า "ระบบไม่พร้อม"
MOCK_STORE = Path(__file__).parent / "mock_store.json"

# ชื่อช่องรับคำถาม ต้องตรงกับที่ตั้งไว้ใน backend/api.py
ENDPOINTS = {
    "risk_list": "risk-list",
    "product": "product",
    "create_request": "restock-request",
    "list_requests": "restock-requests",
    "update_request": "restock-request/update",
}


@dataclass
class Result:
    kind: str                 # success / not_found / unavailable / error
    data: Any = None
    message: str = ""
    source: str = ""          # บอกว่าข้อมูลมาจากไหน (โชว์บนหน้าเว็บ)

    @property
    def ok(self) -> bool:
        return self.kind == "success"


class ApiClient:
    def __init__(self, mode: str = "real", base_url: str = "", simulate_down: bool = False):
        self.mode = mode
        self.base_url = base_url.rstrip("/")
        self.simulate_down = simulate_down  # ใช้กับโหมด mock: แกล้งทำเป็นระบบล่ม

    # ------------------------------------------------------------------
    # ฟังก์ชันที่หน้าเว็บเรียกใช้ (5 ช่องตามสัญญาข้อมูล)
    # ------------------------------------------------------------------
    def get_risk_list(self) -> Result:
        if self.mode == "mock":
            return self._mock(lambda: Result("success", mock_data.PRODUCTS))
        return self._call("GET", ENDPOINTS["risk_list"])

    def get_product(self, product_id: str) -> Result:
        product_id = product_id.strip().upper()
        if not product_id:
            return Result("error", message="กรุณาใส่รหัสสินค้า")
        if self.mode == "mock":
            def find():
                for p in mock_data.PRODUCTS:
                    if p["product_id"] == product_id:
                        return Result("success", p)
                return Result("not_found", message=f"ไม่พบสินค้า {product_id}")
            return self._mock(find)
        return self._call("GET", ENDPOINTS["product"], params={"product_id": product_id})

    def create_request(self, product_id: str, quantity: int, note: str = "") -> Result:
        problem = validate_quantity(quantity)
        if problem:
            return Result("error", message=problem)
        body = {"product_id": product_id, "quantity": int(quantity), "note": note.strip()}
        if self.mode == "mock":
            return self._mock(lambda: self._mock_create(body))
        return self._call("POST", ENDPOINTS["create_request"], json_body=body)

    def list_requests(self) -> Result:
        if self.mode == "mock":
            return self._mock(lambda: Result("success", self._load_store()))
        return self._call("GET", ENDPOINTS["list_requests"])

    def update_request(self, request_id, **changes) -> Result:
        if "quantity" in changes:
            problem = validate_quantity(changes["quantity"])
            if problem:
                return Result("error", message=problem)
            changes["quantity"] = int(changes["quantity"])
        body = {"request_id": request_id, **changes}
        if self.mode == "mock":
            return self._mock(lambda: self._mock_update(body))
        return self._call("POST", ENDPOINTS["update_request"], json_body=body)

    # ------------------------------------------------------------------
    # โหมดจริง: ส่งคำถามไประบบหลังบ้าน แล้วแปลคำตอบเป็น Result
    # ------------------------------------------------------------------
    def _call(self, method: str, path: str, params=None, json_body=None) -> Result:
        if not self.base_url:
            return Result("unavailable", message="ยังไม่ได้ใส่ที่อยู่ระบบหลังบ้าน")
        url = f"{self.base_url}/{path}"
        source = f"API · /{path}"
        try:
            # บรรทัดนี้คือจุดที่ "ส่ง request ข้ามระบบ" จริง ๆ
            resp = requests.request(method, url, params=params, json=json_body, timeout=TIMEOUT_SECONDS)
        except (requests.ConnectionError, requests.Timeout):
            return Result("unavailable", message="เชื่อมต่อระบบหลังบ้านไม่ได้ ข้อมูลบนหน้านี้ยังไม่ถูกอัปเดต", source=source)

        if resp.status_code == 404:
            return Result("not_found", message=_error_text(resp) or "ไม่พบข้อมูลที่ขอ", source=source)
        if resp.status_code >= 500:
            return Result("unavailable", message=f"ระบบหลังบ้านขัดข้อง (รหัส {resp.status_code})", source=source)
        if resp.status_code >= 400:
            return Result("error", message=_error_text(resp) or f"ข้อมูลที่ส่งไปไม่ผ่าน (รหัส {resp.status_code})", source=source)
        try:
            data = resp.json()
        except ValueError:
            return Result("error", message="ระบบหลังบ้านตอบกลับมาในรูปแบบที่อ่านไม่ได้", source=source)
        return Result("success", data, source=source)

    # ------------------------------------------------------------------
    # โหมดข้อมูลตัวอย่าง
    # ------------------------------------------------------------------
    def _mock(self, fn) -> Result:
        if self.simulate_down:
            return Result("unavailable", message="(จำลอง) เชื่อมต่อระบบหลังบ้านไม่ได้", source="mock")
        result = fn()
        result.source = "ข้อมูลตัวอย่าง (mock)"
        return result

    def _load_store(self) -> list[dict]:
        if not MOCK_STORE.exists():
            return []
        return json.loads(MOCK_STORE.read_text(encoding="utf-8"))

    def _save_store(self, rows: list[dict]) -> None:
        MOCK_STORE.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    def _mock_create(self, body: dict) -> Result:
        if not any(p["product_id"] == body["product_id"] for p in mock_data.PRODUCTS):
            return Result("not_found", message=f"ไม่พบสินค้า {body['product_id']}")
        rows = self._load_store()
        now = _now()
        row = {"request_id": len(rows) + 1, "product_id": body["product_id"], "quantity": body["quantity"],
               "status": "รออนุมัติ", "note": body["note"], "created_at": now, "updated_at": now}
        rows.append(row)
        self._save_store(rows)
        return Result("success", row)

    def _mock_update(self, body: dict) -> Result:
        rows = self._load_store()
        for row in rows:
            if row["request_id"] == body["request_id"]:
                for key in ("quantity", "status", "note"):
                    if key in body:
                        row[key] = body[key]
                row["updated_at"] = _now()
                self._save_store(rows)
                return Result("success", row)
        return Result("not_found", message=f"ไม่พบใบสั่งเติม {body['request_id']}")


# ----------------------------------------------------------------------
# ตัวช่วย
# ----------------------------------------------------------------------
def validate_quantity(quantity) -> str:
    """คืนข้อความปัญหา ถ้าจำนวนไม่ถูกต้อง; คืน "" ถ้าผ่าน"""
    try:
        q = float(quantity)
    except (TypeError, ValueError):
        return "จำนวนต้องเป็นตัวเลข"
    if not q.is_integer():
        return "จำนวนต้องเป็นจำนวนเต็ม"
    if q <= 0:
        return "จำนวนที่สั่งต้องมากกว่า 0"
    return ""


def classify_status(risk_status: str) -> str:
    """แปลงข้อความสถานะเป็น 3 กลุ่ม: review / risk / normal"""
    text = str(risk_status or "")
    if "ตรวจ" in text:
        return "review"
    if "เสี่ยง" in text:
        return "risk"
    return "normal"


def _error_text(resp) -> str:
    try:
        body = resp.json()
        return body.get("message") or body.get("detail") or ""
    except Exception:
        return ""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")
