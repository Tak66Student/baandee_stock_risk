"""
mock_data.py — ข้อมูลตัวอย่าง ใช้ทดลองหน้าเว็บโดยไม่ต้องเปิดระบบหลังบ้าน

หน้าตาของแต่ละแถวต้องตรงกับสัญญาข้อมูล (ชีต Fields ใน BaanDee_API_Contract.xlsx)
รหัสและชื่อสินค้ามาจากชุดข้อมูล BaanDee ของอาจารย์ แต่ตัวเลขยอดขายและผลประเมินเป็นค่าตัวอย่าง
ห้ามนำตัวเลขในไฟล์นี้ไปนำเสนอว่าเป็นผลวิเคราะห์จริง
"""

PRODUCTS = [
    {
        "product_id": "SKU-0048", "product_name": "BaanDee Item 48",
        "current_stock": 0, "stock_as_of": "2026-07-31 06:00",
        "daily_sales": 0.25, "days_remaining": 0,
        "risk_status": "เสี่ยง", "note": "สต็อกหมดแล้ว",
    },
    {
        "product_id": "SKU-0005", "product_name": "BaanDee Item 5",
        "current_stock": 1, "stock_as_of": "2026-07-31 06:00",
        "daily_sales": 0.75, "days_remaining": 1,
        "risk_status": "เสี่ยง", "note": "พอขายราว 1 วัน",
    },
    {
        "product_id": "SKU-0025", "product_name": "BaanDee Item 25",
        "current_stock": 1, "stock_as_of": "2026-07-31 06:00",
        "daily_sales": 0.5, "days_remaining": 2,
        "risk_status": "เสี่ยง", "note": "พอขายราว 2 วัน",
    },
    {
        "product_id": "SKU-0032", "product_name": "BaanDee Item 32",
        "current_stock": 2, "stock_as_of": "2026-07-31 06:00",
        "daily_sales": 0.57, "days_remaining": 4,
        "risk_status": "เสี่ยง", "note": "พอขายราว 4 วัน",
    },
    {
        "product_id": "SKU-KT-104", "product_name": "Compact Rice Cooker",
        "current_stock": 3, "stock_as_of": "2026-07-31 11:40",
        "daily_sales": 0.5, "days_remaining": 6,
        "risk_status": "เสี่ยง",
        "note": "สต็อกเช้า 06:00 = 8 แต่ข้อมูลล่าสุด 11:40 = 3 ใช้ค่าล่าสุด",
    },
    {
        "product_id": "SKU-0060", "product_name": "BaanDee Item 60",
        "current_stock": 24, "stock_as_of": "2026-07-31 06:00",
        "daily_sales": None, "days_remaining": None,
        "risk_status": "ต้องให้คนตรวจ",
        "note": "ยอดขายมีวันที่กำกวม (เช่น 07/08/2026) จึงยังคำนวณไม่ได้",
    },
    {
        "product_id": "SKU-BD-220", "product_name": "Cooling Cotton Sheet Set",
        "current_stock": 12, "stock_as_of": "2026-07-31 11:40",
        "daily_sales": 0.04, "days_remaining": 300,
        "risk_status": "ปกติ",
        "note": "สต็อกเช้า 06:00 = 0 แต่ข้อมูลล่าสุด 11:40 = 12 ใช้ค่าล่าสุด",
    },
    {
        "product_id": "SKU-0010", "product_name": "BaanDee Item 10",
        "current_stock": 36, "stock_as_of": "2026-07-31 06:00",
        "daily_sales": 0.6, "days_remaining": 60,
        "risk_status": "ปกติ", "note": "ปกติ",
    },
]
