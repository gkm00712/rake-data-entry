import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz 
import re
import pandas as pd

# --- CONFIGURATION ---
# Your specific URLs are now hardcoded here
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbzJ4WB-UlJkgxN7eC_ekpav-OJ1lY2pNloq0Fn8KahnHHzRoQSwbYjGYnt3kVAbKzbu/exec"
LIVE_EXCEL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ6PaPvxvRG_cUNa9NKfYEnujEShvxjjm13zo_SChUNm_jrj5eq5jNnj2vTJuiVFuApHyVFDe6OZolN/pub?output=xlsx"
IST = pytz.timezone('Asia/Kolkata')

st.set_page_config(page_title="Railway Rake Master Entry", layout="wide")

# --- TIME SYNCHRONIZATION (IST) ---
now_ist = datetime.now(IST)
today_ist = now_ist.date()
yesterday_ist = today_ist - timedelta(days=1)

# --- SESSION STATE INITIALIZATION ---
if 'rake_val' not in st.session_state:
    st.session_state.rake_val = ""
if 'outages_list' not in st.session_state:
    st.session_state.outages_list = [] 

st.title("🚂 Rake Master Data Entry (IST)")

tab1, tab2 = st.tabs(["📝 New Entry Form", "📋 View Yesterday & Today"])

with tab1:
    # ==========================================
    # 1. BASIC DETAILS (Tight Grid)
    # ==========================================
    c1, c2, c3, c4, c5, c6 = st.columns([1, 2, 2, 1, 1, 1.5])
    with c1: sr_no = st.number_input("Sr.No", min_value=1, step=1)
    with c2: rake_no = st.text_input("RAKE No (XX/XXXX)", key="rake_val")
    with c3: source = st.text_input("Coal Source/MINE")
    with c4: w_qty = st.number_input("Wagon Qty", min_value=1, max_value=99, value=58)
    with c5: w_type = st.selectbox("Type", ["N", "R"])
    with c6: demurrage = st.number_input("Demurrage(Hrs)", min_value=0.0, step=0.1)
    wagon_spec = f"{w_qty}{w_type}"

    st.divider()

    # ==========================================
    # 2. TIMELINE (Dropdowns Only)
    # ==========================================
    st.subheader("📅 Timeline (IST)")
    t1, t2, t3, t4 = st.columns(4)
    with t1:
        d_rec = st.date_input("Receipt Date", value=today_ist, min_value=yesterday_ist, max_value=today_ist)
        ti_rec = st.time_input("Receipt Time", value=now_ist.time(), step=60)
    with t2:
        d_pla = st.date_input("Placement Date", value=today_ist, min_value=yesterday_ist, max_value=today_ist)
        ti_pla = st.time_input("Placement Time", value=now_ist.time(), step=60)
    with t3:
        d_end = st.date_input("U/L End Date", value=today_ist, min_value=yesterday_ist, max_value=today_ist)
        ti_end = st.time_input("U/L End Time", value=now_ist.time(), step=60)
    with t4:
        d_rel = st.date_input("Release Date", value=today_ist, min_value=yesterday_ist, max_value=today_ist)
        ti_rel = st.time_input("Release Time", value=now_ist.time(), step=60)

    st.divider()

    # ==========================================
    # 3. TIPPLER DETAILS (Minimal Blank Space)
    # ==========================================
    st.subheader("🏗️ Tipper Details")
    
    nm1, nm2, _ = st.columns([1, 1, 6])
    with nm1: nth = st.text_input("NTH Qty")
    with nm2: muth = st.text_input("MUTH Qty")

    w_cols = st.columns(4)
    tippler_data = {}
    tippler_names = ["WT-1", "WT-2", "WT-3", "WT-4"]

    for i, name in enumerate(tippler_names):
        with w_cols[i]:
            st.markdown(f"**{name}**")
            t_qty = st.number_input("Wagon Count", min_value=0, key=f"q_{name}")
            c_start, c_end = st.columns(2)
            t_start = c_start.time_input("Start", value=None, key=f"s_{name}", step=60)
            t_end = c_end.time_input("End", value=None, key=f"e_{name}", step=60)
            
            if t_qty > 0:
                time_str = f"{t_start.strftime('%H:%M')}-{t_end.strftime('%H:%M')}" if (t_start and t_end) else ""
                tippler_data[name] = f"{t_qty}\n{time_str}".strip()
            else:
                tippler_data[name] = ""

    st.divider()

    # ==========================================
    # 4. DEPARTMENTAL OUTAGES
    # ==========================================
    st.subheader("🛠️ Departmental Outages")
    
    with st.form("outage_form", clear_on_submit=True):
        d1, d2, d3, d4, d5 = st.columns([1.5, 1.5, 1.5, 3, 1])
        with d1:
            dept = st.selectbox("Department", ["MM", "EMD", "C&I", "OPR", "MGR", "CHEMISTRY", "OTHER"])
        with d2:
            o_start = st.time_input("Start Time", value=None, step=60)
        with d3:
            o_end = st.time_input("End Time", value=None, step=60, help="Leave blank for Full Day")
        with d4:
            o_reason = st.text_input("Reason / Remarks for Outage")
        with d5:
            st.write("") # Alignment
            add_outage = st.form_submit_button("➕ Add")
            
        if add_outage and o_start:
            str_start = o_start.strftime('%H:%M')
            str_end = o_end.strftime('%H:%M') if o_end else "FULL DAY"
            log_str = f"{dept} | {str_start} to {str_end} | Reason: {o_reason}"
            
            st.session_state.outages_list.append({
                "Dept": dept, "Start": str_start, "End": str_end, "Reason": o_reason, "Log": log_str
            })

    # Outages Table Display with KeyError Crash Protection
    if st.session_state.outages_list:
        df_outages = pd.DataFrame(st.session_state.outages_list)
        try:
            st.table(df_outages[["Dept", "Start", "End", "Reason"]])
        except KeyError:
            # If old memory conflicts with the updated column names, auto-clear to prevent app crash
            st.session_state.outages_list.clear()
            st.rerun()
            
        if st.button("🗑️ Clear Outages"):
            st.session_state.outages_list.clear()
            st.rerun()

    remarks_text = st.text_area("General Remarks (Logistics, Bunching, etc.)")

    # ==========================================
    # SUBMISSION LOGIC
    # ==========================================
    if st.button("🚀 Submit Final Data to Master Sheet", type="primary"):
        if not re.match(r"^\d+/\d+$", st.session_state.rake_val):
            st.error("❌ Error: RAKE No must be XX/XXXX (e.g., 1/1481). Entry rejected.")
            st.session_state.rake_val = ""
            st.rerun()
        else:
            outage_summary = "\n".join([o["Log"] for o in st.session_state.outages_list])
            final_remarks = f"{outage_summary}\n{remarks_text}".strip()

            payload = {
                "sr_no": sr_no, "rake_no": st.session_state.rake_val, "source": source,
                "wagon_spec": wagon_spec,
                "receipt": f"{d_rec.strftime('%d.%m.%Y')}/{ti_rec.strftime('%H:%M')}",
                "placement": f"{d_pla.strftime('%d.%m.%Y')}/{ti_pla.strftime('%H:%M')}",
                "u_end": f"{d_end.strftime('%d.%m.%Y')}/{ti_end.strftime('%H:%M')}",
                "release": f"{d_rel.strftime('%d.%m.%Y')}/{ti_rel.strftime('%H:%M')}",
                "u_duration": "CALC", "r_duration": "CALC",
                "demurrage": demurrage, "remarks": final_remarks,
                "nth": nth, "muth": muth, 
                "wt1": tippler_data["WT-1"], "wt2": tippler_data["WT-2"], 
                "wt3": tippler_data["WT-3"], "wt4": tippler_data["WT-4"],
                "gcv": 0, "vm": 0
            }
            
            with st.spinner("Writing securely to Google Sheets..."):
                try:
                    res = requests.post(APPS_SCRIPT_URL, json=payload)
                    if res.status_code == 200:
                        st.success(f"✅ Rake {st.session_state.rake_val} saved successfully!")
                        st.session_state.outages_list.clear()
                        st.balloons()
                except Exception as e:
                    st.error(f"Connection failed: {e}")

# ==========================================
# RECENT ENTRIES VIEWER
# ==========================================
with tab2:
    st.info(f"Viewing records restricted to Yesterday ({yesterday_ist.strftime('%d.%m.%Y')}) and Today ({today_ist.strftime('%d.%m.%Y')}) IST.")

st.divider()
st.subheader("📊 Recent Master Sheet Entries")

@st.cache_data(ttl=10) 
def fetch_recent_data():
    try:
        df = pd.read_excel(LIVE_EXCEL_URL, engine='openpyxl')
        return df.dropna(how='all').tail(5)
    except Exception as e:
        return pd.DataFrame()

recent_data = fetch_recent_data()
if not recent_data.empty:
    st.dataframe(recent_data, use_container_width=True, hide_index=True)
else:
    st.info("No recent data found. Make sure your Google Sheet is published and has data.")
