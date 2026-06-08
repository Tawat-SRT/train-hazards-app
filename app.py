import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. ตั้งค่าหน้า Dashboard
st.set_page_config(page_title="Train Hazards App", layout="wide")
st.title("🚂 ระบบบันทึกและแสดงผลข้อมูลเหตุอันตรายรถไฟ")

# 2. สร้างฐานข้อมูลจำลองด้วย Session State
if 'hazard_data' not in st.session_state:
    st.session_state.hazard_data = pd.DataFrame({
        "วันที่": ["2024-02-15"],
        "เหตุการณ์": ["ชนโค ระหว่างสถานีท่าพระ - ขอนแก่น"],
        "ค่าใช้จ่าย": ["ด้านบำรุงทางไม่มีค่าใช้จ่าย"],
        "Latitude": [16.3650],
        "Longitude": [102.8340]
    })

# 3. ส่วนแถบด้านข้าง (Sidebar) สำหรับนำเข้าข้อมูล
with st.sidebar:
    st.header("📂 นำเข้าข้อมูลจากไฟล์")
    st.write("รองรับไฟล์ .csv และ .xlsx")
    
    # ฟังก์ชันอัปโหลดไฟล์
    uploaded_file = st.file_uploader("ลากไฟล์มาวางที่นี่", type=["csv", "xlsx"])
    
    if uploaded_file is not None:
        try:
            # ตรวจสอบนามสกุลไฟล์
            if uploaded_file.name.endswith('.csv'):
                df_uploaded = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith('.xlsx'):
                df_uploaded = pd.read_excel(uploaded_file)
            
            st.success("อ่านไฟล์สำเร็จ! ตรวจสอบข้อมูลด้านล่าง")
            st.dataframe(df_uploaded.head(3)) # แสดงตัวอย่าง 3 บรรทัดแรก
            
            # ปุ่มกดยืนยันเพื่อรวมข้อมูลเข้าสู่ระบบ
            if st.button("➕ เพิ่มข้อมูลเข้าระบบ"):
                st.session_state.hazard_data = pd.concat([st.session_state.hazard_data, df_uploaded], ignore_index=True)
                st.success("เพิ่มข้อมูลเรียบร้อยแล้ว! หน้าจอจะอัปเดตอัตโนมัติ")
                st.rerun() # รีเฟรชหน้าจอ
                
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")

    st.markdown("---")
    st.header("📝 หรือกรอกข้อมูลใหม่ด้วยตัวเอง")
    with st.form("data_input_form"):
        input_date = st.date_input("วันที่เกิดเหตุ")
        input_event = st.text_input("รายละเอียดเหตุการณ์")
        input_cost = st.selectbox("สถานะค่าใช้จ่าย", ["ด้านบำรุงทางไม่มีค่าใช้จ่าย", "มีค่าใช้จ่าย"])
        input_lat = st.number_input("Latitude", value=13.7367, format="%.5f")
        input_lon = st.number_input("Longitude", value=100.5231, format="%.5f")
        
        if st.form_submit_button("💾 บันทึกข้อมูล"):
            new_row = pd.DataFrame([{
                "วันที่": input_date.strftime("%Y-%m-%d"),
                "เหตุการณ์": input_event, "ค่าใช้จ่าย": input_cost,
                "Latitude": input_lat, "Longitude": input_lon
            }])
            st.session_state.hazard_data = pd.concat([st.session_state.hazard_data, new_row], ignore_index=True)
            st.success("บันทึกข้อมูลเรียบร้อยแล้ว!")
            st.rerun()

# 4. ส่วนแสดงผลหลัก (ดึงข้อมูลล่าสุดมาใช้)
df = st.session_state.hazard_data

col1, col2 = st.columns([1.5, 2])

with col1:
    st.subheader("📊 ข้อมูลสรุป (Dashboard)")
    m1, m2 = st.columns(2)
    m1.metric("เหตุการณ์ทั้งหมด", f"{len(df)} ครั้ง")
    m2.metric("ไม่มีค่าใช้จ่าย", f"{len(df[df['ค่าใช้จ่าย'] == 'ด้านบำรุงทางไม่มีค่าใช้จ่าย'])} ครั้ง")
    st.dataframe(df, use_container_width=True, height=400)

with col2:
    st.subheader("🗺️ แผนที่พิกัดจุดเกิดเหตุ")
    if not df.empty:
        center_lat, center_lon = df["Latitude"].mean(), df["Longitude"].mean()
    else:
        center_lat, center_lon = 13.7367, 100.5231
        
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
    for idx, row in df.iterrows():
        # ตรวจสอบว่าพิกัดเป็นตัวเลข ไม่ใช่ค่าว่าง
        if pd.notna(row['Latitude']) and pd.notna(row['Longitude']):
            folium.Marker(
                location=[row["Latitude"], row["Longitude"]],
                popup=folium.Popup(f"<b>{row['เหตุการณ์']}</b><br>วันที่: {row['วันที่']}", max_width=300),
                tooltip=str(row["เหตุการณ์"]),
                icon=folium.Icon(color="red", icon="warning-sign")
            ).add_to(m)
    
    st_folium(m, width=700, height=500)