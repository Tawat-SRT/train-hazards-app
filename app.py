import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import datetime
import plotly.express as px
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

# 1. ตั้งค่าหน้าจอ
st.set_page_config(page_title="Train Hazards Dashboard V1.18", page_icon="🚆", layout="wide")

# --- 🎨 ตกแต่ง UI สวยงามและธีม Safety ---
background_url = "https://images.unsplash.com/photo-1474487548417-781cb71495f3?q=80&w=2000&auto=format&fit=crop"
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap');
    html, body, [class*="css"], .stApp {{ font-family: 'Sarabun', sans-serif !important; }}
    .stApp {{ background-image: linear-gradient(rgba(248, 250, 252, 0.85), rgba(248, 250, 252, 0.95)), url("{background_url}"); background-size: cover; }}
    .dashboard-title {{ font-size: 30px; font-weight: 800; color: #1E3A8A; }}
    .section-header {{ font-size: 20px; font-weight: bold; color: #1E293B; border-bottom: 2px solid #ddd; padding-bottom: 5px; }}
    .app-footer {{ text-align: center; padding: 20px; font-size: 14px; color: #475569; }}
    </style>
""", unsafe_allow_html=True)

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

# 3. ฟังก์ชันสร้าง PDF (ReportLab)
def generate_pdf(df):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.drawString(100, 800, "รายงานอุบัติเหตุรถไฟชนสัตว์ (Executive Summary)")
    y = 750
    for i, row in df.iterrows():
        c.drawString(100, y, f"{row['วัน/เดือน/ปี']} | {row['ชื่อเหตุอันตราย']} | {row['พื้นที่']}")
        y -= 20
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# 4. ส่วนหัว
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown('<p class="dashboard-title">🛡️ Safety First: Train Hazards Dashboard</p>', unsafe_allow_html=True)
with col2:
    pdf_file = generate_pdf(df)
    st.download_button("📄 ดาวน์โหลดรายงาน PDF (A4)", data=pdf_file, file_name="Train_Hazards_Report.pdf", mime="application/pdf", use_container_width=True)

# 5. Dashboard KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("เหตุการณ์ทั้งหมด", f"{len(df)} ครั้ง")
k2.metric("ล่าช้าสะสม", f"{int(pd.to_numeric(df['ผลกระทบ(นาที)'], errors='coerce').fillna(0).sum())} นาที")
k3.metric("จุดเกิดเหตุซ้ำ", f"{len(df[df['หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)'].str.contains('ซ้ำ', na=False)])} แห่ง")
k4.metric("พื้นที่เสี่ยงสูงสุด", df['พื้นที่'].mode()[0] if not df.empty else "-")

# 6. กราฟและแผนที่
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
    st_folium(m, height=350, use_container_width=True)

# 7. จัดการข้อมูล
st.markdown('<p class="section-header">✏️ จัดการและเพิ่มข้อมูล</p>', unsafe_allow_html=True)
st.session_state.hazard_data = st.data_editor(st.session_state.hazard_data, use_container_width=True, num_rows="dynamic")

# 8. Footer
st.markdown("""
    <div class="app-footer">
        ออกแบบโดย : วิศวกรกำกับการกองทางถาวร ศูนย์ทางถาวร ฝ่ายการช่างโยธา<br>
        Version 1.18
    </div>
""", unsafe_allow_html=True)
