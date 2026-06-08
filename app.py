import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import datetime
import plotly.express as px

# 1. ตั้งค่าหน้าจอแบบ Wide สำหรับ Dashboard
st.set_page_config(page_title="Train Hazards Executive Dashboard", page_icon="🚆", layout="wide")

# --- 🎨 ตกแต่ง UI และใส่ Background Image ธีม Safety ---
# URL ของรูปภาพพื้นหลัง (สามารถนำ Link รูปของคุณมาใส่แทนได้)
background_url = "https://images.unsplash.com/photo-1474487548417-781cb71495f3?q=80&w=2000&auto=format&fit=crop"

st.markdown(f"""
    <style>
    /* ซ่อนเมนูเบราว์เซอร์ */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    
    /* 🌟 ใส่ภาพพื้นหลัง พร้อมฟิลเตอร์สีขาวโปร่งแสง 85% เพื่อให้อ่านตัวหนังสือได้ชัดเจน */
    .stApp {{ 
        background-image: linear-gradient(rgba(248, 250, 252, 0.85), rgba(248, 250, 252, 0.95)), url("{background_url}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Tahoma', sans-serif; 
    }}

    /* ตกแต่งกล่องตัวเลข (Metrics Card) ให้ดูมีมิติ สไตล์กระจกฝ้า (Glassmorphism) */
    div[data-testid="metric-container"] {{
        background-color: rgba(255, 255, 255, 0.9);
        border-radius: 12px;
        padding: 20px 15px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.08);
        border-left: 6px solid #B91C1C; /* เปลี่ยนเส้นขอบซ้ายเป็นสีแดงเข้ม (Safety First) */
        backdrop-filter: blur(10px);
    }}
    
    div[data-testid="stMetricValue"] {{ font-size: 32px !important; font-weight: 800 !important; color: #0F172A !important; }}
    div[data-testid="stMetricLabel"] {{ font-size: 16px !important; font-weight: 600 !important; color: #475569 !important; }}

    /* ตกแต่งหัวข้อหลัก */
    .dashboard-title {{ font-size: 30px; font-weight: 900; color: #1E3A8A; margin-bottom: 0px; text-transform: uppercase; text-shadow: 1px 1px 2px rgba(255,255,255,0.8);}}
    .dashboard-subtitle {{ font-size: 16px; color: #334155; margin-bottom: 30px; font-weight: bold;}}
    .section-header {{ font-size: 18px; font-weight: bold; color: #1E293B; margin-top: 20px; border-bottom: 2px solid rgba(0,0,0,0.1); padding-bottom: 8px; margin-bottom: 15px;}}
    
    /* ตกแต่งตารางและพื้นหลังกราฟให้โปร่งแสงสวยงาม */
    .stDataFrame, .stPlotlyChart {{
        background-color: rgba(255,255,255,0.85);
        border-radius: 10px;
        padding: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ส่วนหัว (Header)
# ==========================================
st.markdown('<p class="dashboard-title">🛡️ Safety First: Train Hazards Executive Dashboard</p>', unsafe_allow_html=True)
st.markdown('<p class="dashboard-subtitle">ระบบรายงานและเฝ้าระวังอุบัติเหตุรถไฟเฉี่ยวชนสัตว์แบบเรียลไทม์ (Real-time Monitoring)</p>', unsafe_allow_html=True)

# 2. ฐานข้อมูลจำลองแบบ Session State (ช่วยให้อัปเดตแบบเรียลไทม์ได้)
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
# ส่วนที่ 1: สรุปตัวเลขสำคัญ (KPIs อัปเดตเรียลไทม์)
# ==========================================
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("🚨 จำนวนเหตุการณ์ทั้งหมด", f"{len(df)} ครั้ง")
kpi2.metric("⏱️ ความล่าช้าสะสม", f"{df['ผลกระทบ (นาที)'].sum()} นาที")
kpi3.metric("⚠️ จุดเกิดเหตุซ้ำ (เฝ้าระวัง)", f"{len(df[df['หมายเหตุ'].str.contains('ซ้ำ', na=False)])} แห่ง")
kpi4.metric("📍 พื้นที่เสี่ยงสูงสุด", df['พื้นที่'].mode()[0] if not df.empty else "-")

st.write("") 

# ==========================================
# ส่วนที่ 2: กราฟ และ แผนที่ (เปลี่ยนแปลงทันทีที่มีข้อมูลใหม่)
# ==========================================
col_chart, col_map = st.columns([1, 1.2])

with col_chart:
    st.markdown('<p class="section-header">📊 สถิติความเสี่ยงจำแนกตามพื้นที่</p>', unsafe_allow_html=True)
    if not df.empty:
        area_counts = df['พื้นที่'].value_counts().reset_index()
        area_counts.columns = ['พื้นที่', 'จำนวน']
        
        # ใช้กราฟแท่งแนวนอน โทนสีแดงเพื่องาน Safety
        fig = px.bar(area_counts, x='จำนวน', y='พื้นที่', orientation='h', text='จำนวน', 
                     color_discrete_sequence=['#DC2626']) 
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=20, t=10, b=0), xaxis=dict(showgrid=False, visible=False), 
            yaxis=dict(title=None, showgrid=False), font=dict(family="Tahoma", size=14, color="#1E293B")
        )
        fig.update_traces(textposition='outside', textfont=dict(weight='bold', color='#1E293B'))
        st.plotly_chart(fig, use_container_width=True, height=350)

with col_map:
    st.markdown('<p class="section-header">🗺️ แผนที่เรดาร์เฝ้าระวังจุดเกิดเหตุ</p>', unsafe_allow_html=True)
    if not df.empty and pd.notna(df["Latitude"].iloc[0]):
        center_lat, center_lon = df["Latitude"].mean(), df["Longitude"].mean()
    else:
        center_lat, center_lon = 13.7367, 100.5231
        
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6, 
                   tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google')
    
    for idx, row in df.iterrows():
        is_repeated = "ซ้ำ" in str(row['หมายเหตุ'])
        marker_color = "darkred" if is_repeated else "red" 
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=folium.Popup(f"<div style='font-family:Tahoma; font-size:13px;'><b>{row['ชื่อเหตุอันตราย']}</b><br>พื้นที่: {row['พื้นที่']}<br>ล่าช้า: <b style='color:red;'>{row['ผลกระทบ (นาที)']} นาที</b></div>", max_width=250),
            icon=folium.Icon(color=marker_color, icon="warning-sign")
        ).add_to(m)

    st_folium(m, height=350, use_container_width=True, returned_objects=[]) 

# ==========================================
# ส่วนที่ 3: ตารางข้อมูล
# ==========================================
st.markdown('<p class="section-header">📋 ล็อกบุ๊กเหตุการณ์ล่าสุด</p>', unsafe_allow_html=True)
st.dataframe(df.iloc[::-1], use_container_width=True, height=200) # โชว์ข้อมูลใหม่สุดขึ้นก่อน

# ==========================================
# ส่วนที่ 4: ฟอร์มเพิ่มข้อมูลแบบเรียลไทม์
# ==========================================
with st.expander("➕ เพิ่มข้อมูลเหตุการณ์ใหม่ (ระบบจะอัปเดต Dashboard ทันทีที่กดบันทึก)"):
    with st.form("realtime_input_form"):
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
            
        submit = st.form_submit_button("💾 ยืนยันบันทึกข้อมูล", type="primary", use_container_width=True)
        
        # 💡 จุดสำคัญของการอัปเดตเรียลไทม์
        if submit:
            new_row = pd.DataFrame([{
                "ชื่อเหตุอันตราย": input_name, "พื้นที่": input_area, "ที่ กม.": input_km,
                "วัน/เดือน/ปี": input_date.strftime("%Y-%m-%d"), "เวลา": input_time.strftime("%H:%M"), 
                "ค่าใช้จ่าย": "-", "Latitude": input_lat, "Longitude": input_lon,
                "ผลกระทบ (นาที)": input_impact, "หมายเหตุ": input_remark
            }])
            # 1. นำข้อมูลใหม่ต่อท้ายฐานข้อมูล
            st.session_state.hazard_data = pd.concat([st.session_state.hazard_data, new_row], ignore_index=True)
            # 2. บังคับรีเฟรชหน้าจอ (Real-time Update) ทันที 
            st.rerun()
