import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz # For IST
import re

# --- CONFIGURATION ---
URL = "https://script.google.com/macros/s/AKfycbzIWIysLhf_RPL1o5-NgqwIIM_OgA_hLey2WoschBClY5zku8fDtNLTjcYPkxn6-PJY/exec"
IST = pytz.timezone('Asia/Kolkata')

st.set_page_config(page_title="Railway Rake Master Entry", layout="wide")

# Get Current Time in IST
now_ist = datetime.now(IST)
today_ist = now_ist.date()
tomorrow_ist = today_ist + timedelta(days=1)

# Initialize session state for persistence
if 'form' not in st.session_state:
    st.session_state.form = {
        "rake_no": "", "source": "", "qty": 58, "demurrage": 0.0,
        "remarks": "", "outage_start": "", "outage_end": ""
    }

def update_state(key):
    st.session_state.form[key] = st.session_state[key]

st.title("🚂 Rake Master Data Entry (IST Synchronized)")

tab1, tab2 = st.tabs(["📝 New Entry Form", "📋 View Today/Tomorrow"])

with tab1:
    # --- IDENTITY & SPEC ---
    c1, c2, c3 = st.columns(3)
    with c1:
        sr_no = st.number_input("Sr. No.", min_value=1, step=1)
        
        r_input = st.text_input("RAKE No", value=st.session_state.form["rake_no"])
        if r_input and not re.match(r"^\d+/\d+$", r_input):
            st.warning("⚠️ Invalid RAKE No format (use XX/XXXX). Field cleared.")
            st.session_state.form["rake_no"] = ""
            st.rerun()
        rake_no = r_input
        
    with c2:
        st.write("Wagon Specification")
        w_c1, w_c2 = st.columns([2, 1])
        w_qty = w_c1.number_input("Qty (Numerical)", min_value=1, max_value=99, key="qty", on_change=update_state)
        w_alpha = w_c2.selectbox("Type", ["N", "R"])
        wagon_spec = f"{w_qty}{w_alpha}"
        
    with c3:
        source = st.text_input("Coal Source/MINE", key="source", on_change=update_state)
        demurrage = st.number_input("Demurrage (Hrs)", min_value=0.0, step=0.1, key="demurrage", on_change=update_state)

    st.divider()

    # --- DEPARTMENTAL OUTAGES (FOR COLUMN L) ---
    st.subheader("🛠️ Departmental Outages")
    d1, d2, d3 = st.columns(3)
    with d1:
        dept = st.selectbox("Department", ["MM", "EMD", "C&I", "OPR", "MGR", "CHEMISTRY", "OTHER"])
    with d2:
        o_start = st.text_input("Outage Start (HH:MM)", key="outage_start", on_change=update_state)
    with d3:
        o_end = st.text_input("Outage End (HH:MM)", key="outage_end", on_change=update_state)

    outage_summary = ""
    if o_start:
        if not o_end:
            outage_summary = f"[{dept}: FULL DAY OUTAGE (Start: {o_start})]"
        else:
            outage_summary = f"[{dept}: {o_start} to {o_end}]"

    st.divider()

    # --- IST CALENDAR TIMELINE ---
    st.subheader("📅 Timeline (IST Only)")
    
    
    t1, t2, t3, t4 = st.columns(4)
    with t1:
        d_rec = st.date_input("Receipt Date", value=today_ist, min_value=today_ist, max_value=tomorrow_ist)
        ti_rec = st.time_input("Receipt Time", value=now_ist.time())
    with t2:
        d_pla = st.date_input("Placement Date", value=today_ist, min_value=today_ist, max_value=tomorrow_ist)
        ti_pla = st.time_input("Placement Time", value=now_ist.time())
    with t3:
        d_end = st.date_input("U/L End Date", value=today_ist, min_value=today_ist, max_value=tomorrow_ist)
        ti_end = st.time_input("U/L End Time", value=now_ist.time())
    with t4:
        d_rel = st.date_input("Release Date", value=today_ist, min_value=today_ist, max_value=tomorrow_ist)
        ti_rel = st.time_input("Release Time", value=now_ist.time())

    st.divider()

    # --- SECTION 4: TIPPER DETAILS ---
    st.subheader("🏗️ Tipper Details")
    w1, w2, w3, w4, w5, w6 = st.columns(6)
    with w1: nth = st.text_input("NTH")
    with w2: muth = st.text_input("MUTH")
    with w3: wt1 = st.text_input("WT-1")
    with w4: wt2 = st.text_input("WT-2")
    with w5: wt3 = st.text_input("WT-3")
    with w6: wt4 = st.text_input("WT-4")

    general_rem = st.text_area("General Remarks", key="remarks", on_change=update_state)
    column_l_remarks = f"{outage_summary} {general_rem}".strip()

    if st.button("🚀 Submit to Cloud Master Sheet"):
        if not rake_no:
            st.error("Submission failed: Correct the RAKE No format first.")
        else:
            # Format according to IST
            payload = {
                "sr_no": sr_no, "rake_no": rake_no, "source": st.session_state.form["source"],
                "wagon_spec": wagon_spec,
                "receipt": f"{d_rec.strftime('%d.%m.%Y')}/{ti_rec.strftime('%H:%M')}",
                "placement": f"{d_pla.strftime('%d.%m.%Y')}/{ti_pla.strftime('%H:%M')}",
                "u_end": f"{d_end.strftime('%d.%m.%Y')}/{ti_end.strftime('%H:%M')}",
                "release": f"{d_rel.strftime('%d.%m.%Y')}/{ti_rel.strftime('%H:%M')}",
                "u_duration": "CALC", "r_duration": "CALC",
                "demurrage": demurrage, "remarks": column_l_remarks,
                "nth": nth, "muth": muth, "wt1": wt1, "wt2": wt2, "wt3": wt3, "wt4": wt4,
                "gcv": 0, "vm": 0
            }
            
            with st.spinner("Writing to Cloud..."):
                res = requests.post(URL, json=payload)
                if res.status_code == 200:
                    st.success("✅ Data saved to Master Sheet!")

with tab2:
    st.info(f"Viewing and Editing restricted to Today ({today_ist}) and Tomorrow ({tomorrow_ist}) IST.")
