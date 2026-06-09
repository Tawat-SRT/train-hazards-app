import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import datetime
import plotly.express as px
import os

# 1. ตั้งค่าหน้าจอแบบกว้างพิเศษเพื่อความภูมิฐานระดับผู้บริหาร
st.set_page_config(page_title="Train Hazards Executive Dashboard V1.17.5", page_icon="🚆", layout="wide")

# ฐานข้อมูลกลาง (Shared Database สำหรับทุกคน)
DATA_FILE = "hazard_data_shared.csv"

# ฟังก์ชันแปลงวันที่ให้เป็น วัน เดือน ปี พ.ศ. ไทย สำหรับแสดงผล
def convert_to_thai_date(date_str):
    try:
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
            try:
                dt = datetime.datetime.strptime(str(date_str).strip(), fmt)
                break
            except ValueError:
                continue
        else:
            return date_str
            
        thai_months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
        return f"{dt.day} {thai_months[dt.month-1]} {dt.year + 543}"
    except:
        return date_str

# ฟังก์ชันโหลดและจัดระเบียบข้อมูล (เรียงลำดับเวลาล่าสุด -> เก่าสุด เสมอสำหรับโครงสร้างหลัก)
def load_and_sort_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
    else:
        df = pd.DataFrame({
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
        df.to_csv(DATA_FILE, index=False)
    
    # แปลงคอลัมน์วันที่ให้เป็น datetime เพื่อใช้ในการ Sort ลำดับเวลา
    df['temp_date'] = pd.to_datetime(df['วัน/เดือน/ปี'], errors='coerce')
    
    # สั่งเรียงลำดับจาก ปัจจุบัน (ใหม่สุด) ไปหา อดีต (เก่าสุด)
    df = df.sort_values(by=['temp_date', 'เวลา ที่เกิดเหตุ'], ascending=[False, False]).reset_index(drop=True)
    df = df.drop(columns=['temp_date'])
    return df

# --- 🎨 ตกแต่ง UI และตารางระดับ Premium (Corporate, Clean & Executive Theme) ---
background_url = "https://images.unsplash.com/photo-1474487548417-781cb71495f3?q=80&w=2000&auto=format&fit=crop"

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"], .stApp {{ font-family: 'Sarabun', sans-serif !important; }}
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}
    
    .stApp {{ 
        background-image: linear-gradient(rgba(245, 247, 250, 0.92), rgba(245, 247, 250, 0.98)), url("{background_url}");
        background-size: cover; background-position: center; background-attachment: fixed;
    }}
    
    /* สไตล์กล่อง KPI แบบผู้บริหาร */
    div[data-testid="metric-container"] {{
        background: linear-gradient(135deg, rgba(255,255,255,1) 0%, rgba(248,250,252,1) 100%);
        border-radius: 14px; padding: 20px 16px;
        box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.04), 0 2px 6px -1px rgba(15, 23, 42, 0.03);
        border: 1px solid rgba(226, 232, 240, 0.8);
        border-top: 5px solid #1E3A8A;
    }}
    div[data-testid="stMetricValue"] {{ font-size: 34px !important; font-weight: 800 !important; color: #1E3A8A !important; }}
    div[data-testid="stMetricLabel"] {{ font-size: 15px !important; font-weight: 600 !important; color: #475569 !important; letter-spacing: 0.3px; }}
    
    /* หัวข้อและสไตล์ข้อความ */
    .dashboard-title {{ font-size: 36px; font-weight: 800; color: #0F172A; margin-bottom: 0px; }}
    .dashboard-subtitle {{ font-size: 18px; color: #475569; margin-bottom: 15px; }}
    .section-header {{ font-size: 22px; font-weight: 700; color: #1E3A8A; margin-top: 25px; border-bottom: 2px solid #E2E8F0; padding-bottom: 8px; margin-bottom: 15px; }}
    
    /* การแสดงตาราง กราฟ และแผนที่ให้สวยงาม */
    .stDataFrame, .stPlotlyChart, div[data-testid="stDataEditor"], .leaflet-container {{ 
        background-color: #FFFFFF !important; border-radius: 14px !important; padding: 14px; 
        box-shadow: 0 4px 15px -3px rgba(15, 23, 42, 0.05) !important;
        border: 1px solid #E2E8F0 !important;
    }}
    
    .update-date {{ text-align: right; font-size: 16px; color: #64748B; font-weight: 500; margin-top: 15px; }}
    .danger-box {{ background-color: #FFF5F5; border-left: 6px solid #F43F5E; padding: 16px; border-radius: 10px; margin-bottom: 15px; color: #9F1239; font-size: 15.5px; line-height: 1.6; }}
    
    /* หน้าต่างจัดการข้อมูล */
    .management-panel {{
        background-color: #F8FAFC; border: 1px dashed #CBD5E1; padding: 24px; border-radius: 14px; margin-top: 15px;
    }}

    @media print {{
        @page {{ size: A4 portrait; margin: 1cm; }}
        .stApp {{ background-image: none !important; background-color: white !important; }}
        .stButton, .stExpander, div[data-testid="stDataEditor"], div[data-testid="stToolbar"], .app-footer, .no-print {{ display: none !important; }}
        * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
        .main-data-table {{ page-break-before: always !important; margin-top: 20px; }}
    }}
    
    .app-footer {{ text-align: center; padding: 25px; margin-top: 50px; font-size: 15px; color: #64748B; border-top: 1px solid #E2E8F0; }}
    </style>
""", unsafe_allow_html=True)

# ระบบวันที่อัปเดตภาษาไทย
now = datetime.datetime.now()
thai_months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
thai_date_str = f"{now.day} {thai_months[now.month-1]} {now.year+543} เวลา {now.strftime('%H:%M')} น."

# ==========================================
# ส่วนหัว (Executive Header)
# ==========================================
col_title, col_print = st.columns([3.2, 1])

with col_title:
    st.markdown('<p class="dashboard-title">🚆 สรุปสถานการณ์อุบัติเหตุรถไฟเฉี่ยวชนสัตว์</p>', unsafe_allow_html=True)
    st.markdown('<p class="dashboard-subtitle">รายงานวิเคราะห์เชิงพื้นที่และข้อมูลสถิติสำหรับผู้บริหาร (Executive Intelligence Report)</p>', unsafe_allow_html=True)

with col_print:
    st.markdown(f'<p class="update-date">🕒 ข้อมูลอัปเดตล่าสุด:<br><span style="color:#1E3A8A; font-weight:700;">{thai_date_str}</span></p>', unsafe_allow_html=True)
    if st.button("🖨️ ส่งออกรายงานเป็น PDF (A4)", use_container_width=True, type="primary"):
        st.info("💡 **คำแนะนำผู้บริหาร:** กดปุ่ม **Ctrl + P** (Windows) หรือ **Cmd + P** (Mac) แล้วเลือก 'Save as PDF'")

# โหลดข้อมูลกลาง (Shared File) และเรียงลำดับเวลาใหม่ไปเก่าเสมอ
df_base = load_and_sort_data()

# คลีนนิ่งข้อมูลพื้นฐาน
df_base['พื้นที่'] = df_base['พื้นที่'].astype(str).str.strip()
df_base['Latitude'] = pd.to_numeric(df_base['Latitude'], errors='coerce')
df_base['Longitude'] = pd.to_numeric(df_base['Longitude'], errors='coerce')

# 🌟 จัดตารางส่วนที่ 2: ทะเบียนประวัติข้อมูลเหตุการณ์ทั้งหมด (เพิ่มคอล็มน์ ลำดับที่ และเรียงจากปัจจุบันไปอดีต)
df_display = df_base.copy()
df_display['วัน/เดือน/ปี'] = df_display['วัน/เดือน/ปี'].apply(convert_to_thai_date)
df_display.insert(0, 'ลำดับที่', range(1, len(df_display) + 1)) # รันลำดับเลข 1 ถึง N จากใหม่ไปเก่า

# ==========================================
# ส่วนที่ 1: สรุปสถิติตัวเลขสำคัญ (KPIs)
# ==========================================
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
delay_sum = pd.to_numeric(df_base['ผลกระทบ(นาที)'], errors='coerce').fillna(0).sum()

# คัดกรองข้อมูลจุดเกิดเหตุซ้ำ (ใช้โครงสร้างลำดับเดียวกันกับทะเบียนประวัติหลัก)
repeated_cases_mask = df_base['หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)'].astype(str).str.contains('ซ้ำ', na=False)
df_repeated_display = df_display[df_display['ชื่อเหตุอันตราย'].isin(df_base[repeated_cases_mask]['ชื่อเหตุอันตราย'])].copy()

# 🌟 แก้ไขข้อ 1: บังคับให้ตารางจุดซ้ำรันเลขลำดับใหม่เริ่มจาก 1 ถึงจำนวนล่าสุด ตามลำดับเวลาใหม่ไปเก่าของประวัติหลัก
df_repeated_display['ลำดับที่'] = range(1, len(df_repeated_display) + 1)

kpi1.metric("🚨 เหตุการณ์สะสม", f"{len(df_base)} ครั้ง")
kpi2.metric("⚠️ พิกัดเกิดเหตุซ้ำ (± 3 Km)", f"{len(df_repeated_display)} แห่ง")
kpi3.metric("📍 พื้นที่วิกฤตสูงสุด", df_base['พื้นที่'].mode()[0] if not df_base.empty else "-")
kpi4.metric("⏱️ ความล่าช้ารวมขบวน", f"{int(delay_sum)} นาที")

st.write("") 

# ==========================================
# ส่วนที่ 2: ข้อมูลจุดเกิดเหตุซ้ำ (พิกัดเฝ้าระวังพิเศษ)
# ==========================================
st.markdown('<p class="section-header">❌ พื้นที่เฝ้าระวังพิเศษ (พิกัดที่เกิดเหตุซ้ำซาก)</p>', unsafe_allow_html=True)
show_repeated = st.checkbox("🔍 คลิกที่นี่ เพื่อเปิด/ปิด ตารางแสดงรายละเอียดจุดเกิดเหตุซ้ำสะสม (เรียงตามลำดับเวลาล่าสุด ➡️ อดีต)", value=False, key="rep_check")

if show_repeated:
    if not df_repeated_display.empty:
        st.markdown(
            f"""<div class="danger-box">
                <b>📌 รายงานด่วนเชิงนโยบาย:</b> ระบบจัดเรียงจุดเกิดเหตุซ้ำโดย<b>อ้างอิงลำดับเวลาและหมายเลขเดียวกับทะเบียนประวัติหลัก</b> จำนวน <b>{len(df_repeated_display)} แห่ง</b> 
                เพื่อให้ผู้บริหารสามารถตรวจทานความต่อเนื่องของสถานการณ์ภัยพิกัดซ้ำซากที่เพิ่งเกิดขึ้นล่าสุดได้อย่างมีเอกภาพ
            </div>""", unsafe_allow_html=True
        )
        # 🌟 จัดตารางและคอลัมน์แสดงผลให้สวยงาม สบายตา อ่านง่ายสำหรับผู้บริหาร
        st.dataframe(df_repeated_display, use_container_width=True, hide_index=True)
    else:
        st.success("✅ จากการตรวจสอบ ไม่พบพิกัดที่เกิดเหตุซ้ำซากในระบบ ณ ขณะนี้")
else:
    st.info("💡 ข้อมูลรายละเอียดจุดเกิดเหตุซ้ำซากถูกซ่อนอยู่ (คลิกช่องด้านบนเพื่อเปิดแสดงตารางข้อมูลที่จัดเรียงตามเวลาปัจจุบัน)")

st.write("")

# ==========================================
# ส่วนที่ 3: กราฟ และ แผนที่ (ปรับขนาดตารางและการแสดงผลให้สมดุลสวยงาม)
# ==========================================
col_chart, col_map = st.columns([1.1, 1.1])

with col_chart:
    st.markdown('<p class="section-header">📊 ลำดับความเสี่ยงจำแนกตามแขวงบำรุงทาง</p>', unsafe_allow_html=True)
    if not df_base.empty:
        area_counts = df_base['พื้นที่'].value_counts().reset_index()
        area_counts.columns = ['พื้นที่', 'จำนวนเหตุการณ์']
        area_counts = area_counts.sort_values(by='จำนวนเหตุการณ์', ascending=True)
        
        fig = px.bar(
            area_counts, x='จำนวนเหตุการณ์', y='พื้นที่', orientation='h', text='จำนวนเหตุการณ์',
            color='จำนวนเหตุการณ์', color_continuous_scale=['#FECDD3', '#FB7185', '#E11D48'] # ปรับสีโทน Rose-Crimson นุ่มนวลระดับสากล
        ) 
        
        dynamic_height = max(300, len(area_counts) * 45)
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=30, t=10, b=10), xaxis=dict(showgrid=True, gridcolor='#E2E8F0'), 
            yaxis=dict(title=None, showgrid=False), font=dict(family="Sarabun", size=14),
            coloraxis_showscale=False
        )
        fig.update_traces(textposition='outside', textfont=dict(weight='bold', size=14))
        st.plotly_chart(fig, use_container_width=True, height=dynamic_height)

with col_map:
    st.markdown('<p class="section-header">🗺️ แผนที่พิกัดภาพรวมภูมิศาสตร์ภูมิภาค</p>', unsafe_allow_html=True)
    valid_coords = df_base.dropna(subset=['Latitude', 'Longitude'])
    if not valid_coords.empty:
        center_lat, center_lon = valid_coords["Latitude"].mean(), valid_coords["Longitude"].mean()
    else:
        center_lat, center_lon = 13.7367, 100.5231
        
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6, 
                   tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google Base Map')
    
    for idx, row in df_base.iterrows():
        if pd.notna(row['Latitude']) and pd.notna(row['Longitude']):
            is_repeated = "ซ้ำ" in str(row['หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)'])
            marker_color = "darkred" if is_repeated else "red" 
            
            popup_html = f"""
            <div style='font-family:Sarabun; font-size:15px; min-width:200px; padding:5px;'>
                <b style='color:#1E3A8A;'>{row['ชื่อเหตุอันตราย']}</b><br>
                <span><b>หน่วยงาน:</b> {row['พื้นที่']}</span><br>
                <hr style='margin:5px 0; border:0; border-top:1px solid #CBD5E1;'>
                <b>วันที่เกิดเหตุ:</b> {convert_to_thai_date(row['วัน/เดือน/ปี'])}
            </div>
            """
            folium.Marker(
                location=[row["Latitude"], row["Longitude"]], popup=folium.Popup(popup_html, max_width=300),
                icon=folium.Icon(color=marker_color, icon="warning-sign")
            ).add_to(m)

    st_folium(m, height=dynamic_height, use_container_width=True, returned_objects=[]) 

# ==========================================
# ส่วนที่ 4: ตารางทะเบียนประวัติข้อมูลเหตุการณ์ทั้งหมด (จัดแสดงผลระดับพรีเมียม)
# ==========================================
st.markdown('<div class="main-data-table">', unsafe_allow_html=True)
st.markdown('<p class="section-header">📋 ทะเบียนประวัติข้อมูลเหตุการณ์ทั้งหมด (เรียงลำดับเวลาปัจจุบัน ➡️ อดีต)</p>', unsafe_allow_html=True)
st.dataframe(df_display, use_container_width=True, hide_index=True)
st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# ส่วนที่ 5: ศูนย์จัดการข้อมูลระบบปฏิบัติการ (เรียงลำดับเดียวกับทะเบียนประวัติหลัก)
# ==========================================
st.markdown('<div class="no-print">', unsafe_allow_html=True)
st.markdown('<p class="section-header">⚙️ ศูนย์จัดการข้อมูลระบบปฏิบัติการ (สำหรับเจ้าหน้าที่บันทึกข้อมูล)</p>', unsafe_allow_html=True)

# ปุ่มสวิตช์สำหรับเลือกเปิดโหมดการจัดการข้อมูล
enable_management = st.checkbox("🔓 **คลิกเลือกช่องนี้เพื่อเข้าสู่โหมด เพิ่มเติม แก้ไข หรืออัปเดตข้อมูลระบบ**", value=False)

if enable_management:
    st.markdown('<div class="management-panel">', unsafe_allow_html=True)
    st.warning("⚠️ **โหมดแก้ไขข้อมูลเปิดอยู่:** โครงสร้างตารางจัดการข้อมูลนี้ถูกจัดเรียงตามลำดับประวัติหลัก (ปัจจุบัน ➡️ อดีต) เรียบร้อยแล้ว เพื่อให้ง่ายต่อการแก้ไขข้อมูลเหตุการณ์ล่าสุด")
    
    # 🌟 แก้ไขข้อ 2: ตาราง data_editor จะถูกบังคับให้จัดเรียงแบบเดียวกับทะเบียนประวัติหลัก (ปัจจุบัน ➡️ อดีต) 100%
    edited_df = st.data_editor(
        df_base, 
        use_container_width=True, num_rows="dynamic", height=250, key="editor"
    )

    if st.button("💾 ยืนยันการอัปเดตและบันทึกฐานข้อมูลร่วมกัน", use_container_width=True, type="primary"):
        edited_df.to_csv(DATA_FILE, index=False)
        st.success("✅ บันทึกข้อมูลลงสู่ฐานข้อมูลกลางเรียบร้อยแล้ว!")
        st.rerun()

    # ส่วนฟอร์มเพิ่มข้อมูลแบบแมนนวลและอัปโหลดไฟล์
    col_upload, col_manual = st.columns(2)
    with col_upload:
        with st.expander("📥 การนำเข้าข้อมูลผ่านไฟล์ (.csv, .xlsx)"):
            uploaded_file = st.file_uploader("ลากไฟล์ตารางข้อมูลมาวางที่นี่เพื่อผสานข้อมูล", type=["csv", "xlsx"])
            if uploaded_file is not None:
                if uploaded_file.name.endswith('.csv'): df_new = pd.read_csv(uploaded_file)
                elif uploaded_file.name.endswith('.xlsx'): df_new = pd.read_excel(uploaded_file)
                if st.button("➕ ยืนยันประมวลผลและผสานไฟล์", type="secondary"):
                    combined_df = pd.concat([df_base, df_new], ignore_index=True)
                    combined_df.to_csv(DATA_FILE, index=False)
                    st.success("ผสานข้อมูลร่วมกันสำเร็จ!")
                    st.rerun()

    with col_manual:
        with st.expander("📝 บันทึกรายงานเหตุการณ์ใหม่ด้วยตนเอง"):
            with st.form("realtime_input_form"):
                input_name = st.text_input("ชื่อเหตุอันตราย", placeholder="ตัวอย่างเช่น ชนโค ขบวน 108")
                input_area = st.text_input("พื้นที่", placeholder="ตัวอย่างเช่น แขวงฯ เพชรบุรี")
                input_km = st.text_input("ที่ กม.", placeholder="ตัวอย่างเช่น 150+200")
                c1, c2 = st.columns(2)
                with c1:
                    input_date = st.date_input("วัน/เดือน/ปี")
                    input_lat = st.number_input("Latitude (ละติจูด)", value=13.7367, format="%.5f")
                    input_impact = st.number_input("ผลกระทบขบวนล่าช้า (นาที)", min_value=0, step=1)
                with c2:
                    input_time = st.time_input("เวลา ที่เกิดเหตุ", value=datetime.time(12, 00))
                    input_lon = st.number_input("Longitude (ลองจิจูด)", value=100.5231, format="%.5f")
                    input_cost = st.text_input("ค่าใช้จ่าย", value="ไม่มีค่าใช้จ่าย")
                input_remark = st.text_input("หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)", placeholder="ระบุ 'ซ้ำ' หากเป็นพื้นที่เกิดเหตุซ้ำ")
                    
                if st.form_submit_button("💾 ยืนยันบันทึกข้อมูลเข้าระบบกลาง", use_container_width=True):
                    new_row = pd.DataFrame([{"ชื่อเหตุอันตราย": input_name, "พื้นที่": input_area, "ที่ กม.": input_km,
                        "วัน/เดือน/ปี": input_date.strftime("%Y-%m-%d"), "เวลา ที่เกิดเหตุ": input_time.strftime("%H:%M"), 
                        "ค่าใช้จ่าย": input_cost, "Latitude": input_lat, "Longitude": input_lon,
                        "ผลกระทบ(นาที)": input_impact, "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)": input_remark}])
                    combined_df = pd.concat([df_base, new_row], ignore_index=True)
                    combined_df.to_csv(DATA_FILE, index=False)
                    st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("🔒 **ระบบล็อกอยู่:** ศูนย์จัดการข้อมูลระบบปฏิบัติการถูกซ่อนไว้เพื่อความปลอดภัยเชิงสถิติ (คลิกเลือกช่องปุ่มด้านบนเพื่อแสดงตารางแก้ไขหรือเพิ่มข้อมูล)")
st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# ส่วนที่ 6: เครดิตส่วนท้ายระบบ
# ==========================================
st.markdown("""
    <div class="app-footer">
        <b>ระบบสารสนเทศความปลอดภัย :</b> วิศวกรกำกับการกองทางถาวร ศูนย์ทางถาวร ฝ่ายการช่างโยธา การรถไฟแห่งประเทศไทย<br>
        <span style="color: #94A3B8; font-size: 13px;">Executive Dashboard Version 1.17.5 (Shared Database Engine)</span>
    </div>
""", unsafe_allow_html=True)
