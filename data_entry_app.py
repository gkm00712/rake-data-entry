import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz
import re

# --- CONFIGURATION ---
URL = "https://script.google.com/macros/s/AKfycbyf19TAOq5mEITCsWIOBBuOW3t9hwEMHbadsQdAWz7XOrBzretoqhw4YjQTiDaZ32Bz/exec"

# Force IST Timezone
IST = pytz.timezone('Asia/Kolkata')

st.set_page_config(page_title="Railway Command Center", layout="wide")
st.title("🚂 Rake Unloading Command Center")

# --- DATA FETCHING HELPER ---
@st.cache_data(ttl=60) # Caches data for 60 seconds to make the app fast
def fetch_google_sheet_data():
    try:
        response = requests.get(URL)
        if response.status_code == 200:
            json_data = response.json()
            all_rows = []
            for sheet in json_data:
                sheet_data = sheet['data']
                if len(sheet_data) > 1: # Skip if only header exists
                    header = sheet_data[0]
                    for row in sheet_data[1:]:
                        all_rows.append(dict(zip(header, row)))
            return pd.DataFrame(all_rows)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")
        return pd.DataFrame()

# --- TABS ---
tab_entry, tab_today, tab_download = st.tabs(["📝 Data Entry", "📅 Today's Data", "📥 Download Data"])

# ==========================================
# TAB 1: DATA ENTRY
# ==========================================
with tab_entry:
    with st.form("master_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1: sr_no = st.number_input("Sr. No.", min_value=1, step=1)
        with c2: rake_no = st.text_input("RAKE No (e.g., 1/1481)")
        with c3: source = st.text_input("Coal Source / MINE")
        with c4: w_type = st.selectbox("Wagon Type", ["58N", "59N", "BOXN", "BOBR", "58R"])

        t1, t2, t3, t4 = st.columns(4)
        with t1: receipt = st.datetime_input("Receipt Time (IST)", datetime.now(IST))
        with t2: placement = st.datetime_input("Placement Time (IST)", datetime.now(IST))
        with t3: u_end = st.datetime_input("Unloading End (IST)", datetime.now(IST))
        with t4: release = st.datetime_input("Release Time (IST)", datetime.now(IST))

        q1, q2, q3 = st.columns(3)
        with q1: demurrage = st.text_input("Demurrage (Hrs)", value="NIL")
        with q2: gcv = st.number_input("GCV", value=0)
        with q3: vm = st.number_input("VM", value=0.0, format="%.1f")

        st.markdown("### 🏗️ Tipper Unloading Counts (Format: XX / (xx:xx - xx:xx))")
        st.caption("Leave blank if no data. Example: 33 / (07:10 - 11:40)")
        w1, w2, w3, w4, w5, w6 = st.columns(6)
        with w1: nth = st.text_input("NTH")
        with w2: muth = st.text_input("MUTH")
        with w3: wt1 = st.text_input("WT-1", placeholder="25 / (07:55 - 11:30)")
        with w4: wt2 = st.text_input("WT-2")
        with w5: wt3 = st.text_input("WT-3")
        with w6: wt4 = st.text_input("WT-4")

        st.divider()
        st.markdown("### 📝 Column L: Department Delays")
        st.caption("Format: `xx:xx - xx:xx Reason`. Leave completely blank if none.")
        colA, colB = st.columns(2)
        with colA:
            rem_mm = st.text_area("MM")
            rem_emd = st.text_area("EMD")
            rem_cni = st.text_area("C&I")
            rem_opr = st.text_area("OPR")
        with colB:
            rem_mgr = st.text_area("MGR")
            rem_chem = st.text_area("CHEMISTRY")
            rem_other = st.text_area("OTHER (Bunching/Quality)")

        if st.form_submit_button("Submit Data"):
            # Validate Wagon Tipper Formats
            pattern = r"^\d+\s*/\s*\(\d{2}:\d{2}\s*-\s*\d{2}:\d{2}\)$"
            invalid_inputs = []
            for field, val in zip(["NTH", "MUTH", "WT-1", "WT-2", "WT-3", "WT-4"], [nth, muth, wt1, wt2, wt3, wt4]):
                if val and not re.match(pattern, val.strip()):
                    invalid_inputs.append(field)
            
            if invalid_inputs:
                st.error(f"❌ Invalid format in: {', '.join(invalid_inputs)}. Must be like `33 / (07:10 - 11:40)`")
            else:
                u_duration = str(u_end - placement)
                r_duration = str(release - receipt)

                payload = {
                    "sr_no": sr_no, "rake_no": rake_no, "source": source, "wagon_type": w_type,
                    "receipt": receipt.strftime("%d.%m.%Y/%H:%M"),
                    "placement": placement.strftime("%d.%m.%Y/%H:%M"),
                    "u_end": u_end.strftime("%d.%m.%Y/%H:%M"),
                    "release": release.strftime("%d.%m.%Y/%H:%M"),
                    "u_duration": u_duration, "r_duration": r_duration,
                    "demurrage": demurrage, "gcv": gcv, "vm": vm,
                    "nth": nth, "muth": muth, "wt1": wt1, "wt2": wt2, "wt3": wt3, "wt4": wt4,
                    "rem_mm": rem_mm, "rem_emd": rem_emd, "rem_cni": rem_cni,
                    "rem_opr": rem_opr, "rem_mgr": rem_mgr, "rem_chem": rem_chem, "rem_other": rem_other
                }

                with st.spinner("Processing..."):
                    response = requests.post(URL, json=payload)
                    if response.status_code == 200:
                        st.success(f"✅ Rake {rake_no} recorded successfully!")
                        st.cache_data.clear() # Clears cache so the new data shows up instantly in the other tabs

# ==========================================
# TAB 2: TODAY'S DATA
# ==========================================
with tab_today:
    st.subheader(f"📊 Rake Reports for {datetime.now(IST).strftime('%d %B %Y')}")
    df = fetch_google_sheet_data()
    
    if not df.empty and "Receipt Time & Date" in df.columns:
        # Get today's date string in DD.MM.YYYY format
        today_str = datetime.now(IST).strftime("%d.%m.%Y")
        
        # Filter dataframe for rows containing today's date in the Receipt Time column
        today_df = df[df["Receipt Time & Date"].astype(str).str.contains(today_str, na=False)]
        
        if not today_df.empty:
            st.dataframe(today_df, use_container_width=True)
        else:
            st.info("No data entered for today yet.")
    else:
        st.info("Database is currently empty.")

# ==========================================
# TAB 3: DOWNLOAD DATA
# ==========================================
with tab_download:
    st.subheader("📥 Filter and Download Reports")
    df_all = fetch_google_sheet_data()
    
    if not df_all.empty:
        col1, col2 = st.columns(2)
        with col1:
            filter_month = st.selectbox("Select Month", ["All", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"])
        with col2:
            current_year = datetime.now(IST).strftime("%Y")
            filter_year = st.text_input("Enter Year (e.g. 2026)", value=current_year)
            
        filtered_df = df_all.copy()
        
        if filter_month != "All":
            # Filters rows matching the MM.YYYY pattern in Receipt Date
            search_pattern = f".{filter_month}.{filter_year}"
            filtered_df = filtered_df[filtered_df["Receipt Time & Date"].astype(str).str.contains(search_pattern, na=False)]
            
        st.markdown(f"**Showing {len(filtered_df)} records**")
        st.dataframe(filtered_df, use_container_width=True)
        
        if not filtered_df.empty:
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Download Data as CSV",
                data=csv,
                file_name=f"Rake_Report_{filter_month}_{filter_year}.csv",
                mime="text/csv",
            )
