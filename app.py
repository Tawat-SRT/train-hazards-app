import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import datetime
import plotly.express as px

# 1. ตั้งค่าหน้าจอเป็น Centered (เหมาะสำหรับ Mobile)
st.set_page_config(page_title="Train Hazards", page_icon="🚂", layout="centered")

# --- 🎨 ตกแต่ง UI ให้เป็น Mobile App (Single Page) ---
st.markdown("""
    <style>
    /* ซ่อนแถบเมนูเบราว์เซอร์ ลายน้ำ และพื้นที่ว่างด้านบน */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container { padding-top: 1rem; padding-bottom: 0rem; }

    /* ตกแต่งกล่องตัวเลข (Metrics) */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #f0f0f0;
        border-radius: 12px;
        padding: 10px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.05);
        text-align: center;
    }
    
    /* ตกแต่งหัวข้อแอป */
    .app-title { font-size: 24px; font-weight: 800; color: #1E3A8A; text-align: center; margin-bottom: 0px; }
    .app-subtitle { font-size: 14px; color: #6B7280; text-align: center; margin-bottom: 20px; }
    .section-title { font-size: 18px; font-weight: bold; color: #374151; margin-top: 25px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="app-title">🚂 Train Hazards App</p>', unsafe_allow_html=True)
st.markdown('<p class="app-subtitle">ระบบรายงานเหตุอันตรายรถไฟชนสัตว์</p>', unsafe_allow_html=True)

# 2. ฐานข้อมูลจำลอง (Session State)
if 'hazard_data' not in st.session_state:
    st.session_state.hazard_data = pd.DataFrame({
        "ชื่อเหตุอันตราย": ["ชนโค ท่าพระ-ขอนแก่น", "เฉี่ยวชนกระบือ บ้านช่อง-หินซ้อน"],
        "พื้นที่": ["แขวงฯ ขอนแก่น", "แขวงฯ ฉะเชิงเทรา"],
        "ที่ กม.": ["345+100", "150+200"],
        "วัน/เดือน/ปี": ["2024-02-15", "2024-03-11"],
        "เวลา": ["10:30", "14:45"],
        "ค่าใช้จ่าย": ["ไม่มีค่าใช้จ่าย", "มีค่าใช้จ่าย 5,000 บาท"],
        "Latitude": [16.3650, 14.6540], "Longitude": [102.8340, 101.1230],
        "ผลกระทบ (นาที)": [15, 30], "หมายเหตุ": ["-", "ซ้ำ ± 3 Km"]
    })

df = st.session_state.hazard_data

# ==========================================
# ส่วนที่ 1: แถบสรุปผล (Dashboard Metrics)
# ==========================================
col1, col2 = st.columns(2)
col1.metric("เหตุการณ์ทั้งหมด", f"{len(df)} ครั้ง")
col2.metric("ล่าช้ารวม", f"{df['ผลกระทบ (นาที)'].sum()} นาที")

# ==========================================
# ส่วนที่ 2: กราฟแท่งสรุปสัดส่วน (Chart)
# ==========================================
st.markdown('<p class="section-title">📊 สัดส่วนพื้นที่เกิดเหตุ</p>', unsafe_allow_html=True)
if not df.empty:
    area_counts = df['พื้นที่'].value_counts().reset_index()
    area_counts.columns = ['พื้นที่', 'จำนวน']
    fig = px.bar(area_counts, x='พื้นที่', y='จำนวน', text_auto=True, color='พื้นที่', color_discrete_sequence=px.colors.qualitative.Pastel)
    fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=250, xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# ส่วนที่ 3: แผนที่ (Google Maps Base)
# ==========================================
st.markdown('<p class="section-title">📍 แผนที่จุดเกิดเหตุ</p>', unsafe_allow_html=True)
if not df.empty and pd.notna(df["Latitude"].iloc[0]):
    center_lat, center_lon = df["Latitude"].mean(), df["Longitude"].mean()
else:
    center_lat, center_lon = 13.7367, 100.5231
    
m = folium.Map(location=[center_lat, center_lon], zoom_start=6, 
               tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google',
               control_scale=True)

for idx, row in df.iterrows():
    is_repeated = "ซ้ำ" in str(row['หมายเหตุ'])
    folium.Marker(
        location=[row["Latitude"], row["Longitude"]],
        popup=folium.Popup(f"<div style='font-family:Tahoma; font-size:12px;'><b>{row['ชื่อเหตุอันตราย']}</b><br>พื้นที่: {row['พื้นที่']}<br>กม: {row['ที่ กม.']}</div>", max_width=200),
        icon=folium.Icon(color="orange" if is_repeated else "red")
    ).add_to(m)

# แสดงแผนที่ให้พอดีกับหน้าจอมือถือ
st_folium(m, height=350, use_container_width=True, returned_objects=[]) 

# ==========================================
# ส่วนที่ 4: ฟอร์มบันทึกข้อมูล (Input Form)
# ==========================================
st.markdown('<p class="section-title">📝 เพิ่มข้อมูลจุดเกิดเหตุ</p>', unsafe_allow_html=True)

# ใช้ Expander เพื่อให้หน้าจอไม่ยาวเกินไป ผู้ใช้กดกางออกได้เมื่อต้องการพิมพ์
with st.expander("➕ แตะเพื่อเปิดฟอร์มบันทึกข้อมูล", expanded=False):
    with st.form("mobile_input_form"):
        input_name = st.text_input("ชื่อเหตุอันตราย", placeholder="เช่น ชนโค สถานี A-B")
        input_area = st.text_input("พื้นที่ (แขวงฯ)", placeholder="เช่น แขวงฯ ขอนแก่น")
        
        c1, c2 = st.columns(2)
        with c1:
            input_km = st.text_input("ที่ กม.", placeholder="123+456")
            input_impact = st.number_input("ล่าช้า (นาที)", min_value=0, step=1)
        with c2:
            input_date = st.date_input("วันที่เกิดเหตุ")
            input_time = st.time_input("เวลา", value=datetime.time(12, 00))
            
        c3, c4 = st.columns(2)
        with c3:
            input_lat = st.number_input("Latitude", value=13.7367, format="%.5f")
        with c4:
            input_lon = st.number_input("Longitude", value=100.5231, format="%.5f")
            
        input_remark = st.text_input("หมายเหตุ", placeholder="ใส่ 'ซ้ำ' หากเป็นจุดเดิม")
        
        # ปุ่มกดขนาดใหญ่แบบเต็มจอ
        submit = st.form_submit_button("💾 บันทึกข้อมูลลงระบบ", use_container_width=True)
        if submit:
            new_row = pd.DataFrame([{
                "ชื่อเหตุอันตราย": input_name, "พื้นที่": input_area, "ที่ กม.": input_km,
                "วัน/เดือน/ปี": input_date.strftime("%Y-%m-%d"), 
                "เวลา": input_time.strftime("%H:%M"), "ค่าใช้จ่าย": "ไม่มีค่าใช้จ่าย", 
                "Latitude": input_lat, "Longitude": input_lon,
                "ผลกระทบ (นาที)": input_impact, "หมายเหตุ": input_remark
            }])
            st.session_state.hazard_data = pd.concat([st.session_state.hazard_data, new_row], ignore_index=True)
            st.success("บันทึกสำเร็จ!")
            st.rerun()

# ==========================================
# ส่วนที่ 5: ตารางดูข้อมูลย้อนหลัง
# ==========================================
st.markdown('<p class="section-title">📋 ข้อมูลล่าสุด</p>', unsafe_allow_html=True)
st.dataframe(df.tail(5).iloc[::-1], use_container_width=True, hide_index=True) # แสดง 5 รายการล่าสุด
st.caption("แสดงข้อมูล 5 รายการล่าสุด")
