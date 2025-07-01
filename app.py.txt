# %%writefile เป็น Colab magic command ที่ใช้บันทึกเนื้อหา Cell ลงในไฟล์
%%writefile app.py
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- กำหนดค่า Google Sheet ---
# ขอบเขตการอนุญาต (Permissions) สำหรับ Google Sheets API
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# ชื่อไฟล์ Service Account JSON key ที่คุณอัปโหลดไป Colab
# ตรวจสอบให้แน่ใจว่าไฟล์นี้อยู่ใน Colab Session Storage แล้ว และชื่อไฟล์ตรงกัน
# สำหรับการ Deploy บน Streamlit Cloud เราจะจัดการไฟล์นี้ด้วย Streamlit Secrets
SERVICE_ACCOUNT_FILE = 'service_account_key.json' # << ตรวจสอบชื่อไฟล์ของคุณ

# Sheet ID ของ Google Sheet ของคุณ (หาได้จาก URL ของ Google Sheet)
# โปรดเปลี่ยน '16uC4Rj1EohFXhR1mHEMraB4xPafI2WltO4Q8_DL4Zac' เป็น Sheet ID ของคุณเอง
SPREADSHEET_ID = '16uC4Rj1EohFXhR1mHEMraB4xPafI2WltO4Q8_DL4Zac'

# ชื่อ Tab ของ Google Sheet ที่มีข้อมูล (เช่น 'TradeData' หรือ 'Sheet1')
# โปรดเปลี่ยน 'TradeData' เป็นชื่อ Tab ของคุณเอง
SHEET_NAME = 'TradeData'

# --- ฟังก์ชันสำหรับดึงข้อมูลจาก Google Sheet (พร้อม Cache) ---
# @st.cache_data เป็น decorator ของ Streamlit ที่ใช้ Cache ข้อมูล
# เพื่อให้แอปทำงานเร็วขึ้น ไม่ต้องดึงข้อมูลซ้ำบ่อยๆ
@st.cache_data(ttl=300) # Cache ข้อมูล 5 นาที (300 วินาที)
def get_data_from_sheet():
    """ดึงข้อมูลทั้งหมดจาก Google Sheet ที่ระบุโดยใช้ Service Account."""
    try:
        # สร้าง Credentials จากไฟล์ Service Account JSON key
        # สำหรับ Streamlit Cloud, เราจะโหลดจาก st.secrets แทน
        if st.secrets.get("gspread_service_account_credentials"):
            # โหลดจาก Streamlit Secrets
            creds_json = st.secrets["gspread_service_account_credentials"]
            creds = ServiceAccountCredentials.from_json(creds_json, SCOPE)
        else:
            # โหลดจากไฟล์ JSON (สำหรับ Colab หรือ Local Testing)
            creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPE)
            
        # ให้สิทธิ์ gspread ในการเข้าถึง Google Sheets
        client = gspread.authorize(creds)

        # เปิด Spreadsheet และเลือก Worksheet (Tab)
        spreadsheet = client.open_by_id(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(SHEET_NAME)

        # ดึงข้อมูลทั้งหมดเป็น list of lists
        data = worksheet.get_all_values()

        # แปลงเป็น Pandas DataFrame (แถวแรกเป็น Header)
        df = pd.DataFrame(data[1:], columns=data[0])

        # แปลงคอลัมน์ 'นำเข้า', 'ส่งออก', 'ปี พ.ศ.' ให้เป็นตัวเลข
        numeric_cols = ['นำเข้า', 'ส่งออก', 'ปี พ.ศ.']
        for col in numeric_cols:
            if col in df.columns:
                # errors='coerce' จะเปลี่ยนค่าที่ไม่สามารถแปลงเป็นตัวเลขได้ให้เป็น NaN
                # fillna(0) จะแทนที่ NaN ด้วย 0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        st.success("โหลดข้อมูลจาก Google Sheet สำเร็จ!")
        return df
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"เกิดข้อผิดพลาด: ไม่พบ Spreadsheet ID '{SPREADSHEET_ID}' หรือชื่อชีต '{SHEET_NAME}'")
        st.info("โปรดตรวจสอบ SPREADSHEET_ID และ SHEET_NAME ในโค้ด")
        return pd.DataFrame() # คืน DataFrame ว่างเปล่า
    except FileNotFoundError:
        st.error(f"เกิดข้อผิดพลาด: ไม่พบไฟล์ Service Account JSON ที่ชื่อ '{SERVICE_ACCOUNT_FILE}'")
        st.info("โปรดตรวจสอบว่าคุณได้อัปโหลดไฟล์ '{SERVICE_ACCOUNT_FILE}' ไปยัง Colab แล้ว และชื่อไฟล์ถูกต้อง")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
        st.info("โปรดตรวจสอบว่า Service Account มีสิทธิ์เข้าถึง Google Sheet และการเชื่อมต่อถูกต้อง")
        return pd.DataFrame()

# --- สร้าง Streamlit UI ---
st.set_page_config(layout="wide", page_title="แดชบอร์ดข้อมูลการค้า") # ตั้งค่าหน้ากว้างขึ้นและชื่อหน้า
st.title('📊 แดชบอร์ดข้อมูลการค้าระหว่างประเทศ')

# ดึงข้อมูล
df = get_data_from_sheet()

if not df.empty:
    st.sidebar.header("ตัวเลือกการวิเคราะห์และค้นหา")

    # ตัวเลือกการวิเคราะห์
    analysis_type = st.sidebar.selectbox(
        "เลือกประเภทการวิเคราะห์:",
        ("ภาพรวม", "การวิเคราะห์สินค้า", "การวิเคราะห์ประเทศคู่ค้า", "การวิเคราะห์พิกัดศุลกากร")
    )

    # ตัวกรองข้อมูลหลัก
    st.sidebar.subheader("ตัวกรองข้อมูล")
    selected_country = st.sidebar.text_input('ค้นหาชื่อประเทศ (บางส่วน)')
    selected_hs_code = st.sidebar.text_input('ค้นหาพิกัดศุลกากร (บางส่วน)')
    selected_item = st.sidebar.text_input('ค้นหารายการสินค้า (บางส่วน)')
    selected_year = st.sidebar.text_input('ค้นหาปี พ.ศ. (เช่น 2564)')

    # กรองข้อมูลตามเงื่อนไขที่ผู้ใช้ระบุ
    filtered_df = df.copy()

    if selected_country:
        filtered_df = filtered_df[filtered_df['ชื่อประเทศ'].astype(str).str.contains(selected_country.strip(), case=False, na=False)]
    if selected_hs_code:
        filtered_df = filtered_df[filtered_df['พิกัดศุลกากร'].astype(str).str.contains(selected_hs_code.strip(), case=False, na=False)]
    if selected_item:
        filtered_df = filtered_df[filtered_df['รายการสินค้า'].astype(str).str.contains(selected_item.strip(), case=False, na=False)]
    if selected_year:
        filtered_df = filtered_df[filtered_df['ปี พ.ศ.'].astype(str).str.contains(selected_year.strip(), case=False, na=False)]

    st.subheader(f"ข้อมูลที่กรองแล้ว ({len(filtered_df)} แถว)")
    st.dataframe(filtered_df, use_container_width=True)

    # --- ส่วนแสดงผลกราฟตามประเภทการวิเคราะห์ที่เลือก ---
    st.header(analysis_type)

    if filtered_df.empty:
        st.warning("ไม่พบข้อมูลตามเงื่อนไขที่เลือก กรุณาลองเลือกใหม่.")
    else:
        # ฟังก์ชันช่วยสร้างกราฟหลัก (Bar/Line Chart)
        def create_trade_chart(df_data, group_col, title):
            summary_df = df_data.groupby(group_col)[['นำเข้า', 'ส่งออก']].sum().reset_index()
            fig = go.Figure(data=[
                go.Bar(name='นำเข้า', x=summary_df[group_col], y=summary_df['นำเข้า']),
                go.Bar(name='ส่งออก', x=summary_df[group_col], y=summary_df['ส่งออก'])
            ])
            fig.update_layout(barmode='group', title_text=title)
            return fig

        # ฟังก์ชันช่วยสร้างกราฟ Top N (Bar Chart)
        def create_top_n_chart(df_data, col_name, value_col, title, top_n=10):
            if col_name not in df_data.columns:
                st.warning(f"ไม่พบคอลัมน์ '{col_name}' ในข้อมูล.")
                return go.Figure()
            summary = df_data.groupby(col_name)[value_col].sum().nlargest(top_n).reset_index()
            fig = px.bar(summary, x=col_name, y=value_col, title=title)
            fig.update_xaxes(title_text=col_name)
            fig.update_yaxes(title_text=value_col)
            return fig
            
        # ฟังก์ชันช่วยสร้างกราฟดุลการค้า (Column Chart)
        def create_balance_chart(df_data, group_col, title, top_n=10):
            if group_col not in df_data.columns:
                st.warning(f"ไม่พบคอลัมน์ '{group_col}' ในข้อมูล.")
                return go.Figure()
            summary_df = df_data.groupby(group_col)[['นำเข้า', 'ส่งออก']].sum().reset_index()
            summary_df['ดุลการค้า'] = summary_df['ส่งออก'] - summary_df['นำเข้า']
            
            # Sort by absolute balance to show top imbalances (both surplus and deficit)
            summary_df_sorted = summary_df.loc[summary_df['ดุลการค้า'].abs().nlargest(top_n).index]

            fig = px.bar(summary_df_sorted, x=group_col, y='ดุลการค้า', title=title,
                         color='ดุลการค้า', color_continuous_scale=px.colors.sequential.RdBu)
            fig.update_xaxes(title_text=group_col)
            fig.update_yaxes(title_text='ดุลการค้า')
            return fig


        if analysis_type == "ภาพรวม":
            st.subheader("ภาพรวมการค้า")
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(create_top_n_chart(filtered_df, 'ชื่อประเทศ', 'นำเข้า', '10 อันดับแรกประเทศคู่ค้า (นำเข้า)'), use_container_width=True)
            with col2:
                st.plotly_chart(create_top_n_chart(filtered_df, 'ชื่อประเทศ', 'ส่งออก', '10 อันดับแรกประเทศคู่ค้า (ส่งออก)'), use_container_width=True)

            # กราฟแนวโน้มการนำเข้า-ส่งออกรายปี
            if 'ปี พ.ศ.' in filtered_df.columns:
                yearly_summary = filtered_df.groupby('ปี พ.ศ.')[['นำเข้า', 'ส่งออก']].sum().reset_index().sort_values(by='ปี พ.ศ.')
                fig = px.line(yearly_summary, x='ปี พ.ศ.', y=['นำเข้า', 'ส่งออก'], title='แนวโน้มการนำเข้า-ส่งออกรายปี')
                fig.update_xaxes(type='category') # ให้แกน X เป็น Category สำหรับปี พ.ศ.
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("ไม่พบคอลัมน์ 'ปี พ.ศ.' สำหรับกราฟแนวโน้มรายปี.")


        elif analysis_type == "การวิเคราะห์สินค้า":
            st.subheader("การวิเคราะห์สินค้า (รายการสินค้า)")
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(create_top_n_chart(filtered_df, 'รายการสินค้า', 'นำเข้า', '10 อันดับแรกสินค้า (นำเข้า)'), use_container_width=True)
            with col2:
                st.plotly_chart(create_top_n_chart(filtered_df, 'รายการสินค้า', 'ส่งออก', '10 อันดับแรกสินค้า (ส่งออก)'), use_container_width=True)
            
            st.plotly_chart(create_balance_chart(filtered_df, 'รายการสินค้า', 'ดุลการค้า 10 อันดับแรกของรายการสินค้า'), use_container_width=True)

        elif analysis_type == "การวิเคราะห์ประเทศคู่ค้า":
            st.subheader("การวิเคราะห์ประเทศคู่ค้า")
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(create_top_n_chart(filtered_df, 'ชื่อประเทศ', 'นำเข้า', '10 อันดับแรกประเทศคู่ค้า (นำเข้า)'), use_container_width=True)
            with col2:
                st.plotly_chart(create_top_n_chart(filtered_df, 'ชื่อประเทศ', 'ส่งออก', '10 อันดับแรกประเทศคู่ค้า (ส่งออก)'), use_container_width=True)
            
            st.plotly_chart(create_balance_chart(filtered_df, 'ชื่อประเทศ', 'ดุลการค้า 10 อันดับแรกของประเทศคู่ค้า'), use_container_width=True)

        elif analysis_type == "การวิเคราะห์พิกัดศุลกากร":
            st.subheader("การวิเคราะห์พิกัดศุลกากร")
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(create_top_n_chart(filtered_df, 'พิกัดศุลกากร', 'นำเข้า', '10 อันดับแรกพิกัดศุลกากร (นำเข้า)'), use_container_width=True)
            with col2:
                st.plotly_chart(create_top_n_chart(filtered_df, 'พิกัดศุลกากร', 'ส่งออก', '10 อันดับแรกพิกัดศุลกากร (ส่งออก)'), use_container_width=True)
            
            st.plotly_chart(create_balance_chart(filtered_df, 'พิกัดศุลกากร', 'ดุลการค้า 10 อันดับแรกของพิกัดศุลกากร'), use_container_width=True)

else:
    st.info("ไม่สามารถโหลดข้อมูลได้ โปรดตรวจสอบการตั้งค่า Service Account และ Google Sheet ID/Sheet Name.")
