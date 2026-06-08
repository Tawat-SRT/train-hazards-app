import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import datetime
import plotly.express as px

# 1. ตั้งค่าหน้าจอ (Mobile Friendly)
st.set_page_config(page_title="Train Hazards", page_icon="🚂", layout="centered")

# --- 🎨 ตกแต่ง UI ให้เหมือน Mobile App ด้วย CSS ---
st.markdown("""
    <style>
    /* ซ่อนเมนูเบราว์เซอร์และลายน้ำของ Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ตกแต่งกล่องตัวเลข (Metrics) ให้เป็นแบบการ์ด 3 มิติขอบมน */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 15px;
        padding: 15px;
        box-shadow: 2px 4px 10px rgba(0,0,0,0.05);
        text-align: center;
    }
    
    /* ตกแต่งหัวข้อแอป */
    .app-title { 
        font-size: 26px; 
        font-weight: 800; 
        color: #1E3A8A; 
        text-align: center; 
        margin-top: -30px;
        margin-bottom: 5px; 
    }
    .app-subtitle { 
        font-size: 14px; 
        color: #6B7280; 
        text-align: center; 
        margin-bottom: 25px; 
    }
    </style>
""", unsafe_allow_html=True)

# หัวข้อแอปพลิเคชัน
st.markdown('<p class="app-title">🚂 Train Hazards App</p>', unsafe_allow_html=True)
st.markdown('<p class="app-subtitle">ระบบบันทึกพิกัดและสรุปเหตุอันตราย</p>', unsafe_allow_html=True)

# 2. ฐานข้อมูลจำลอง (Session State)
if 'hazard_data' not in st.session_state:
    st.session_state.hazard_data = pd.DataFrame({
        "ชื่อเหตุอันตราย": ["ชนโค ท่าพระ-ขอนแก่น"],
        "พื้นที่": ["แขวงฯ ขอนแก่น"],
        "ที่ กม.": ["345+100"],
        "วัน/เดือน/ปี": ["2024-02-15"],
        "เวลา": ["10:30"],
        "ค่าใช้จ่าย": ["ไม่มีค่าใช้จ่าย"],
        "Latitude": [16.3650], "Longitude": [102.8340],
        "ผลกระทบ (นาที)": [15], "หมายเหตุ": ["-"]
    })

df = st.session_state.hazard_data

# 3. สร้างแท็บ (Tabs) แบบแอปมือถือ เพื่อไม่ให้หน้าจอยาวเกินไป
tab1, tab2, tab3 = st.tabs(["📊 หน้าแรก", "🗺️ แผนที่", "📝 บันทึกข้อมูล"])

# --- TAB 1: หน้าสรุปผล (Dashboard) ---
with tab1:
    col1, col2 = st.columns(2)
    col1.metric("เหตุการณ์ทั้งหมด", f"{len(df)} ครั้ง")
    col2.metric("ล่าช้ารวม", f"{df['ผลกระทบ (นาที)'].sum()} นาที")
    
    st.markdown("<br><b>สัดส่วนพื้นที่เกิดเหตุ:</b>", unsafe_allow_html=True)
    if not df.empty:
        area_counts = df['พื้นที่'].value_counts().reset_index()
        area_counts.columns = ['พื้นที่', 'จำนวน']
        fig = px.bar(area_counts, x='พื้นที่', y='จำนวน', text_auto=True, color='พื้นที่')
        fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: แผนที่ (Map) ---
with tab2:
    st.markdown("<b>📍 พิกัดเหตุการณ์:</b>", unsafe_allow_html=True)
    if not df.empty:
        center_lat, center_lon = df["Latitude"].mean(), df["Longitude"].mean()
    else:
        center_lat, center_lon = 13.7367, 100.5231
        
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6, 
                   tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google')
    
    for idx, row in df.iterrows():
        is_repeated = "ซ้ำ" in str(row['หมายเหตุ'])
        folium.Marker(
            location=[row["Latitude"], row["Longitude"]],
            popup=f"<b>{row['ชื่อเหตุอันตราย']}</b><br>กม: {row['ที่ กม.']}",
            icon=folium.Icon(color="orange" if is_repeated else "red")
        ).add_to(m)
    st_folium(m, width=350, height=450, returned_objects=[]) # ปรับขนาดให้พอดีหน้าจอมือถือ

# --- TAB 3: ฟอร์มบันทึกข้อมูล (Input) ---
with tab3:
    st.markdown("<b>เพิ่มจุดเกิดเหตุใหม่:</b>", unsafe_allow_html=True)
    with st.form("mobile_input_form"):
        input_name = st.text_input("ชื่อเหตุอันตราย")
        input_area = st.text_input("พื้นที่ (แขวงฯ)")
        input_km = st.text_input("ที่ กม.")
        input_lat = st.number_input("Latitude", value=13.7367, format="%.5f")
        input_lon = st.number_input("Longitude", value=100.5231, format="%.5f")
        input_impact = st.number_input("ผลกระทบ (นาที)", min_value=0, step=1)
        
        # ทำให้ปุ่มกดดูเด่นขึ้นบนมือถือ
        submit = st.form_submit_button("💾 บันทึกข้อมูลลงระบบ", use_container_width=True)
        if submit:
            new_row = pd.DataFrame([{
                "ชื่อเหตุอันตราย": input_name, "พื้นที่": input_area, "ที่ กม.": input_km,
                "วัน/เดือน/ปี": datetime.datetime.now().strftime("%Y-%m-%d"), 
                "เวลา": "12:00", "ค่าใช้จ่าย": "-", 
                "Latitude": input_lat, "Longitude": input_lon,
                "ผลกระทบ (นาที)": input_impact, "หมายเหตุ": "-"
            }])
            st.session_state.hazard_data = pd.concat([st.session_state.hazard_data, new_row], ignore_index=True)
            st.success("บันทึกสำเร็จ!")
            st.rerun()
