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
    initial_sidebar_state="expanded"
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

# ==========================================
# HELPERS
# ==========================================
def parse_date(value):
    if pd.isna(value):
        return pd.NaT
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return pd.to_datetime(datetime.datetime.strptime(str(value).strip(), fmt))
        except ValueError:
            continue
    return pd.to_datetime(value, errors="coerce")


def convert_to_thai_date(date_value):
    try:
        dt = parse_date(date_value)
        if pd.isna(dt):
            return str(date_value)
        return f"{dt.day} {THAI_MONTHS[dt.month - 1]} {dt.year + 543}"
    except Exception:
        return str(date_value)


def convert_to_thai_datetime_now():
    now = datetime.datetime.now()
    return f"{now.day} {THAI_MONTHS[now.month - 1]} {now.year + 543} เวลา {now.strftime('%H:%M')} น."


def load_data():
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

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = None

    df["พื้นที่"] = df["พื้นที่"].astype(str).str.strip()
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df["ผลกระทบ(นาที)"] = pd.to_numeric(df["ผลกระทบ(นาที)"], errors="coerce").fillna(0)
    df["parsed_date"] = df["วัน/เดือน/ปี"].apply(parse_date)
    df["parsed_time"] = pd.to_datetime(df["เวลา ที่เกิดเหตุ"], format="%H:%M", errors="coerce")
    df = df.sort_values(by=["parsed_date", "parsed_time"], ascending=[False, False]).reset_index(drop=True)

    return df


def save_data(df):
    save_df = df.copy()
    drop_cols = [c for c in ["parsed_date", "parsed_time", "severity_score", "severity_level", "year_month"] if c in save_df.columns]
    save_df = save_df.drop(columns=drop_cols, errors="ignore")
    save_df.to_csv(DATA_FILE, index=False)


def build_display_table(df):
    display_df = df.copy()
    display_df["วัน/เดือน/ปี"] = display_df["วัน/เดือน/ปี"].apply(convert_to_thai_date)
    display_df.insert(0, "ลำดับที่", range(1, len(display_df) + 1))
    return display_df


def is_repeated_case(val):
    return "ซ้ำ" in str(val)


def extract_cost_flag(cost_text):
    text = str(cost_text).strip()
    return 0 if text == "ไม่มีค่าใช้จ่าย" or text == "" or text == "nan" else 1


def compute_severity_score(row):
    delay = pd.to_numeric(row.get("ผลกระทบ(นาที)", 0), errors="coerce")
    delay = 0 if pd.isna(delay) else float(delay)

    repeated = 1 if is_repeated_case(row.get("หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)", "")) else 0
    cost_flag = extract_cost_flag(row.get("ค่าใช้จ่าย", ""))

    delay_score = min(delay, 120) / 120 * 60
    repeated_score = 25 if repeated else 0
    cost_score = 15 if cost_flag else 0

    total = round(delay_score + repeated_score + cost_score, 1)

    if total >= 75:
        level = "สูงมาก"
    elif total >= 50:
        level = "สูง"
    elif total >= 25:
        level = "ปานกลาง"
    else:
        level = "ต่ำ"

    return total, level


def add_analytics(df):
    if df.empty:
        df["severity_score"] = []
        df["severity_level"] = []
        return df

    scores = df.apply(compute_severity_score, axis=1)
    df["severity_score"] = [s[0] for s in scores]
    df["severity_level"] = [s[1] for s in scores]
    df["year_month"] = df["parsed_date"].dt.to_period("M").astype(str)
    return df


def get_duplicate_key(df):
    temp = df.copy()
    temp["dup_key"] = (
        temp["ชื่อเหตุอันตราย"].astype(str).str.strip().str.lower() + "|" +
        temp["พื้นที่"].astype(str).str.strip().str.lower() + "|" +
        temp["ที่ กม."].astype(str).str.strip().str.lower() + "|" +
        temp["วัน/เดือน/ปี"].astype(str).str.strip() + "|" +
        temp["เวลา ที่เกิดเหตุ"].astype(str).str.strip()
    )
    return temp


def deduplicate_combined(existing_df, new_df):
    existing = get_duplicate_key(existing_df)
    incoming = get_duplicate_key(new_df)
    combined = pd.concat([existing, incoming], ignore_index=True)
    before = len(combined)
    combined = combined.drop_duplicates(subset=["dup_key"], keep="first")
    removed = before - len(combined)
    combined = combined.drop(columns=["dup_key"], errors="ignore")
    return combined, removed


def validate_input_record(record):
    errors = []

    if not str(record.get("ชื่อเหตุอันตราย", "")).strip():
        errors.append("กรุณาระบุชื่อเหตุอันตราย")
    if not str(record.get("พื้นที่", "")).strip():
        errors.append("กรุณาระบุพื้นที่")
    if not str(record.get("ที่ กม.", "")).strip():
        errors.append("กรุณาระบุที่ กม.")
    if pd.isna(parse_date(record.get("วัน/เดือน/ปี", None))):
        errors.append("กรุณาระบุวัน/เดือน/ปี ให้ถูกต้อง")
    if not str(record.get("เวลา ที่เกิดเหตุ", "")).strip():
        errors.append("กรุณาระบุเวลา ที่เกิดเหตุ")

    lat = pd.to_numeric(record.get("Latitude", None), errors="coerce")
    lon = pd.to_numeric(record.get("Longitude", None), errors="coerce")
    impact = pd.to_numeric(record.get("ผลกระทบ(นาที)", None), errors="coerce")

    if pd.isna(lat) or lat < -90 or lat > 90:
        errors.append("Latitude ไม่ถูกต้อง")
    if pd.isna(lon) or lon < -180 or lon > 180:
        errors.append("Longitude ไม่ถูกต้อง")
    if pd.isna(impact) or impact < 0:
        errors.append("ผลกระทบ(นาที) ต้องเป็นตัวเลขตั้งแต่ 0 ขึ้นไป")

    return errors


def validate_uploaded_dataframe(df_new):
    errors = []

    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df_new.columns]
    if missing_cols:
        errors.append(f"ไฟล์ขาดคอลัมน์ที่จำเป็น: {', '.join(missing_cols)}")
        return errors

    for idx, row in df_new.iterrows():
        row_errors = validate_input_record(row.to_dict())
        if row_errors:
            errors.append(f"แถวที่ {idx + 1}: " + " | ".join(row_errors))

    return errors


def render_metric_card(title, value, subtitle, icon):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-header">
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
bg_url = "[images.unsplash.com](https://images.unsplash.com/photo-1517420879524-86d64ac2f339?q=80&w=2000&auto=format&fit=crop)"

st.markdown(f"""
<style>
@import url('[fonts.googleapis.com](https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;500;600;700;800&display=swap)');

html, body, [class*="css"], .stApp {{
    font-family: 'Sarabun', sans-serif !important;
}}

#MainMenu, footer, header {{
    visibility: hidden;
}}

.stApp {{
    background:
        linear-gradient(180deg, rgba(248,250,252,0.96) 0%, rgba(241,245,249,0.98) 100%),
        url("{bg_url}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}

.block-container {{
    max-width: 1600px;
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}}

.dashboard-hero {{
    background: linear-gradient(135deg, rgba(15,23,42,0.96) 0%, rgba(30,58,138,0.93) 50%, rgba(8,145,178,0.88) 100%);
    border-radius: 24px;
    padding: 30px 34px;
    color: white;
    box-shadow: 0 20px 40px rgba(15,23,42,0.18);
    margin-bottom: 22px;
}}

.hero-title {{
    font-size: 34px;
    font-weight: 800;
    line-height: 1.25;
    margin-bottom: 6px;
}}

.hero-subtitle {{
    font-size: 16px;
    color: rgba(255,255,255,0.88);
    margin-bottom: 14px;
}}

.hero-badge {{
    display: inline-block;
    padding: 8px 14px;
    border-radius: 999px;
    background: rgba(255,255,255,0.13);
    border: 1px solid rgba(255,255,255,0.18);
    color: #E2E8F0;
    font-size: 14px;
    font-weight: 500;
}}

.section-title {{
    font-size: 22px;
    font-weight: 800;
    color: #0F172A;
    margin-top: 10px;
    margin-bottom: 12px;
}}

.metric-card {{
    background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
    border: 1px solid #E2E8F0;
    border-radius: 20px;
    padding: 18px;
    box-shadow: 0 10px 24px rgba(15,23,42,0.05);
    min-height: 145px;
}}

.metric-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
}}

.metric-icon {{
    width: 42px;
    height: 42px;
    border-radius: 12px;
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
    font-size: 30px;
    font-weight: 800;
    color: #0F172A;
    line-height: 1.15;
    margin-bottom: 4px;
}}

.metric-subtitle {{
    font-size: 13px;
    color: #64748B;
}}

.panel-card {{
    background: rgba(255,255,255,0.85);
    backdrop-filter: blur(10px);
    border: 1px solid #E2E8F0;
    border-radius: 22px;
    padding: 16px;
    box-shadow: 0 10px 28px rgba(15,23,42,0.05);
    margin-bottom: 18px;
}}

.alert-box {{
    background: linear-gradient(135deg, #FFF1F2 0%, #FFE4E6 100%);
    border: 1px solid #FECDD3;
    border-left: 6px solid #E11D48;
    border-radius: 16px;
    padding: 16px 18px;
    color: #881337;
    font-size: 15px;
    line-height: 1.6;
}}

.info-box {{
    background: linear-gradient(135deg, #EFF6FF 0%, #F0F9FF 100%);
    border: 1px solid #BFDBFE;
    border-left: 6px solid #2563EB;
    border-radius: 16px;
    padding: 16px 18px;
    color: #1E3A8A;
    font-size: 15px;
    line-height: 1.6;
}}

.admin-box {{
    background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
    border: 1px solid #E2E8F0;
    border-radius: 18px;
    padding: 16px;
    box-shadow: 0 10px 24px rgba(15,23,42,0.05);
}}

.stDataFrame, div[data-testid="stDataEditor"], .stPlotlyChart, .leaflet-container {{
    background: #FFFFFF !important;
    border-radius: 18px !important;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0 8px 24px rgba(15,23,42,0.05) !important;
    padding: 8px !important;
}}

.stButton > button, .stDownloadButton > button {{
    border-radius: 12px !important;
    font-weight: 700 !important;
}}

.app-footer {{
    text-align: center;
    padding: 24px;
    margin-top: 36px;
    font-size: 14px;
    color: #64748B;
    border-top: 1px solid #CBD5E1;
}}
</style>
""", unsafe_allow_html=True)

# ==========================================
# LOAD & ANALYTICS
# ==========================================
df_base = load_data()
df_base = add_analytics(df_base)

# ==========================================
# SIDEBAR ADMIN
# ==========================================
with st.sidebar:
    st.markdown("## ⚙️ ศูนย์จัดการข้อมูล (Admin)")
    st.caption("สำหรับเจ้าหน้าที่บันทึกและปรับปรุงข้อมูลระบบ")

    admin_mode = st.toggle("เปิดโหมดผู้ดูแลระบบ", value=False)

    if admin_mode:
        st.markdown("---")
        st.markdown("### ✏️ แก้ไขข้อมูลทั้งชุด")
        edited_df = st.data_editor(
            df_base.drop(columns=["parsed_date", "parsed_time", "severity_score", "severity_level", "year_month"], errors="ignore"),
            use_container_width=True,
            num_rows="dynamic",
            height=320,
            key="admin_editor"
        )

        if st.button("💾 บันทึกข้อมูลที่แก้ไข", use_container_width=True, type="primary"):
            temp_df = edited_df.copy()
            temp_df["parsed_date"] = temp_df["วัน/เดือน/ปี"].apply(parse_date)
            temp_df["parsed_time"] = pd.to_datetime(temp_df["เวลา ที่เกิดเหตุ"], format="%H:%M", errors="coerce")

            validation_errors = []
            for idx, row in temp_df.iterrows():
                errs = validate_input_record(row.to_dict())
                if errs:
                    validation_errors.append(f"แถวที่ {idx + 1}: " + " | ".join(errs))

            if validation_errors:
                for e in validation_errors[:10]:
                    st.error(e)
                if len(validation_errors) > 10:
                    st.error(f"ยังมีข้อผิดพลาดเพิ่มเติมอีก {len(validation_errors) - 10} รายการ")
            else:
                save_data(temp_df)
                st.success("บันทึกข้อมูลเรียบร้อยแล้ว")
                st.rerun()

        st.markdown("---")
        st.markdown("### 📥 นำเข้าข้อมูลจากไฟล์")
        uploaded_file = st.file_uploader("อัปโหลดไฟล์ .csv หรือ .xlsx", type=["csv", "xlsx"])

        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df_new = pd.read_csv(uploaded_file)
                else:
                    df_new = pd.read_excel(uploaded_file)

                st.write("ตัวอย่างข้อมูลที่นำเข้า")
                st.dataframe(df_new.head(), use_container_width=True, hide_index=True)

                upload_errors = validate_uploaded_dataframe(df_new)

                if upload_errors:
                    for e in upload_errors[:10]:
                        st.error(e)
                    if len(upload_errors) > 10:
                        st.error(f"ยังมีข้อผิดพลาดเพิ่มเติมอีก {len(upload_errors) - 10} รายการ")
                else:
                    if st.button("➕ ผสานข้อมูลเข้าระบบ", use_container_width=True):
                        combined_df, removed_dup = deduplicate_combined(
                            df_base.drop(columns=["parsed_date", "parsed_time", "severity_score", "severity_level", "year_month"], errors="ignore"),
                            df_new
                        )
                        save_data(combined_df)
                        st.success(f"ผสานข้อมูลสำเร็จ และตัดข้อมูลซ้ำออก {removed_dup} รายการ")
                        st.rerun()

            except Exception as e:
                st.error(f"ไม่สามารถอ่านไฟล์ได้: {e}")

        st.markdown("---")
        st.markdown("### 📝 เพิ่มเหตุการณ์ใหม่")
        with st.form("manual_input_form"):
            input_name = st.text_input("ชื่อเหตุอันตราย")
            input_area = st.text_input("พื้นที่")
            input_km = st.text_input("ที่ กม.")

            c1, c2 = st.columns(2)
            with c1:
                input_date = st.date_input("วัน/เดือน/ปี")
                input_lat = st.number_input("Latitude", value=13.73670, format="%.5f")
                input_impact = st.number_input("ผลกระทบ(นาที)", min_value=0, step=1)
            with c2:
                input_time = st.time_input("เวลา ที่เกิดเหตุ", value=datetime.time(12, 0))
                input_lon = st.number_input("Longitude", value=100.52310, format="%.5f")
                input_cost = st.text_input("ค่าใช้จ่าย", value="ไม่มีค่าใช้จ่าย")

            input_remark = st.text_input("หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)", placeholder="ระบุ 'ซ้ำ' หากเป็นจุดเกิดเหตุซ้ำ")

            submitted = st.form_submit_button("💾 บันทึกเหตุการณ์ใหม่", use_container_width=True)

            if submitted:
                new_record = {
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
                }

                validation_errors = validate_input_record(new_record)
                if validation_errors:
                    for e in validation_errors:
                        st.error(e)
                else:
                    new_df = pd.DataFrame([new_record])
                    combined_df, removed_dup = deduplicate_combined(
                        df_base.drop(columns=["parsed_date", "parsed_time", "severity_score", "severity_level", "year_month"], errors="ignore"),
                        new_df
                    )

                    if removed_dup > 0:
                        st.warning("ไม่สามารถบันทึกได้ เนื่องจากข้อมูลนี้ซ้ำกับรายการที่มีอยู่แล้วในระบบ")
                    else:
                        save_data(combined_df)
                        st.success("บันทึกเหตุการณ์ใหม่เรียบร้อยแล้ว")
                        st.rerun()
    else:
        st.info("โหมดผู้ดูแลระบบถูกปิดอยู่")

# ==========================================
# TOP HERO
# ==========================================
st.markdown(f"""
<div class="dashboard-hero">
    <div class="hero-title">🚆 Executive Dashboard: สถานการณ์อุบัติเหตุรถไฟเฉี่ยวชนสัตว์</div>
    <div class="hero-subtitle">รายงานวิเคราะห์เชิงพื้นที่ สถิติ แนวโน้ม และความรุนแรง สำหรับผู้บริหาร</div>
    <div class="hero-badge">อัปเดตล่าสุด: {convert_to_thai_datetime_now()}</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# FILTERS TOP
# ==========================================
st.markdown('<div class="section-title">ตัวกรองข้อมูล</div>', unsafe_allow_html=True)

filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1.3, 1.2, 1, 1])

min_date = df_base["parsed_date"].min()
max_date = df_base["parsed_date"].max()

with filter_col1:
    if pd.notna(min_date) and pd.notna(max_date):
        date_range = st.date_input(
            "ช่วงวันที่",
            value=(min_date.date(), max_date.date())
        )
    else:
        today = datetime.date.today()
        date_range = st.date_input("ช่วงวันที่", value=(today, today))

with filter_col2:
    area_options = sorted([a for a in df_base["พื้นที่"].dropna().unique() if str(a).strip() != ""])
    selected_areas = st.multiselect("พื้นที่", options=area_options, default=area_options)

with filter_col3:
    repeated_only = st.selectbox("เหตุซ้ำ", ["ทั้งหมด", "เฉพาะจุดซ้ำ", "ไม่รวมจุดซ้ำ"])

with filter_col4:
    severity_filter = st.multiselect(
        "ระดับความรุนแรง",
        options=["สูงมาก", "สูง", "ปานกลาง", "ต่ำ"],
        default=["สูงมาก", "สูง", "ปานกลาง", "ต่ำ"]
    )

df_filtered = df_base.copy()

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    df_filtered = df_filtered[
        (df_filtered["parsed_date"].dt.date >= start_date) &
        (df_filtered["parsed_date"].dt.date <= end_date)
    ]

if selected_areas:
    df_filtered = df_filtered[df_filtered["พื้นที่"].isin(selected_areas)]

if repeated_only == "เฉพาะจุดซ้ำ":
    df_filtered = df_filtered[df_filtered["หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"].apply(is_repeated_case)]
elif repeated_only == "ไม่รวมจุดซ้ำ":
    df_filtered = df_filtered[~df_filtered["หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"].apply(is_repeated_case)]

if severity_filter:
    df_filtered = df_filtered[df_filtered["severity_level"].isin(severity_filter)]
else:
    df_filtered = df_filtered.iloc[0:0]

df_display = build_display_table(df_filtered)
df_repeated = df_filtered[df_filtered["หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"].apply(is_repeated_case)].copy()
df_repeated_display = build_display_table(df_repeated)

# ==========================================
# KPI SECTION
# ==========================================
st.markdown('<div class="section-title">ภาพรวมตัวชี้วัดสำคัญ</div>', unsafe_allow_html=True)

total_cases = len(df_filtered)
repeated_cases = len(df_repeated)
delay_sum = int(df_filtered["ผลกระทบ(นาที)"].sum()) if not df_filtered.empty else 0
top_area = df_filtered["พื้นที่"].mode().iloc[0] if not df_filtered.empty and not df_filtered["พื้นที่"].mode().empty else "-"
avg_delay = round(df_filtered["ผลกระทบ(นาที)"].mean(), 1) if not df_filtered.empty else 0
repeat_ratio = round((repeated_cases / total_cases) * 100, 1) if total_cases > 0 else 0
avg_severity = round(df_filtered["severity_score"].mean(), 1) if not df_filtered.empty else 0

if not df_filtered.empty and df_filtered["parsed_date"].notna().any():
    latest_dt = df_filtered["parsed_date"].max()
    latest_month_cases = len(df_filtered[
        (df_filtered["parsed_date"].dt.month == latest_dt.month) &
        (df_filtered["parsed_date"].dt.year == latest_dt.year)
    ])
else:
    latest_month_cases = 0

kpi_row1 = st.columns(4)
with kpi_row1[0]:
    render_metric_card("เหตุการณ์สะสม", f"{total_cases}", "จำนวนเหตุการณ์ตามเงื่อนไขที่เลือก", "🚨")
with kpi_row1[1]:
    render_metric_card("พิกัดเกิดเหตุซ้ำ", f"{repeated_cases}", "จุดเฝ้าระวังในรัศมี ± 3 Km", "📍")
with kpi_row1[2]:
    render_metric_card("พื้นที่วิกฤตสูงสุด", top_area, "พื้นที่ที่พบเหตุบ่อยที่สุด", "⚠️")
with kpi_row1[3]:
    render_metric_card("ความล่าช้ารวม", f"{delay_sum} นาที", "ผลกระทบรวมต่อการเดินขบวน", "⏱️")

kpi_row2 = st.columns(4)
with kpi_row2[0]:
    render_metric_card("ผลกระทบเฉลี่ย", f"{avg_delay} นาที", "ค่าเฉลี่ยต่อเหตุการณ์", "📊")
with kpi_row2[1]:
    render_metric_card("เหตุเดือนล่าสุด", f"{latest_month_cases}", "จำนวนเหตุในเดือนล่าสุดของข้อมูลที่กรอง", "🗓️")
with kpi_row2[2]:
    render_metric_card("สัดส่วนเหตุซ้ำ", f"{repeat_ratio}%", "เทียบกับเหตุการณ์ทั้งหมด", "🔁")
with kpi_row2[3]:
    render_metric_card("Severity เฉลี่ย", f"{avg_severity}", "คะแนนความรุนแรงเฉลี่ย", "🔥")

# ==========================================
# ALERT / WATCHLIST
# ==========================================
st.markdown('<div class="section-title">พื้นที่เฝ้าระวังพิเศษ</div>', unsafe_allow_html=True)

if repeated_cases > 0:
    st.markdown(
        f"""
        <div class="alert-box">
            <b>ข้อสังเกตเชิงบริหาร:</b> พบจุดเกิดเหตุซ้ำจำนวน <b>{repeated_cases} แห่ง</b>
            ภายใต้ข้อมูลที่กรองอยู่ในขณะนี้ ซึ่งควรใช้เป็นพื้นที่เป้าหมายในการกำหนดมาตรการเฝ้าระวัง
            ติดตามแนวโน้ม และเร่งลดความเสี่ยงเชิงพื้นที่
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown(
        """
        <div class="info-box">
            <b>สถานะปัจจุบัน:</b> ไม่พบจุดเกิดเหตุซ้ำภายใต้เงื่อนไขข้อมูลที่เลือก
        </div>
        """,
        unsafe_allow_html=True
    )

show_repeated = st.toggle("แสดงรายละเอียดจุดเกิดเหตุซ้ำ", value=True)
if show_repeated and not df_repeated_display.empty:
    st.dataframe(df_repeated_display, use_container_width=True, hide_index=True)

# ==========================================
# CHARTS
# ==========================================
st.markdown('<div class="section-title">การวิเคราะห์ข้อมูลเชิงภาพ</div>', unsafe_allow_html=True)

col_chart1, col_chart2 = st.columns([1.05, 1.15])

with col_chart1:
    if not df_filtered.empty:
        area_counts = df_filtered["พื้นที่"].value_counts().reset_index()
        area_counts.columns = ["พื้นที่", "จำนวนเหตุการณ์"]
        area_counts = area_counts.sort_values(by="จำนวนเหตุการณ์", ascending=True)

        fig_area = px.bar(
            area_counts,
            x="จำนวนเหตุการณ์",
            y="พื้นที่",
            orientation="h",
            text="จำนวนเหตุการณ์",
            color="จำนวนเหตุการณ์",
            color_continuous_scale=["#DBEAFE", "#60A5FA", "#1D4ED8"]
        )
        fig_area.update_layout(
            height=max(360, len(area_counts) * 48),
            margin=dict(l=10, r=20, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Sarabun", size=14),
            coloraxis_showscale=False,
            xaxis=dict(title=None, showgrid=True, gridcolor="#E2E8F0"),
            yaxis=dict(title=None, showgrid=False)
        )
        fig_area.update_traces(textposition="outside")
        st.plotly_chart(fig_area, use_container_width=True)
    else:
        st.info("ไม่พบข้อมูลสำหรับสร้างกราฟพื้นที่")

with col_chart2:
    valid_coords = df_filtered.dropna(subset=["Latitude", "Longitude"])

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

    for _, row in df_filtered.iterrows():
        if pd.notna(row["Latitude"]) and pd.notna(row["Longitude"]):
            is_repeat = is_repeated_case(row["หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"])
            severity = row.get("severity_score", 0)

            if severity >= 75:
                color = "#991B1B"
                radius = 10
            elif severity >= 50:
                color = "#DC2626"
                radius = 8
            elif severity >= 25:
                color = "#F59E0B"
                radius = 7
            else:
                color = "#2563EB"
                radius = 6

            popup_html = f"""
            <div style="font-family:Sarabun; min-width:240px; padding:6px 4px;">
                <div style="font-size:15px; font-weight:800; color:#0F172A; margin-bottom:6px;">
                    {row["ชื่อเหตุอันตราย"]}
                </div>
                <div style="font-size:13px; color:#334155; line-height:1.65;">
                    <b>พื้นที่:</b> {row["พื้นที่"]}<br>
                    <b>กม.:</b> {row["ที่ กม."]}<br>
                    <b>วันที่:</b> {convert_to_thai_date(row["วัน/เดือน/ปี"])}<br>
                    <b>ผลกระทบ:</b> {int(row["ผลกระทบ(นาที)"])} นาที<br>
                    <b>Severity:</b> {row["severity_score"]} ({row["severity_level"]})<br>
                    <b>เหตุซ้ำ:</b> {"ใช่" if is_repeat else "ไม่ใช่"}
                </div>
            </div>
            """

            folium.CircleMarker(
                location=[row["Latitude"], row["Longitude"]],
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.85,
                popup=folium.Popup(popup_html, max_width=320)
            ).add_to(m)

    st_folium(m, height=420, use_container_width=True, returned_objects=[])

# ==========================================
# MONTHLY TREND
# ==========================================
st.markdown('<div class="section-title">แนวโน้มรายเดือน</div>', unsafe_allow_html=True)

if not df_filtered.empty and df_filtered["parsed_date"].notna().any():
    monthly = df_filtered.copy()
    monthly["month_label"] = monthly["parsed_date"].apply(lambda x: f"{x.month:02d}/{x.year + 543}" if pd.notna(x) else "")
    monthly_summary = monthly.groupby("month_label", as_index=False).agg(
        จำนวนเหตุการณ์=("ชื่อเหตุอันตราย", "count"),
        ผลกระทบรวม=("ผลกระทบ(นาที)", "sum"),
        Severityเฉลี่ย=("severity_score", "mean")
    )

    monthly_summary["sort_date"] = pd.to_datetime(
        monthly["parsed_date"].dt.to_period("M").astype(str).drop_duplicates().sort_values().astype(str).tolist(),
        errors="coerce"
    )

    month_map = (
        monthly[["month_label", "parsed_date"]]
        .dropna()
        .assign(month_start=lambda x: x["parsed_date"].dt.to_period("M").dt.to_timestamp())
        .drop_duplicates(subset=["month_label"])
        .sort_values("month_start")
    )

    monthly_summary = monthly_summary.merge(
        month_map[["month_label", "month_start"]],
        on="month_label",
        how="left"
    ).sort_values("month_start")

    fig_month = px.line(
        monthly_summary,
        x="month_label",
        y="จำนวนเหตุการณ์",
        markers=True
    )
    fig_month.update_traces(line=dict(color="#1D4ED8", width=4), marker=dict(size=9))
    fig_month.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Sarabun", size=14),
        xaxis_title="เดือน/ปี พ.ศ.",
        yaxis_title="จำนวนเหตุการณ์",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#E2E8F0")
    )
    st.plotly_chart(fig_month, use_container_width=True)

    st.dataframe(
        monthly_summary[["month_label", "จำนวนเหตุการณ์", "ผลกระทบรวม", "Severityเฉลี่ย"]]
        .rename(columns={
            "month_label": "เดือน/ปี พ.ศ.",
            "Severityเฉลี่ย": "Severity เฉลี่ย"
        }),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("ไม่พบข้อมูลเพียงพอสำหรับสร้างแนวโน้มรายเดือน")

# ==========================================
# SEVERITY TABLE
# ==========================================
st.markdown('<div class="section-title">อันดับความรุนแรงของเหตุการณ์</div>', unsafe_allow_html=True)

if not df_filtered.empty:
    severity_table = df_filtered.copy()
    severity_table["วัน/เดือน/ปี"] = severity_table["วัน/เดือน/ปี"].apply(convert_to_thai_date)
    severity_table = severity_table.sort_values(by=["severity_score", "parsed_date"], ascending=[False, False])

    severity_display = severity_table[[
        "ชื่อเหตุอันตราย",
        "พื้นที่",
        "ที่ กม.",
        "วัน/เดือน/ปี",
        "ผลกระทบ(นาที)",
        "severity_score",
        "severity_level",
        "หมายเหตุ(จุดเกิดเหตุซ้ำ ± 3 Km)"
    ]].rename(columns={
        "severity_score": "Severity Score",
        "severity_level": "ระดับความรุนแรง"
    })

    st.dataframe(severity_display, use_container_width=True, hide_index=True)
else:
    st.info("ไม่พบข้อมูลสำหรับจัดอันดับความรุนแรง")

# ==========================================
# MAIN REGISTRY
# ==========================================
st.markdown('<div class="section-title">ทะเบียนประวัติข้อมูลเหตุการณ์ทั้งหมด</div>', unsafe_allow_html=True)
st.dataframe(df_display, use_container_width=True, hide_index=True)

# ==========================================
# FOOTER
# ==========================================
st.markdown("""
<div class="app-footer">
    <b>ระบบสารสนเทศความปลอดภัย</b><br>
    วิศวกรกำกับการกองทางถาวร ศูนย์ทางถาวร ฝ่ายการช่างโยธา การรถไฟแห่งประเทศไทย<br>
    <span style="color:#94A3B8;">Executive Dashboard - Advanced Analytics Version</span>
</div>
""", unsafe_allow_html=True)
