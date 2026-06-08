import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import datetime
import plotly.express as px

# 1. ตั้งค่าหน้าจอ
st.set_page_config(page_title="Train Hazards Dashboard V1.16", page_icon="🚆", layout="wide")

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
        background-color: rgba(255, 255, 255, 0.9); border-radius: 12px; padding: 20px 15px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.08); border-left: 6px solid #B91C1C; backdrop-filter: blur(10px);
    }}
    div[data-testid="stMetricValue"] {{ font-size: 34px !important; font-weight: 800 !important; color: #0F172A !important; }}
    div[data-testid="stMetricLabel"] {{ font-size: 18px !important; font-weight: 600 !important; color: #475569 !important; }}
    
    .dashboard-title {{ font-size: 34px; font-weight: 800; color: #1E3A8A; margin-bottom: 0px; text-shadow: 1px 1px 2px rgba(255,255,255,0.8);}}
    .dashboard-subtitle {{ font-size: 18px; color: #334155; margin-bottom: 10px; font-weight: bold;}}
    .section-header {{ font-size: 22px; font-weight: bold; color: #1E293B; margin-top: 20px; border-bottom: 2px solid rgba(0,0,0,0.1); padding-bottom: 8px; margin-bottom: 15px;}}
    .stDataFrame, .stPlotlyChart, div[data-testid="stDataEditor"] {{ background-color: rgba(255,255,255,0.85); border-radius: 10px; padding: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
    
    /* 🌟 สไตล์สำหรับวันที่มุมขวาบน */
    .update-date {{
        text-align: right;
        font-size: 18px;
        color: #475569;
        font-weight: 600;
        margin-top: 15px;
        margin-bottom: 10px;
    }}
    
    @media print {{
        @page {{ size: A4 portrait; margin: 1.5cm; }}
        .stApp {{ background-image: none !important; background-color: white !important; }}
        .stButton, .stExpander, div[data-testid="stDataEditor"], div[data-testid="stToolbar"] {{ display: none !important; }}
        * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
        div[data-testid="metric-container"] {{ border: 1px solid #E2E8F0 !important; box-shadow: none !important; page-break-inside: avoid; }}
        /* ให้วันที่ชิดขวาในเอกสาร PDF ด้วย */
        .update-date {{ font-size: 16px; color: gray; margin-top: 0px; }}
    }}
    
    .app-footer {{ text-align: center; padding: 20px; margin-top: 40px; font-size: 16px; color: #475569; border-top: 1px solid rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.6); border-radius: 10px; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# สร้างระบบวันที่และเวลาปัจจุบันแบบภาษาไทย
# ==========================================
now = datetime.datetime.now()
thai_months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
# แปลงเป็น พ.ศ. และดึงเวลา
thai_date_str = f"{now.day} {thai_months[now.month-1]} {now.year+543} เวลา {now.strftime('%H:%M')} น."

# ==========================================
# ส่วนหัว (Header) & มุมขวาบน
# ==========================================
col_title, col_print = st.columns([3, 1.2])

with col_title:
    st.markdown('<p class="dashboard-title">🛡️ Safety First: Train Hazards Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="dashboard-subtitle">รายงานสรุปสถานการณ์อุบัติเหตุรถไฟเฉี่ยวชนสัตว์ (รูปแบบผู้บริหาร)</p>', unsafe_allow_html=True)

with col_print:
    # 🌟 แสดงข้อความอัปเดตล่าสุดที่มุมขวาบน
    st.markdown(f'<p class="update-date">🕒 ปรับปรุงข้อมูล ณ วันที่:<br><span style="color:#1E3A8A;">{thai_date_str}</span></p>', unsafe_allow_html=True)
    
    if st.button("🖨️ บันทึกรายงาน PDF (A4)", use_container_width=True, type="primary"):
        st.info("💡 **วิธีบันทึกเป็น PDF:** กรุณากดปุ่ม **Ctrl + P** (Windows) หรือ **Cmd + P** (Mac) บนคีย์บอร์ด แล้วเลือกปลายทางเป็น 'Save as PDF' ระบบได้จัดหน้ากระดาษและซ่อนเมนูเรียบร้อยแล้วครับ")

# 2. ฐานข้อมูลจำลอง
if 'hazard_data' not in st.session_state:
    st.session_state.hazard_data = pd.DataFrame({
        "ชื่อเหตุอันตราย": ["ชนโค ท่าพระ-ขอนแก่น", "เฉี่ยวชนกระบือ บ้านช่อง-หินซ้อน", "ชนโค หนองน้ำขุ่น-บ้านใหม่"],
        "พื้นที่": ["แขวงฯ ขอนแก่น", "แขวงฯ ฉะเชิงเทรา", "แขวงฯ นครราชสีมา"],
        "ที่ กม.": ["345+100", "150+200", "250+500"],
        "วัน/เดือน/ปี": ["2024-02-15", "2024-03-11", "2024-04-05"],
        "เวลา ที่เกิดเหตุ": ["10:30", "14:45", "08:15"],
        "ค่าใช้จ่าย": ["ไม่มีค่าใช้จ่าย", "มีค่าใช้จ่าย 5,000 บาท", "ไม่มีค่าใช้จ่าย"],
        "Latitude": [16.3650, 14.6540, 14.9722], 
        "Longitude": [102.8340, 101.1230, 102.0833],
        "ผลกระทบ(นาที)": [15, 30, 10], 
        "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)": ["-", "ซ้ำ ± 3 Km", "-"]
    })

df = st.session_state.hazard_data
df['พื้นที่'] = df['พื้นที่'].astype(str).str.strip()
df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')

# ==========================================
# ส่วนที่ 1: สรุปตัวเลขสำคัญ (KPIs)
# ==========================================
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
delay_sum = pd.to_numeric(df['ผลกระทบ(นาที)'], errors='coerce').fillna(0).sum()

kpi1.metric("🚨 จำนวนเหตุการณ์ทั้งหมด", f"{len(df)} ครั้ง")
kpi2.metric("⏱️ ความล่าช้าสะสม", f"{int(delay_sum)} นาที")

repeated_cases = df['หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)'].astype(str)
kpi3.metric("⚠️ จุดเกิดเหตุซ้ำ", f"{len(df[repeated_cases.str.contains('ซ้ำ', na=False)])} แห่ง")
kpi4.metric("📍 พื้นที่เสี่ยงสูงสุด", df['พื้นที่'].mode()[0] if not df.empty else "-")
st.write("") 

# ==========================================
# ส่วนที่ 2: กราฟ และ แผนที่
# ==========================================
col_chart, col_map = st.columns([1, 1.2])

with col_chart:
    st.markdown('<p class="section-header">📊 สถิติความเสี่ยงจำแนกตามพื้นที่</p>', unsafe_allow_html=True)
    if not df.empty:
        area_counts = df['พื้นที่'].value_counts().reset_index()
        area_counts.columns = ['พื้นที่', 'จำนวน']
        
        fig = px.bar(area_counts, x='จำนวน', y='พื้นที่', orientation='h', text='จำนวน', color_discrete_sequence=['#DC2626']) 
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=20, t=10, b=0), xaxis=dict(showgrid=False, visible=False), 
            yaxis=dict(title=None, showgrid=False), font=dict(family="Sarabun", size=16, color="#1E293B")
        )
        fig.update_traces(textposition='outside', textfont=dict(weight='bold', color='#1E293B', size=16))
        st.plotly_chart(fig, use_container_width=True, height=350)

with col_map:
    st.markdown('<p class="section-header">🗺️ แผนที่พิกัดเฝ้าระวังภัย</p>', unsafe_allow_html=True)
    valid_coords = df.dropna(subset=['Latitude', 'Longitude'])
    if not valid_coords.empty:
        center_lat, center_lon = valid_coords["Latitude"].mean(), valid_coords["Longitude"].mean()
    else:
        center_lat, center_lon = 13.7367, 100.5231
        
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6, 
                   tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google')
    
    for idx, row in df.iterrows():
        if pd.notna(row['Latitude']) and pd.notna(row['Longitude']):
            is_repeated = "ซ้ำ" in str(row['หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)'])
            marker_color = "darkred" if is_repeated else "red" 
            
            popup_html = f"""
            <div style='font-family:Sarabun; font-size:16px; min-width:200px;'>
                <b>{row['ชื่อเหตุอันตราย']}</b><br>
                <span style='color:gray;'>พื้นที่: {row['พื้นที่']}</span><br>
                <hr style='margin:5px 0;'>
                เวลา: {row['วัน/เดือน/ปี']} ({row['เวลา ที่เกิดเหตุ']} น.)<br>
                ล่าช้า: <b style='color:red;'>{row['ผลกระทบ(นาที)']} นาที</b>
            </div>
            """
            folium.Marker(
                location=[row["Latitude"], row["Longitude"]], popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color=marker_color, icon="warning-sign")
            ).add_to(m)

    st_folium(m, height=350, use_container_width=True, returned_objects=[]) 

# ==========================================
# ส่วนที่ 3: ตารางข้อมูล
# ==========================================
st.markdown('<p class="section-header">📋 รายละเอียดข้อมูลเหตุการณ์</p>', unsafe_allow_html=True)
st.dataframe(df, use_container_width=True, hide_index=True)

# ==========================================
# ส่วนที่ 4: สำหรับเจ้าหน้าที่ (ซ่อนเมื่อ Print)
# ==========================================
st.markdown('<p class="section-header">✏️ สำหรับเจ้าหน้าที่: จัดการข้อมูล (ซ่อนอัตโนมัติเมื่อพิมพ์ PDF)</p>', unsafe_allow_html=True)

edited_df = st.data_editor(
    st.session_state.hazard_data,
    use_container_width=True, num_rows="dynamic", height=200, key="editor"
)
if st.button("🔄 อัปเดตและบันทึกการแก้ไข", use_container_width=True):
    st.session_state.hazard_data = edited_df
    st.success("✅ บันทึกการแก้ไขข้อมูลเรียบร้อยแล้ว!")
    st.rerun()

col_upload, col_manual = st.columns(2)
with col_upload:
    with st.expander("📥 1. นำเข้าข้อมูลจากไฟล์ (.csv, .xlsx)"):
        uploaded_file = st.file_uploader("ลากไฟล์มาวาง หรือ กดเพื่อเลือกไฟล์", type=["csv", "xlsx"])
        if uploaded_file is not None:
            if uploaded_file.name.endswith('.csv'): df_new = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith('.xlsx'): df_new = pd.read_excel(uploaded_file)
            if st.button("➕ ยืนยันผสานข้อมูลเข้าระบบ", type="primary"):
                st.session_state.hazard_data = pd.concat([st.session_state.hazard_data, df_new], ignore_index=True)
                st.rerun()

with col_manual:
    with st.expander("📝 2. กรอกข้อมูลใหม่ด้วยตัวเอง"):
        with st.form("realtime_input_form"):
            input_name = st.text_input("ชื่อเหตุอันตราย")
            input_area = st.text_input("พื้นที่")
            input_km = st.text_input("ที่ กม.")
            c1, c2 = st.columns(2)
            with c1:
                input_date = st.date_input("วัน/เดือน/ปี")
                input_lat = st.number_input("Latitude", value=13.7367, format="%.5f")
                input_impact = st.number_input("ผลกระทบ(นาที)", min_value=0, step=1)
            with c2:
                input_time = st.time_input("เวลา ที่เกิดเหตุ", value=datetime.time(12, 00))
                input_lon = st.number_input("Longitude", value=100.5231, format="%.5f")
                input_cost = st.text_input("ค่าใช้จ่าย", value="ไม่มีค่าใช้จ่าย")
            input_remark = st.text_input("หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)", placeholder="เช่น ซ้ำ")
                
            if st.form_submit_button("💾 ยืนยันบันทึกข้อมูล", type="primary", use_container_width=True):
                new_row = pd.DataFrame([{"ชื่อเหตุอันตราย": input_name, "พื้นที่": input_area, "ที่ กม.": input_km,
                    "วัน/เดือน/ปี": input_date.strftime("%Y-%m-%d"), "เวลา ที่เกิดเหตุ": input_time.strftime("%H:%M"), 
                    "ค่าใช้จ่าย": input_cost, "Latitude": input_lat, "Longitude": input_lon,
                    "ผลกระทบ(นาที)": input_impact, "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)": input_remark}])
                st.session_state.hazard_data = pd.concat([st.session_state.hazard_data, new_row], ignore_index=True)
                st.rerun()

# ==========================================
# ส่วนที่ 5: Footer
# ==========================================
st.markdown("""
    <div class="app-footer">
        <b>ออกแบบโดย :</b> วิศวกรกำกับการกองทางถาวร ศูนย์ทางถาวร ฝ่ายการช่างโยธา<br>
        <span style="color: gray; font-size: 14px;">Version 1.16</span>
    </div>
""", unsafe_allow_html=True)
