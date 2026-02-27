import streamlit as st
import requests
from datetime import datetime, date, timedelta
import re

# --- CONFIGURATION ---
URL = "https://script.google.com/macros/s/AKfycbzIWIysLhf_RPL1o5-NgqwIIM_OgA_hLey2WoschBClY5zku8fDtNLTjcYPkxn6-PJY/exec"

st.set_page_config(page_title="Railway Rake Master Entry", layout="wide")

# Initialize session state for persistence
if 'form' not in st.session_state:
    st.session_state.form = {
        "sr_no": 1, "rake_no": "", "source": "", "qty": 58, "demurrage": 0.0,
        "nth": "", "muth": "", "wt1": "", "wt2": "", "wt3": "", "wt4": "",
        "remarks": "", "tipper_time": ""
    }

def update_val(key):
    st.session_state.form[key] = st.session_state[key]

# --- MAIN UI ---
st.title("🚂 Rake Unloading Master Entry")

tab1, tab2 = st.tabs(["📝 Data Entry Form", "📋 View Today/Tomorrow"])

with tab1:
    with st.container():
        col1, col2, col3 = st.columns(3)
        
        with col1:
            sr_no = st.number_input("Sr. No.", min_value=1, key="sr_no", on_change=update_val)
            
            # Rake No Validation
            rake_input = st.text_input("RAKE No (Format: XX/XXXX)", value=st.session_state.form["rake_no"])
            if rake_input and not re.match(r"^\d+/\d+$", rake_input):
                st.error("⚠️ Invalid Format! Use numbers and a slash (e.g., 1/1481). Field reset.")
                st.session_state.form["rake_no"] = ""
                st.rerun()
            else:
                st.session_state.form["rake_no"] = rake_input

            source = st.text_input("Coal Source/MINE", key="source", on_change=update_val)

        with col2:
            st.write("Wagon Specification")
            w_c1, w_c2 = st.columns([2, 1])
            w_qty = w_c1.number_input("Qty (XX)", min_value=1, max_value=99, key="qty", on_change=update_val)
            w_type = w_c2.selectbox("Type", ["N", "R"])
            wagon_spec = f"{w_qty}{w_type}"

        with col3:
            demurrage = st.number_input("Demurrage (Hrs) - Numbers Only", min_value=0.0, step=0.5, key="demurrage", on_change=update_val)

    st.divider()

    st.subheader("📅 Timeline (Calendar Selection)")
    # Date Restriction: Only Today and Tomorrow
    min_d = date.today()
    max_d = date.today() + timedelta(days=1)
    
    t1, t2, t3, t4 = st.columns(4)
    with t1:
        d_rec = st.date_input("Receipt Date", min_value=min_d, max_value=max_d)
        t_rec = st.time_input("Receipt Time")
    with t2:
        d_pla = st.date_input("Placement Date", min_value=min_d, max_value=max_d)
        t_pla = st.time_input("Placement Time")
    with t3:
        d_end = st.date_input("Unloading End Date", min_value=min_d, max_value=max_d)
        t_end = st.time_input("Unloading End Time")
    with t4:
        d_rel = st.date_input("Release Date", min_value=min_d, max_value=max_d)
        t_rel = st.time_input("Release Time")

    st.divider()

    st.subheader("🏗️ Tipper Unloading Details")
    # Tipping Interval (XX:XX-XX:XX format)
    tipper_time = st.text_input("Tipper Interval (Format: XX:XX-XX:XX)", value=st.session_state.form["tipper_time"], key="tipper_time", on_change=update_val)
    if tipper_time and not re.match(r"^\d{2}:\d{2}-\d{2}:\d{2}$", tipper_time):
        st.warning("⚠️ Warning: Interval should be XX:XX-XX:XX format.")

    w1, w2, w3, w4, w5, w6 = st.columns(6)
    with w1: nth = st.text_input("NTH", key="nth", on_change=update_val)
    with w2: muth = st.text_input("MUTH", key="muth", on_change=update_val)
    with w3: wt1 = st.text_input("WT-1", key="wt1", on_change=update_val)
    with w4: wt2 = st.text_input("WT-2", key="wt2", on_change=update_val)
    with w5: wt3 = st.text_input("WT-3", key="wt3", on_change=update_val)
    with w6: wt4 = st.text_input("WT-4", key="wt4", on_change=update_val)

    remarks = st.text_area("REMARKS (Column L)", key="remarks", on_change=update_val)

    if st.button("🚀 Final Submit to Master Sheet"):
        if not st.session_state.form["rake_no"]:
            st.error("Submission failed: Correct the RAKE No first.")
        else:
            payload = {
                "sr_no": st.session_state.form["sr_no"],
                "rake_no": st.session_state.form["rake_no"],
                "source": st.session_state.form["source"],
                "wagon_spec": wagon_spec,
                "receipt": f"{d_rec.strftime('%d.%m.%Y')}/{t_rec.strftime('%H:%M')}",
                "placement": f"{d_pla.strftime('%d.%m.%Y')}/{t_pla.strftime('%H:%M')}",
                "u_end": f"{d_end.strftime('%d.%m.%Y')}/{t_end.strftime('%H:%M')}",
                "release": f"{d_rel.strftime('%d.%m.%Y')}/{t_rel.strftime('%H:%M')}",
                "u_duration": "CALC", "r_duration": "CALC", # Optimizer handles durations
                "demurrage": st.session_state.form["demurrage"],
                "remarks": f"{st.session_state.form['remarks']} [Interval: {tipper_time}]",
                "nth": nth, "muth": muth, "wt1": wt1, "wt2": wt2, "wt3": wt3, "wt4": wt4,
                "gcv": 0, "vm": 0
            }
            res = requests.post(URL, json=payload)
            if res.status_code == 200:
                st.success("✅ Data saved to Cloud Master Sheet.")
                st.balloons()

with tab2:
    st.info(f"Displaying restricted records for Today ({min_d}) and Tomorrow ({max_d})")
    # For a full integration, use st.connection("gsheets") to pull and filter rows by date
