import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime

# 1. ตั้งค่าหน้า Dashboard
st.set_page_config(page_title="Train Hazards App", layout="wide")
st.title("🚂 ระบบบันทึกและแสดงผลข้อมูลเหตุอันตรายรถไฟ")

# 2. สร้างฐานข้อมูลจำลองด้วย Session State (เพื่อเก็บข้อมูลที่กรอกเข้ามาใหม่ไม่ให้หายไปเมื่อหน้ารีเฟรช)
if 'hazard_data' not in st.session_state:
    # สร้างข้อมูลเริ่มต้น (Mock Data)
    st.session_state.hazard_data = pd.DataFrame({
        "วันที่": ["2024-02-15", "2024-03-11"],
        "เหตุการณ์": ["ชนโค ระหว่างสถานีท่าพระ - ขอนแก่น", "เฉี่ยวชนกระบือ ระหว่างสถานีบ้านช่อง - หินซ้อน"],
        "ค่าใช้จ่าย": ["ด้านบำรุงทางไม่มีค่าใช้จ่าย", "ด้านบำรุงทางไม่มีค่าใช้จ่าย"],
        "Latitude": [16.3650, 14.6540],
        "Longitude": [102.8340, 101.1230]
    })

# 3. ส่วนรับข้อมูล (Sidebar Input Form)
with st.sidebar:
    st.header("📝 นำเข้าข้อมูลใหม่")
    st.write("กรอกรายละเอียดจุดเกิดเหตุที่นี่")
    
    # สร้างฟอร์มเพื่อให้หน้าเว็บไม่อัปเดตจนกว่าจะกดปุ่ม Submit
    with st.form("data_input_form"):
        input_date = st.date_input("วันที่เกิดเหตุ")
        input_event = st.text_input("รายละเอียดเหตุการณ์ (เช่น ชนโค สถานี A-B)")
        input_cost = st.selectbox("สถานะค่าใช้จ่าย", ["ด้านบำรุงทางไม่มีค่าใช้จ่าย", "มีค่าใช้จ่าย"])
        input_lat = st.number_input("Latitude (ละติจูด)", value=13.7367, format="%.5f")
        input_lon = st.number_input("Longitude (ลองจิจูด)", value=100.5231, format="%.5f")
        
        # ปุ่มยืนยันการบันทึก
        submitted = st.form_submit_button("💾 บันทึกข้อมูล")
        
        if submitted:
            # เมื่อกดปุ่ม ให้นำข้อมูลใหม่มาต่อท้ายข้อมูลเดิมใน Session State
            new_row = pd.DataFrame([{
                "วันที่": input_date.strftime("%Y-%m-%d"),
                "เหตุการณ์": input_event,
                "ค่าใช้จ่าย": input_cost,
                "Latitude": input_lat,
                "Longitude": input_lon
            }])
            st.session_state.hazard_data = pd.concat([st.session_state.hazard_data, new_row], ignore_index=True)
            st.success("บันทึกข้อมูลเรียบร้อยแล้ว!")

# ดึงข้อมูลปัจจุบันมาใช้งาน
df = st.session_state.hazard_data

# 4. ส่วนแสดงผล Dashboard และ Map (แบ่งเป็น 2 คอลัมน์)
col1, col2 = st.columns([1.5, 2])

with col1:
    st.subheader("📊 ข้อมูลสรุป (Dashboard)")
    
    # การ์ดแสดงสถิติ (Metrics)
    total_events = len(df)
    cost_free = len(df[df["ค่าใช้จ่าย"] == "ด้านบำรุงทางไม่มีค่าใช้จ่าย"])
    
    m1, m2 = st.columns(2)
    m1.metric("เหตุการณ์ทั้งหมด", f"{total_events} ครั้ง")
    m2.metric("ไม่มีค่าใช้จ่าย", f"{cost_free} ครั้ง")
    
    st.markdown("---")
    st.write("**ตารางข้อมูลล่าสุด:**")
    st.dataframe(df, use_container_width=True, height=350)

with col2:
    st.subheader("🗺️ แผนที่พิกัดจุดเกิดเหตุ")
    
    # หาค่าเฉลี่ยของพิกัดเพื่อจัดกึ่งกลางแผนที่อัตโนมัติ (หากมีข้อมูล)
    if not df.empty:
        center_lat = df["Latitude"].mean()
        center_lon = df["Longitude"].mean()
    else:
        center_lat, center_lon = 13.7367, 100.5231 # ค่าเริ่มต้น (กรุงเทพฯ)
        
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
    
    # วนลูปเพื่อปักหมุดข้อมูลทั้งหมดลงบนแผนที่
    for idx, row in df.iterrows():
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=folium.Popup(f"<b>{row['เหตุการณ์']}</b><br>วันที่: {row['วันที่']}", max_width=300),
            tooltip=row["เหตุการณ์"],
            icon=folium.Icon(color="red", icon="warning-sign")
        ).add_to(m)
    
    # แสดงผลแผนที่
    st_folium(m, width=700, height=500)