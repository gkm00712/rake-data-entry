import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz 
import re
import pandas as pd

# --- CONFIGURATION ---
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzIWIysLhf_RPL1o5-NgqwIIM_OgA_hLey2WoschBClY5zku8fDtNLTjcYPkxn6-PJY/exec"
LIVE_EXCEL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ6PaPvxvRG_cUNa9NKfYEnujEShvxjjm13zo_SChUNm_jrj5eq5jNnj2vTJuiVFuApHyVFDe6OZolN/pub?output=xlsx"
IST = pytz.timezone('Asia/Kolkata')

st.set_page_config(page_title="Railway Rake Master Entry", layout="wide")

# --- TIME SYNCHRONIZATION (IST) ---
now_ist = datetime.now(IST)
today_ist = now_ist.date()
tomorrow_ist = today_ist + timedelta(days=1)

# --- SESSION STATE INITIALIZATION ---
# This safely stores the Rake No to allow selective clearing without Callback Loops
if 'rake_val' not in st.session_state:
    st.session_state.rake_val = ""

st.title("🚂 Rake Master Data Entry (IST)")

# --- DATA ENTRY FORM ---
with st.container():
    c1, c2, c3 = st.columns(3)
    with c1:
        sr_no = st.number_input("Sr. No.", min_value=1, step=1)
        # Rake No is tied directly to session state
        rake_no = st.text_input("RAKE No (Format: XX/XXXX)", key="rake_val", placeholder="e.g. 1/1481")
        source = st.text_input("Coal Source/MINE")
        
    with c2:
        st.write("Wagon Specification")
        w_c1, w_c2 = st.columns([2, 1])
        w_qty = w_c1.number_input("Qty (Numerical)", min_value=1, max_value=99, value=58)
        w_type = w_c2.selectbox("Type", ["N", "R"])
        wagon_spec = f"{w_qty}{w_type}"
        
    with c3:
        # Strictly Numerical Demurrage
        demurrage = st.number_input("Demurrage (Hrs)", min_value=0.0, step=0.1)

st.divider()

# --- DEPARTMENTAL OUTAGES (COLUMN L) ---
st.subheader("🛠️ Departmental Outages")
d1, d2, d3 = st.columns(3)
with d1:
    dept = st.selectbox("Department", ["NONE", "MM", "EMD", "C&I", "OPR", "MGR", "CHEMISTRY", "OTHER"])
with d2:
    o_start = st.text_input("Outage Start (HH:MM)", placeholder="e.g. 09:30")
with d3:
    o_end = st.text_input("Outage End (HH:MM)", placeholder="Leave blank for Full Day")

st.divider()

# --- TIMELINE (IST + 1-MINUTE RESOLUTION) ---
st.subheader("📅 Timeline (IST - Restricted to Today/Tomorrow)")
t1, t2, t3, t4 = st.columns(4)
with t1:
    d_rec = st.date_input("Receipt Date", value=today_ist, min_value=today_ist, max_value=tomorrow_ist)
    ti_rec = st.time_input("Receipt Time", value=now_ist.time(), step=60)
with t2:
    d_pla = st.date_input("Placement Date", value=today_ist, min_value=today_ist, max_value=tomorrow_ist)
    ti_pla = st.time_input("Placement Time", value=now_ist.time(), step=60)
with t3:
    d_end = st.date_input("U/L End Date", value=today_ist, min_value=today_ist, max_value=tomorrow_ist)
    ti_end = st.time_input("U/L End Time", value=now_ist.time(), step=60)
with t4:
    d_rel = st.date_input("Release Date", value=today_ist, min_value=today_ist, max_value=tomorrow_ist)
    ti_rel = st.time_input("Release Time", value=now_ist.time(), step=60)

st.divider()

# --- TIPPER DETAILS (ALLOWS TEXT FOR XX:XX-XX:XX FORMAT) ---
st.subheader("🏗️ Tipper Details")
st.caption("You can write counts and time intervals here (e.g. '33 07:10-11:40')")
w1, w2, w3, w4, w5, w6 = st.columns(6)
with w1: nth = st.text_input("NTH")
with w2: muth = st.text_input("MUTH")
with w3: wt1 = st.text_input("WT-1")
with w4: wt2 = st.text_input("WT-2")
with w5: wt3 = st.text_input("WT-3")
with w6: wt4 = st.text_input("WT-4")

remarks_text = st.text_area("General Remarks")

# --- SUBMISSION LOGIC ---
if st.button("🚀 Submit to Cloud Master Sheet"):
    # 1. Strict Regex Validation for RAKE No
    if not re.match(r"^\d+/\d+$", st.session_state.rake_val):
        st.error("❌ Error: RAKE No must be XX/XXXX (e.g., 1/1481). Entry rejected.")
        # Selectively clear only the Rake field
        st.session_state.rake_val = ""
        st.rerun()
    else:
        # 2. Process Outage for Column L
        outage_summary = ""
        if dept != "NONE" and o_start:
            if not o_end:
                outage_summary = f"[{dept}: FULL DAY OUTAGE (Start: {o_start})]"
            else:
                outage_summary = f"[{dept}: {o_start} to {o_end}]"
        
        final_remarks = f"{outage_summary} {remarks_text}".strip()

        # 3. Assemble the exact payload format
        payload = {
            "sr_no": sr_no, "rake_no": st.session_state.rake_val, "source": source,
            "wagon_spec": wagon_spec,
            "receipt": f"{d_rec.strftime('%d.%m.%Y')}/{ti_rec.strftime('%H:%M')}",
            "placement": f"{d_pla.strftime('%d.%m.%Y')}/{ti_pla.strftime('%H:%M')}",
            "u_end": f"{d_end.strftime('%d.%m.%Y')}/{ti_end.strftime('%H:%M')}",
            "release": f"{d_rel.strftime('%d.%m.%Y')}/{ti_rel.strftime('%H:%M')}",
            "u_duration": "CALC", "r_duration": "CALC",
            "demurrage": demurrage, "remarks": final_remarks,
            "nth": nth, "muth": muth, "wt1": wt1, "wt2": wt2, "wt3": wt3, "wt4": wt4,
            "gcv": 0, "vm": 0
        }
        
        # 4. Send to Google Sheets
        with st.spinner("Writing securely to Google Sheets..."):
            try:
                res = requests.post(APPS_SCRIPT_URL, json=payload)
                if res.status_code == 200:
                    st.success(f"✅ Rake {st.session_state.rake_val} saved successfully!")
                    st.balloons()
            except Exception as e:
                st.error(f"Connection failed: {e}")

# --- RECENT ENTRIES VIEWER (LIVE FROM EXCEL LINK) ---
st.divider()
st.subheader("📊 Recent Master Sheet Entries")

@st.cache_data(ttl=10) # Fetches fresh data every 10 seconds
def fetch_recent_data():
    try:
        df = pd.read_excel(LIVE_EXCEL_URL, engine='openpyxl')
        df = df.dropna(how='all') # Clean empty rows
        return df.tail(5) # Get last 5
    except Exception as e:
        return pd.DataFrame()

recent_data = fetch_recent_data()

if not recent_data.empty:
    st.dataframe(recent_data, use_container_width=True, hide_index=True)
else:
    st.info("No recent data found. Make sure your Google Sheet is published and has data.")
