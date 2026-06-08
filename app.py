import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import datetime
import plotly.express as px

# 1. ตั้งค่าหน้าจอเป็นแบบ Wide เพื่อให้พื้นที่แสดงผลกว้างขวาง เหมาะกับ Dashboard
st.set_page_config(page_title="Train Hazards Executive Dashboard", page_icon="🚆", layout="wide")

# --- 🎨 ตกแต่ง UI ระดับพรีเมียม (Executive Theme) ---
st.markdown("""
    <style>
    /* ซ่อนเมนูขยะ */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* ปรับแต่งสีพื้นหลังแอปให้เป็นสีเทาอ่อน สบายตา */
    .stApp { background-color: #F8FAFC; font-family: 'Tahoma', sans-serif; }

    /* ตกแต่งกล่องตัวเลข (Metrics Card) ให้ดูมีมิติและหรูหรา */
    div[data-testid="metric-container"] {
        background-color: #FFFFFF;
        border-radius: 10px;
        padding: 20px 15px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
        border-left: 6px solid #1E3A8A; /* เส้นขอบซ้ายสีน้ำเงินกรมท่า */
    }
    
    /* ปรับฟอนต์ของกล่องตัวเลข */
    div[data-testid="stMetricValue"] { font-size: 32px !important; font-weight: 800 !important; color: #0F172A !important; }
    div[data-testid="stMetricLabel"] { font-size: 16px !important; font-weight: 600 !important; color: #64748B !important; }

    /* ตกแต่งหัวข้อหลัก */
    .dashboard-title { font-size: 28px; font-weight: 800; color: #0F172A; margin-bottom: 0px; text-transform: uppercase; letter-spacing: 1px;}
    .dashboard-subtitle { font-size: 15px; color: #64748B; margin-bottom: 30px; font-weight: 500;}
    .section-header { font-size: 18px; font-weight: bold; color: #1E293B; margin-top: 20px; border-bottom: 2px solid #E2E8F0; padding-bottom: 8px; margin-bottom: 15px;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ส่วนหัว (Header)
# ==========================================
col_logo, col_title = st.columns([1, 10])
with col_title:
    st.markdown('<p class="dashboard-title">🚆 Train Hazards Executive Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="dashboard-subtitle">รายงานสรุปสถานการณ์และผลกระทบเหตุรถไฟเฉี่ยวชนสัตว์ (อัปเดตล่าสุด)</p>', unsafe_allow_html=True)

# 2. ฐานข้อมูลจำลอง 
if 'hazard_data' not in st.session_state:
    st.session_state.hazard_data = pd.DataFrame({
        "ชื่อเหตุอันตราย": ["ชนโค ท่าพระ-ขอนแก่น", "เฉี่ยวชนกระบือ บ้านช่อง-หินซ้อน", "ชนโค หนองน้ำขุ่น-บ้านใหม่"],
        "พื้นที่": ["แขวงฯ ขอนแก่น", "แขวงฯ ฉะเชิงเทรา", "แขวงฯ นครราชสีมา"],
        "ที่ กม.": ["345+100", "150+200", "250+500"],
        "วัน/เดือน/ปี": ["2024-02-15", "2024-03-11", "2024-04-05"],
        "เวลา": ["10:30", "14:45", "08:15"],
        "ค่าใช้จ่าย": ["ไม่มีค่าใช้จ่าย", "มีค่าใช้จ่าย 5,000 บาท", "ไม่มีค่าใช้จ่าย"],
        "Latitude": [16.3650, 14.6540, 14.9722], "Longitude": [102.8340, 101.1230, 102.0833],
        "ผลกระทบ (นาที)": [15, 30, 10], "หมายเหตุ": ["-", "ซ้ำ ± 3 Km", "-"]
    })

df = st.session_state.hazard_data

# ==========================================
# ส่วนที่ 1: สรุปตัวเลขสำคัญ (Key Performance Indicators - KPIs)
# ==========================================
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("🚨 จำนวนเหตุการณ์ทั้งหมด", f"{len(df)} ครั้ง")
kpi2.metric("⏱️ ความล่าช้าสะสม", f"{df['ผลกระทบ (นาที)'].sum()} นาที")
kpi3.metric("⚠️ จุดเกิดเหตุซ้ำ", f"{len(df[df['หมายเหตุ'].str.contains('ซ้ำ', na=False)])} แห่ง")
kpi4.metric("📍 พื้นที่เสี่ยงสูงสุด", df['พื้นที่'].mode()[0] if not df.empty else "-")

st.write("") # เว้นบรรทัด

# ==========================================
# ส่วนที่ 2: กราฟ และ แผนที่ (แบ่งครึ่งจอ ซ้าย-ขวา เพื่อให้ผู้บริหารมองเห็นภาพรวมในระดับสายตา)
# ==========================================
col_chart, col_map = st.columns([1, 1.2])

with col_chart:
    st.markdown('<p class="section-header">📊 สถิติเหตุการณ์จำแนกตามพื้นที่</p>', unsafe_allow_html=True)
    if not df.empty:
        area_counts = df['พื้นที่'].value_counts().reset_index()
        area_counts.columns = ['พื้นที่', 'จำนวน']
        
        # ปรับแต่งกราฟให้ดูพรีเมียม คลีนๆ ไม่มีเส้นตารางรบกวนสายตา
        fig = px.bar(area_counts, x='จำนวน', y='พื้นที่', orientation='h', text='จำนวน', 
                     color_discrete_sequence=['#2563EB']) # ใช้สี Corporate Blue
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', # พื้นหลังโปร่งใส
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=20, t=10, b=0),
            xaxis=dict(showgrid=False, visible=False), # ซ่อนแกน X ให้ดูมินิมอล
            yaxis=dict(title=None, showgrid=False),
            font=dict(family="Tahoma", size=14, color="#334155")
        )
        fig.update_traces(textposition='outside', textfont=dict(weight='bold', color='#1E293B'))
        st.plotly_chart(fig, use_container_width=True, height=350)

with col_map:
    st.markdown('<p class="section-header">🗺️ แผนที่เฝ้าระวังจุดเกิดเหตุ</p>', unsafe_allow_html=True)
    if not df.empty and pd.notna(df["Latitude"].iloc[0]):
        center_lat, center_lon = df["Latitude"].mean(), df["Longitude"].mean()
    else:
        center_lat, center_lon = 13.7367, 100.5231
        
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6, 
                   tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google')
    
    for idx, row in df.iterrows():
        is_repeated = "ซ้ำ" in str(row['หมายเหตุ'])
        # ปรับสีหมุดให้สื่อความหมายชัดเจน: แดง=ทั่วไป, ดำ/ม่วงเข้ม=จุดซ้ำซาก (อันตรายสูง)
        marker_color = "darkred" if is_repeated else "red" 
        
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=folium.Popup(f"<div style='font-family:Tahoma; font-size:13px;'><b>{row['ชื่อเหตุอันตราย']}</b><br>พื้นที่: {row['พื้นที่']}<br>ล่าช้า: <b style='color:red;'>{row['ผลกระทบ (นาที)']} นาที</b></div>", max_width=250),
            icon=folium.Icon(color=marker_color, icon="warning-sign")
        ).add_to(m)

    st_folium(m, height=350, use_container_width=True, returned_objects=[]) 

# ==========================================
# ส่วนที่ 3: ตารางข้อมูล และ ฟอร์มเพิ่มข้อมูล
# ==========================================
st.markdown('<p class="section-header">📋 รายละเอียดข้อมูลเหตุการณ์</p>', unsafe_allow_html=True)

# ให้ตารางแสดงผลเด่นชัด 
st.dataframe(df, use_container_width=True, height=200)

# นำฟอร์มกรอกข้อมูลไปซ่อนไว้ด้านล่างสุด เพราะผู้บริหารเน้นดูผลลัพธ์ ไม่เน้นกรอกข้อมูล
with st.expander("➕ สำหรับเจ้าหน้าที่: เพิ่มข้อมูลเหตุการณ์ใหม่"):
    with st.form("executive_input_form"):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            input_name = st.text_input("ชื่อเหตุอันตราย")
            input_area = st.text_input("พื้นที่ (แขวงฯ)")
            input_date = st.date_input("วันที่เกิดเหตุ")
        with col_f2:
            input_km = st.text_input("ที่ กม.")
            input_impact = st.number_input("ล่าช้า (นาที)", min_value=0, step=1)
            input_time = st.time_input("เวลา", value=datetime.time(12, 00))
        with col_f3:
            input_lat = st.number_input("Latitude", value=13.7367, format="%.5f")
            input_lon = st.number_input("Longitude", value=100.5231, format="%.5f")
            input_remark = st.text_input("หมายเหตุ (เช่น ซ้ำ)")
            
        submit = st.form_submit_button("บันทึกข้อมูล", type="primary")
        if submit:
            new_row = pd.DataFrame([{
                "ชื่อเหตุอันตราย": input_name, "พื้นที่": input_area, "ที่ กม.": input_km,
                "วัน/เดือน/ปี": input_date.strftime("%Y-%m-%d"), "เวลา": input_time.strftime("%H:%M"), 
                "ค่าใช้จ่าย": "-", "Latitude": input_lat, "Longitude": input_lon,
                "ผลกระทบ (นาที)": input_impact, "หมายเหตุ": input_remark
            }])
            st.session_state.hazard_data = pd.concat([st.session_state.hazard_data, new_row], ignore_index=True)
            st.rerun()
