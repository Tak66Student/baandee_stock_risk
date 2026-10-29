"""
test ของระบบ (รัน: pytest -v จากโฟลเดอร์หลักของโปรเจกต์)
แต่ละ test เขียน input / ผลที่ควรได้ ไว้ในคอมเมนต์ ผลจริงดูได้จากผลรัน pytest
"""
import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "frontend"))

from backend import api            # noqa: E402
from api_client import ApiClient   # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DB_PATH", tmp_path / "test.db")   # ฐานข้อมูลชั่วคราว ไม่ทับของจริง
    return TestClient(api.app)


# ---------------- ข้อมูล ----------------
def test_T01_ambiguous_date_is_quarantined_not_guessed():
    # input: ออร์เดอร์ ORD-260730-2201 วันที่ 07/08/2026   expected: อยู่ในไฟล์กักไว้ ไม่ถูกเดา
    q = pd.read_csv(ROOT / "data/cleaned/quarantine_order_dates.csv")
    assert "ORD-260730-2201" in set(q.order_id)


def test_T02_latest_stock_is_used():
    # input: SKU-BD-220 สต็อก 06:00 = 0, 11:40 = 12   expected: ใช้ 12 พร้อมเวลา 11:40
    r = pd.read_csv(ROOT / "data/cleaned/stock_risk.csv").set_index("product_id").loc["SKU-BD-220"]
    assert r.current_stock == 12 and "11:40" in r.stock_as_of


# ---------------- ระบบหลังบ้าน (API) ----------------
def test_T03_risk_list_counts(client):
    # input: GET /risk-list   expected: 82 สินค้า แบ่งเป็น เสี่ยง 7 / ต้องให้คนตรวจ 5 / ปกติ 70
    rows = client.get("/risk-list").json()
    counts = pd.Series([r["risk_status"] for r in rows]).value_counts().to_dict()
    assert len(rows) == 82 and counts == {"ปกติ": 70, "เสี่ยง": 7, "ต้องให้คนตรวจ": 5}


def test_T04_product_not_found(client):
    # input: GET /product?product_id=SKU-9999   expected: 404 ไม่เดาข้อมูลขึ้นมาเอง
    assert client.get("/product", params={"product_id": "SKU-9999"}).status_code == 404


def test_T05_zero_quantity_rejected_by_backend(client):
    # input: สร้างใบสั่งเติม จำนวน 0   expected: 400 และไม่มีใบถูกบันทึก
    resp = client.post("/restock-request", json={"product_id": "SKU-0048", "quantity": 0})
    assert resp.status_code == 400 and client.get("/restock-requests").json() == []


def test_T06_unknown_product_rejected(client):
    # input: สร้างใบสั่งเติมให้ SKU-9999   expected: 404
    resp = client.post("/restock-request", json={"product_id": "SKU-9999", "quantity": 5})
    assert resp.status_code == 404


def test_T07_create_edit_persists(client):
    # input: สร้างใบ 8 ชิ้น แล้วแก้เป็น 16 และอนุมัติ   expected: เปิดดูใหม่ยังเห็น 16 / อนุมัติแล้ว
    rid = client.post("/restock-request", json={"product_id": "SKU-0048", "quantity": 8}).json()["request_id"]
    client.post("/restock-request/update", json={"request_id": rid, "quantity": 16, "status": "อนุมัติแล้ว"})
    row = TestClient(api.app).get("/restock-requests").json()[0]   # client ใหม่ = เหมือนเปิดโปรแกรมใหม่
    assert row["quantity"] == 16 and row["status"] == "อนุมัติแล้ว"


def test_T08_update_missing_request(client):
    # input: แก้ใบเลขที่ 999 ที่ไม่มีอยู่   expected: 404
    resp = client.post("/restock-request/update", json={"request_id": 999, "quantity": 5})
    assert resp.status_code == 404


# ---------------- หน้าเว็บ ----------------
def test_T09_backend_down_is_reported():
    # input: ที่อยู่ระบบหลังบ้านที่ไม่มีใครเปิด   expected: unavailable (หน้าเว็บไม่พัง)
    assert ApiClient(mode="real", base_url="http://127.0.0.1:9").get_risk_list().kind == "unavailable"


def test_T10_frontend_blocks_bad_quantity():
    # input: กรอกจำนวน -5 ที่หน้าเว็บ   expected: error ทันที ไม่ส่งไประบบหลังบ้าน
    assert ApiClient(mode="real", base_url="http://127.0.0.1:9").create_request("SKU-0048", -5).kind == "error"
