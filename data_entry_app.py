import streamlit as st
import requests
from datetime import datetime
import re

# --- CONFIGURATION ---
# Your specific Live Google Apps Script Web App URL
GOOGLE_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwN3-BGw9XJPHCcXbO6QbXH9alAXGVYvjdbCu0tA3zfUq5TOrdvlo-9P5Y1Np-t0keQ/exec"

# --- MAIN APP UI ---
st.set_page_config(page_title="Rake Data Entry", layout="wide")
st.title("📝 Cloud Rake Data Entry (Direct to Google Sheets)")
st.markdown("All data entered here is strictly validated and saved instantly to your cloud Google Sheet.")

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
    
    # --- STRICT VALIDATION & CLOUD SAVE LOGIC ---
    submit_btn = st.form_submit_button("Validate & Send to Google Sheets")
    
    if submit_btn:
        # Rule 1: Validate Rake Number Format
        if not re.match(r"^\d+/\d+$", rake_no):
            st.error("❌ Invalid Rake Number! It must be numbers separated by a slash (e.g., 1/1481).")
            st.stop() 
            
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

        # Rule 3: Auto-Calculate Durations
        unloading_duration = str(unloading_end - placement)
        release_duration = str(release - receipt)

        # Rule 4: Package Data into JSON format for Google Sheets
        payload = {
            "rake_no": rake_no,
            "source": source,
            "wagon_type": wagon_type,
            "receipt": receipt.strftime("%d.%m.%Y/%H:%M"),
            "placement": placement.strftime("%d.%m.%Y/%H:%M"),
            "unloading_end": unloading_end.strftime("%d.%m.%Y/%H:%M"),
            "release": release.strftime("%d.%m.%Y/%H:%M"),
            "unloading_duration": unloading_duration,
            "release_duration": release_duration,
            "demurrage": demurrage,
            "wt1": int(wt1_val),
            "wt2": int(wt2_val),
            "wt3": int(wt3_val),
            "wt4": int(wt4_val),
            "gcv": int(gcv),
            "vm": float(vm),
            "remarks": remarks.replace('\n', ' | ') # Remove newlines
        }
        
        # Send to Google Sheets via POST request
        with st.spinner('Saving securely to Google Sheets...'):
            try:
                response = requests.post(GOOGLE_WEB_APP_URL, json=payload)
                
                if response.status_code == 200:
                    st.success(f"✅ Strict Validation Passed! Rake {rake_no} added to Google Sheets.")
                    st.balloons()
                else:
                    st.error(f"❌ Failed to reach Google Sheets. Error code: {response.status_code}")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Connection error: {e}")
