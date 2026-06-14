import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import datetime
import plotly.express as px
import os
import base64
import re

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
LOGO_FILE = "logo.png"

THAI_MONTHS = [
    "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]

THAI_MONTH_MAP = {
    "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4,
    "พฤษภาคม": 5, "มิถุนายน": 6, "กรกฎาคม": 7, "สิงหาคม": 8,
    "กันยายน": 9, "ตุลาคม": 10, "พฤศจิกายน": 11, "ธันวาคม": 12
}

REQUIRED_COLUMNS = [
    "ชื่อเหตุอันตราย",
    "สาย",
    "ระหว่างสถานี",
    "พื้นที่",
    "ที่ กม.",
    "วัน/เดือน/ปี",
    "เวลา ที่เกิดเหตุ",
    "สาเหตุ",
    "ค่าใช้จ่าย",
    "Latitude",
    "Longitude",
    "ผลกระทบ(นาที)",
    "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"
]

THAILAND_BOUNDS = [[5.6, 97.3], [20.5, 105.7]]
THAILAND_CENTER = [13.7367, 100.5231]
THAILAND_DEFAULT_ZOOM = 6

# ==========================================
# HELPERS
# ==========================================
def get_logo_data_url():
    try:
        if os.path.exists(LOGO_FILE):
            with open(LOGO_FILE, "rb") as f:
                logo_base64 = base64.b64encode(f.read()).decode()
            return f"data:image/png;base64,{logo_base64}"
        return None
    except Exception:
        return None


def normalize_text(value):
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def parse_thai_date(date_str):
    text = normalize_text(date_str)
    if not text:
        return pd.NaT

    text = text.replace("เวลา", "").strip()

    # กรณีไทย เช่น 7 ตุลาคม 2567
    thai_pattern = r"(\d{1,2})\s+([ก-๙]+)\s+(\d{4})"
    m = re.search(thai_pattern, text)
    if m:
        day = int(m.group(1))
        month_name = m.group(2)
        year = int(m.group(3))
        month = THAI_MONTH_MAP.get(month_name)
        if month:
            if year > 2400:
                year -= 543
            try:
                return pd.Timestamp(year=year, month=month, day=day)
            except Exception:
                return pd.NaT

    # กรณีอังกฤษ เช่น 3 January 2024, 12-May-67
    for fmt in [
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d",
        "%d %B %Y", "%d-%b-%y", "%d-%B-%y", "%d-%b-%Y", "%d-%B-%Y"
    ]:
        try:
            dt = datetime.datetime.strptime(text, fmt)
            year = dt.year
            if year < 100:
                year += 2000
            return pd.Timestamp(year=year, month=dt.month, day=dt.day)
        except ValueError:
            continue

    # fallback
    dt = pd.to_datetime(text, errors="coerce", dayfirst=True)
    return dt


def parse_time_value(time_str):
    text = normalize_text(time_str)
    if not text:
        return pd.NaT

    text = text.replace("น.", "").replace("น", "").replace(" ", "").strip()
    text = text.replace(".", ":")

    for fmt in ["%H:%M", "%H:%M:%S"]:
        try:
            return pd.to_datetime(text, format=fmt, errors="raise")
        except Exception:
            pass

    return pd.to_datetime(text, errors="coerce")


def convert_to_thai_date(date_str):
    try:
        dt = parse_thai_date(date_str)
        if pd.notna(dt):
            return f"{dt.day} {THAI_MONTHS[dt.month - 1]} {dt.year + 543}"
        return str(date_str)
    except Exception:
        return str(date_str)


def get_thai_datetime_now():
    now = datetime.datetime.now()
    return f"{now.day} {THAI_MONTHS[now.month - 1]} {now.year + 543} เวลา {now.strftime('%H:%M')} น."


def ensure_required_columns(df):
    df = df.copy()
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df


def clean_dataframe(df):
    df = ensure_required_columns(df)

    text_cols = [
        "ชื่อเหตุอันตราย", "สาย", "ระหว่างสถานี", "พื้นที่", "ที่ กม.",
        "วัน/เดือน/ปี", "เวลา ที่เกิดเหตุ", "สาเหตุ", "ค่าใช้จ่าย",
        "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"
    ]
    for col in text_cols:
        df[col] = df[col].apply(normalize_text)

    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df["ผลกระทบ(นาที)"] = pd.to_numeric(df["ผลกระทบ(นาที)"], errors="coerce").fillna(0)

    return df


def build_duplicate_key(df):
    return (
        df["ชื่อเหตุอันตราย"].astype(str).str.strip().str.lower() + "|" +
        df["พื้นที่"].astype(str).str.strip().str.lower() + "|" +
        df["ที่ กม."].astype(str).str.strip().str.lower() + "|" +
        df["วัน/เดือน/ปี"].astype(str).str.strip() + "|" +
        df["เวลา ที่เกิดเหตุ"].astype(str).str.strip()
    )


def deduplicate_combined(existing_df, new_df):
    existing = existing_df.copy()
    incoming = new_df.copy()

    existing["dup_key"] = build_duplicate_key(existing)
    incoming["dup_key"] = build_duplicate_key(incoming)

    combined = pd.concat([existing, incoming], ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates(subset=["dup_key"], keep="first")
    removed = before - len(combined)
    combined = combined.drop(columns=["dup_key"], errors="ignore")
    return combined, removed


@st.cache_data(show_spinner=False)
def load_data_cached(file_path, mtime):
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
    else:
        df = pd.DataFrame({
            "ชื่อเหตุอันตราย": ["ชนโค ท่าพระ-ขอนแก่น"],
            "สาย": ["สายหนองคาย"],
            "ระหว่างสถานี": ["ท่าพระ - ขอนแก่น"],
            "พื้นที่": ["แขวงบำรุงทางขอนแก่น"],
            "ที่ กม.": ["345+100"],
            "วัน/เดือน/ปี": ["2024-02-15"],
            "เวลา ที่เกิดเหตุ": ["10:30"],
            "สาเหตุ": [""],
            "ค่าใช้จ่าย": ["ไม่มีค่าใช้จ่าย"],
            "Latitude": [16.3650],
            "Longitude": [102.8340],
            "ผลกระทบ(นาที)": [15],
            "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)": ["-"]
        })
        df.to_csv(file_path, index=False)

    df = clean_dataframe(df)
    df["temp_date"] = df["วัน/เดือน/ปี"].apply(parse_thai_date)
    df["temp_time"] = df["เวลา ที่เกิดเหตุ"].apply(parse_time_value)
    df = df.sort_values(by=["temp_date", "temp_time"], ascending=[False, False]).reset_index(drop=True)
    return df


def load_and_sort_data():
    if not os.path.exists(DATA_FILE):
        load_data_cached(DATA_FILE, 0)

    mtime = os.path.getmtime(DATA_FILE) if os.path.exists(DATA_FILE) else 0
    return load_data_cached(DATA_FILE, mtime)


def save_data(df):
    save_df = df.copy()
    save_df = ensure_required_columns(save_df)
    save_df = save_df[REQUIRED_COLUMNS]
    save_df.to_csv(DATA_FILE, index=False)
    load_data_cached.clear()


def build_display_table(df):
    display_df = df.copy()
    display_df = display_df.drop(columns=["temp_date", "temp_time"], errors="ignore")
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


def validate_uploaded_columns(df_new):
    return [col for col in REQUIRED_COLUMNS if col not in df_new.columns]


def apply_filters(df, areas, lines, date_range, repeat_mode):
    filtered = df.copy()

    if areas:
        filtered = filtered[filtered["พื้นที่"].isin(areas)]

    if lines:
        filtered = filtered[filtered["สาย"].isin(lines)]

    if date_range and len(date_range) == 2 and all(date_range):
        start_date, end_date = date_range
        mask = (
            (filtered["temp_date"].dt.date >= start_date) &
            (filtered["temp_date"].dt.date <= end_date)
        )
        filtered = filtered[mask]

    if repeat_mode == "เฉพาะจุดซ้ำ":
        filtered = filtered[filtered["หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"].astype(str).str.contains("ซ้ำ|ครั้งที่", na=False)]
    elif repeat_mode == "ไม่รวมจุดซ้ำ":
        filtered = filtered[~filtered["หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"].astype(str).str.contains("ซ้ำ|ครั้งที่", na=False)]

    return filtered


# ==========================================
# SESSION STATE
# ==========================================
if "flash_message" not in st.session_state:
    st.session_state["flash_message"] = None

logo_data_url = get_logo_data_url()

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

html {{
    overflow-y: scroll !important;
}}

::-webkit-scrollbar {{
    width: 12px;
    height: 12px;
}}

::-webkit-scrollbar-track {{
    background: #F1F5F9;
    border-radius: 10px;
}}

::-webkit-scrollbar-thumb {{
    background: linear-gradient(180deg, #1E3A8A 0%, #2563EB 100%);
    border-radius: 10px;
    border: 2px solid #F1F5F9;
}}

#MainMenu, footer, header {{
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
    padding: 28px 34px 24px 34px;
    color: white;
    box-shadow: 0 24px 50px rgba(15, 23, 42, 0.18);
    margin-bottom: 22px;
    position: relative;
    overflow: hidden;
}}

.hero-flex {{
    display: flex;
    align-items: center;
    gap: 22px;
    position: relative;
    z-index: 2;
}}

.hero-logo {{
    flex-shrink: 0;
    width: 88px;
    height: 88px;
    border-radius: 20px;
    background: rgba(255,255,255,0.95);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 8px;
    box-shadow: 0 10px 24px rgba(0,0,0,0.20);
    border: 1px solid rgba(255,255,255,0.4);
}}

.hero-logo img {{
    width: 100%;
    height: 100%;
    object-fit: contain;
}}

.hero-text {{
    flex: 1;
}}

.hero-org {{
    font-size: 13px;
    font-weight: 600;
    color: rgba(255,255,255,0.75);
    letter-spacing: 0.5px;
    margin-bottom: 4px;
    text-transform: uppercase;
}}

.hero-title {{
    font-size: 32px;
    font-weight: 800;
    margin-bottom: 6px;
    line-height: 1.2;
}}

.hero-subtitle {{
    font-size: 16px;
    color: rgba(255,255,255,0.84);
    margin-bottom: 12px;
}}

.hero-badge {{
    display: inline-block;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 999px;
    padding: 8px 14px;
    font-size: 13px;
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

.sidebar-logo {{
    text-align: center;
    padding: 8px 0 16px 0;
    border-bottom: 1px solid #E2E8F0;
    margin-bottom: 16px;
}}

.sidebar-logo img {{
    width: 90px;
    height: 90px;
    object-fit: contain;
}}

.sidebar-org {{
    font-size: 13px;
    font-weight: 700;
    color: #1E3A8A;
    margin-top: 8px;
    line-height: 1.4;
}}

.stDataFrame, div[data-testid="stDataEditor"], .stPlotlyChart, .leaflet-container {{
    background: #FFFFFF !important;
    border-radius: 18px !important;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0 8px 24px rgba(15,23,42,0.05) !important;
    padding: 8px !important;
}}

.stButton > button {{
    border-radius: 14px !important;
    font-weight: 700 !important;
}}
</style>
""", unsafe_allow_html=True)

# ==========================================
# LOAD DATA
# ==========================================
df_base = load_and_sort_data()

# ==========================================
# SIDEBAR ADMIN
# ==========================================
with st.sidebar:
    if logo_data_url:
        st.markdown(
            f"""
            <div class="sidebar-logo">
                <img src="{logo_data_url}" alt="โลโก้ฝ่ายการช่างโยธา"/>
                <div class="sidebar-org">ฝ่ายการช่างโยธา<br/>การรถไฟแห่งประเทศไทย</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown("### ฝ่ายการช่างโยธา")
        st.caption("ไม่พบไฟล์ logo.png")

    st.markdown("## ⚙️ ศูนย์จัดการข้อมูล")
    admin_mode = st.toggle("เปิดโหมดผู้ดูแลระบบ", value=False)

    if admin_mode:
        if st.session_state.get("flash_message"):
            msg_type, msg_text = st.session_state["flash_message"]
            if msg_type == "success":
                st.success(msg_text)
            elif msg_type == "warning":
                st.warning(msg_text)
            st.session_state["flash_message"] = None

        with st.expander("✏️ แก้ไขข้อมูลทั้งชุด", expanded=False):
            edited_df = st.data_editor(
                df_base[REQUIRED_COLUMNS],
                use_container_width=True,
                num_rows="dynamic",
                height=320,
                key="admin_editor"
            )

            if st.button("💾 บันทึกข้อมูลที่แก้ไข", use_container_width=True, type="primary", key="save_edit_btn"):
                cleaned = clean_dataframe(edited_df)
                save_data(cleaned)
                st.session_state["flash_message"] = ("success", "บันทึกข้อมูลเรียบร้อยแล้ว")
                st.rerun()

        with st.expander("📥 นำเข้าข้อมูลจากไฟล์", expanded=False):
            uploaded_file = st.file_uploader("อัปโหลด .csv หรือ .xlsx", type=["csv", "xlsx"], key="file_uploader")
            if uploaded_file is not None:
                try:
                    if uploaded_file.name.endswith(".csv"):
                        df_new = pd.read_csv(uploaded_file)
                    else:
                        df_new = pd.read_excel(uploaded_file)

                    st.dataframe(df_new.head(), use_container_width=True, hide_index=True)

                    missing_cols = validate_uploaded_columns(df_new)
                    if missing_cols:
                        st.error(f"ไฟล์ขาดคอลัมน์: {', '.join(missing_cols)}")
                    else:
                        if st.button("➕ ผสานข้อมูลเข้าระบบ", use_container_width=True, key="merge_btn"):
                            df_new_clean = clean_dataframe(df_new[REQUIRED_COLUMNS])
                            combined_df, removed = deduplicate_combined(df_base[REQUIRED_COLUMNS], df_new_clean)
                            save_data(combined_df)
                            st.session_state["flash_message"] = ("success", f"ผสานข้อมูลสำเร็จ ตัดข้อมูลซ้ำออก {removed} รายการ")
                            st.rerun()
                except Exception as e:
                    st.error(f"อ่านไฟล์ไม่ได้: {e}")

        with st.expander("📝 เพิ่มเหตุการณ์ใหม่", expanded=False):
            with st.form("realtime_input_form", clear_on_submit=True):
                input_name = st.text_input("ชื่อเหตุอันตราย")
                input_line = st.text_input("สาย")
                input_station = st.text_input("ระหว่างสถานี")
                input_area = st.text_input("พื้นที่")
                input_km = st.text_input("ที่ กม.")
                input_cause = st.text_input("สาเหตุ")

                c1, c2 = st.columns(2)
                with c1:
                    input_date = st.date_input("วัน/เดือน/ปี")
                    input_lat = st.number_input("Latitude", value=13.7367, format="%.6f")
                    input_impact = st.number_input("ผลกระทบ(นาที)", min_value=0, step=1)
                with c2:
                    input_time = st.time_input("เวลา ที่เกิดเหตุ", value=datetime.time(12, 0))
                    input_lon = st.number_input("Longitude", value=100.5231, format="%.6f")
                    input_cost = st.text_input("ค่าใช้จ่าย", value="ไม่มีค่าใช้จ่าย")

                input_remark = st.text_input("หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)")

                submitted = st.form_submit_button("💾 บันทึกเหตุการณ์ใหม่", use_container_width=True)
                if submitted:
                    if not input_name.strip() or not input_area.strip() or not input_km.strip():
                        st.error("กรุณากรอกชื่อเหตุ, พื้นที่, ที่ กม. ให้ครบ")
                    else:
                        new_row = pd.DataFrame([{
                            "ชื่อเหตุอันตราย": input_name.strip(),
                            "สาย": input_line.strip(),
                            "ระหว่างสถานี": input_station.strip(),
                            "พื้นที่": input_area.strip(),
                            "ที่ กม.": input_km.strip(),
                            "วัน/เดือน/ปี": input_date.strftime("%Y-%m-%d"),
                            "เวลา ที่เกิดเหตุ": input_time.strftime("%H:%M"),
                            "สาเหตุ": input_cause.strip(),
                            "ค่าใช้จ่าย": input_cost.strip() if str(input_cost).strip() else "ไม่มีค่าใช้จ่าย",
                            "Latitude": input_lat,
                            "Longitude": input_lon,
                            "ผลกระทบ(นาที)": input_impact,
                            "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)": input_remark.strip()
                        }])

                        new_row = clean_dataframe(new_row)
                        combined_df, removed = deduplicate_combined(df_base[REQUIRED_COLUMNS], new_row)

                        if removed > 0:
                            st.session_state["flash_message"] = ("warning", "ข้อมูลนี้ซ้ำกับรายการที่มีอยู่แล้วในระบบ ไม่ได้บันทึกซ้ำ")
                        else:
                            save_data(combined_df)
                            st.session_state["flash_message"] = ("success", "เพิ่มข้อมูลใหม่เรียบร้อยแล้ว")
                        st.rerun()

# ==========================================
# HERO
# ==========================================
last_update = get_thai_datetime_now()
hero_logo_html = (
    f'<div class="hero-logo"><img src="{logo_data_url}" alt="โลโก้ฝ่ายการช่างโยธา"/></div>'
    if logo_data_url else
    '<div class="hero-logo"><span style="color:#1E3A8A;font-weight:800;">LOGO</span></div>'
)

st.markdown(f"""
<div class="dashboard-hero">
    <div class="hero-flex">
        {hero_logo_html}
        <div class="hero-text">
            <div class="hero-org">ฝ่ายการช่างโยธา · การรถไฟแห่งประเทศไทย</div>
            <div class="hero-title">🚆 Executive Dashboard: สถานการณ์อุบัติเหตุรถไฟเฉี่ยวชนสัตว์</div>
            <div class="hero-subtitle">รายงานวิเคราะห์เชิงพื้นที่ สถิติ และจุดเฝ้าระวังสำคัญ สำหรับผู้บริหาร</div>
            <div class="hero-badge">อัปเดตล่าสุด: {last_update}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# FILTER BAR
# ==========================================
st.markdown('<div class="section-wrap">', unsafe_allow_html=True)
st.markdown('<div class="section-title">🔎 ตัวกรองข้อมูล</div>', unsafe_allow_html=True)

f1, f2, f3, f4 = st.columns([1.2, 1.2, 1.2, 1])

with f1:
    min_date = df_base["temp_date"].min()
    max_date = df_base["temp_date"].max()
    if pd.notna(min_date) and pd.notna(max_date):
        date_range = st.date_input("ช่วงวันที่", value=(min_date.date(), max_date.date()))
    else:
        today = datetime.date.today()
        date_range = st.date_input("ช่วงวันที่", value=(today, today))

with f2:
    area_options = sorted([a for a in df_base["พื้นที่"].dropna().unique() if a])
    selected_areas = st.multiselect("พื้นที่ / แขวง", options=area_options, default=area_options)

with f3:
    line_options = sorted([a for a in df_base["สาย"].dropna().unique() if a])
    selected_lines = st.multiselect("สาย", options=line_options, default=line_options)

with f4:
    repeat_mode = st.selectbox("จุดเกิดเหตุซ้ำ", ["ทั้งหมด", "เฉพาะจุดซ้ำ", "ไม่รวมจุดซ้ำ"])

df_filtered = apply_filters(df_base, selected_areas, selected_lines, date_range, repeat_mode)
st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# DERIVED DATA
# ==========================================
repeated_mask = df_filtered["หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"].astype(str).str.contains("ซ้ำ|ครั้งที่", na=False)
df_repeated = df_filtered[repeated_mask].copy()

df_display = build_display_table(df_filtered)
df_repeated_display = build_display_table(df_repeated)

delay_sum = int(df_filtered["ผลกระทบ(นาที)"].sum()) if not df_filtered.empty else 0
highest_risk_area = df_filtered["พื้นที่"].mode().iloc[0] if not df_filtered.empty and not df_filtered["พื้นที่"].mode().empty else "-"

# ==========================================
# KPI
# ==========================================
st.markdown('<div class="section-wrap">', unsafe_allow_html=True)
st.markdown('<div class="section-title">ภาพรวมตัวชี้วัดสำคัญ</div>', unsafe_allow_html=True)

k1, k2, k3, k4 = st.columns(4)
with k1:
    render_metric_card("เหตุการณ์สะสม", f"{len(df_filtered)}", "ตามตัวกรองที่เลือก", "🚨", "red")
with k2:
    render_metric_card("พิกัดเกิดเหตุซ้ำ", f"{len(df_repeated_display)}", "จุดเฝ้าระวังพิเศษ ± 3 Km", "📍", "amber")
with k3:
    render_metric_card("พื้นที่วิกฤตสูงสุด", highest_risk_area, "พื้นที่ที่พบเหตุบ่อยที่สุด", "⚠️", "blue")
with k4:
    render_metric_card("ความล่าช้ารวม", f"{delay_sum} นาที", "ผลกระทบรวมต่อการเดินขบวน", "⏱️", "teal")

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
            <b>รายงานเตือนเชิงบริหาร:</b> พบ <b>{len(df_repeated_display)} พิกัด</b>
            ที่มีลักษณะเกิดเหตุซ้ำในรัศมีใกล้เคียงกัน ควรได้รับการติดตามและบริหารความเสี่ยงเชิงพื้นที่อย่างต่อเนื่อง
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown(
        """
        <div class="info-box">
            <b>สถานะปัจจุบัน:</b> ไม่พบจุดเกิดเหตุซ้ำภายใต้เงื่อนไขที่เลือก
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

    if not df_filtered.empty:
        area_counts = df_filtered["พื้นที่"].value_counts().reset_index()
        area_counts.columns = ["พื้นที่", "จำนวนเหตุการณ์"]
        area_counts = area_counts.sort_values(by="จำนวนเหตุการณ์", ascending=True)

        fig = px.bar(
            area_counts,
            x="จำนวนเหตุการณ์",
            y="พื้นที่",
            orientation="h",
            text="จำนวนเหตุการณ์",
            color="จำนวนเหตุการณ์",
            color_continuous_scale=["#DBEAFE", "#60A5FA", "#1D4ED8"]
        )

        fig.update_layout(
            height=max(360, len(area_counts) * 48),
            margin=dict(l=10, r=20, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Sarabun", size=14, color="#0F172A"),
            coloraxis_showscale=False,
            xaxis=dict(title=None, showgrid=True, gridcolor="#E2E8F0", zeroline=False),
            yaxis=dict(title=None, showgrid=False)
        )
        fig.update_traces(textposition="outside", marker_line_width=0)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ไม่พบข้อมูลสำหรับสร้างกราฟ")

    st.markdown('</div>', unsafe_allow_html=True)

with right_col:
    st.markdown('<div class="section-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🗺️ แผนที่ภาพรวมประเทศไทย</div>', unsafe_allow_html=True)

    m = folium.Map(
        location=THAILAND_CENTER,
        zoom_start=THAILAND_DEFAULT_ZOOM,
        min_zoom=5,
        max_zoom=18,
        max_bounds=True,
        tiles="CartoDB positron"
    )
    m.fit_bounds(THAILAND_BOUNDS)
    m.options["maxBounds"] = THAILAND_BOUNDS
    m.options["maxBoundsViscosity"] = 1.0

    for _, row in df_filtered.iterrows():
        if pd.notna(row["Latitude"]) and pd.notna(row["Longitude"]):
            is_repeated = bool(re.search(r"ซ้ำ|ครั้งที่", str(row["หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"])))
            color = "#B91C1C" if is_repeated else "#2563EB"
            impact_val = pd.to_numeric(row["ผลกระทบ(นาที)"], errors="coerce")
            impact_val = int(impact_val) if pd.notna(impact_val) else 0

            popup_html = f"""
            <div style="font-family:Sarabun; min-width:250px; padding:6px 4px;">
                <div style="font-size:15px; font-weight:800; color:#0F172A; margin-bottom:6px;">
                    {row["ชื่อเหตุอันตราย"]}
                </div>
                <div style="font-size:13px; color:#334155; line-height:1.7;">
                    <b>สาย:</b> {row["สาย"]}<br>
                    <b>ระหว่างสถานี:</b> {row["ระหว่างสถานี"]}<br>
                    <b>พื้นที่:</b> {row["พื้นที่"]}<br>
                    <b>กม.:</b> {row["ที่ กม."]}<br>
                    <b>วันที่:</b> {convert_to_thai_date(row["วัน/เดือน/ปี"])}<br>
                    <b>ผลกระทบ:</b> {impact_val} นาที
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
                popup=folium.Popup(popup_html, max_width=320)
            ).add_to(m)

    st_folium(m, height=520, use_container_width=True, returned_objects=[], key="thailand_map")
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# TABLE
# ==========================================
st.markdown('<div class="section-wrap">', unsafe_allow_html=True)
st.markdown('<div class="section-title">ทะเบียนประวัติข้อมูลเหตุการณ์ทั้งหมด</div>', unsafe_allow_html=True)
st.dataframe(df_display, use_container_width=True, hide_index=True)
st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# FOOTER
# ==========================================
st.markdown("""
<div class="app-footer">
    <b>ระบบสารสนเทศความปลอดภัย</b><br>
    วิศวกรกำกับการกองทางถาวร ศูนย์ทางถาวร ฝ่ายการช่างโยธา การรถไฟแห่งประเทศไทย<br>
    <span style="color:#94A3B8;">Executive Dashboard - Integrated Excel Schema Version</span>
</div>
""", unsafe_allow_html=True)
