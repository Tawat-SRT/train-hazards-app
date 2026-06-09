import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import datetime
import plotly.express as px
import os

# 1. ตั้งค่าหน้าจอแบบกว้างพิเศษเพื่อความภูมิฐาน
st.set_page_config(page_title="Train Hazards Executive Dashboard V1.17.2", page_icon="🚆", layout="wide")

# ฐานข้อมูลกลาง (Shared Database สำหรับทุกคน)
DATA_FILE = "hazard_data_shared.csv"

# ฟังก์ชันแปลงวันที่ให้เป็น วัน เดือน ปี พ.ศ. ไทย สำหรับแสดงผล
def convert_to_thai_date(date_str):
    try:
        # พยายาม parse วันที่รองรับหลายฟอร์แมต
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
            try:
                dt = datetime.datetime.strptime(str(date_str).strip(), fmt)
                break
            except ValueError:
                continue
        else:
            return date_str # หากแปลงไม่ได้ให้ส่งค่าเดิมกลับไป
            
        thai_months = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
        return f"{dt.day} {thai_months[dt.month-1]} {dt.year + 543}"
    except:
        return date_str

# ฟังก์ชันโหลดและจัดระเบียบข้อมูล (Sort ล่าสุด -> เก่าสุด)
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
    
    # แปลงคอลัมน์วันที่ให้เป็น datetime เพื่อใช้ในการ Sort ลำดับ
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            df['temp_date'] = pd.to_datetime(df['วัน/เดือน/ปี'], format=fmt)
            break
        except:
            continue
    else:
        df['temp_date'] = pd.to_datetime(df['วัน/เดือน/ปี'], errors='coerce')
        
    # เรียงลำดับจาก ล่าสุด ไปหา เก่าสุด
    df = df.sort_values(by='temp_date', ascending=False).drop(columns=['temp_date'])
    return df

# --- 🎨 ตกแต่ง UI ระดับ Premium (Corporate & Executive Theme) ---
background_url = "https://images.unsplash.com/photo-1474487548417-781cb71495f3?q=80&w=2000&auto=format&fit=crop"

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"], .stApp {{ font-family: 'Sarabun', sans-serif !important; }}
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}
    
    .stApp {{ 
        background-image: linear-gradient(rgba(244, 246, 249, 0.90), rgba(244, 246, 249, 0.97)), url("{background_url}");
        background-size: cover; background-position: center; background-attachment: fixed;
    }}
    
    /* สไตล์กล่อง KPI แบบผู้บริหาร */
    div[data-testid="metric-container"] {{
        background: rgb(255,255,255);
        background: linear-gradient(135deg, rgba(255,255,255,1) 0%, rgba(248,250,252,1) 100%);
        border-radius: 14px; padding: 18px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.05), 0 8px 10px -6px rgba(15, 23, 42, 0.05);
        border: 1px solid rgba(226, 232, 240, 0.8);
        border-top: 4px solid #1E3A8A;
    }}
    div[data-testid="stMetricValue"] {{ font-size: 34px !important; font-weight: 800 !important; color: #1E3A8A !important; }}
    div[data-testid="stMetricLabel"] {{ font-size: 16px !important; font-weight: 600 !important; color: #475569 !important; text-transform: uppercase; letter-spacing: 0.5px; }}
    
    /* หัวข้อและป้ายกำกับ */
    .dashboard-title {{ font-size: 36px; font-weight: 800; color: #0F172A; margin-bottom: 0px; letter-spacing: -0.5px; }}
    .dashboard-subtitle {{ font-size: 18px; color: #475569; margin-bottom: 15px; font-weight: 400; }}
    .section-header {{ font-size: 22px; font-weight: 700; color: #1E3A8A; margin-top: 20px; border-bottom: 2px solid #E2E8F0; padding-bottom: 8px; margin-bottom: 12px; }}
    
    /* คอมโพเนนต์การแสดงผล */
    .stDataFrame, .stPlotlyChart, div[data-testid="stDataEditor"], .leaflet-container {{ 
        background-color: #FFFFFF !important; border-radius: 14px !important; padding: 12px; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
        border: 1px solid #E2E8F0 !important;
    }}
    
    .update-date {{ text-align: right; font-size: 16px; color: #64748B; font-weight: 500; margin-top: 15px; }}
    .danger-box {{ background-color: #FFF5F5; border-left: 6px solid #E11D48; padding: 16px; border-radius: 10px; margin-bottom: 15px; color: #9F1239; font-size: 16px; }}
    
    /* ปรับแต่งปุ่มกดสไตล์พรีเมียม */
    .sub-toggle-btn {{
        background-color: #FFFFFF; border: 1px solid #CBD5E1; padding: 12px 20px; 
        border-radius: 8px; font-weight: 600; color: #334155; display: inline-block; margin-bottom: 15px;
    }}

    @media print {{
        @page {{ size: A4 portrait; margin: 1cm; }}
        .stApp {{ background-image: none !important; background-color: white !important; }}
        .stButton, .stExpander, div[data-testid="stDataEditor"], div[data-testid="stToolbar"], .app-footer {{ display: none !important; }}
        * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
        .main-data-table {{ page-break-before: always !important; margin-top: 20px; }}
    }}
    
    .app-footer {{ text-align: center; padding: 25px; margin-top: 50px; font-size: 15px; color: #64748B; border-top: 1px solid #E2E8F0; }}
    </style>
""", unsafe_allow_html=True)

# ระบบวันที่อัปเดตภาษาไทยแบบเป็นทางการ
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
        st.info("💡 **คำแนะนำผู้บริหาร:** กดปุ่ม **Ctrl + P** (Windows) หรือ **Cmd + P** (Mac) แล้วเลือก 'Save as PDF' เพื่อพิมพ์รายงานจัดหน้าขนาด A4 ทันที")

# โหลดข้อมูลและจัดลำดับล่าสุดขึ้นก่อน
df = load_and_sort_data()
df['พื้นที่'] = df['พื้นที่'].astype(str).str.strip()
df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')

# เตรียมข้อมูลสำหรับตารางผู้บริหาร (แสดงเป็น ปี พ.ศ. ไทย)
df_display = df.copy()
df_display['วัน/เดือน/ปี'] = df_display['วัน/เดือน/ปี'].apply(convert_to_thai_date)

# ==========================================
# ส่วนที่ 1: สรุปสถิติตัวเลขสำคัญ (KPIs)
# ==========================================
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
delay_sum = pd.to_numeric(df['ผลกระทบ(นาที)'], errors='coerce').fillna(0).sum()

# คัดกรองข้อมูลจุดซ้ำ
repeated_cases_mask = df['หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)'].astype(str).str.contains('ซ้ำ', na=False)
df_repeated = df_display[repeated_cases_mask]

kpi1.metric("🚨 เหตุการณ์สะสม", f"{len(df)} ครั้ง")
kpi2.metric("⚠️ พิกัดเกิดเหตุซ้ำ (± 3 Km)", f"{len(df_repeated)} แห่ง")
kpi3.metric("📍 พื้นที่วิกฤตสูงสุด", df['พื้นที่'].mode()[0] if not df.empty else "-")
kpi4.metric("⏱️ ความล่าช้ารวมขบวน", f"{int(delay_sum)} นาที")

st.write("") 

# ==========================================
# 🌟 ข้อ 1: ปุ่มกดแสดงข้อมูลจุดเกิดเหตุซ้ำ (Toggle Button)
# ==========================================
st.markdown('<p class="section-header">❌ พื้นที่เฝ้าระวังพิเศษ (พิกัดที่เกิดเหตุซ้ำซาก)</p>', unsafe_allow_html=True)

# ใช้ st.checkbox ตกแต่งเพื่อเป็นสวิตช์เปิดปิดข้อมูลจุดซ้ำ
show_repeated = st.checkbox("🔍 คลิกที่นี่ เพื่อเปิด/ปิด ตารางแสดงรายละเอียดจุดเกิดเหตุซ้ำสะสม", value=False)

if show_repeated:
    if not df_repeated.empty:
        st.markdown(
            f"""<div class="danger-box">
                <b>📌 รายงานด่วนเชิงนโยบาย:</b> ปัจจุบันพบจุดเกิดอุบัติเหตุซ้ำซากในรัศมี 3 กิโลเมตร จำนวน <b>{len(df_repeated)} พิกัด</b> 
                ฝ่ายการช่างโยธาเสนอแนะให้กำหนดมาตรการเร่งด่วนในการสร้างรั้วกั้นเขตกรรรมสิทธิ์หรือทำเนินดินเสริมความปลอดภัยร่วมกับชุมชนโดยรอบ
            </div>""", unsafe_allow_html=True
        )
        st.dataframe(
            df_repeated[["ชื่อเหตุอันตราย", "พื้นที่", "ที่ กม.", "วัน/เดือน/ปี", "เวลา ที่เกิดเหตุ", "ผลกระทบ(นาที)", "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"]], 
            use_container_width=True, hide_index=True
        )
    else:
        st.success("✅ จากการตรวจสอบ ไม่พบพิกัดที่เกิดเหตุซ้ำซากในระบบ ณ ขณะนี้")
else:
    st.info("💡 ข้อมูลรายละเอียดจุดเกิดเหตุซ้ำซากถูกซ่อนอยู่ (คลิกที่ช่องทำเครื่องหมายด้านบนเพื่อเปิดแสดงข้อมูล)")

st.write("")

# ==========================================
# 🌟 ข้อ 3 & 4: ปรับปรุงกราฟให้ดูง่ายกรณีมีหลายแขวง + แผนที่ที่สวยงาม
# ==========================================
col_chart, col_map = st.columns([1.1, 1.1])

with col_chart:
    st.markdown('<p class="section-header">📊 ลำดับความเสี่ยงจำแนกตามแขวงบำรุงทาง</p>', unsafe_allow_html=True)
    if not df.empty:
        # นับจำนวนและจัดเรียงจากมากไปน้อยที่สุดเสมอ
        area_counts = df['พื้นที่'].value_counts().reset_index()
        area_counts.columns = ['พื้นที่', 'จำนวนเหตุการณ์']
        area_counts = area_counts.sort_values(by='จำนวนเหตุการณ์', ascending=True) # Ascending true เพื่อให้แท่งด้านบนสูงสุดเมื่อทำกราฟแนวนอน
        
        # 💡 ปรับปรุงกราฟ: ใช้ Color scale (ไล่สีโทนเข้ม-อ่อนตามระดับความวิกฤต) เพื่อรองรับกรณีมีหลายแขวงให้ดูง่ายขึ้น
        fig = px.bar(
            area_counts, x='จำนวนเหตุการณ์', y='พื้นที่', orientation='h', text='จำนวนเหตุการณ์',
            color='จำนวนเหตุการณ์', color_continuous_scale=['#FCA5A5', '#EF4444', '#991B1B'], # ไล่ระดับสีแดงเพื่อบอกความเสี่ยง
            labels={'จำนวนเหตุการณ์': 'จำนวนครั้ง'}
        ) 
        
        # 💡 คำนวณความสูงกราฟแบบไดนามิก: ยิ่งแขวงเยอะ กราฟจะยืดสูงขึ้นตามอัตโนมัติเพื่อไม่ให้ตัวหนังสือทับกัน
        dynamic_height = max(300, len(area_counts) * 45)
        
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=30, t=10, b=10), 
            xaxis=dict(showgrid=True, gridcolor='#E2E8F0', title="จำนวนครั้งที่เกิดเหตุ"), 
            yaxis=dict(title=None, showgrid=False), 
            font=dict(family="Sarabun", size=14, color="#1E293B"),
            coloraxis_showscale=False # ซ่อนแถบแถบสีด้านข้างเพื่อให้หน้าจอสะอาด
        )
        fig.update_traces(textposition='outside', textfont=dict(weight='bold', size=14))
        st.plotly_chart(fig, use_container_width=True, height=dynamic_height)

with col_map:
    st.markdown('<p class="section-header">🗺️ แผนที่พิกัดภาพรวมภูมิศาสตร์ภูมิภาค</p>', unsafe_allow_html=True)
    valid_coords = df.dropna(subset=['Latitude', 'Longitude'])
    if not valid_coords.empty:
        center_lat, center_lon = valid_coords["Latitude"].mean(), valid_coords["Longitude"].mean()
    else:
        center_lat, center_lon = 13.7367, 100.5231
        
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6, 
                   tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', attr='Google Base Map')
    
    for idx, row in df.iterrows():
        if pd.notna(row['Latitude']) and pd.notna(row['Longitude']):
            is_repeated = "ซ้ำ" in str(row['หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)'])
            # 💡 ใช้สีแดงเข้มพิเศษ (Darkred) สำหรับจุดซ้ำให้เด่นชัดตัดกับจุดปกติที่เป็นสีแดงทั่วไป
            marker_color = "darkred" if is_repeated else "red" 
            
            popup_html = f"""
            <div style='font-family:Sarabun; font-size:15px; min-width:200px; padding:5px;'>
                <b style='color:#1E3A8A;'>{row['ชื่อเหตุอันตราย']}</b><br>
                <span style='color:#475569;'><b>หน่วยงาน:</b> {row['พื้นที่']}</span><br>
                <span style='color:#475569;'><b>พิกัด กม.:</b> {row['ที่ กม.']}</span><br>
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
# 🌟 ข้อ 2: ตารางแสดงข้อมูลรวม (เรียงลำดับจาก ล่าสุด -> เก่าสุด และปี พ.ศ. ไทย)
# ==========================================
st.markdown('<div class="main-data-table">', unsafe_allow_html=True)
st.markdown('<p class="section-header">📋 ทะเบียนประวัติข้อมูลเหตุการณ์ทั้งหมด (เรียงลำดับล่าสุด)</p>', unsafe_allow_html=True)
st.dataframe(df_display, use_container_width=True, hide_index=True)
st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# ส่วนที่ 5: ระบบจัดการข้อมูลสำหรับผู้ใช้ (ซ่อนเมื่อพิมพ์รายงานเป็น PDF)
# ==========================================
st.markdown('<p class="section-header">✏️ ศูนย์จัดการข้อมูลระบบปฏิบัติการ (ซ่อนอัตโนมัติในรายงาน PDF)</p>', unsafe_allow_html=True)

edited_df = st.data_editor(
    df, # แก้ไขข้อมูลบนฐานข้อมูลดิบโดยตรง เพื่อรักษารูปแบบเวลาดั้งเดิมในไฟล์ CSV สำหรับคำนวณ
    use_container_width=True, num_rows="dynamic", height=220, key="editor"
)

# ปุ่มเซฟข้อมูลพร้อมระบบ Real-time รีเฟรชทันที
if st.button("💾 ยืนยันการอัปเดตและบันทึกฐานข้อมูลร่วมกัน", use_container_width=True):
    edited_df.to_csv(DATA_FILE, index=False)
    st.success("✅ บันทึกข้อมูลลงสู่ระบบเรียบร้อย! ข้อมูลสรุปและกราฟวิเคราะห์ได้อัปเดตแบบ Real-time บนหน้าจอของผู้ใช้งานทุกคน")
    st.rerun()

# ฟอร์มการนำเข้าข้อมูล
col_upload, col_manual = st.columns(2)
with col_upload:
    with st.expander("📥 1. การนำเข้าข้อมูลผ่านไฟล์ (.csv, .xlsx)"):
        uploaded_file = st.file_uploader("ลากไฟล์ตารางข้อมูลมาวางที่นี่เพื่อผสานข้อมูล", type=["csv", "xlsx"])
        if uploaded_file is not None:
            if uploaded_file.name.endswith('.csv'): df_new = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith('.xlsx'): df_new = pd.read_excel(uploaded_file)
            if st.button("➕ ยืนยันประมวลผลและผสานไฟล์", type="primary"):
                combined_df = pd.concat([df, df_new], ignore_index=True)
                combined_df.to_csv(DATA_FILE, index=False)
                st.success("ผสานข้อมูลร่วมกันสำเร็จ!")
                st.rerun()

with col_manual:
    with st.expander("📝 2. บันทึกรายงานเหตุการณ์ใหม่ด้วยตนเอง"):
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
                
            if st.form_submit_button("💾 ยืนยันบันทึกข้อมูลเข้าระบบกลาง", type="primary", use_container_width=True):
                new_row = pd.DataFrame([{"ชื่อเหตุอันตราย": input_name, "พื้นที่": input_area, "ที่ กม.": input_km,
                    "วัน/เดือน/ปี": input_date.strftime("%Y-%m-%d"), "เวลา ที่เกิดเหตุ": input_time.strftime("%H:%M"), 
                    "ค่าใช้จ่าย": input_cost, "Latitude": input_lat, "Longitude": input_lon,
                    "ผลกระทบ(นาที)": input_impact, "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)": input_remark}])
                combined_df = pd.concat([df, new_row], ignore_index=True)
                combined_df.to_csv(DATA_FILE, index=False)
                st.rerun()

# ==========================================
# ส่วนที่ 6: เครดิตส่วนท้ายระบบ
# ==========================================
st.markdown("""
    <div class="app-footer">
        <b>ระบบสารสนเทศความปลอดภัย :</b> วิศวกรกำกับการกองทางถาวร ศูนย์ทางถาวร ฝ่ายการช่างโยธา การรถไฟแห่งประเทศไทย<br>
        <span style="color: #94A3B8; font-size: 13px;">Executive Dashboard Version 1.17.2 (Shared Database Engine)</span>
    </div>
""", unsafe_allow_html=True)
