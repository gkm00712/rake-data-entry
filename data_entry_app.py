import streamlit as st
import requests
from datetime import datetime

# PASTE YOUR LATEST DEPLOYMENT URL HERE
URL = "https://script.google.com/macros/s/AKfycbxotji-va5_iEZl7Us8rXJVeVvblZIK_n4V25b8cE8fzqCOjr_F_NHcjRjHdYdRGGNR/exec"

st.set_page_config(page_title="Railway Rake Entry", layout="wide")
st.title("🚂 Rake Unloading Master Data Entry")

with st.form("master_form", clear_on_submit=True):
    # Top Row: Primary Identity
    c1, c2, c3, c4 = st.columns(4)
    with c1: sr_no = st.number_input("Sr. No.", min_value=1, step=1)
    with c2: rake_no = st.text_input("RAKE No", placeholder="e.g. 1/1481")
    with c3: source = st.text_input("Coal Source / MINE")
    with c4: w_type = st.selectbox("Wagon Type", ["BOXN", "BOBR", "58N", "59N", "58R"])

    # Second Row: Timeline (E to H)
    t1, t2, t3, t4 = st.columns(4)
    with t1: receipt = st.datetime_input("Receipt Date & Time", datetime.now())
    with t2: placement = st.datetime_input("Placement Date & Time", datetime.now())
    with t3: u_end = st.datetime_input("Unloading End Time", datetime.now())
    with t4: release = st.datetime_input("Release Date & Time", datetime.now())

    # Third Row: Calculations & Quality (K, S, T)
    q1, q2, q3 = st.columns(3)
    with q1: demurrage = st.text_input("Demurrage (Hrs)", value="NIL")
    with q2: gcv = st.number_input("GCV", value=0)
    with q3: vm = st.number_input("VM", value=0.0, format="%.1f")

    # Remarks Section (Column L)
    st.markdown("### 📝 Column L: REMARKS")
    remarks = st.text_area("Enter technical logs, bunching details, or delays here:", 
                           help="This corresponds to Column L in your Master Sheet.")

    # Bottom Row: Tipper Counts (M to R)
    st.markdown("### 🏗️ Tipper Unloading Details")
    w1, w2, w3, w4, w5, w6 = st.columns(6)
    with w1: nth = st.text_input("NTH")
    with w2: muth = st.text_input("MUTH")
    with w3: wt1 = st.text_input("WT-1")
    with w4: wt2 = st.text_input("WT-2")
    with w5: wt3 = st.text_input("WT-3")
    with w6: wt4 = st.text_input("WT-4")

    if st.form_submit_button("Submit to Cloud Google Sheet"):
        # Auto-calculate durations for the Optimizer
        u_duration = str(u_end - placement)
        r_duration = str(release - receipt)

        payload = {
            "sr_no": sr_no, "rake_no": rake_no, "source": source, "wagon_type": w_type,
            "receipt": receipt.strftime("%d.%m.%Y/%H:%M"),
            "placement": placement.strftime("%d.%m.%Y/%H:%M"),
            "u_end": u_end.strftime("%d.%m.%Y/%H:%M"),
            "release": release.strftime("%d.%m.%Y/%H:%M"),
            "u_duration": u_duration, "r_duration": r_duration,
            "demurrage": demurrage, "remarks": remarks,
            "nth": nth, "muth": muth, "wt1": wt1, "wt2": wt2, "wt3": wt3, "wt4": wt4,
            "gcv": gcv, "vm": vm
        }

        with st.spinner("Writing to Master Sheet..."):
            response = requests.post(URL, json=payload)
            if response.status_code == 200:
                st.success(f"✅ Rake {rake_no} added to Master Database successfully!")
                st.balloons()
