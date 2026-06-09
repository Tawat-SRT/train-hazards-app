import datetime
import os
from typing import Iterable, Optional

import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

# ==========================================
# CONFIG
# ==========================================
st.set_page_config(
    page_title="Train Hazards Executive Dashboard",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DATA_FILE = "hazard_data_shared.csv"

THAI_MONTHS = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]

REQUIRED_COLS = [
    "ชื่อเหตุอันตราย",
    "พื้นที่",
    "ที่ กม.",
    "วัน/เดือน/ปี",
    "เวลา ที่เกิดเหตุ",
    "ค่าใช้จ่าย",
    "Latitude",
    "Longitude",
    "ผลกระทบ(นาที)",
    "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)",
]

# ==========================================
# DATA HELPERS
# ==========================================
def parse_date(value) -> pd.Timestamp:
    """Parse common Thai/ISO date strings safely."""
    if pd.isna(value):
        return pd.NaT

    value = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return pd.Timestamp(datetime.datetime.strptime(value, fmt))
        except ValueError:
            continue

    return pd.to_datetime(value, errors="coerce", dayfirst=True)


def convert_to_thai_date(date_value) -> str:
    dt = parse_date(date_value)
    if pd.isna(dt):
        return "-" if pd.isna(date_value) or str(date_value).strip() == "" else str(date_value)
    return f"{dt.day} {THAI_MONTHS[dt.month - 1]} {dt.year + 543}"


def get_thai_datetime_now() -> str:
    now = datetime.datetime.now()
    return f"{now.day} {THAI_MONTHS[now.month - 1]} {now.year + 543} เวลา {now:%H:%M} น."


def sample_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ชื่อเหตุอันตราย": [
                "ชนโค ท่าพระ-ขอนแก่น",
                "เฉี่ยวชนกระบือ บ้านช่อง-หินซ้อน",
                "ชนโค หนองน้ำขุ่น-บ้านใหม่",
                "ชนโค ท่าพระ-ขอนแก่น",
            ],
            "พื้นที่": ["แขวงฯ ขอนแก่น", "แขวงฯ ฉะเชิงเทรา", "แขวงฯ นครราชสีมา", "แขวงฯ ขอนแก่น"],
            "ที่ กม.": ["345+100", "150+200", "250+500", "346+200"],
            "วัน/เดือน/ปี": ["2024-02-15", "2024-03-11", "2024-04-05", "2024-05-21"],
            "เวลา ที่เกิดเหตุ": ["10:30", "14:45", "08:15", "19:20"],
            "ค่าใช้จ่าย": ["ไม่มีค่าใช้จ่าย", "มีค่าใช้จ่าย 5,000 บาท", "ไม่มีค่าใช้จ่าย", "ไม่มีค่าใช้จ่าย"],
            "Latitude": [16.3650, 14.6540, 14.9722, 16.3702],
            "Longitude": [102.8340, 101.1230, 102.0833, 102.8392],
            "ผลกระทบ(นาที)": [15, 30, 10, 22],
            "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)": ["-", "ซ้ำ ± 3 Km", "-", "ซ้ำ ± 3 Km"],
        }
    )


@st.cache_data(show_spinner=False)
def load_and_sort_data(path: str) -> pd.DataFrame:
    if os.path.exists(path):
        df = pd.read_csv(path)
    else:
        df = sample_data()
        df.to_csv(path, index=False)

    for col in REQUIRED_COLS:
        if col not in df.columns:
            df[col] = None

    df = df[REQUIRED_COLS].copy()
    df["พื้นที่"] = df["พื้นที่"].fillna("ไม่ระบุพื้นที่").astype(str).str.strip()
    df["ชื่อเหตุอันตราย"] = df["ชื่อเหตุอันตราย"].fillna("ไม่ระบุชื่อเหตุ").astype(str).str.strip()
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df["ผลกระทบ(นาที)"] = pd.to_numeric(df["ผลกระทบ(นาที)"], errors="coerce").fillna(0).astype(int)
    df["วันที่"] = df["วัน/เดือน/ปี"].apply(parse_date)
    df["เวลา_sort"] = pd.to_datetime(df["เวลา ที่เกิดเหตุ"], errors="coerce").dt.time
    df = df.sort_values(by=["วันที่", "เวลา ที่เกิดเหตุ"], ascending=[False, False]).reset_index(drop=True)
    return df.drop(columns=["เวลา_sort"])


def build_display_table(df: pd.DataFrame) -> pd.DataFrame:
    display_df = df.drop(columns=["วันที่"], errors="ignore").copy()
    display_df["วัน/เดือน/ปี"] = display_df["วัน/เดือน/ปี"].apply(convert_to_thai_date)
    display_df.insert(0, "ลำดับที่", range(1, len(display_df) + 1))
    return display_df


def money_to_number(value) -> float:
    if pd.isna(value):
        return 0.0
    text = str(value).replace(",", "")
    digits = "".join(ch for ch in text if ch.isdigit() or ch == ".")
    try:
        return float(digits) if digits else 0.0
    except ValueError:
        return 0.0


def make_download_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")

# ==========================================
# STYLE
# ==========================================
def inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700;800&display=swap');

        :root {
            --ink: #0f172a;
            --muted: #64748b;
            --line: rgba(148,163,184,.25);
            --panel: rgba(255,255,255,.88);
            --panel-strong: rgba(255,255,255,.96);
            --blue: #2563eb;
            --cyan: #0891b2;
            --red: #e11d48;
            --amber: #f59e0b;
            --green: #10b981;
        }

        html, body, [class*="css"], .stApp {
            font-family: 'Sarabun', sans-serif !important;
        }

        #MainMenu, footer, header {visibility: hidden;}

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(37,99,235,.18), transparent 28%),
                radial-gradient(circle at top right, rgba(8,145,178,.16), transparent 24%),
                linear-gradient(180deg, #f8fafc 0%, #eef2ff 44%, #f8fafc 100%);
        }

        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
            max-width: 1680px;
        }

        .hero {
            position: relative;
            overflow: hidden;
            color: white;
            border-radius: 30px;
            padding: 32px 36px;
            margin-bottom: 18px;
            border: 1px solid rgba(255,255,255,.14);
            background:
                linear-gradient(135deg, rgba(15,23,42,.98) 0%, rgba(30,64,175,.95) 48%, rgba(14,116,144,.92) 100%);
            box-shadow: 0 24px 60px rgba(15,23,42,.22);
        }

        .hero:after {
            content: "";
            position: absolute;
            right: -80px;
            top: -80px;
            width: 280px;
            height: 280px;
            border-radius: 50%;
            background: rgba(255,255,255,.10);
        }

        .hero-grid {
            position: relative;
            z-index: 2;
            display: grid;
            grid-template-columns: 1.7fr .9fr;
            gap: 22px;
            align-items: center;
        }

        .eyebrow {
            display: inline-flex;
            gap: 8px;
            align-items: center;
            background: rgba(255,255,255,.13);
            border: 1px solid rgba(255,255,255,.18);
            border-radius: 999px;
            padding: 7px 13px;
            color: #dbeafe;
            font-size: 14px;
            font-weight: 700;
            margin-bottom: 12px;
        }

        .hero-title {
            font-size: clamp(28px, 3vw, 44px);
            font-weight: 800;
            line-height: 1.16;
            margin: 0 0 8px 0;
            letter-spacing: -.4px;
        }

        .hero-subtitle {
            color: rgba(255,255,255,.86);
            font-size: 16px;
            line-height: 1.65;
            max-width: 920px;
        }

        .hero-side {
            background: rgba(255,255,255,.12);
            border: 1px solid rgba(255,255,255,.16);
            border-radius: 22px;
            padding: 18px;
            backdrop-filter: blur(12px);
        }

        .hero-side-label {font-size:13px;color:#bfdbfe;font-weight:700;margin-bottom:8px;}
        .hero-side-value {font-size:24px;font-weight:800;margin-bottom:8px;}
        .hero-side-note {font-size:13px;color:rgba(255,255,255,.78);line-height:1.55;}

        .section-title {
            color: var(--ink);
            font-size: 22px;
            font-weight: 800;
            margin: 8px 0 12px 0;
            letter-spacing: -.2px;
        }

        .section-caption {
            color: var(--muted);
            margin-top: -6px;
            margin-bottom: 14px;
            font-size: 14px;
        }

        .metric-card {
            position: relative;
            overflow: hidden;
            background: linear-gradient(180deg, var(--panel-strong), rgba(248,250,252,.92));
            border: 1px solid var(--line);
            border-radius: 24px;
            padding: 18px 18px 16px;
            min-height: 152px;
            box-shadow: 0 16px 42px rgba(15,23,42,.08);
        }

        .metric-card:after {
            content: "";
            position: absolute;
            right: -48px;
            top: -54px;
            width: 130px;
            height: 130px;
            border-radius: 50%;
            background: var(--glow, rgba(37,99,235,.13));
        }

        .metric-row {display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:16px;}
        .metric-icon {width:46px; height:46px; border-radius:16px; display:flex; align-items:center; justify-content:center; font-size:22px; background: rgba(37,99,235,.10);}
        .metric-title {font-size:14px; font-weight:800; color:#475569;}
        .metric-value {font-size:32px; line-height:1.1; font-weight:800; color:var(--ink); word-break:break-word;}
        .metric-subtitle {font-size:13px; color:var(--muted); line-height:1.55; margin-top:7px;}
        .metric-pill {font-size:12px; font-weight:800; color:#1d4ed8; background:#dbeafe; border-radius:999px; padding:5px 9px;}

        .panel {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 26px;
            padding: 18px;
            box-shadow: 0 16px 46px rgba(15,23,42,.07);
            backdrop-filter: blur(12px);
            margin-bottom: 18px;
        }

        .alert-box, .success-box, .note-box {
            border-radius: 22px;
            padding: 18px 20px;
            line-height: 1.7;
            font-size: 15px;
            border: 1px solid;
            box-shadow: 0 14px 34px rgba(15,23,42,.06);
        }
        .alert-box {background: linear-gradient(135deg,#fff1f2,#ffe4e6); border-color:#fecdd3; color:#881337; border-left:7px solid var(--red);}
        .success-box {background: linear-gradient(135deg,#ecfdf5,#f0fdfa); border-color:#a7f3d0; color:#064e3b; border-left:7px solid var(--green);}
        .note-box {background: linear-gradient(135deg,#eff6ff,#f0f9ff); border-color:#bfdbfe; color:#1e3a8a; border-left:7px solid var(--blue);}

        .recommend-card {
            background: linear-gradient(180deg, rgba(255,255,255,.96), rgba(248,250,252,.94));
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 16px 18px;
            min-height: 130px;
        }
        .recommend-title {font-weight:800;color:var(--ink);font-size:16px;margin-bottom:6px;}
        .recommend-body {color:#475569;font-size:14px;line-height:1.65;}

        .stDataFrame, div[data-testid="stDataEditor"], .stPlotlyChart, .leaflet-container {
            background: #fff !important;
            border-radius: 20px !important;
            border: 1px solid rgba(148,163,184,.25) !important;
            box-shadow: 0 12px 30px rgba(15,23,42,.06) !important;
            padding: 8px !important;
        }

        .stButton > button, .stDownloadButton > button {
            border-radius: 14px !important;
            font-weight: 800 !important;
            min-height: 44px;
            border: 1px solid rgba(148,163,184,.25) !important;
        }

        div[data-baseweb="select"] > div, input, textarea {
            border-radius: 14px !important;
        }

        .footer {
            text-align:center;
            color:#64748b;
            border-top:1px solid rgba(148,163,184,.35);
            margin-top:30px;
            padding:22px 10px;
            font-size:14px;
            line-height:1.7;
        }

        @media (max-width: 980px) {
            .hero-grid {grid-template-columns: 1fr;}
            .hero {padding: 26px 24px;}
        }

        @media print {
            @page {size: A4 landscape; margin: 0.8cm;}
            .stApp {background:white !important;}
            .no-print, .stButton, .stDownloadButton, .stExpander, div[data-testid="stToolbar"], div[data-testid="stSidebar"] {display:none !important;}
            .panel, .metric-card, .hero {box-shadow:none !important; break-inside:avoid;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(title: str, value: str, subtitle: str, icon: str, pill: str = "", glow: str = "rgba(37,99,235,.13)") -> None:
    st.markdown(
        f"""
        <div class="metric-card" style="--glow:{glow};">
            <div class="metric-row">
                <div>
                    <div class="metric-title">{title}</div>
                </div>
                <div class="metric-icon">{icon}</div>
            </div>
            <div class="metric-value">{value}</div>
            <div class="metric-subtitle">{subtitle}</div>
            {f'<div style="margin-top:10px;"><span class="metric-pill">{pill}</span></div>' if pill else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_recommendation(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="recommend-card">
            <div class="recommend-title">{title}</div>
            <div class="recommend-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ==========================================
# APP
# ==========================================
inject_css()

df_base = load_and_sort_data(DATA_FILE)

# Sidebar filters for executive slicing
with st.sidebar:
    st.header("ตัวกรองข้อมูล")
    min_date = df_base["วันที่"].min()
    max_date = df_base["วันที่"].max()

    area_options = sorted([x for x in df_base["พื้นที่"].dropna().unique().tolist() if x and x != "nan"])
    selected_areas = st.multiselect("พื้นที่", area_options, default=area_options)

    repeated_only = st.checkbox("แสดงเฉพาะจุดเกิดเหตุซ้ำ", value=False)
    impact_min = st.slider("ผลกระทบขั้นต่ำ (นาที)", 0, int(max(df_base["ผลกระทบ(นาที)"].max(), 0)), 0)

    if pd.notna(min_date) and pd.notna(max_date):
        date_range = st.date_input(
            "ช่วงวันที่",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date(),
        )
    else:
        date_range = None

filtered = df_base.copy()
if selected_areas:
    filtered = filtered[filtered["พื้นที่"].isin(selected_areas)]
if repeated_only:
    filtered = filtered[filtered["หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"].astype(str).str.contains("ซ้ำ", na=False)]
filtered = filtered[filtered["ผลกระทบ(นาที)"] >= impact_min]
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    filtered = filtered[(filtered["วันที่"] >= start_date) & (filtered["วันที่"] <= end_date)]

repeated_mask = filtered["หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"].astype(str).str.contains("ซ้ำ", na=False)
df_repeated = filtered[repeated_mask].copy()
valid_coords = filtered.dropna(subset=["Latitude", "Longitude"])

delay_sum = int(filtered["ผลกระทบ(นาที)"].sum()) if not filtered.empty else 0
avg_delay = float(filtered["ผลกระทบ(นาที)"].mean()) if not filtered.empty else 0.0
highest_risk_area = filtered["พื้นที่"].mode().iloc[0] if not filtered.empty else "-"
total_cost = int(filtered["ค่าใช้จ่าย"].apply(money_to_number).sum()) if not filtered.empty else 0
latest_event = filtered.iloc[0]["ชื่อเหตุอันตราย"] if not filtered.empty else "ไม่พบข้อมูล"
last_update = get_thai_datetime_now()

# HERO
st.markdown(
    f"""
    <div class="hero">
        <div class="hero-grid">
            <div>
                <div class="eyebrow">🚆 TRAIN HAZARDS COMMAND CENTER</div>
                <div class="hero-title">Dashboard อุบัติเหตุรถไฟเฉี่ยวชนสัตว์</div>
                <div class="hero-subtitle">
                    ภาพรวมเชิงบริหารสำหรับติดตามสถานการณ์ จุดเกิดเหตุซ้ำ พื้นที่เสี่ยง ผลกระทบต่อการเดินขบวน
                    และแนวทางกำกับมาตรการป้องกันเชิงพื้นที่
                </div>
            </div>
            <div class="hero-side">
                <div class="hero-side-label">อัปเดตล่าสุด</div>
                <div class="hero-side-value">{last_update}</div>
                <div class="hero-side-note">เหตุล่าสุด: {latest_event}</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ACTION BAR
st.markdown('<div class="no-print">', unsafe_allow_html=True)
a1, a2, a3, a4 = st.columns([1.1, 1.1, 1.3, 5.2])
with a1:
    if st.button("🖨️ พิมพ์/ส่งออก PDF", use_container_width=True, type="primary"):
        st.info("กด Ctrl + P หรือ Cmd + P แล้วเลือก Save as PDF")
with a2:
    if st.button("🔄 รีเฟรช", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
with a3:
    st.download_button(
        "⬇️ ดาวน์โหลด CSV",
        data=make_download_csv(filtered.drop(columns=["วันที่"], errors="ignore")),
        file_name="train_hazards_filtered.csv",
        mime="text/csv",
        use_container_width=True,
    )
st.markdown('</div>', unsafe_allow_html=True)

# KPI
st.markdown('<div class="section-title">ภาพรวมตัวชี้วัดสำคัญ</div>', unsafe_allow_html=True)
st.markdown('<div class="section-caption">สรุปสถานการณ์เพื่อการตัดสินใจระดับผู้บริหาร</div>', unsafe_allow_html=True)

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    render_metric_card("เหตุการณ์ทั้งหมด", f"{len(filtered):,}", "จำนวนเหตุการณ์ตามตัวกรองปัจจุบัน", "🚨", glow="rgba(225,29,72,.13)")
with k2:
    repeated_pct = (len(df_repeated) / len(filtered) * 100) if len(filtered) else 0
    render_metric_card("จุดเกิดเหตุซ้ำ", f"{len(df_repeated):,}", f"คิดเป็น {repeated_pct:.1f}% ของเหตุทั้งหมด", "📍", "ต้องเฝ้าระวัง", "rgba(245,158,11,.18)")
with k3:
    render_metric_card("พื้นที่เสี่ยงสูงสุด", highest_risk_area, "พื้นที่ที่พบเหตุบ่อยที่สุด", "⚠️", glow="rgba(37,99,235,.14)")
with k4:
    render_metric_card("ความล่าช้ารวม", f"{delay_sum:,} นาที", f"เฉลี่ย {avg_delay:.1f} นาที/เหตุ", "⏱️", glow="rgba(8,145,178,.16)")
with k5:
    render_metric_card("ค่าใช้จ่ายรวม", f"{total_cost:,} บาท", "ประเมินจากข้อความค่าใช้จ่ายที่บันทึก", "💰", glow="rgba(16,185,129,.16)")

# EXECUTIVE ALERT
st.markdown('<div class="section-title">Executive Brief</div>', unsafe_allow_html=True)
if filtered.empty:
    st.markdown('<div class="note-box"><b>ไม่พบข้อมูล:</b> กรุณาปรับตัวกรองหรือนำเข้าข้อมูลเพิ่มเติม</div>', unsafe_allow_html=True)
elif len(df_repeated) > 0:
    st.markdown(
        f"""
        <div class="alert-box">
            <b>ประเด็นเร่งด่วน:</b> พบจุดเกิดเหตุซ้ำ <b>{len(df_repeated):,} รายการ</b>
            โดยพื้นที่ที่ควรให้ความสำคัญลำดับแรกคือ <b>{highest_risk_area}</b>
            ควรกำหนดมาตรการเฝ้าระวังเชิงพื้นที่ เพิ่มการตรวจแนวเขต และติดตามผลหลังดำเนินมาตรการเป็นรายเดือน
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <div class="success-box">
            <b>สถานะปัจจุบัน:</b> ยังไม่พบรายการที่ระบุว่าเป็นจุดเกิดเหตุซ้ำตามตัวกรองปัจจุบัน
            แต่ยังควรติดตามพื้นที่ที่มีจำนวนเหตุสูงและเหตุที่มีผลกระทบต่อการเดินขบวนสูงเป็นพิเศษ
        </div>
        """,
        unsafe_allow_html=True,
    )

# CHARTS
st.markdown('<div class="section-title">วิเคราะห์แนวโน้มและพื้นที่เสี่ยง</div>', unsafe_allow_html=True)
chart_left, chart_right = st.columns([1.05, 1])

with chart_left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("อันดับพื้นที่ตามจำนวนเหตุการณ์")
    if not filtered.empty:
        area_counts = filtered["พื้นที่"].value_counts().reset_index()
        area_counts.columns = ["พื้นที่", "จำนวนเหตุการณ์"]
        area_counts = area_counts.sort_values("จำนวนเหตุการณ์", ascending=True)

        fig_area = px.bar(
            area_counts,
            x="จำนวนเหตุการณ์",
            y="พื้นที่",
            orientation="h",
            text="จำนวนเหตุการณ์",
            color="จำนวนเหตุการณ์",
            color_continuous_scale=["#dbeafe", "#60a5fa", "#1d4ed8"],
        )
        fig_area.update_layout(
            height=max(390, len(area_counts) * 44),
            margin=dict(l=10, r=28, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Sarabun", size=14, color="#0f172a"),
            coloraxis_showscale=False,
            xaxis=dict(title=None, gridcolor="#e2e8f0", zeroline=False),
            yaxis=dict(title=None),
        )
        fig_area.update_traces(textposition="outside", marker_line_width=0, hovertemplate="<b>%{y}</b><br>จำนวนเหตุการณ์: %{x}<extra></extra>")
        st.plotly_chart(fig_area, use_container_width=True)
    else:
        st.info("ไม่พบข้อมูลสำหรับสร้างกราฟ")
    st.markdown('</div>', unsafe_allow_html=True)

with chart_right:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("แนวโน้มรายเดือน")
    if not filtered.empty and filtered["วันที่"].notna().any():
        monthly = filtered.dropna(subset=["วันที่"]).copy()
        monthly["เดือน"] = monthly["วันที่"].dt.to_period("M").dt.to_timestamp()
        monthly_summary = monthly.groupby("เดือน", as_index=False).agg(
            จำนวนเหตุการณ์=("ชื่อเหตุอันตราย", "count"),
            ผลกระทบรวม=("ผลกระทบ(นาที)", "sum"),
        )
        monthly_summary["เดือน_แสดงผล"] = monthly_summary["เดือน"].apply(lambda d: f"{THAI_MONTHS[d.month - 1]} {d.year + 543}")

        fig_month = go.Figure()
        fig_month.add_bar(
            x=monthly_summary["เดือน_แสดงผล"],
            y=monthly_summary["จำนวนเหตุการณ์"],
            name="จำนวนเหตุการณ์",
            marker_color="#2563eb",
            hovertemplate="%{x}<br>จำนวนเหตุการณ์: %{y}<extra></extra>",
        )
        fig_month.add_scatter(
            x=monthly_summary["เดือน_แสดงผล"],
            y=monthly_summary["ผลกระทบรวม"],
            name="ผลกระทบรวม (นาที)",
            mode="lines+markers",
            yaxis="y2",
            line=dict(color="#e11d48", width=3),
            marker=dict(size=8),
            hovertemplate="%{x}<br>ผลกระทบรวม: %{y} นาที<extra></extra>",
        )
        fig_month.update_layout(
            height=390,
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Sarabun", size=13, color="#0f172a"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            xaxis=dict(title=None, tickangle=-25),
            yaxis=dict(title="จำนวนเหตุการณ์", gridcolor="#e2e8f0", zeroline=False),
            yaxis2=dict(title="นาที", overlaying="y", side="right", showgrid=False),
        )
        st.plotly_chart(fig_month, use_container_width=True)
    else:
        st.info("ไม่พบข้อมูลวันที่สำหรับสร้างแนวโน้มรายเดือน")
    st.markdown('</div>', unsafe_allow_html=True)

# MAP + DONUT
map_col, donut_col = st.columns([1.2, .8])
with map_col:
    st.markdown('<div class="section-title">แผนที่จุดเกิดเหตุและจุดเฝ้าระวัง</div>', unsafe_allow_html=True)
    if not valid_coords.empty:
        center_lat = valid_coords["Latitude"].mean()
        center_lon = valid_coords["Longitude"].mean()
    else:
        center_lat, center_lon = 13.7367, 100.5231

    m = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles="CartoDB positron")
    for _, row in filtered.iterrows():
        if pd.notna(row["Latitude"]) and pd.notna(row["Longitude"]):
            is_repeated = "ซ้ำ" in str(row["หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"])
            color = "#e11d48" if is_repeated else "#2563eb"
            radius = min(16, 6 + int(row["ผลกระทบ(นาที)"]) / 8)
            popup_html = f"""
            <div style="font-family:Sarabun; min-width:240px; padding:8px 5px;">
                <div style="font-size:15px; font-weight:800; color:#0f172a; margin-bottom:7px;">{row['ชื่อเหตุอันตราย']}</div>
                <div style="font-size:13px; color:#334155; line-height:1.65;">
                    <b>พื้นที่:</b> {row['พื้นที่']}<br>
                    <b>กม.:</b> {row['ที่ กม.']}<br>
                    <b>วันที่:</b> {convert_to_thai_date(row['วัน/เดือน/ปี'])}<br>
                    <b>เวลา:</b> {row['เวลา ที่เกิดเหตุ']}<br>
                    <b>ผลกระทบ:</b> {int(row['ผลกระทบ(นาที)'])} นาที<br>
                    <b>สถานะ:</b> {'จุดเกิดเหตุซ้ำ' if is_repeated else 'เหตุทั่วไป'}
                </div>
            </div>
            """
            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.82,
                weight=2,
                popup=folium.Popup(popup_html, max_width=330),
            ).add_to(m)

    st_folium(m, height=460, use_container_width=True, returned_objects=[])

with donut_col:
    st.markdown('<div class="section-title">สัดส่วนประเภทความเสี่ยง</div>', unsafe_allow_html=True)
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    if not filtered.empty:
        risk_df = pd.DataFrame(
            {
                "ประเภท": ["จุดเกิดเหตุซ้ำ", "เหตุทั่วไป"],
                "จำนวน": [len(df_repeated), max(len(filtered) - len(df_repeated), 0)],
            }
        )
        fig_donut = px.pie(
            risk_df,
            names="ประเภท",
            values="จำนวน",
            hole=.62,
            color="ประเภท",
            color_discrete_map={"จุดเกิดเหตุซ้ำ": "#e11d48", "เหตุทั่วไป": "#2563eb"},
        )
        fig_donut.update_traces(textinfo="label+percent", hovertemplate="%{label}: %{value} รายการ<extra></extra>")
        fig_donut.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Sarabun", size=14, color="#0f172a"),
        )
        st.plotly_chart(fig_donut, use_container_width=True)
        st.caption("สีแดง = จุดที่ระบุว่าเกิดเหตุซ้ำ / สีน้ำเงิน = เหตุทั่วไป")
    else:
        st.info("ไม่พบข้อมูลสำหรับแสดงสัดส่วน")
    st.markdown('</div>', unsafe_allow_html=True)

# RECOMMENDATIONS
st.markdown('<div class="section-title">ข้อเสนอแนะเชิงบริหาร</div>', unsafe_allow_html=True)
r1, r2, r3 = st.columns(3)
with r1:
    render_recommendation("1) จัดลำดับพื้นที่เร่งด่วน", f"เริ่มจากพื้นที่ <b>{highest_risk_area}</b> และจุดที่มีหมายเหตุเกิดเหตุซ้ำ เพื่อกำหนดมาตรการปิดช่องทางสัตว์/แนวเขต")
with r2:
    render_recommendation("2) ลดผลกระทบการเดินขบวน", f"เหตุการณ์ตามตัวกรองมีผลกระทบรวม <b>{delay_sum:,} นาที</b> ควรติดตามเหตุที่มีความล่าช้าสูงเป็นรายกรณี")
with r3:
    render_recommendation("3) ติดตามผลทุกเดือน", "ใช้แนวโน้มรายเดือนเป็นตัวชี้วัดผลหลังดำเนินมาตรการ และรายงานต่อผู้บริหารในรูปแบบ Dashboard เดียวกัน")

# TABLES
st.markdown('<div class="section-title">ทะเบียนข้อมูลเหตุการณ์</div>', unsafe_allow_html=True)
tab_all, tab_repeat, tab_manage = st.tabs(["ข้อมูลทั้งหมด", "จุดเกิดเหตุซ้ำ", "จัดการข้อมูล"])

with tab_all:
    st.dataframe(build_display_table(filtered), use_container_width=True, hide_index=True, height=420)

with tab_repeat:
    if not df_repeated.empty:
        st.dataframe(build_display_table(df_repeated), use_container_width=True, hide_index=True, height=360)
    else:
        st.info("ไม่พบจุดเกิดเหตุซ้ำตามตัวกรองปัจจุบัน")

with tab_manage:
    st.markdown('<div class="no-print">', unsafe_allow_html=True)
    st.warning("โหมดนี้ใช้สำหรับเพิ่ม/แก้ไขข้อมูล ควรสำรองไฟล์ CSV ก่อนบันทึก")
    enable_management = st.checkbox("เปิดโหมดจัดการข้อมูล", value=False)

    if enable_management:
        edited_df = st.data_editor(
            df_base.drop(columns=["วันที่"], errors="ignore"),
            use_container_width=True,
            num_rows="dynamic",
            height=300,
            key="editor",
        )
        c_save, c_upload = st.columns([1, 2])
        with c_save:
            if st.button("💾 บันทึกข้อมูลที่แก้ไข", use_container_width=True, type="primary"):
                edited_df.to_csv(DATA_FILE, index=False)
                st.cache_data.clear()
                st.success("บันทึกข้อมูลเรียบร้อยแล้ว")
                st.rerun()
        with c_upload:
            uploaded_file = st.file_uploader("นำเข้าไฟล์ .csv หรือ .xlsx เพื่อผสานข้อมูล", type=["csv", "xlsx"])
            if uploaded_file is not None:
                try:
                    df_new = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
                    st.dataframe(df_new.head(10), use_container_width=True, hide_index=True)
                    if st.button("➕ ผสานข้อมูลเข้าระบบ", use_container_width=True):
                        combined_df = pd.concat([df_base.drop(columns=["วันที่"], errors="ignore"), df_new], ignore_index=True)
                        combined_df.to_csv(DATA_FILE, index=False)
                        st.cache_data.clear()
                        st.success("ผสานข้อมูลสำเร็จ")
                        st.rerun()
                except Exception as exc:
                    st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {exc}")

        with st.expander("📝 เพิ่มเหตุการณ์ใหม่แบบฟอร์ม"):
            with st.form("new_event_form"):
                name = st.text_input("ชื่อเหตุอันตราย")
                area = st.text_input("พื้นที่")
                km = st.text_input("ที่ กม.")
                c1, c2, c3 = st.columns(3)
                with c1:
                    event_date = st.date_input("วัน/เดือน/ปี")
                    lat = st.number_input("Latitude", value=13.7367, format="%.5f")
                with c2:
                    event_time = st.time_input("เวลา ที่เกิดเหตุ", value=datetime.time(12, 0))
                    lon = st.number_input("Longitude", value=100.5231, format="%.5f")
                with c3:
                    impact = st.number_input("ผลกระทบ(นาที)", min_value=0, step=1)
                    cost = st.text_input("ค่าใช้จ่าย", value="ไม่มีค่าใช้จ่าย")
                remark = st.text_input("หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)")
                submitted = st.form_submit_button("💾 บันทึกเหตุการณ์ใหม่", use_container_width=True)

                if submitted:
                    new_row = pd.DataFrame([
                        {
                            "ชื่อเหตุอันตราย": name,
                            "พื้นที่": area,
                            "ที่ กม.": km,
                            "วัน/เดือน/ปี": event_date.strftime("%Y-%m-%d"),
                            "เวลา ที่เกิดเหตุ": event_time.strftime("%H:%M"),
                            "ค่าใช้จ่าย": cost,
                            "Latitude": lat,
                            "Longitude": lon,
                            "ผลกระทบ(นาที)": impact,
                            "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)": remark,
                        }
                    ])
                    combined_df = pd.concat([df_base.drop(columns=["วันที่"], errors="ignore"), new_row], ignore_index=True)
                    combined_df.to_csv(DATA_FILE, index=False)
                    st.cache_data.clear()
                    st.success("เพิ่มข้อมูลใหม่เรียบร้อยแล้ว")
                    st.rerun()
    else:
        st.info("ระบบจัดการข้อมูลถูกปิดไว้เพื่อความปลอดภัย")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="footer">
        <b>ระบบสารสนเทศความปลอดภัยทางรถไฟ</b><br>
        วิศวกรกำกับการกองทางถาวร ศูนย์ทางถาวร ฝ่ายการช่างโยธา การรถไฟแห่งประเทศไทย<br>
        <span style="color:#94a3b8;">Executive Dashboard · Modern UI Version</span>
    </div>
    """,
    unsafe_allow_html=True,
)
