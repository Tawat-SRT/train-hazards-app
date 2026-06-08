import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import datetime

# 1. ตั้งค่าหน้า Dashboard
st.set_page_config(page_title="Train Hazards App", layout="wide")
st.title("🚂 ระบบบันทึกและแสดงผลข้อมูลเหตุอันตรายรถไฟชนสัตว์")

# 2. สร้างฐานข้อมูลจำลอง (ปรับปรุงคอลัมน์ใหม่ตามที่ระบุ)
if 'hazard_data' not in st.session_state:
    st.session_state.hazard_data = pd.DataFrame({
        "ชื่อเหตุอันตราย": ["ชนโค ระหว่างสถานีท่าพระ - ขอนแก่น", "เฉี่ยวชนกระบือ ระหว่างสถานีบ้านช่อง - หินซ้อน"],
        "ที่ กม.": ["345+100", "150+200"],
        "วัน/เดือน/ปี": ["2024-02-15", "2024-03-11"],
        "เวลา": ["10:30", "14:45"],
        "ค่าใช้จ่าย": ["ด้านบำรุงทางไม่มีค่าใช้จ่าย", "มีค่าใช้จ่าย 5,000 บาท"],
        "Latitude": [16.3650, 14.6540],
        "Longitude": [102.8340, 101.1230],
        "ผลกระทบ (นาที)": [15, 30],
        "หมายเหตุ": ["-", "จุดเกิดเหตุซ้ำ ± 3 Km"]
    })

# 3. ส่วนแถบด้านข้าง (Sidebar) สำหรับนำเข้าและกรอกข้อมูล
with st.sidebar:
    st.header("📂 นำเข้าข้อมูลจากไฟล์")
    st.caption("รองรับ .csv และ .xlsx (หัวคอลัมน์ต้องตรงกับฟอร์มด้านล่าง)")
    uploaded_file = st.file_uploader("อัปโหลดไฟล์ที่นี่", type=["csv", "xlsx"])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_uploaded = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith('.xlsx'):
                df_uploaded = pd.read_excel(uploaded_file)
            
            st.success("อ่านไฟล์สำเร็จ!")
            if st.button("➕ ยืนยันเพิ่มข้อมูลจากไฟล์"):
                st.session_state.hazard_data = pd.concat([st.session_state.hazard_data, df_uploaded], ignore_index=True)
                st.rerun()
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")

    st.markdown("---")
    st.header("📝 ฟอร์มบันทึกข้อมูลใหม่")
    with st.form("data_input_form"):
        input_name = st.text_input("ชื่อเหตุอันตราย", placeholder="เช่น ชนโค สถานี A-B")
        input_km = st.text_input("ที่ กม.", placeholder="เช่น 123+456")
        
        c1, c2 = st.columns(2)
        with c1:
            input_date = st.date_input("วัน/เดือน/ปี")
        with c2:
            input_time = st.time_input("เวลา ที่เกิดเหตุ", value=datetime.time(12, 00))
            
        input_cost = st.text_input("ค่าใช้จ่าย", value="ด้านบำรุงทางไม่มีค่าใช้จ่าย")
        
        c3, c4 = st.columns(2)
        with c3:
            input_lat = st.number_input("Latitude", value=13.7367, format="%.5f")
        with c4:
            input_lon = st.number_input("Longitude", value=100.5231, format="%.5f")
            
        input_impact = st.number_input("ผลกระทบ (ความล่าช้า/นาที)", min_value=0, step=1, value=0)
        input_remark = st.text_input("หมายเหตุ", placeholder="เช่น จุดเกิดเหตุซ้ำ ± 3 Km")
        
        if st.form_submit_button("💾 บันทึกข้อมูล"):
            new_row = pd.DataFrame([{
                "ชื่อเหตุอันตราย": input_name,
                "ที่ กม.": input_km,
                "วัน/เดือน/ปี": input_date.strftime("%Y-%m-%d"),
                "เวลา": input_time.strftime("%H:%M"),
                "ค่าใช้จ่าย": input_cost,
                "Latitude": input_lat,
                "Longitude": input_lon,
                "ผลกระทบ (นาที)": input_impact,
                "หมายเหตุ": input_remark
            }])
            st.session_state.hazard_data = pd.concat([st.session_state.hazard_data, new_row], ignore_index=True)
            st.success("บันทึกข้อมูลเรียบร้อยแล้ว!")
            st.rerun()

# 4. ส่วนแสดงผลหลัก (Dashboard & Map)
df = st.session_state.hazard_data

col1, col2 = st.columns([1.5, 2])

with col1:
    st.subheader("📊 ข้อมูลสรุป (Dashboard)")
    
    # คำนวณสถิติ
    total_events = len(df)
    total_impact = df["ผลกระทบ (นาที)"].sum() if not df.empty else 0
    repeated_spots = len(df[df["หมายเหตุ"].str.contains("ซ้ำ", na=False)])
    
    m1, m2, m3 = st.columns(3)
    m1.metric("เหตุการณ์ทั้งหมด", f"{total_events} ครั้ง")
    m2.metric("ผลกระทบรวม", f"{total_impact} นาที")
    m3.metric("เกิดเหตุซ้ำ", f"{repeated_spots} จุด")
    
    st.write("**ตารางข้อมูลล่าสุด:**")
    st.dataframe(df, use_container_width=True, height=450)

with col2:
    st.subheader("🗺️ แผนที่พิกัดจุดเกิดเหตุ")
    if not df.empty and pd.notna(df["Latitude"].iloc[0]):
        center_lat, center_lon = df["Latitude"].mean(), df["Longitude"].mean()
    else:
        center_lat, center_lon = 13.7367, 100.5231
        
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
    
    for idx, row in df.iterrows():
        if pd.notna(row['Latitude']) and pd.notna(row['Longitude']):
            # สร้างข้อความแสดงใน Popup เมื่อคลิกที่หมุด
            popup_html = f"""
            <div style="font-family: Tahoma; font-size: 12px; min-width: 200px;">
                <b>🚨 {row['ชื่อเหตุอันตราย']}</b><br>
                <hr style="margin: 5px 0;">
                <b>ที่ กม.:</b> {row['ที่ กม.']}<br>
                <b>วัน-เวลา:</b> {row['วัน/เดือน/ปี']} เวลา {row['เวลา']} น.<br>
                <b>ผลกระทบ:</b> ล่าช้า {row['ผลกระทบ (นาที)']} นาที<br>
                <b>ค่าใช้จ่าย:</b> {row['ค่าใช้จ่าย']}<br>
                <b>หมายเหตุ:</b> <span style="color:red;">{row['หมายเหตุ']}</span>
            </div>
            """
            
            # กำหนดสีหมุด ถ้าเป็นจุดเกิดเหตุซ้ำให้เป็นสีดำ-แดง (หรือส้ม)
            is_repeated = "ซ้ำ" in str(row['หมายเหตุ'])
            marker_color = "orange" if is_repeated else "red"
            icon_type = "info-sign" if is_repeated else "warning-sign"

            folium.Marker(
                location=[row["Latitude"], row["Longitude"]],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=str(row["ชื่อเหตุอันตราย"]),
                icon=folium.Icon(color=marker_color, icon=icon_type)
            ).add_to(m)
    
    st_folium(m, width=700, height=550)