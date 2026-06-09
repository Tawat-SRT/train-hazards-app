import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import datetime
import plotly.express as px
import plotly.graph_objects as go
import os

# ==========================================
# CONFIG
# ==========================================
st.set_page_config(
    page_title="Train Hazards Executive Dashboard",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="collapsed"
)

DATA_FILE = "hazard_data_shared.csv"

THAI_MONTHS = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]

# ==========================================
# HELPERS
# ==========================================
def convert_to_thai_date(date_str):
    try:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                dt = datetime.datetime.strptime(str(date_str).strip(), fmt)
                return f"{dt.day} {THAI_MONTHS[dt.month - 1]} {dt.year + 543}"
            except ValueError:
                continue
        return str(date_str)
    except Exception:
        return str(date_str)


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

    required_cols = [
        "ชื่อเหตุอันตราย", "พื้นที่", "ที่ กม.", "วัน/เดือน/ปี", "เวลา ที่เกิดเหตุ",
        "ค่าใช้จ่าย", "Latitude", "Longitude", "ผลกระทบ(นาที)",
        "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = None

    df["พื้นที่"] = df["พื้นที่"].astype(str).str.strip()
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df["ผลกระทบ(นาที)"] = pd.to_numeric(df["ผลกระทบ(นาที)"], errors="coerce").fillna(0)

    df["temp_date"] = pd.to_datetime(df["วัน/เดือน/ปี"], errors="coerce")
    df = df.sort_values(by=["temp_date", "เวลา ที่เกิดเหตุ"], ascending=[False, False]).reset_index(drop=True)
    df = df.drop(columns=["temp_date"])

    return df


def get_thai_datetime_now():
    now = datetime.datetime.now()
    return f"{now.day} {THAI_MONTHS[now.month - 1]} {now.year + 543} เวลา {now.strftime('%H:%M')} น."


def build_display_table(df):
    display_df = df.copy()
    display_df["วัน/เดือน/ปี"] = display_df["วัน/เดือน/ปี"].apply(convert_to_thai_date)
    display_df.insert(0, "ลำดับที่", range(1, len(display_df) + 1))
    return display_df


def render_metric_card(title, value, subtitle, icon, accent="blue"):
    st.markdown(
        f"""
        <div class="metric-card {accent}">
            <div class="metric-top">
                <div class="metric-icon">{icon}</div>
                <div class="metric-title">{title}</div>
            </div>
            <div class="metric-value">{value}</div>
            <div class="metric-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ==========================================
# STYLES
# ==========================================
background_url = "[images.unsplash.com](https://images.unsplash.com/photo-1517420879524-86d64ac2f339?q=80&w=2000&auto=format&fit=crop)"

st.markdown(f"""
<style>
@import url('[fonts.googleapis.com](https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700;800&display=swap)');

html, body, [class*="css"], .stApp {{
    font-family: 'Sarabun', sans-serif !important;
}}

#MainMenu {{
    visibility: hidden;
}}
footer {{
    visibility: hidden;
}}
header {{
    visibility: hidden;
}}

.stApp {{
    background:
        radial-gradient(circle at top left, rgba(219,234,254,0.55) 0%, rgba(248,250,252,0.92) 35%, rgba(241,245,249,0.98) 100%),
        url("{background_url}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}

.block-container {{
    padding-top: 1.2rem;
    padding-bottom: 2rem;
    max-width: 1580px;
}}

.dashboard-hero {{
    background:
        linear-gradient(135deg, rgba(15,23,42,0.96) 0%, rgba(30,41,59,0.95) 35%, rgba(30,58,138,0.92) 70%, rgba(14,116,144,0.88) 100%);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 28px;
    padding: 34px 38px 28px 38px;
    color: white;
    box-shadow: 0 24px 50px rgba(15, 23, 42, 0.18);
    margin-bottom: 22px;
    position: relative;
    overflow: hidden;
}}

.dashboard-hero::after {{
    content: "";
    position: absolute;
    top: -30px;
    right: -30px;
    width: 220px;
    height: 220px;
    background: radial-gradient(circle, rgba(255,255,255,0.10) 0%, rgba(255,255,255,0.00) 70%);
    border-radius: 50%;
}}

.hero-title {{
    font-size: 36px;
    font-weight: 800;
    margin-bottom: 8px;
    line-height: 1.2;
    letter-spacing: -0.3px;
}}

.hero-subtitle {{
    font-size: 17px;
    color: rgba(255,255,255,0.84);
    margin-bottom: 14px;
}}

.hero-badge {{
    display: inline-block;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 999px;
    padding: 9px 15px;
    font-size: 14px;
    color: #E2E8F0;
    font-weight: 500;
}}

.section-wrap {{
    background: rgba(255,255,255,0.76);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(226,232,240,0.85);
    border-radius: 24px;
    padding: 18px 18px 16px 18px;
    box-shadow: 0 12px 32px rgba(15,23,42,0.05);
    margin-bottom: 18px;
}}

.section-title {{
    font-size: 22px;
    font-weight: 800;
    color: #0F172A;
    margin-top: 0;
    margin-bottom: 14px;
    letter-spacing: -0.2px;
}}

.metric-card {{
    background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
    border: 1px solid #E2E8F0;
    border-radius: 22px;
    padding: 18px;
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
    min-height: 148px;
    position: relative;
    overflow: hidden;
}}

.metric-card::before {{
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    height: 5px;
    width: 100%;
    background: linear-gradient(90deg, #2563EB, #38BDF8);
}}

.metric-card.red::before {{
    background: linear-gradient(90deg, #E11D48, #FB7185);
}}

.metric-card.amber::before {{
    background: linear-gradient(90deg, #D97706, #FBBF24);
}}

.metric-card.teal::before {{
    background: linear-gradient(90deg, #0F766E, #2DD4BF);
}}

.metric-top {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
}}

.metric-icon {{
    width: 44px;
    height: 44px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #DBEAFE 0%, #E0F2FE 100%);
    font-size: 20px;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.6);
}}

.metric-title {{
    font-size: 15px;
    font-weight: 700;
    color: #475569;
}}

.metric-value {{
    font-size: 34px;
    font-weight: 800;
    color: #0F172A;
    line-height: 1.1;
    margin-bottom: 6px;
}}

.metric-subtitle {{
    font-size: 13px;
    color: #64748B;
    line-height: 1.5;
}}

.alert-box {{
    background: linear-gradient(135deg, #FFF1F2 0%, #FFE4E6 100%);
    border: 1px solid #FECDD3;
    border-left: 6px solid #E11D48;
    border-radius: 18px;
    padding: 16px 18px;
    color: #881337;
    font-size: 15px;
    line-height: 1.7;
}}

.info-box {{
    background: linear-gradient(135deg, #EFF6FF 0%, #F0F9FF 100%);
    border: 1px solid #BFDBFE;
    border-left: 6px solid #2563EB;
    border-radius: 18px;
    padding: 16px 18px;
    color: #1E3A8A;
    font-size: 15px;
    line-height: 1.7;
}}

.management-panel {{
    background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
    border: 1px solid #E2E8F0;
    border-radius: 22px;
    padding: 22px;
    box-shadow: 0 10px 24px rgba(15,23,42,0.05);
}}

.stDataFrame, div[data-testid="stDataEditor"], .stPlotlyChart, .leaflet-container {{
    background: #FFFFFF !important;
    border-radius: 18px !important;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0 8px 24px rgba(15,23,42,0.05) !important;
    padding: 8px !important;
}}

div[data-testid="stMetric"] {{
    background: transparent !important;
    border: none !important;
}}

.stButton > button {{
    border-radius: 14px !important;
    font-weight: 700 !important;
    border: 1px solid #DCE7F3 !important;
    padding: 0.72rem 1rem !important;
    box-shadow: 0 6px 16px rgba(15,23,42,0.05) !important;
}}

.stDownloadButton > button {{
    border-radius: 14px !important;
    font-weight: 700 !important;
}}

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-baseweb="base-input"] {{
    border-radius: 12px !important;
}}

.app-footer {{
    text-align: center;
    padding: 28px 24px;
    margin-top: 40px;
    font-size: 14px;
    color: #64748B;
    border-top: 1px solid #CBD5E1;
}}

@media print {{
    @page {{
        size: A4 portrait;
        margin: 1cm;
    }}

    .stApp {{
        background: white !important;
    }}

    .stButton,
    .stExpander,
    div[data-testid="stDataEditor"],
    div[data-testid="stToolbar"],
    .app-footer,
    .no-print {{
        display: none !important;
    }}
}}
</style>
""", unsafe_allow_html=True)

# ==========================================
# LOAD DATA
# ==========================================
df_base = load_and_sort_data()
df_display = build_display_table(df_base)

repeated_cases_mask = df_base["หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"].astype(str).str.contains("ซ้ำ", na=False)
df_repeated = df_base[repeated_cases_mask].copy()
df_repeated_display = build_display_table(df_repeated)

delay_sum = int(df_base["ผลกระทบ(นาที)"].sum()) if not df_base.empty else 0
highest_risk_area = df_base["พื้นที่"].mode()[0] if not df_base.empty and not df_base["พื้นที่"].mode().empty else "-"
last_update = get_thai_datetime_now()

# ==========================================
# HERO HEADER
# ==========================================
st.markdown(f"""
<div class="dashboard-hero">
    <div class="hero-title">🚆 Executive Dashboard: สถานการณ์อุบัติเหตุรถไฟเฉี่ยวชนสัตว์</div>
    <div class="hero-subtitle">รายงานวิเคราะห์เชิงพื้นที่ สถิติ และจุดเฝ้าระวังสำคัญ สำหรับผู้บริหาร</div>
    <div class="hero-badge">อัปเดตล่าสุด: {last_update}</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# TOP ACTIONS
# ==========================================
action_col1, action_col2, action_col3 = st.columns([1.2, 1.2, 4])
with action_col1:
    if st.button("🖨️ ส่งออก PDF", use_container_width=True, type="primary"):
        st.info("กรุณากด Ctrl + P หรือ Cmd + P และเลือก Save as PDF")

with action_col2:
    if st.button("🔄 รีเฟรชข้อมูล", use_container_width=True):
        st.rerun()

# ==========================================
# KPI SECTION
# ==========================================
st.markdown('<div class="section-wrap">', unsafe_allow_html=True)
st.markdown('<div class="section-title">ภาพรวมตัวชี้วัดสำคัญ</div>', unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)

with k1:
    render_metric_card(
        "เหตุการณ์สะสม",
        f"{len(df_base)}",
        "จำนวนเหตุการณ์ทั้งหมดในระบบ",
        "🚨",
        "red"
    )

with k2:
    render_metric_card(
        "พิกัดเกิดเหตุซ้ำ",
        f"{len(df_repeated_display)}",
        "จุดเฝ้าระวังพิเศษในระยะ ± 3 Km",
        "📍",
        "amber"
    )

with k3:
    render_metric_card(
        "พื้นที่วิกฤตสูงสุด",
        highest_risk_area,
        "พื้นที่ที่พบเหตุบ่อยที่สุด",
        "⚠️",
        "blue"
    )

with k4:
    render_metric_card(
        "ความล่าช้ารวม",
        f"{delay_sum} นาที",
        "ผลกระทบรวมต่อการเดินขบวน",
        "⏱️",
        "teal"
    )

st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# REPEATED ALERTS
# ==========================================
st.markdown('<div class="section-wrap">', unsafe_allow_html=True)
st.markdown('<div class="section-title">พื้นที่เฝ้าระวังพิเศษ</div>', unsafe_allow_html=True)

if not df_repeated_display.empty:
    st.markdown(
        f"""
        <div class="alert-box">
            <b>รายงานเตือนเชิงบริหาร:</b> ขณะนี้ระบบพบ <b>{len(df_repeated_display)} พิกัด</b>
            ที่มีลักษณะเกิดเหตุซ้ำในรัศมีใกล้เคียงกัน ซึ่งควรได้รับการติดตามเชิงมาตรการ
            ทั้งด้านการป้องกัน การเฝ้าระวัง และการบริหารความเสี่ยงเชิงพื้นที่อย่างต่อเนื่อง
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown(
        """
        <div class="info-box">
            <b>สถานะปัจจุบัน:</b> ยังไม่พบพิกัดเกิดเหตุซ้ำซากในระบบ ณ เวลานี้
        </div>
        """,
        unsafe_allow_html=True
    )

show_repeated = st.toggle("แสดงรายละเอียดจุดเกิดเหตุซ้ำ", value=True)

if show_repeated and not df_repeated_display.empty:
    st.dataframe(df_repeated_display, use_container_width=True, hide_index=True)

st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# CHART + MAP
# ==========================================
left_col, right_col = st.columns([1.05, 1.15])

with left_col:
    st.markdown('<div class="section-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">การกระจายเหตุการณ์ตามพื้นที่</div>', unsafe_allow_html=True)

    if not df_base.empty:
        area_counts = df_base["พื้นที่"].value_counts().reset_index()
        area_counts.columns = ["พื้นที่", "จำนวนเหตุการณ์"]
        area_counts = area_counts.sort_values(by="จำนวนเหตุการณ์", ascending=True)

        dynamic_height = max(360, len(area_counts) * 48)

        fig = px.bar(
            area_counts,
            x="จำนวนเหตุการณ์",
            y="พื้นที่",
            orientation="h",
            text="จำนวนเหตุการณ์",
            color="จำนวนเหตุการณ์",
            color="จำนวนเหตุการณ์",
            color_continuous_scale=["#DBEAFE", "#60A5FA", "#1D4ED8"]
        )

        fig.update_layout(
            height=dynamic_height,
            margin=dict(l=10, r=20, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Sarabun", size=14, color="#0F172A"),
            coloraxis_showscale=False,
            xaxis=dict(
                title=None,
                showgrid=True,
                gridcolor="#E2E8F0",
                zeroline=False
            ),
            yaxis=dict(
                title=None,
                showgrid=False
            )
        )
        fig.update_traces(
            textposition="outside",
            marker_line_width=0,
            hovertemplate="<b>%{y}</b><br>จำนวนเหตุการณ์: %{x}<extra></extra>"
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ไม่พบข้อมูลสำหรับสร้างกราฟ")

    st.markdown('</div>', unsafe_allow_html=True)

with right_col:
    st.markdown('<div class="section-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">แผนที่ภาพรวมเชิงพื้นที่</div>', unsafe_allow_html=True)

    valid_coords = df_base.dropna(subset=["Latitude", "Longitude"])
    if not valid_coords.empty:
        center_lat = valid_coords["Latitude"].mean()
        center_lon = valid_coords["Longitude"].mean()
    else:
        center_lat, center_lon = 13.7367, 100.5231

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=6,
        tiles="CartoDB positron"
    )

    for _, row in df_base.iterrows():
        if pd.notna(row["Latitude"]) and pd.notna(row["Longitude"]):
            is_repeated = "ซ้ำ" in str(row["หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"])
            color = "#B91C1C" if is_repeated else "#2563EB"

            popup_html = f"""
            <div style="font-family:Sarabun; min-width:220px; padding:6px 4px;">
                <div style="font-size:15px; font-weight:800; color:#0F172A; margin-bottom:6px;">
                    {row["ชื่อเหตุอันตราย"]}
                </div>
                <div style="font-size:13px; color:#334155; line-height:1.7;">
                    <b>พื้นที่:</b> {row["พื้นที่"]}<br>
                    <b>กม.:</b> {row["ที่ กม."]}<br>
                    <b>วันที่:</b> {convert_to_thai_date(row["วัน/เดือน/ปี"])}<br>
                    <b>ผลกระทบ:</b> {int(pd.to_numeric(row["ผลกระทบ(นาที)"], errors="coerce") if pd.notna(row["ผลกระทบ(นาที)"]) else 0)} นาที
                </div>
            </div>
            """

            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=8 if is_repeated else 6,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.88,
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(m)

    st_folium(
        m,
        height=max(380, len(valid_coords) * 20 + 250),
        use_container_width=True,
        returned_objects=[]
    )

    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# MAIN TABLE
# ==========================================
st.markdown('<div class="section-wrap">', unsafe_allow_html=True)
st.markdown('<div class="section-title">ทะเบียนประวัติข้อมูลเหตุการณ์ทั้งหมด</div>', unsafe_allow_html=True)
st.dataframe(df_display, use_container_width=True, hide_index=True)
st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# MANAGEMENT
# ==========================================
st.markdown('<div class="no-print">', unsafe_allow_html=True)
st.markdown('<div class="section-wrap">', unsafe_allow_html=True)
st.markdown('<div class="section-title">ศูนย์จัดการข้อมูลระบบปฏิบัติการ</div>', unsafe_allow_html=True)

enable_management = st.checkbox("เปิดโหมดจัดการข้อมูล", value=False)

if enable_management:
    st.markdown('<div class="management-panel">', unsafe_allow_html=True)
    st.warning("โหมดแก้ไขข้อมูลเปิดอยู่ กรุณาตรวจสอบความถูกต้องก่อนบันทึกทุกครั้ง")

    edited_df = st.data_editor(
        df_base,
        use_container_width=True,
        num_rows="dynamic",
        height=300,
        key="editor"
    )

    if st.button("💾 บันทึกข้อมูลที่แก้ไข", use_container_width=True, type="primary"):
        edited_df.to_csv(DATA_FILE, index=False)
        st.success("บันทึกข้อมูลเรียบร้อยแล้ว")
        st.rerun()

    col_upload, col_manual = st.columns(2)

    with col_upload:
        with st.expander("📥 นำเข้าข้อมูลจากไฟล์"):
            uploaded_file = st.file_uploader("อัปโหลดไฟล์ .csv หรือ .xlsx", type=["csv", "xlsx"])
            if uploaded_file is not None:
                try:
                    if uploaded_file.name.endswith(".csv"):
                        df_new = pd.read_csv(uploaded_file)
                    else:
                        df_new = pd.read_excel(uploaded_file)

                    st.dataframe(df_new.head(), use_container_width=True, hide_index=True)

                    if st.button("➕ ผสานข้อมูลเข้าระบบ", type="secondary", use_container_width=True):
                        combined_df = pd.concat([df_base, df_new], ignore_index=True)
                        combined_df.to_csv(DATA_FILE, index=False)
                        st.success("ผสานข้อมูลสำเร็จ")
                        st.rerun()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")

    with col_manual:
        with st.expander("📝 เพิ่มเหตุการณ์ใหม่"):
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
                    input_time = st.time_input("เวลา ที่เกิดเหตุ", value=datetime.time(12, 0))
                    input_lon = st.number_input("Longitude", value=100.5231, format="%.5f")
                    input_cost = st.text_input("ค่าใช้จ่าย", value="ไม่มีค่าใช้จ่าย")

                input_remark = st.text_input("หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)")

                if st.form_submit_button("💾 บันทึกเหตุการณ์ใหม่", use_container_width=True):
                    new_row = pd.DataFrame([{
                        "ชื่อเหตุอันตราย": input_name,
                        "พื้นที่": input_area,
                        "ที่ กม.": input_km,
                        "วัน/เดือน/ปี": input_date.strftime("%Y-%m-%d"),
                        "เวลา ที่เกิดเหตุ": input_time.strftime("%H:%M"),
                        "ค่าใช้จ่าย": input_cost,
                        "Latitude": input_lat,
                        "Longitude": input_lon,
                        "ผลกระทบ(นาที)": input_impact,
                        "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)": input_remark
                    }])

                    combined_df = pd.concat([df_base, new_row], ignore_index=True)
                    combined_df.to_csv(DATA_FILE, index=False)
                    st.success("เพิ่มข้อมูลใหม่เรียบร้อยแล้ว")
                    st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("ระบบจัดการข้อมูลถูกซ่อนอยู่เพื่อความปลอดภัยของข้อมูล")

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# FOOTER
# ==========================================
st.markdown("""
<div class="app-footer">
    <b>ระบบสารสนเทศความปลอดภัย</b><br>
    วิศวกรกำกับการกองทางถาวร ศูนย์ทางถาวร ฝ่ายการช่างโยธา การรถไฟแห่งประเทศไทย<br>
    <span style="color:#94A3B8;">Executive Dashboard - Modern Premium UI</span>
</div>
""", unsafe_allow_html=True)
