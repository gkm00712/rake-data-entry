import streamlit as st
import requests
from datetime import datetime

# PASTE YOUR NEW GOOGLE APPS SCRIPT DEPLOYMENT URL HERE
URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ6PaPvxvRG_cUNa9NKfYEnujEShvxjjm13zo_SChUNm_jrj5eq5jNnj2vTJuiVFuApHyVFDe6OZolN/pub?output=xlsx"

st.set_page_config(page_title="Rake Entry System", layout="wide")
st.title("🚂 Master Rake Data Entry")
st.markdown("Logs will dynamically format into the correct Monthly Tab on Google Sheets.")

with st.form("master_form", clear_on_submit=True):
    # --- MAIN RAKE DETAILS ---
    c1, c2, c3, c4 = st.columns(4)
    with c1: sr_no = st.number_input("Sr. No.", min_value=1, step=1)
    with c2: rake_no = st.text_input("RAKE No (e.g., 1/1481)")
    with c3: source = st.text_input("Coal Source / MINE")
    with c4: w_type = st.selectbox("Wagon Type", ["58N", "59N", "BOXN", "BOBR", "58R"])

    t1, t2, t3, t4 = st.columns(4)
    with t1: receipt = st.datetime_input("Receipt Date & Time", datetime.now())
    with t2: placement = st.datetime_input("Placement Date & Time", datetime.now())
    with t3: u_end = st.datetime_input("Unloading End Time", datetime.now())
    with t4: release = st.datetime_input("Release Date & Time", datetime.now())

    q1, q2, q3 = st.columns(3)
    with q1: demurrage = st.text_input("Demurrage (Hrs)", value="NIL")
    with q2: gcv = st.number_input("GCV", value=0)
    with q3: vm = st.number_input("VM", value=0.0, format="%.1f")

    st.markdown("### 🏗️ Tipper Unloading Counts")
    w1, w2, w3, w4, w5, w6 = st.columns(6)
    with w1: nth = st.text_input("NTH")
    with w2: muth = st.text_input("MUTH")
    with w3: wt1 = st.text_input("WT-1")
    with w4: wt2 = st.text_input("WT-2")
    with w5: wt3 = st.text_input("WT-3")
    with w6: wt4 = st.text_input("WT-4")

    st.divider()

    # --- DEPARTMENTAL REMARKS ---
    st.markdown("### 📝 Column L: Department Delays & Remarks")
    st.warning("Format exactly as: `xx:xx - xx:xx Reason`. **Leave boxes entirely blank if no delay occurred.**")
    
    colA, colB = st.columns(2)
    with colA:
        rem_mm = st.text_area("MM", placeholder="e.g. 10:30-11:45 WT-1 U/PTW")
        rem_emd = st.text_area("EMD", placeholder="e.g. 12:00-13:00 C-29A BSS shortcircuit")
        rem_cni = st.text_area("C&I", placeholder="e.g. 14:00-14:30 ZSS Malfunctioning")
        rem_opr = st.text_area("OPR", placeholder="e.g. Operational adjustments")
    with colB:
        rem_mgr = st.text_area("MGR", placeholder="e.g. 15:00-16:00 Wagon jammed at outhaul")
        rem_chem = st.text_area("CHEMISTRY", placeholder="e.g. 03:40-04:40 Sampling time at WT-03")
        rem_other = st.text_area("OTHER", placeholder="e.g. BUNCHING / 1-2 Bucket boulders in wagon")

    # --- SUBMIT & CALCULATE ---
    if st.form_submit_button("Submit & Organize in Google Sheets"):
        # Auto-calculate durations (HH:MM:SS format)
        u_duration = str(u_end - placement)
        r_duration = str(release - receipt)

        # JSON Payload
        payload = {
            "sr_no": sr_no, "rake_no": rake_no, "source": source, "wagon_type": w_type,
            "receipt": receipt.strftime("%d.%m.%Y/%H:%M"),
            "placement": placement.strftime("%d.%m.%Y/%H:%M"),
            "u_end": u_end.strftime("%d.%m.%Y/%H:%M"),
            "release": release.strftime("%d.%m.%Y/%H:%M"),
            "u_duration": u_duration, "r_duration": r_duration,
            "demurrage": demurrage, "gcv": gcv, "vm": vm,
            "nth": nth, "muth": muth, "wt1": wt1, "wt2": wt2, "wt3": wt3, "wt4": wt4,
            
            # Department Remarks mapping
            "rem_mm": rem_mm,
            "rem_emd": rem_emd,
            "rem_cni": rem_cni,
            "rem_opr": rem_opr,
            "rem_mgr": rem_mgr,
            "rem_chem": rem_chem,
            "rem_other": rem_other
        }

        with st.spinner("Processing & formatting in Master Sheet..."):
            try:
                response = requests.post(URL, json=payload)
                if response.status_code == 200:
                    st.success(f"✅ Rake {rake_no} recorded and formatted successfully!")
                else:
                    st.error("❌ Failed to reach Google Sheets.")
            except Exception as e:
                st.error(f"❌ Connection error: {e}")
