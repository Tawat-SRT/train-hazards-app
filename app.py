import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import datetime
import plotly.express as px

# 1. ตั้งค่าหน้าจอ
st.set_page_config(page_title="Train Hazards Dashboard V1.17", page_icon="🚆", layout="wide")

# --- 🎨 ตกแต่ง UI, ฟอนต์ TH Sarabun และระบบ Print A4 ---
background_url = "https://images.unsplash.com/photo-1474487548417-781cb71495f3?q=80&w=2000&auto=format&fit=crop"

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"], .stApp {{ font-family: 'Sarabun', sans-serif !important; }}
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}
    
    .stApp {{ 
        background-image: linear-gradient(rgba(248, 250, 252, 0.85), rgba(248, 250, 252, 0.95)), url("{background_url}");
        background-size: cover; background-position: center; background-attachment: fixed;
    }}
    
    div[data-testid="metric-container"] {{
        background-color: rgba(255, 255, 255, 0.9); border-radius: 12px; padding: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05); border-left: 6px solid #B91C1C; backdrop-filter: blur(10px);
    }}
    div[data-testid="stMetricValue"] {{ font-size: 32px !important; font-weight: 800 !important; color: #0F172A !important; }}
    div[data-testid="stMetricLabel"] {{ font-size: 18px !important; font-weight: 600 !important; color: #475569 !important; }}
    
    .dashboard-title {{ font-size: 34px; font-weight: 800; color: #1E3A8A; margin-bottom: 0px; text-shadow: 1px 1px 2px rgba(255,255,255,0.8);}}
    .dashboard-subtitle {{ font-size: 18px; color: #334155; margin-bottom: 10px; font-weight: bold;}}
    .section-header {{ font-size: 22px; font-weight: bold; color: #1E293B; margin-top: 15px; border-bottom: 2px solid rgba(0,0,0,0.1); padding-bottom: 5px; margin-bottom: 10px;}}
    .stDataFrame, .stPlotlyChart, div[data-testid="stDataEditor"] {{ background-color: rgba(255,255,255,0.85); border-radius: 10px; padding: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
    
    .update-date {{ text-align: right; font-size: 18px; color: #475569; font-weight: 600; margin-top: 15px; margin-bottom: 10px; }}
    
    @media print {{
        @page {{ size: A4 portrait; margin: 1cm; }}
        .stApp {{ background-image: none !important; background-color: white !important; }}
        .stButton, .stExpander, div[data-testid="stDataEditor"], div[data-testid="stToolbar"], .app-footer {{ display: none !important; }}
        * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
        div[data-testid="metric-container"] {{ border: 1px solid #E2E8F0 !important; box-shadow: none !important; margin-bottom: 10px; }}
        .stPlotlyChart, iframe {{ page-break-inside: avoid !important; }}
        .stDataFrame {{ page-break-before: always !important; margin-top: 20px; }}
        .update-date {{ font-size: 14px; margin-top: 0px; }}
    }}
    
    .app-footer {{ text-align: center; padding: 20px; margin-top: 40px; font-size: 16px; color: #475569; border-top: 1px solid rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.6); border-radius: 10px; }}
    </style>
""", unsafe_allow_html=True)

# วันที่ไทย
now = datetime.datetime.now()
thai_months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
thai_date_str = f"{now.day} {thai_months[now.month-1]} {now.year+543} เวลา {now.strftime('%H:%M')} น."

# 2. ฐานข้อมูลเริ่มต้น
if 'hazard_data' not in st.session_state:
    st.session_state.hazard_data = pd.DataFrame({
        "ชื่อเหตุอันตราย": ["ชนโค ท่าพระ-ขอนแก่น", "เฉี่ยวชนกระบือ บ้านช่อง-หินซ้อน"],
        "พื้นที่": ["แขวงฯ ขอนแก่น", "แขวงฯ ฉะเชิงเทรา"],
        "ที่ กม.": ["345+100", "150+200"],
        "วัน/เดือน/ปี": ["2024-02-15", "2024-03-11"],
        "เวลา ที่เกิดเหตุ": ["10:30", "14:45"],
        "ค่าใช้จ่าย": ["ไม่มีค่าใช้จ่าย", "มีค่าใช้จ่าย 5,000 บาท"],
        "Latitude": [16.3650, 14.6540], "Longitude": [102.8340, 101.1230],
        "ผลกระทบ(นาที)": [15, 30], "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)": ["-", "ซ้ำ ± 3 Km"]
    })

df = st.session_state.hazard_data
df['พื้นที่'] = df['พื้นที่'].astype(str).str.strip()

# หัวข้อและปุ่มพิมพ์
col_title, col_print = st.columns([3, 1.2])
with col_title:
    st.markdown('<p class="dashboard-title">🛡️ Safety First: Train Hazards Report</p>', unsafe_allow_html=True)
with col_print:
    st.markdown(f'<p class="update-date">🕒 ปรับปรุงข้อมูล ณ:<br><span style="color:#1E3A8A;">{thai_date_str}</span></p>', unsafe_allow_html=True)
    if st.button("🖨️ บันทึกรายงาน PDF (A4)", use_container_width=True, type="primary"):
        st.info("💡 กด Ctrl + P เพื่อบันทึกเป็น PDF")

# KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("เหตุการณ์ทั้งหมด", f"{len(df)} ครั้ง")
k2.metric("ล่าช้าสะสม", f"{int(pd.to_numeric(df['ผลกระทบ(นาที)'], errors='coerce').fillna(0).sum())} นาที")
k3.metric("จุดเกิดเหตุซ้ำ", f"{len(df[df['หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)'].str.contains('ซ้ำ', na=False)])} แห่ง")
k4.metric("พื้นที่เสี่ยงสูงสุด", df['พื้นที่'].mode()[0] if not df.empty else "-")

# กราฟและแผนที่
c1, c2 = st.columns([1, 1.2])
with c1:
    st.markdown('<p class="section-header">📊 สถิติความเสี่ยงรายพื้นที่</p>', unsafe_allow_html=True)
    fig = px.bar(df['พื้นที่'].value_counts().reset_index(), x='count', y='พื้นที่', orientation='h', color_discrete_sequence=['#DC2626'])
    st.plotly_chart(fig, use_container_width=True)
with c2:
    st.markdown('<p class="section-header">🗺️ แผนที่พิกัดเฝ้าระวัง</p>', unsafe_allow_html=True)
    m = folium.Map(location=[13.7367, 100.5231], zoom_start=6)
    for _, row in df.iterrows():
        folium.Marker([row["Latitude"], row["Longitude"]], popup=row["ชื่อเหตุอันตราย"]).add_to(m)
    st_folium(m, height=300, use_container_width=True)

# ตารางจัดการข้อมูล
st.markdown('<p class="section-header">✏️ จัดการและเพิ่มข้อมูล</p>', unsafe_allow_html=True)
st.session_state.hazard_data = st.data_editor(st.session_state.hazard_data, use_container_width=True, num_rows="dynamic")

# Footer
st.markdown('<div class="app-footer">ออกแบบโดย : วิศวกรกำกับการกองทางถาวร ศูนย์ทางถาวร ฝ่ายการช่างโยธา<br>Version 1.17</div>', unsafe_allow_html=True)
