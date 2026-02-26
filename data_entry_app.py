import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- CONFIGURATION ---
EXCEL_FILE = "Rake_Master_Database.xlsx"

# --- INITIALIZE EXCEL FILE ---
def init_excel():
    if not os.path.exists(EXCEL_FILE):
        # Create an empty DataFrame with your specific columns
        columns = [
            "RAKE No", "Coal Source", "Wagon Type", "Receipt Time", 
            "Placement Time", "Release Time", "Demurrage (Hrs)", 
            "WT-1", "WT-2", "WT-3", "WT-4", "GCV", "VM", "REMARKS"
        ]
        df = pd.DataFrame(columns=columns)
        # Save it as an Excel file
        df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')

init_excel()

# --- MAIN APP UI ---
st.set_page_config(page_title="Rake Data Entry", layout="wide")
st.title("📝 Standalone Rake Data Entry (Excel)")

with st.form("entry_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        rake_no = st.text_input("RAKE No (e.g. 1/1481)")
        source = st.selectbox("Coal Source", ["SLSP/CCL", "NUGP/CCL", "BNDG/NTPC", "CHRI/CCL"])
        wagon_type = st.selectbox("Wagon Type", ["58N", "59N", "58R", "BOXN", "BOBR"])
        
    with col2:
        receipt = st.datetime_input("Receipt Time", datetime.now())
        placement = st.datetime_input("Placement Time", datetime.now())
        release = st.datetime_input("Rake Release Time", datetime.now())
        
    with col3:
        demurrage = st.number_input("Demurrage (Hrs)", min_value=0.0, step=0.5)
        gcv = st.number_input("GCV", value=3800)
        vm = st.number_input("VM", value=20.0, format="%.1f")

    st.subheader("Wagon Tipper Unloading Counts")
    wt1, wt2, wt3, wt4 = st.columns(4)
    with wt1: wt1_val = st.number_input("WT-1", min_value=0)
    with wt2: wt2_val = st.number_input("WT-2", min_value=0)
    with wt3: wt3_val = st.number_input("WT-3", min_value=0)
    with wt4: wt4_val = st.number_input("WT-4", min_value=0)
    
    remarks = st.text_area("REMARKS (Delays, Breakdowns, etc.)")
    
    # --- SAVE TO EXCEL LOGIC ---
    if st.form_submit_button("Save to Excel"):
        if rake_no == "":
            st.error("Please enter a RAKE No.")
        else:
            # 1. Package the new data
            new_data = pd.DataFrame([{
                "RAKE No": rake_no,
                "Coal Source": source,
                "Wagon Type": wagon_type,
                "Receipt Time": receipt.strftime("%d.%m.%Y/%H:%M"),
                "Placement Time": placement.strftime("%d.%m.%Y/%H:%M"),
                "Release Time": release.strftime("%d.%m.%Y/%H:%M"),
                "Demurrage (Hrs)": demurrage,
                "WT-1": wt1_val,
                "WT-2": wt2_val,
                "WT-3": wt3_val,
                "WT-4": wt4_val,
                "GCV": gcv,
                "VM": vm,
                "REMARKS": remarks
            }])
            
            # 2. Read the existing Excel file
            existing_df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
            
            # 3. Combine old data with new data
            updated_df = pd.concat([existing_df, new_data], ignore_index=True)
            
            # 4. Save it back to Excel
            updated_df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')
            
            st.success(f"✅ Rake {rake_no} successfully added to {EXCEL_FILE}!")

# --- VIEW RECENT ENTRIES ---
st.divider()
st.subheader("📊 Recent Excel Entries")
try:
    display_df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
    st.dataframe(display_df.tail(5), use_container_width=True)
except Exception as e:
    st.info("No data yet.")
