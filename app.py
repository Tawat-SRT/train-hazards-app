import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import datetime
import plotly.express as px
import os

# 1. ตั้งค่าหน้าจอ
st.set_page_config(page_title="Train Hazards Dashboard V1.17.1", page_icon="🚆", layout="wide")

# 🌟 กำหนดชื่อไฟล์สำหรับเป็นฐานข้อมูลกลาง (Shared Database สำหรับทุกคน)
DATA_FILE = "hazard_data_shared.csv"

# 🌟 ฟังก์ชันสำหรับโหลดข้อมูลกลาง หรือสร้างข้อมูลเริ่มต้นหากยังไม่มีไฟล์
def load_shared_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        # ข้อมูลเริ่มต้นตามโครงสร้างเดิมของ Version 1.17
        initial_df = pd.DataFrame({
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
        initial_df.to_csv(DATA_FILE, index=False)
        return initial_df

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
    
    /* สไตล์กล่องแจ้งเตือนจุดซ้ำ */
    .danger-box {{
        background-color: #FEF2F2; border-left: 6px solid #DC2626; padding: 15px; border-radius: 8px; margin-bottom: 15px;
    }}
    
    /* 🖨️ คำสั่งพิเศษสำหรับตั้งค่าเครื่องปริ้นและจัดหน้า PDF (A4) 🖨️ */
    @media print {{
        @page {{ size: A4 portrait; margin: 1cm; }}
        .stApp {{ background-image: none !important; background-color: white !important; }}
        
        /* ซ่อนสิ่งที่ไม่จำเป็นสำหรับผู้บริหาร */
        .stButton, .stExpander, div[data-testid="stDataEditor"], div[data-testid="stToolbar"], .app-footer {{ display: none !important; }}
        
        /* บังคับสีกราฟและพื้นหลัง */
        * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
        
        /* ปรับกล่อง KPI ให้เรียง 4 ช่องสวยงามบน A4 */
        div[data-testid="stMetricValue"] {{ font-size: 24px !important; }}
        div[data-testid="metric-container"] {{ border: 1px solid #E2E8F0 !important; box-shadow: none !important; margin-bottom: 10px; }}
        
        /* ป้องกันกราฟและแผนที่ถูกตัดขาดครึ่ง */
        .stPlotlyChart, iframe, .danger-box {{ page-break-inside: avoid !important; }}
        
        /* ดันตารางข้อมูลทั้งหมดไปหน้าถัดไป เพื่อให้หน้าแรกสะอาด */
        .main-data-table {{ page-break-before: always !important; margin-top: 20px; }}
        
        /* ปรับวันที่ให้อยู่มุมบนขวา */
        .update-date {{ font-size: 14px; margin-top: 0px; }}
    }}
    
    .app-footer {{ text-align: center; padding: 20px; margin-top: 40px; font-size: 16px; color: #475569; border-top: 1px solid rgba(0,0,0,0.1); background-color: rgba(255,255,255,0.6); border-radius: 10px; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# สร้างระบบวันที่และเวลาปัจจุบันแบบภาษาไทย
# ==========================================
now = datetime.datetime.now()
thai_months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
thai_date_str = f"{now.day} {thai_months[now.month-1]} {now.year+543} เวลา {now.strftime('%H:%M')} น."

# ==========================================
# ส่วนหัว (Header) & มุมขวาบน
# ==========================================
col_title, col_print = st.columns([3, 1.2])

with col_title:
    st.markdown('<p class="dashboard-title">🛡️ Safety First: Train Hazards Report</p>', unsafe_allow_html=True)
    st.markdown('<p class="dashboard-subtitle">รายงานสรุปภาพรวมอุบัติเหตุรถไฟเฉี่ยวชนสัตว์ (Executive Summary)</p>', unsafe_allow_html=True)

with col_print:
    st.markdown(f'<p class="update-date">🕒 ปรับปรุงข้อมูล ณ วันที่:<br><span style="color:#1E3A8A;">{thai_date_str}</span></p>', unsafe_allow_html=True)
    if st.button("🖨️ บันทึกรายงาน PDF (A4)", use_container_width=True, type="primary"):
        st.info("💡 **กดปุ่ม Ctrl + P** หรือ **Cmd + P** แล้วเลือก Save as PDF ระบบได้จัดกระดาษให้เหมาะกับขนาด A4 เรียบร้อยแล้วครับ")

# ดึงข้อมูลจากฐานข้อมูล Shared CSV
df = load_shared_data()

# คลีนนิ่งและแปลงประเภทข้อมูลพื้นฐาน
df['พื้นที่'] = df['พื้นที่'].astype(str).str.strip()
df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')

# ==========================================
# ส่วนที่ 1: สรุปตัวเลขสำคัญ (KPIs)
# ==========================================
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
delay_sum = pd.to_numeric(df['ผลกระทบ(นาที)'], errors='coerce').fillna(0).sum()

# คัดกรองข้อมูลจุดเกิดเหตุซ้ำเพื่อใช้นับจำนวนและแสดงตาราง
repeated_cases_mask = df['หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)'].astype(str).str.contains('ซ้ำ', na=False)
df_repeated = df[repeated_cases_mask]

kpi1.metric("🚨 จำนวนเหตุการณ์ทั้งหมด", f"{len(df)} ครั้ง")
kpi2.metric("⚠️ จุดเกิดเหตุซ้ำ (± 3 Km)", f"{len(df_repeated)} แห่ง")
kpi3.metric("📍 พื้นที่เสี่ยงสูงสุด", df['พื้นที่'].mode()[0] if not df.empty else "-")
kpi4.metric("⏱️ ความล่าช้าสะสม", f"{int(delay_sum)} นาที")

st.write("") 

# ==========================================
# 🌟 ส่วนที่เพิ่มเข้ามาใหม่: ตารางแสดงรายการจุดเกิดเหตุซ้ำ (สำหรับผู้บริหาร) 🌟
# ==========================================
st.markdown('<p class="section-header">❌ รายการพื้นที่เฝ้าระวังพิเศษ (จุดที่เกิดเหตุซ้ำซาก ± 3 Km)</p>', unsafe_allow_html=True)
if not df_repeated.empty:
    st.markdown(
        f"""<div class="danger-box">
            📌 <b>ข้อเสนอแนะเชิงนโยบาย:</b> พบจุดเกิดอุบัติเหตุซ้ำซากจำนวน <b>{len(df_repeated)} แห่ง</b> 
            ควรประสานงานแขวงบำรุงทางในพื้นที่เพื่อพิจารณาตั้งงบประมาณล้อมรั้วกั้นทางรถไฟ หรือทำเนินดิน/ป้ายเตือนเจ้าของสัตว์ในพิกัดดังกล่าวโดยด่วน
        </div>""", unsafe_allow_html=True
    )
    # แสดงตารางเฉพาะคอลัมน์สำคัญที่ผู้บริหารต้องการวิเคราะห์จุดซ้ำ
    st.dataframe(
        df_repeated[["ชื่อเหตุอันตราย", "พื้นที่", "ที่ กม.", "วัน/เดือน/ปี", "ผลกระทบ(นาที)", "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"]], 
        use_container_width=True, 
        hide_index=True
    )
else:
    st.success("✅ ปัจจุบันยังไม่พบข้อมูลจุดเกิดเหตุซ้ำซากในระบบ")

st.write("")

# ==========================================
# ส่วนที่ 3: กราฟ และ แผนที่ (ปรับขนาดให้พอดี A4)
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
        st.plotly_chart(fig, use_container_width=True, height=300)

with col_map:
    st.markdown('<p class="section-header">🗺️ แผนที่พิกัดภาพรวมทุกจุด</p>', unsafe_allow_html=True)
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
                เวลา: {row['วัน/เดือน/ปี']} ({row['เวลา ที่เกิดเหตุ']} น.)
            </div>
            """
            folium.Marker(
                location=[row["Latitude"], row["Longitude"]], popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color=marker_color, icon="warning-sign")
            ).add_to(m)

    st_folium(m, height=300, use_container_width=True, returned_objects=[]) 

# ==========================================
# ส่วนที่ 4: ตารางข้อมูลดิบทั้งหมด (จะถูกปัดไปหน้าถัดไปเมื่อพิมพ์รายงาน)
# ==========================================
st.markdown('<div class="main-data-table">', unsafe_allow_html=True)
st.markdown('<p class="section-header">📋 รายละเอียดข้อมูลเหตุการณ์ทั้งหมดในระบบ</p>', unsafe_allow_html=True)
st.dataframe(df, use_container_width=True, hide_index=True)
st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# ส่วนที่ 5: สำหรับเจ้าหน้าที่ (ซ่อนเมื่อ Print และ อัปเดตข้อมูลแบบสดๆ ร่วมกัน)
# ==========================================
st.markdown('<p class="section-header">✏️ สำหรับเจ้าหน้าที่: จัดการข้อมูล (ซ่อนอัตโนมัติเมื่อพิมพ์ PDF)</p>', unsafe_allow_html=True)

# แสดงตารางแก้ไขฐานข้อมูลกลาง
edited_df = st.data_editor(
    df,
    use_container_width=True, num_rows="dynamic", height=200, key="editor"
)

# ปุ่มบันทึกระบบและสั่ง Rerun ทันทีเพื่ออัปเดต Dashboard ของทุกคนแบบ Real-time
if st.button("🔄 อัปเดตและบันทึกการแก้ไขข้อมูล", use_container_width=True):
    edited_df.to_csv(DATA_FILE, index=False) # เซฟทับไฟล์ CSV กลางทันที
    st.success("✅ บันทึกข้อมูลเรียบร้อยแล้ว! ข้อมูลตัวเลข กราฟ และตารางจุดซ้ำได้อัปเดตแบบ Real-time แล้ว")
    st.rerun()

col_upload, col_manual = st.columns(2)
with col_upload:
    with st.expander("📥 1. นำเข้าข้อมูลจากไฟล์ (.csv, .xlsx)"):
        uploaded_file = st.file_uploader("ลากไฟล์มาวาง หรือ กดเพื่อเลือกไฟล์", type=["csv", "xlsx"])
        if uploaded_file is not None:
            if uploaded_file.name.endswith('.csv'): df_new = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith('.xlsx'): df_new = pd.read_excel(uploaded_file)
            if st.button("➕ ยืนยันผสานข้อมูลเข้าระบบ", type="primary"):
                combined_df = pd.concat([df, df_new], ignore_index=True)
                combined_df.to_csv(DATA_FILE, index=False)
                st.success("ผสานไฟล์นำเข้าเรียบร้อย!")
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
                combined_df = pd.concat([df, new_row], ignore_index=True)
                combined_df.to_csv(DATA_FILE, index=False)
                st.rerun()

# ==========================================
# ส่วนที่ 6: Footer
# ==========================================
st.markdown("""
    <div class="app-footer">
        <b>ออกแบบโดย :</b> วิศวกรกำกับการกองทางถาวร ศูนย์ทางถาวร ฝ่ายการช่างโยธา<br>
        <span style="color: gray; font-size: 14px;">Version 1.17.1 (Shared-Database Edition)</span>
    </div>
""", unsafe_allow_html=True)
