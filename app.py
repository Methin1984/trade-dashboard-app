# app.py - Streamlit Web App Dashboard for Trade Data

import streamlit as st
import pandas as pd
import gspread
import json # Import json library to parse secrets
import plotly.express as px # Import plotly.express for easier plotting
import plotly.graph_objects as go # Import plotly.graph_objects for general plotting

# --- Google Sheet Configuration ---
# Permissions scope for Google Sheets API
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# File name for Service Account JSON key (used for local/Colab testing)
# For Streamlit Cloud deployment, this file is handled via Streamlit Secrets
SERVICE_ACCOUNT_FILE = 'service_account_key.json' 

# Google Sheet ID (find this in your Google Sheet's URL)
# Please replace '1iyNH3jgsAVHcuPzLY_kMhvNNrET-LwnKv6snUrP7khs' with your actual Sheet ID
SPREADSHEET_ID = '1iyNH3jgsAVHcuPzLY_kMhvNNrET-LwnKv6snUrP7khs'

# Name of the tab (worksheet) in your Google Sheet that contains the data
# Please replace 'TradeData' with your actual tab name
SHEET_NAME = 'TradeData'

# --- Function to Fetch Data from Google Sheet (with Caching) ---
# @st.cache_data is a Streamlit decorator that caches the data
# This makes the app faster by avoiding repeated data fetches
@st.cache_data(ttl=300) # Cache data for 5 minutes (300 seconds)
def get_data_from_sheet():
    """Fetches all data from the specified Google Sheet using a Service Account."""
    try:
        # Create Credentials from Service Account JSON key
        # For Streamlit Cloud, we explicitly load from st.secrets and pass to service_account_from_dict
        if st.secrets.get("gcp_service_account"):
            try:
                creds_data = st.secrets["gcp_service_account"]
                
                # Streamlit secrets can sometimes load JSON directly as a dict, or as a string.
                # We need to handle both cases to ensure creds_info is a dictionary.
                if isinstance(creds_data, str):
                    creds_info = json.loads(creds_data)
                elif isinstance(creds_data, dict):
                    creds_info = creds_data
                else:
                    st.error(f"Error: Unexpected type for 'gcp_service_account' secret: {type(creds_data)}")
                    return pd.DataFrame() # Return empty DataFrame on unexpected type
                
                # Use gspread.service_account_from_dict() to explicitly create client from dictionary
                client = gspread.service_account_from_dict(creds_info) 
            except json.JSONDecodeError as e_json:
                st.error(f"Error: Failed to parse 'gcp_service_account' secret as JSON. Check secret format. Error: {e_json}")
                return pd.DataFrame()
            except Exception as e_gspread:
                st.error(f"Error: Failed to create gspread client from 'gcp_service_account' secret. Error: {e_gspread}")
                return pd.DataFrame()
        else:
            # Load credentials from a JSON file (for Colab or local testing)
            # This path requires the SERVICE_ACCOUNT_FILE to exist
            from oauth2client.service_account import ServiceAccountCredentials
            creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPE)
            client = gspread.authorize(creds)
            
        # Open the Spreadsheet and select the Worksheet (tab)
        spreadsheet = client.open_by_id(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(SHEET_NAME)

        # Fetch all data as a list of lists
        data = worksheet.get_all_values()

        # Convert to Pandas DataFrame (first row as header)
        df = pd.DataFrame(data[1:], columns=data[0])

        # Convert 'นำเข้า', 'ส่งออก', 'ปี พ.ศ.' columns to numeric
        numeric_cols = ['นำเข้า', 'ส่งออก', 'ปี พ.ศ.']
        for col in numeric_cols:
            if col in df.columns:
                # errors='coerce' converts non-numeric values to NaN
                # fillna(0) replaces NaN with 0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        st.success("โหลดข้อมูลจาก Google Sheet สำเร็จ!")
        return df
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"เกิดข้อผิดพลาด: ไม่พบ Spreadsheet ID '{SPREADSHEET_ID}' หรือชื่อชีต '{SHEET_NAME}'")
        st.info("โปรดตรวจสอบ SPREADSHEET_ID และ SHEET_NAME ในโค้ด")
        return pd.DataFrame() # Return an empty DataFrame
    except FileNotFoundError:
        st.error(f"เกิดข้อผิดพลาด: ไม่พบไฟล์ Service Account JSON ที่ชื่อ '{SERVICE_ACCOUNT_FILE}'")
        st.info("โปรดตรวจสอบว่าคุณได้อัปโหลดไฟล์ '{SERVICE_ACCOUNT_FILE}' ไปยัง Colab แล้ว และชื่อไฟล์ถูกต้อง")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
        st.info("โปรดตรวจสอบว่า Service Account มีสิทธิ์เข้าถึง Google Sheet และการเชื่อมต่อถูกต้อง")
        return pd.DataFrame()

# --- Build Streamlit UI ---
st.set_page_config(layout="wide", page_title="แดชบอร์ดข้อมูลการค้า") # Set wide layout and page title
st.title('� แดชบอร์ดข้อมูลการค้าระหว่างประเทศ')

# Fetch data
df = get_data_from_sheet()

if not df.empty:
    st.sidebar.header("ตัวเลือกการวิเคราะห์และค้นหา")

    # Analysis options
    analysis_type = st.sidebar.selectbox(
        "เลือกประเภทการวิเคราะห์:",
        ("ภาพรวม", "การวิเคราะห์สินค้า", "การวิเคราะห์ประเทศคู่ค้า", "การวิเคราะห์พิกัดศุลกากร")
    )

    # Main data filters
    st.sidebar.subheader("ตัวกรองข้อมูล")
    selected_country = st.sidebar.text_input('ค้นหาชื่อประเทศ (บางส่วน)')
    selected_hs_code = st.sidebar.text_input('ค้นหาพิกัดศุลกากร (บางส่วน)')
    selected_item = st.sidebar.text_input('ค้นหารายการสินค้า (บางส่วน)')
    selected_year = st.sidebar.text_input('ค้นหาปี พ.ศ. (เช่น 2564)')

    # Filter data based on user input
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

    # --- Display Graphs based on selected analysis type ---
    st.header(analysis_type)

    if filtered_df.empty:
        st.warning("ไม่พบข้อมูลตามเงื่อนไขที่เลือก กรุณาลองเลือกใหม่.")
    else:
        # Helper function to create main trade charts (Bar/Line Chart)
        def create_trade_chart(df_data, group_col, title):
            summary_df = df_data.groupby(group_col)[['นำเข้า', 'ส่งออก']].sum().reset_index()
            fig = go.Figure(data=[
                go.Bar(name='นำเข้า', x=summary_df[group_col], y=summary_df['นำเข้า']),
                go.Bar(name='ส่งออก', x=summary_df[group_col], y=summary_df['ส่งออก'])
            ])
            fig.update_layout(barmode='group', title_text=title)
            return fig

        # Helper function to create Top N charts (Bar Chart)
        def create_top_n_chart(df_data, col_name, value_col, title, top_n=10):
            if col_name not in df_data.columns:
                st.warning(f"ไม่พบคอลัมน์ '{col_name}' ในข้อมูล.")
                return go.Figure()
            summary = df_data.groupby(col_name)[value_col].sum().nlargest(top_n).reset_index()
            fig = px.bar(summary, x=col_name, y=value_col, title=title)
            fig.update_xaxes(title_text=col_name)
            fig.update_yaxes(title_text=value_col)
            return fig
            
        # Helper function to create trade balance charts (Column Chart)
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

            # Yearly import-export trend graph
            if 'ปี พ.ศ.' in filtered_df.columns:
                yearly_summary = filtered_df.groupby('ปี พ.ศ.')[['นำเข้า', 'ส่งออก']].sum().reset_index().sort_values(by='ปี พ.ศ.')
                fig = px.line(yearly_summary, x='ปี พ.ศ.', y=['นำเข้า', 'ส่งออก'], title='แนวโน้มการนำเข้า-ส่งออกรายปี')
                fig.update_xaxes(type='category') # Set X-axis as Category for year
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
    st.info("ไม่สามารถโหลดข้อมูลได้ โปรดตรวจสอบการตั้งค่าและไฟล์ Service Account JSON.")
