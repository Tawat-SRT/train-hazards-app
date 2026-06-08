import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import datetime
import plotly.express as px

# 1. ตั้งค่าหน้า Dashboard 
st.set_page_config(page_title="Train Hazards Dashboard", page_icon="🚂", layout="wide", initial_sidebar_state="expanded")

# --- ปรับแต่งสีสันและฟอนต์ ---
st.markdown("""
    <style>
    .main-title { font-size: 32px; font-weight: bold; color: #1E3A8A; margin-bottom: 0px; }
    .sub-title { font-size: 16px; color: #6B7280; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🚂 ระบบวิเคราะห์และติดตามเหตุอันตรายรถไฟชนสัตว์</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">แสดงข้อมูลเชิงสถิติ กราฟจำแนกพื้นที่ และแผนที่พิกัดจุดเกิดเหตุ</p>', unsafe_allow_html=True)

# 2. สร้างฐานข้อมูลจำลอง 
if 'hazard_data' not in st.session_state:
    st.session_state.hazard_data = pd.DataFrame({
        "ชื่อเหตุอันตราย": ["ชนโค ท่าพระ-ขอนแก่น", "เฉี่ยวชนกระบือ บ้านช่อง-หินซ้อน", "ชนโค หนองน้ำขุ่น-บ้านใหม่สำโรง"],
        "พื้นที่": ["แขวงบำรุงทางขอนแก่น", "แขวงบำรุงทางฉะเชิงเทรา", "แขวงบำรุงทางนครราชสีมา"],
        "ที่ กม.": ["345+100", "150+200", "250+500"],
        "วัน/เดือน/ปี": ["2024-02-15", "2024-03-11", "2024-04-05"],
        "เวลา": ["10:30", "14:45", "08:15"],
        "ค่าใช้จ่าย": ["ไม่มีค่าใช้จ่าย", "มีค่าใช้จ่าย 5,000 บาท", "ไม่มีค่าใช้จ่าย"],
        "Latitude": [16.3650, 14.6540, 14.9722],
        "Longitude": [102.8340, 101.1230, 102.0833],
        "ผลกระทบ (นาที)": [15, 30, 10],
        "หมายเหตุ": ["-", "จุดเกิดเหตุซ้ำ ± 3 Km", "-"]
    })

# 3. แถบด้านข้าง (Sidebar) สำหรับจัดการข้อมูล
with st.sidebar:
    st.header("⚙️ จัดการข้อมูล")
    
    with st.expander("📂 อัปโหลดไฟล์ (.csv, .xlsx)"):
        uploaded_file = st.file_uploader("เลือกไฟล์ของคุณ", type=["csv", "xlsx"])
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df_uploaded = pd.read_csv(uploaded_file)
                else:
                    df_uploaded = pd.read_excel(uploaded_file)
                if st.button("➕ ยืนยันเพิ่มข้อมูล"):
                    st.session_state.hazard_data = pd.concat([st.session_state.hazard_data, df_uploaded], ignore_index=True)
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("---")
    st.header("📝 เพิ่มข้อมูลใหม่")
    with st.form("data_input_form"):
        input_name = st.text_input("ชื่อเหตุอันตราย", placeholder="เช่น ชนโค สถานี A-B")
        input_area = st.text_input("พื้นที่ (แขวงบำรุงทาง)", placeholder="เช่น แขวงฯ ขอนแก่น")
        input_km = st.text_input("ที่ กม.", placeholder="เช่น 123+456")
        
        c1, c2 = st.columns(2)
        with c1:
            input_date = st.date_input("วันที่เกิดเหตุ")
        with c2:
            input_time = st.time_input("เวลา", value=datetime.time(12, 00))
            
        input_cost = st.text_input("ค่าใช้จ่าย", value="ไม่มีค่าใช้จ่าย")
        
        c3, c4 = st.columns(2)
        with c3:
            input_lat = st.number_input("Latitude", value=13.7367, format="%.5f")
        with c4:
            input_lon = st.number_input("Longitude", value=100.5231, format="%.5f")
            
        input_impact = st.number_input("ผลกระทบ (นาที)", min_value=0, step=1)
        input_remark = st.text_input("หมายเหตุ", placeholder="ระบุ 'ซ้ำ' หากเป็นจุดเดิม")
        
        if st.form_submit_button("💾 บันทึกข้อมูล"):
            new_row = pd.DataFrame([{
                "ชื่อเหตุอันตราย": input_name, "พื้นที่": input_area, "ที่ กม.": input_km,
                "วัน/เดือน/ปี": input_date.strftime("%Y-%m-%d"), "เวลา": input_time.strftime("%H:%M"),
                "ค่าใช้จ่าย": input_cost, "Latitude": input_lat, "Longitude": input_lon,
                "ผลกระทบ (นาที)": input_impact, "หมายเหตุ": input_remark
            }])
            st.session_state.hazard_data = pd.concat([st.session_state.hazard_data, new_row], ignore_index=True)
            st.success("บันทึกสำเร็จ!")
            st.rerun()

# --- ส่วนแสดงผลหลัก (Dashboard) ---
df = st.session_state.hazard_data

# ส่วนที่ 1: แถบตัวเลขสรุปผล
st.markdown("### 📊 ภาพรวมสถิติ")
metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
metric_col1.metric("🚨 จำนวนเหตุการณ์ทั้งหมด", f"{len(df)} ครั้ง")
metric_col2.metric("⏱️ ผลกระทบความล่าช้ารวม", f"{df['ผลกระทบ (นาที)'].sum()} นาที")
metric_col3.metric("📍 พื้นที่เกิดเหตุมากที่สุด", df['พื้นที่'].mode()[0] if not df.empty else "-")
metric_col4.metric("⚠️ จุดเกิดเหตุซ้ำ", f"{len(df[df['หมายเหตุ'].str.contains('ซ้ำ', na=False)])} จุด")

st.markdown("---")

# ส่วนที่ 2: กราฟแท่ง และ แผนที่
col_chart, col_map = st.columns([1.2, 1.8])

with col_chart:
    st.markdown("### 📊 จำนวนเหตุการณ์จำแนกตามพื้นที่")
    if not df.empty:
        # นับจำนวนเหตุการณ์ในแต่ละพื้นที่
        area_counts = df['พื้นที่'].value_counts().reset_index()
        area_counts.columns = ['พื้นที่', 'จำนวน']
        
        # 💡 สร้างกราฟแท่ง (Bar Chart) แทนที่กราฟวงกลม
        fig = px.bar(area_counts, x='พื้นที่', y='จำนวน', 
                     color='พื้นที่', # แยกสีตามพื้นที่
                     text_auto=True,  # ให้แสดงตัวเลขบนแท่งกราฟอัตโนมัติ
                     color_discrete_sequence=px.colors.qualitative.Set2) # ชุดสีที่สบายตา
        
        # ปรับแต่ง Layout ของกราฟแท่ง
        fig.update_layout(
            xaxis_title="แขวงบำรุงทาง",
            yaxis_title="จำนวนเหตุการณ์ (ครั้ง)",
            showlegend=False, # ซ่อนคำอธิบายสีด้านข้าง เพราะแกน X บอกชื่ออยู่แล้ว
            margin=dict(t=20, b=20, l=20, r=20)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ยังไม่มีข้อมูลสำหรับสร้างกราฟ")

with col_map:
    st.markdown("### 🗺️ แผนที่พิกัดจุดเกิดเหตุ (Google Maps Base)")
    if not df.empty and pd.notna(df["Latitude"].iloc[0]):
        center_lat, center_lon = df["Latitude"].mean(), df["Longitude"].mean()
    else:
        center_lat, center_lon = 13.7367, 100.5231
        
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6, 
                   tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google')
    
    for idx, row in df.iterrows():
        if pd.notna(row['Latitude']) and pd.notna(row['Longitude']):
            google_map_url = f"https://www.google.com/maps/search/?api=1&query={row['Latitude']},{row['Longitude']}"
            
            popup_html = f"""
            <div style="font-family: Tahoma; font-size: 13px; min-width: 220px;">
                <b style="color:#B91C1C;">{row['ชื่อเหตุอันตราย']}</b><br>
                <span style="color:gray;">{row['พื้นที่']}</span>
                <hr style="margin: 8px 0;">
                <b>กม.:</b> {row['ที่ กม.']}<br>
                <b>เวลา:</b> {row['วัน/เดือน/ปี']} ({row['เวลา']} น.)<br>
                <b>ล่าช้า:</b> {row['ผลกระทบ (นาที)']} นาที<br>
                <b style="color:red;">หมายเหตุ: {row['หมายเหตุ']}</b><br><br>
                <a href="{google_map_url}" target="_blank" style="background-color: #2563EB; color: white; padding: 6px 12px; text-decoration: none; border-radius: 4px; display: block; text-align: center; font-weight: bold;">📍 นำทางด้วย Google Maps</a>
            </div>
            """
            is_repeated = "ซ้ำ" in str(row['หมายเหตุ'])
            folium.Marker(
                location=[row["Latitude"], row["Longitude"]],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=row["ชื่อเหตุอันตราย"],
                icon=folium.Icon(color="orange" if is_repeated else "red", icon="info-sign" if is_repeated else "warning-sign")
            ).add_to(m)
            
    st_folium(m, width=800, height=400, returned_objects=[])

# ส่วนที่ 3: ตารางข้อมูล
st.markdown("### 📋 ตารางข้อมูลรายละเอียดทั้งหมด")
st.dataframe(df, use_container_width=True, height=250)