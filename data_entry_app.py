import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz
import re

# PASTE YOUR NEW GOOGLE APPS SCRIPT URL HERE
URL = "https://script.google.com/macros/s/AKfycbyFnT0UCZGcJ8JscKTa-7RtwyWr1UuzRz4hsoxD9Ov3drajglBEITnE7fT5O8n5TdB2/exec"
IST = pytz.timezone('Asia/Kolkata')

st.set_page_config(page_title="Rake Entry System", layout="wide")
st.title("🚂 Strict Master Rake Entry")

@st.cache_data(ttl=10)
def fetch_today_data():
    try:
        response = requests.get(URL)
        if response.status_code == 200:
            json_data = response.json()
            all_rows = []
            for sheet in json_data:
                sheet_data = sheet['data']
                if len(sheet_data) > 1:
                    header = sheet_data[0]
                    for row in sheet_data[1:]:
                        all_rows.append(dict(zip(header, row)))
            return pd.DataFrame(all_rows)
    except:
        return pd.DataFrame()

with st.form("master_form", clear_on_submit=True):
    st.subheader("1. Rake Details")
    c1, c2, c3, c4 = st.columns(4)
    # Using text_input for everything ensures they stay completely blank
    with c1: sr_no = st.text_input("Sr. No.", placeholder="1")
    with c2: rake_no = st.text_input("RAKE No", placeholder="e.g. 145/1625")
    with c3: source = st.text_input("Coal Source / MINE", placeholder="e.g. PNGH/NTPC")
    with c4: w_type = st.text_input("Wagon Type (xx/N or xx/R)", placeholder="e.g. 58/N")

    st.subheader("2. Timeline (Format: DD.MM.YYYY/HH:MM)")
    t1, t2, t3, t4 = st.columns(4)
    with t1: receipt = st.text_input("Receipt Time & Date", placeholder="26.02.2026/05:50")
    with t2: placement = st.text_input("Placement Date & Time", placeholder="26.02.2026/06:25")
    with t3: u_end = st.text_input("Unloading End Date & Time", placeholder="26.02.2026/10:15")
    with t4: release = st.text_input("Rake Release Date & Time", placeholder="26.02.2026/11:15")

    st.subheader("3. Quality & Demurrage")
    q1, q2, q3 = st.columns(3)
    with q1: demurrage = st.text_input("Demurrage (Hrs)", placeholder="0 or NIL")
    with q2: gcv = st.text_input("GCV", placeholder="e.g. 3840")
    with q3: vm = st.text_input("VM", placeholder="e.g. 23.1")

    st.subheader("4. Tipper Unloading Counts (Format: XX / (xx:xx - xx:xx))")
    w1, w2, w3, w4, w5, w6 = st.columns(6)
    with w1: nth = st.text_input("NTH", placeholder=" ")
    with w2: muth = st.text_input("MUTH", placeholder=" ")
    with w3: wt1 = st.text_input("WT-1", placeholder="33 / (07:10 - 11:40)")
    with w4: wt2 = st.text_input("WT-2", placeholder=" ")
    with w5: wt3 = st.text_input("WT-3", placeholder=" ")
    with w6: wt4 = st.text_input("WT-4", placeholder=" ")

    st.divider()
    st.markdown("### 📝 Column L: Department Delays (Format: `xx:xx - xx:xx Reason`)")
    colA, colB = st.columns(2)
    # height=100 ensures a medium box size
    with colA:
        rem_mm = st.text_area("MM", height=100)
        rem_emd = st.text_area("EMD", height=100)
        rem_cni = st.text_area("C&I", height=100)
        rem_opr = st.text_area("OPR", height=100)
    with colB:
        rem_mgr = st.text_area("MGR", height=100)
        rem_chem = st.text_area("CHEMISTRY", height=100)
        rem_other = st.text_area("OTHER", height=100)

    if st.form_submit_button("Submit Data"):
        # --- STRICT REGEX VALIDATIONS ---
        errors = []
        if not re.match(r"^\d{1,3}/\d{4}$", rake_no): errors.append("RAKE No must be format xxx/xxxx (e.g. 145/1625).")
        if not re.match(r"^\d{2}/[NR]$", w_type): errors.append("Wagon Type must be format xx/N or xx/R (e.g. 58/N).")
        
        time_pattern = r"^\d{2}\.\d{2}\.\d{4}/\d{2}:\d{2}$"
        for t_val, name in zip([receipt, placement, u_end, release], ["Receipt", "Placement", "Unloading", "Release"]):
            if not re.match(time_pattern, t_val): errors.append(f"{name} Time must be exact DD.MM.YYYY/HH:MM")

        tipper_pattern = r"^\d+\s*/\s*\(\d{2}:\d{2}\s*-\s*\d{2}:\d{2}\)$"
        for val, name in zip([nth, muth, wt1, wt2, wt3, wt4], ["NTH", "MUTH", "WT-1", "WT-2", "WT-3", "WT-4"]):
            if val and not re.match(tipper_pattern, val.strip()): errors.append(f"{name} must be format XX / (xx:xx - xx:xx).")

        if errors:
            for e in errors: st.error(f"❌ {e}")
        else:
            # Calculate durations automatically
            fmt = "%d.%m.%Y/%H:%M"
            dt_receipt = datetime.strptime(receipt, fmt)
            dt_placement = datetime.strptime(placement, fmt)
            dt_u_end = datetime.strptime(u_end, fmt)
            dt_release = datetime.strptime(release, fmt)
            
            # Format as HH:MM:SS
            u_duration = str(dt_u_end - dt_placement)
            r_duration = str(dt_release - dt_receipt)

            payload = {
                "sr_no": sr_no, "rake_no": rake_no, "source": source, "wagon_type": w_type,
                "receipt": receipt, "placement": placement, "u_end": u_end, "release": release,
                "u_duration": u_duration, "r_duration": r_duration,
                "demurrage": demurrage, "gcv": gcv, "vm": vm,
                "nth": nth, "muth": muth, "wt1": wt1, "wt2": wt2, "wt3": wt3, "wt4": wt4,
                "rem_mm": rem_mm, "rem_emd": rem_emd, "rem_cni": rem_cni,
                "rem_opr": rem_opr, "rem_mgr": rem_mgr, "rem_chem": rem_chem, "rem_other": rem_other
            }

            with st.spinner("Writing formatted data to Google Sheets..."):
                resp = requests.post(URL, json=payload)
                if resp.status_code == 200:
                    st.success(f"✅ Rake {rake_no} recorded successfully!")
                    st.cache_data.clear() # Clears cache to instantly show today's data below
                else:
                    st.error("❌ Failed to reach database.")

# --- SHOW TODAY'S ENTERED DATA ---
st.divider()
st.subheader(f"📋 Today's Entries ({datetime.now(IST).strftime('%d.%m.%Y')})")
df = fetch_today_data()

if not df.empty and "Receipt Time & Date" in df.columns:
    today_str = datetime.now(IST).strftime("%d.%m.%Y")
    today_df = df[df["Receipt Time & Date"].astype(str).str.contains(today_str, na=False)]
    
    if not today_df.empty:
        st.dataframe(today_df, use_container_width=True)
    else:
        st.info("No data entered for today yet.")
else:
    st.info("Database is empty or loading.")
