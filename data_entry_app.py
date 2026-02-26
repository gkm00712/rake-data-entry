import streamlit as st
import pandas as pd
from datetime import datetime
import os
import re

# --- CONFIGURATION ---
EXCEL_FILE = "Rake_Master_Database.xlsx"

# --- INITIALIZE EXCEL FILE ---
def init_excel():
    """Creates the master Excel file with Optimizer-ready columns if it doesn't exist."""
    if not os.path.exists(EXCEL_FILE):
        columns = [
            "RAKE No", "Coal Source", "Wagon Type", "Receipt Time", 
            "Placement Time", "Unloading End Time", "Release Time",
            "Unloading Duration", "Release Duration", "Demurrage (Hrs)", 
            "WT-1", "WT-2", "WT-3", "WT-4", "GCV", "VM", "REMARKS"
        ]
        df = pd.DataFrame(columns=columns)
        df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')

init_excel()

# --- MAIN APP UI ---
st.set_page_config(page_title="Rake Data Entry", layout="wide")
st.title("📝 Strict Rake Data Entry (Optimizer Ready)")
st.markdown("All data entered here is strictly validated and saved to a local Excel file for your Optimization Dashboard.")

with st.form("entry_form", clear_on_submit=False):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        rake_no = st.text_input("RAKE No (Strict Format: e.g., 1/1481)")
        source = st.selectbox("Coal Source", ["SLSP/CCL", "NUGP/CCL", "BNDG/NTPC", "CHRI/CCL", "BCSR/CCL", "OTHER"])
        wagon_type = st.selectbox("Wagon Type", ["58N", "59N", "58R", "BOXN", "BOBR"])
        
    with col2:
        receipt = st.datetime_input("Receipt Date & Time", datetime.now())
        placement = st.datetime_input("Placement Date & Time", datetime.now())
        unloading_end = st.datetime_input("Unloading End Date & Time", datetime.now())
        release = st.datetime_input("Rake Release Date & Time", datetime.now())
        
    with col3:
        demurrage = st.number_input("Demurrage (Hrs)", min_value=0.0, step=0.5, format="%.1f")
        gcv = st.number_input("GCV", value=3800, min_value=1000, max_value=8000, step=1)
        vm = st.number_input("VM", value=20.0, min_value=0.0, max_value=50.0, format="%.1f")

    st.subheader("Wagon Tipper Unloading Counts (Must be Numbers)")
    wt1, wt2, wt3, wt4 = st.columns(4)
    with wt1: wt1_val = st.number_input("WT-1", min_value=0, step=1)
    with wt2: wt2_val = st.number_input("WT-2", min_value=0, step=1)
    with wt3: wt3_val = st.number_input("WT-3", min_value=0, step=1)
    with wt4: wt4_val = st.number_input("WT-4", min_value=0, step=1)
    
    remarks = st.text_area("REMARKS (Delays, Breakdowns, etc.)")
    
    # --- STRICT VALIDATION & SAVE LOGIC ---
    submit_btn = st.form_submit_button("Validate & Save for Optimizer")
    
    if submit_btn:
        # Rule 1: Validate Rake Number Format using Regex
        if not re.match(r"^\d+/\d+$", rake_no):
            st.error("❌ Invalid Rake Number! It must be numbers separated by a slash (e.g., 1/1481).")
            st.stop() # Stops the script from saving
            
        # Rule 2: Chronological Time Checks
        if placement < receipt:
            st.error("❌ Time Error: Placement Time cannot be before Receipt Time.")
            st.stop()
        if unloading_end < placement:
            st.error("❌ Time Error: Unloading End Time cannot be before Placement Time.")
            st.stop()
        if release < unloading_end:
            st.error("❌ Time Error: Release Time cannot be before Unloading End Time.")
            st.stop()

        # Rule 3: Auto-Calculate Durations for the Optimizer
        unloading_duration = str(unloading_end - placement)
        release_duration = str(release - receipt)

        # Rule 4: Package Data exactly as the Optimizer expects
        new_data = pd.DataFrame([{
            "RAKE No": rake_no,
            "Coal Source": source,
            "Wagon Type": wagon_type,
            "Receipt Time": receipt.strftime("%d.%m.%Y/%H:%M"),
            "Placement Time": placement.strftime("%d.%m.%Y/%H:%M"),
            "Unloading End Time": unloading_end.strftime("%d.%m.%Y/%H:%M"),
            "Release Time": release.strftime("%d.%m.%Y/%H:%M"),
            "Unloading Duration": unloading_duration,
            "Release Duration": release_duration,
            "Demurrage (Hrs)": demurrage,
            "WT-1": int(wt1_val),
            "WT-2": int(wt2_val),
            "WT-3": int(wt3_val),
            "WT-4": int(wt4_val),
            "GCV": int(gcv),
            "VM": float(vm),
            "REMARKS": remarks.replace('\n', ' | ') # Remove newlines so they don't break Excel parsing
        }])
        
        # Save to Local Excel File
        try:
            existing_df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
            updated_df = pd.concat([existing_df, new_data], ignore_index=True)
            updated_df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')
            
            st.success(f"✅ Strict Validation Passed! Rake {rake_no} added to {EXCEL_FILE}.")
        except PermissionError:
            st.error(f"❌ Cannot save data! Please close '{EXCEL_FILE}' if you have it open in Excel.")

# --- VIEW RECENT ENTRIES ---
st.divider()
st.subheader("📊 Recent Excel Entries")
try:
    display_df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
    st.dataframe(display_df.tail(5), use_container_width=True)
except Exception as e:
    st.info("No data yet. Submit a form to create the first entry!")
