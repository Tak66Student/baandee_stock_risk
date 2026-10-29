"""
app.py — หน้าเว็บของระบบเตือนสินค้าเสี่ยงขาดสต็อก (BaanDee Living)

วิธีรัน (จากโฟลเดอร์หลักของโปรเจกต์):   streamlit run frontend/app.py
หน้าเว็บนี้ไม่คำนวณความเสี่ยงเอง แค่ถามระบบหลังบ้าน (backend/api.py) ผ่าน api_client.py แล้วแสดงผล
"""

import os

import pandas as pd
import streamlit as st

from api_client import ApiClient, Result, classify_status

st.set_page_config(page_title="BaanDee · สินค้าเสี่ยงขาดสต็อก", page_icon="📦", layout="wide")

STATUS_LABEL = {"risk": "🔴 เสี่ยงขาด", "review": "🟡 ต้องให้คนตรวจ", "normal": "🟢 ปกติ"}
REQUEST_STATUSES = ["รออนุมัติ", "อนุมัติแล้ว", "ยกเลิก"]

# ----------------------------------------------------------------------
# แถบข้าง: เลือกโหมดข้อมูล
# ----------------------------------------------------------------------
with st.sidebar:
    st.header("ตั้งค่าการเชื่อมต่อ")
    mode_label = st.radio(
        "แหล่งข้อมูล",
        ["ระบบจริง (API ในเครื่อง)", "ข้อมูลตัวอย่าง (mock)"],
        help="ข้อมูลตัวอย่างใช้ทดลองหน้าเว็บได้โดยไม่ต้องเปิดระบบหลังบ้าน",
    )
    mode = "mock" if mode_label.startswith("ข้อมูลตัวอย่าง") else "real"

    base_url = st.text_input(
        "ที่อยู่ระบบหลังบ้าน (API)",
        value=os.getenv("BACKEND_URL", "http://127.0.0.1:8000"),
        disabled=(mode == "mock"),
    )
    simulate_down = st.checkbox(
        "จำลองว่าระบบล่ม",
        disabled=(mode == "real"),
        help="ใช้กับข้อมูลตัวอย่าง ในโหมดจริงให้ปิดหน้าต่าง API แทน",
    )

client = ApiClient(mode=mode, base_url=base_url, simulate_down=simulate_down)


def show_problem(result: Result) -> None:
    """แสดงข้อความตามชนิดปัญหา แทนที่จะปล่อยให้หน้าเว็บพัง"""
    if result.kind == "unavailable":
        st.error(f"⚠️ {result.message} — ลองใหม่อีกครั้ง หรือตรวจว่าระบบหลังบ้านเปิดอยู่")
    elif result.kind == "not_found":
        st.warning(f"🔍 {result.message}")
    elif result.kind == "error":
        st.error(f"✋ {result.message}")


def source_line(result: Result, as_of: str | None = None) -> None:
    text = f"ที่มาของข้อมูล: {result.source}"
    if as_of:
        text += f"  |  เวลาของข้อมูลสต็อก: {as_of}"
    st.caption(text)


# ----------------------------------------------------------------------
# หัวหน้าเว็บ
# ----------------------------------------------------------------------
st.title("สินค้าที่เสี่ยงขาดสต็อก")
st.write("ดูว่าสินค้าตัวไหนใกล้หมด ตรวจหลักฐาน แล้วสร้างใบขอสั่งเติมให้หัวหน้าอนุมัติ ระบบไม่สั่งซื้อเอง")
if mode == "mock":
    st.info("กำลังใช้ข้อมูลตัวอย่าง ตัวเลขบนหน้านี้ยังไม่ใช่ผลวิเคราะห์จริง")

tab_list, tab_detail, tab_requests = st.tabs(["รายการความเสี่ยง", "ดูสินค้ารายตัว", "ใบขอสั่งเติม"])

# ----------------------------------------------------------------------
# แท็บ 1: รายการความเสี่ยง
# ----------------------------------------------------------------------
with tab_list:
    risk = client.get_risk_list()
    if not risk.ok:
        show_problem(risk)
    elif not risk.data:
        st.write("ยังไม่มีข้อมูลสินค้าจากระบบหลังบ้าน")
    else:
        df = pd.DataFrame(risk.data)
        df["กลุ่ม"] = df["risk_status"].map(classify_status)

        c1, c2, c3 = st.columns(3)
        c1.metric("เสี่ยงขาด", int((df["กลุ่ม"] == "risk").sum()))
        c2.metric("ต้องให้คนตรวจ", int((df["กลุ่ม"] == "review").sum()))
        c3.metric("ปกติ", int((df["กลุ่ม"] == "normal").sum()))

        order = {"risk": 0, "review": 1, "normal": 2}
        df = df.sort_values(by=["กลุ่ม", "days_remaining"], key=lambda s: s.map(order) if s.name == "กลุ่ม" else s,
                            na_position="last")
        show = pd.DataFrame({
            "สถานะ": df["กลุ่ม"].map(STATUS_LABEL),
            "รหัสสินค้า": df["product_id"],
            "ชื่อสินค้า": df["product_name"],
            "สต็อกคงเหลือ": df["current_stock"],
            "เวลาของข้อมูลสต็อก": df["stock_as_of"],
            "ขายต่อวัน": df["daily_sales"],
            "พอขายอีก (วัน)": df["days_remaining"],
            "หมายเหตุ": df["note"],
        })
        st.dataframe(show, hide_index=True, width="stretch")
        source_line(risk)

# ----------------------------------------------------------------------
# แท็บ 2: ดูสินค้ารายตัว
# ----------------------------------------------------------------------
with tab_detail:
    pid = st.text_input("รหัสสินค้า", value="SKU-0060", key="detail_pid", help="ลองพิมพ์รหัสที่ไม่มีอยู่จริง เพื่อดูกรณีไม่พบ")
    if st.button("ดูหลักฐาน", type="primary", key="detail_btn"):
        st.session_state["detail"] = client.get_product(pid)

    detail: Result | None = st.session_state.get("detail")
    if detail is not None:
        if not detail.ok:
            show_problem(detail)
        else:
            p = detail.data
            group = classify_status(p.get("risk_status"))
            st.subheader(f"{p['product_id']} · {p.get('product_name', '')}")
            st.markdown(f"**ผลประเมิน:** {STATUS_LABEL[group]}")

            verified, uncertain = st.columns(2)
            with verified:
                st.markdown("##### ✅ ข้อมูลที่ยืนยันได้")
                facts = {
                    "สต็อกคงเหลือ": p.get("current_stock"),
                    "เวลาของข้อมูลสต็อก": p.get("stock_as_of"),
                    "ขายเฉลี่ยต่อวัน": p.get("daily_sales"),
                    "พอขายอีก (วัน)": p.get("days_remaining"),
                }
                for label, value in facts.items():
                    if value is not None:
                        st.write(f"{label}: **{value}**")

            with uncertain:
                st.markdown("##### ❓ ยังไม่แน่นอน / ต้องให้คนตรวจ")
                doubts = [f"ยังไม่มีข้อมูล: {label}" for label, value in facts.items() if value is None]
                if group == "review" and p.get("note"):
                    doubts.append(p["note"])
                if doubts:
                    for d in doubts:
                        st.write(f"• {d}")
                    st.warning("ระบบยังไม่ประเมินสินค้านี้ ส่งให้เจ้าหน้าที่ตรวจก่อนตัดสินใจสั่งเติม")
                else:
                    st.write("ไม่มี")

            if group != "review" and p.get("note"):
                st.caption(f"หมายเหตุ: {p['note']}")
            source_line(detail)

# ----------------------------------------------------------------------
# แท็บ 3: ใบขอสั่งเติม (สร้าง / ดู / แก้ไข)
# ----------------------------------------------------------------------
with tab_requests:
    if "flash" in st.session_state:
        st.success(st.session_state.pop("flash"))
    st.subheader("สร้างใบขอสั่งเติม")
    risk_for_form = client.get_risk_list()
    with st.form("create_form", clear_on_submit=True):
        if risk_for_form.ok and risk_for_form.data:
            options = [p["product_id"] for p in risk_for_form.data]
            new_pid = st.selectbox("สินค้า", options)
        else:
            new_pid = st.text_input("รหัสสินค้า")
        new_qty = st.number_input("จำนวนที่จะสั่ง (ชิ้น)", min_value=0, step=1, value=10, key="new_qty")
        new_note = st.text_input("หมายเหตุ (ไม่บังคับ)")
        submitted = st.form_submit_button("สร้างใบขอสั่งเติม", type="primary", key="create_btn")
    if submitted:
        created = client.create_request(new_pid, new_qty, new_note)
        if created.ok:
            st.success(f"สร้างใบขอสั่งเติม {created.data['request_id']} แล้ว สถานะ: รออนุมัติ")
        else:
            show_problem(created)

    st.divider()
    st.subheader("ใบขอสั่งเติมทั้งหมด")
    reqs = client.list_requests()
    if not reqs.ok:
        show_problem(reqs)
    elif not reqs.data:
        st.write("ยังไม่มีใบขอสั่งเติม สร้างใบแรกได้จากฟอร์มด้านบน")
    else:
        rdf = pd.DataFrame(reqs.data)
        st.dataframe(
            rdf.rename(columns={
                "request_id": "เลขที่ใบ", "product_id": "รหัสสินค้า", "quantity": "จำนวน",
                "status": "สถานะ", "note": "หมายเหตุ", "created_at": "สร้างเมื่อ", "updated_at": "แก้ไขล่าสุด",
            }),
            hide_index=True, width="stretch",
        )
        source_line(reqs)

        st.subheader("แก้ไขใบขอสั่งเติม")
        rid = st.selectbox("เลือกเลขที่ใบ", rdf["request_id"].tolist())
        current = rdf[rdf["request_id"] == rid].iloc[0]
        with st.form("edit_form"):
            edit_qty = st.number_input("จำนวน (ชิ้น)", min_value=0, step=1, value=int(current["quantity"]), key=f"edit_qty_{rid}")
            status_now = current["status"] if current["status"] in REQUEST_STATUSES else REQUEST_STATUSES[0]
            edit_status = st.selectbox("สถานะ", REQUEST_STATUSES, index=REQUEST_STATUSES.index(status_now),
                                       help="เลือก 'ยกเลิก' แทนการลบ ใบที่ยกเลิกยังเก็บไว้ดูย้อนหลังได้")
            edit_note = st.text_input("หมายเหตุ", value=str(current.get("note") or ""))
            saved = st.form_submit_button("บันทึกการแก้ไข", key="edit_btn")
        if saved:
            updated = client.update_request(rid, quantity=edit_qty, status=edit_status, note=edit_note)
            if updated.ok:
                st.session_state["flash"] = f"บันทึกการแก้ไข {rid} แล้ว"
                st.rerun()
            else:
                show_problem(updated)
