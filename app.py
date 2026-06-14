import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import datetime
import plotly.express as px
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

REQUIRED_COLUMNS = [
    "ชื่อเหตุอันตราย",
    "พื้นที่",
    "ที่ กม.",
    "วัน/เดือน/ปี",
    "เวลา ที่เกิดเหตุ",
    "ค่าใช้จ่าย",
    "Latitude",
    "Longitude",
    "ผลกระทบ(นาที)",
    "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"
]

# ขอบเขตประเทศไทยโดยประมาณ (ใช้สำหรับจำกัดการ pan/zoom)
THAILAND_BOUNDS = [[5.6, 97.3], [20.5, 105.7]]
THAILAND_CENTER = [13.7367, 100.5231]
THAILAND_DEFAULT_ZOOM = 6

# โลโก้ฝ่ายการช่างโยธา การรถไฟแห่งประเทศไทย
LOGO_URL = "[upload.wikimedia.org](https://upload.wikimedia.org/wikipedia/commons/thumb/3/35/State_Railway_of_Thailand_Logo.svg/200px-State_Railway_of_Thailand_Logo.svg.png)"

# ==========================================
# HELPERS
# ==========================================
def convert_to_thai_date(date_str):
    try:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                dt = datetime.datetime.strptime(str(date_str).strip(), fmt)
                return f"{dt.day} {THAI_MONTHS[dt.month - 1]} {dt.year + 543}"
            except ValueError:
                continue

        dt = pd.to_datetime(date_str, errors="coerce")
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
        "ชื่อเหตุอันตราย",
        "พื้นที่",
        "ที่ กม.",
        "วัน/เดือน/ปี",
        "เวลา ที่เกิดเหตุ",
        "ค่าใช้จ่าย",
        "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"
    ]
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()

    df["พื้นที่"] = df["พื้นที่"].replace("nan", "")
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
    """โหลดและจัด sort ข้อมูล โดย cache ตาม mtime ของไฟล์
    เมื่อไฟล์เปลี่ยนแปลง cache จะถูก invalidate อัตโนมัติ
    """
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
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
        df.to_csv(file_path, index=False)

    df = clean_dataframe(df)
    df["temp_date"] = pd.to_datetime(df["วัน/เดือน/ปี"], errors="coerce")
    df["temp_time"] = pd.to_datetime(df["เวลา ที่เกิดเหตุ"], format="%H:%M", errors="coerce")
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
    drop_cols = [col for col in ["temp_date", "temp_time"] if col in display_df.columns]
    display_df = display_df.drop(columns=drop_cols, errors="ignore")
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


def apply_filters(df, areas, date_range, repeat_mode):
    filtered = df.copy()

    if areas:
        filtered = filtered[filtered["พื้นที่"].isin(areas)]

    if date_range and len(date_range) == 2 and all(date_range):
        start_date, end_date = date_range
        mask = (
            (filtered["temp_date"].dt.date >= start_date) &
            (filtered["temp_date"].dt.date <= end_date)
        )
        filtered = filtered[mask]

    if repeat_mode == "เฉพาะจุดซ้ำ":
        filtered = filtered[filtered["หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"].astype(str).str.contains("ซ้ำ", na=False)]
    elif repeat_mode == "ไม่รวมจุดซ้ำ":
        filtered = filtered[~filtered["หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"].astype(str).str.contains("ซ้ำ", na=False)]

    return filtered


# ==========================================
# SESSION STATE INIT
# ==========================================
if "flash_message" not in st.session_state:
    st.session_state["flash_message"] = None
if "data_version" not in st.session_state:
    st.session_state["data_version"] = 0

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

/* บังคับให้หน้าจอมี scrollbar แนวตั้งตลอดเวลา และ scrollbar สวยขึ้น */
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

::-webkit-scrollbar-thumb:hover {{
    background: linear-gradient(180deg, #1E40AF 0%, #1D4ED8 100%);
}}

* {{
    scrollbar-width: thin;
    scrollbar-color: #2563EB #F1F5F9;
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
    padding: 28px 34px 24px 34px;
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
    letter-spacing: -0.3px;
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

# ==========================================
# SIDEBAR - ADMIN PANEL
# ==========================================
with st.sidebar:
    st.markdown(
        f"""
        <div class="sidebar-logo">
            <img src="{LOGO_URL}" alt="โลโก้ฝ่ายการช่างโยธา"/>
            <div class="sidebar-org">ฝ่ายการช่างโยธา<br/>การรถไฟแห่งประเทศไทย</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("## ⚙️ ศูนย์จัดการข้อมูล")
    st.caption("สำหรับเจ้าหน้าที่บันทึกและปรับปรุงข้อมูลระบบ")

    admin_mode = st.toggle("เปิดโหมดผู้ดูแลระบบ", value=False)

    if admin_mode:
        st.markdown("---")

        if st.session_state.get("flash_message"):
            msg_type, msg_text = st.session_state["flash_message"]
            if msg_type == "success":
                st.success(msg_text)
            elif msg_type == "warning":
                st.warning(msg_text)
            elif msg_type == "error":
                st.error(msg_text)
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
                        if st.button("➕ ผสานข้อมูลเข้าระบบ", type="secondary", use_container_width=True, key="merge_btn"):
                            df_new_clean = clean_dataframe(df_new[REQUIRED_COLUMNS])
                            combined_df, removed = deduplicate_combined(df_base[REQUIRED_COLUMNS], df_new_clean)
                            save_data(combined_df)
                            st.session_state["flash_message"] = (
                                "success",
                                f"ผสานข้อมูลสำเร็จ ตัดข้อมูลซ้ำออก {removed} รายการ"
                            )
                            st.rerun()

                except Exception as e:
                    st.error(f"อ่านไฟล์ไม่ได้: {e}")

        with st.expander("📝 เพิ่มเหตุการณ์ใหม่", expanded=False):
            with st.form("realtime_input_form", clear_on_submit=True):
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

                submitted = st.form_submit_button("💾 บันทึกเหตุการณ์ใหม่", use_container_width=True)

                if submitted:
                    if not input_name.strip() or not input_area.strip() or not input_km.strip():
                        st.error("กรุณากรอกชื่อเหตุ, พื้นที่, ที่ กม. ให้ครบ")
                    else:
                        new_row = pd.DataFrame([{
                            "ชื่อเหตุอันตราย": input_name.strip(),
                            "พื้นที่": input_area.strip(),
                            "ที่ กม.": input_km.strip(),
                            "วัน/เดือน/ปี": input_date.strftime("%Y-%m-%d"),
                            "เวลา ที่เกิดเหตุ": input_time.strftime("%H:%M"),
                            "ค่าใช้จ่าย": input_cost.strip() if str(input_cost).strip() else "ไม่มีค่าใช้จ่าย",
                            "Latitude": input_lat,
                            "Longitude": input_lon,
                            "ผลกระทบ(นาที)": input_impact,
                            "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)": input_remark.strip()
                        }])

                        new_row = clean_dataframe(new_row)
                        combined_df, removed = deduplicate_combined(df_base[REQUIRED_COLUMNS], new_row)

                        if removed > 0:
                            st.session_state["flash_message"] = (
                                "warning",
                                "ข้อมูลนี้ซ้ำกับรายการที่มีอยู่แล้วในระบบ ไม่ได้บันทึกซ้ำ"
                            )
                        else:
                            save_data(combined_df)
                            st.session_state["flash_message"] = ("success", "เพิ่มข้อมูลใหม่เรียบร้อยแล้ว")
                        st.rerun()
    else:
        st.info("โหมดผู้ดูแลระบบถูกปิดอยู่")

# ==========================================
# HERO HEADER (with logo)
# ==========================================
last_update = get_thai_datetime_now()

st.markdown(f"""
<div class="dashboard-hero">
    <div class="hero-flex">
        <div class="hero-logo">
            <img src="{LOGO_URL}" alt="โลโก้ฝ่ายการช่างโยธา"/>
        </div>
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
# FILTER BAR (TOP)
# ==========================================
st.markdown('<div class="section-wrap">', unsafe_allow_html=True)
st.markdown('<div class="section-title">🔎 ตัวกรองข้อมูล</div>', unsafe_allow_html=True)

filter_col1, filter_col2, filter_col3 = st.columns([1.4, 1.4, 1])

with filter_col1:
    min_date = df_base["temp_date"].min()
    max_date = df_base["temp_date"].max()

    if pd.notna(min_date) and pd.notna(max_date):
        date_range = st.date_input(
            "ช่วงวันที่",
            value=(min_date.date(), max_date.date()),
            key="filter_date"
        )
    else:
        today = datetime.date.today()
        date_range = st.date_input("ช่วงวันที่", value=(today, today), key="filter_date")

with filter_col2:
    area_options = sorted([a for a in df_base["พื้นที่"].dropna().unique() if str(a).strip() != ""])
    selected_areas = st.multiselect("พื้นที่ / แขวง", options=area_options, default=area_options, key="filter_area")

with filter_col3:
    repeat_mode = st.selectbox(
        "จุดเกิดเหตุซ้ำ",
        ["ทั้งหมด", "เฉพาะจุดซ้ำ", "ไม่รวมจุดซ้ำ"],
        key="filter_repeat"
    )

df_filtered = apply_filters(df_base, selected_areas, date_range, repeat_mode)

st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# Prepare derived data (จาก filter)
# ==========================================
repeated_mask = df_filtered["หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"].astype(str).str.contains("ซ้ำ", na=False)
df_repeated = df_filtered[repeated_mask].copy()

df_display = build_display_table(df_filtered)
df_repeated_display = build_display_table(df_repeated)

delay_sum = int(df_filtered["ผลกระทบ(นาที)"].sum()) if not df_filtered.empty else 0
highest_risk_area = (
    df_filtered["พื้นที่"].mode().iloc[0]
    if not df_filtered.empty and not df_filtered["พื้นที่"].mode().empty
    else "-"
)

# ==========================================
# KPI SECTION
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

show_repeated = st.toggle("แสดงรายละเอียดจุดเกิดเหตุซ้ำ", value=True, key="toggle_repeated")

if show_repeated and not df_repeated_display.empty:
    st.dataframe(df_repeated_display, use_container_width=True, hide_index=True)

st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# CHART + MAP (focus on Thailand)
# ==========================================
left_col, right_col = st.columns([1.05, 1.15])

with left_col:
    st.markdown('<div class="section-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">การกระจายเหตุการณ์ตามพื้นที่</div>', unsafe_allow_html=True)

    if not df_filtered.empty:
        area_counts = df_filtered["พื้นที่"].value_counts().reset_index()
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
            color_continuous_scale=["#DBEAFE", "#60A5FA", "#1D4ED8"]
        )

        fig.update_layout(
            height=dynamic_height,
            margin=dict(l=10, r=20, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Sarabun", size=14, color="#0F172A"),
            coloraxis_showscale=False,
            xaxis=dict(title=None, showgrid=True, gridcolor="#E2E8F0", zeroline=False),
            yaxis=dict(title=None, showgrid=False)
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
    st.markdown('<div class="section-title">🗺️ แผนที่ภาพรวมประเทศไทย</div>', unsafe_allow_html=True)

    m = folium.Map(
        location=THAILAND_CENTER,
        zoom_start=THAILAND_DEFAULT_ZOOM,
        min_zoom=5,
        max_zoom=18,
        max_bounds=True,
        tiles="CartoDB positron"
    )

    # จำกัดขอบเขตแผนที่เฉพาะประเทศไทย
    m.fit_bounds(THAILAND_BOUNDS)
    m.options["maxBounds"] = THAILAND_BOUNDS
    m.options["maxBoundsViscosity"] = 1.0

    for _, row in df_filtered.iterrows():
        if pd.notna(row["Latitude"]) and pd.notna(row["Longitude"]):
            is_repeated = "ซ้ำ" in str(row["หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"])
            color = "#B91C1C" if is_repeated else "#2563EB"

            impact_val = pd.to_numeric(row["ผลกระทบ(นาที)"], errors="coerce")
            impact_val = int(impact_val) if pd.notna(impact_val) else 0

            popup_html = f"""
            <div style="font-family:Sarabun; min-width:220px; padding:6px 4px;">
                <div style="font-size:15px; font-weight:800; color:#0F172A; margin-bottom:6px;">
                    {row["ชื่อเหตุอันตราย"]}
                </div>
                <div style="font-size:13px; color:#334155; line-height:1.7;">
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
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(m)

    # ใช้ key คงที่ + returned_objects=[] เพื่อลด rerun ระหว่างเลื่อน/ซูม
    st_folium(
        m,
        height=520,
        use_container_width=True,
        returned_objects=[],
        key="thailand_map"
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
# FOOTER
# ==========================================
st.markdown("""
<div class="app-footer">
    <b>ระบบสารสนเทศความปลอดภัย</b><br>
    วิศวกรกำกับการกองทางถาวร ศูนย์ทางถาวร ฝ่ายการช่างโยธา การรถไฟแห่งประเทศไทย<br>
    <span style="color:#94A3B8;">Executive Dashboard - Modern Premium UI</span>
</div>
""", unsafe_allow_html=True)
