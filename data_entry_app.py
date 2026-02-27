import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz 
import re
import pandas as pd

# --- CONFIGURATION ---
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwXAQcE3gKmvSPetG-Lp1QFecUSzMYS-GyTtHcXSLVl8G-ffYcN121ARSbfc9z1dtdk/exec"
LIVE_EXCEL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ6PaPvxvRG_cUNa9NKfYEnujEShvxjjm13zo_SChUNm_jrj5eq5jNnj2vTJuiVFuApHyVFDe6OZolN/pub?output=xlsx"
IST = pytz.timezone('Asia/Kolkata')

# Squeeze UI to remove blank space
st.set_page_config(page_title="Rake Master Entry", layout="wide")
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; max-width: 98%; }
    div[data-testid="stVerticalBlock"] { gap: 0.2rem; }
    </style>
""", unsafe_allow_html=True)

# Time logic
now_ist = datetime.now(IST)
today_ist = now_ist.date()
yesterday_ist = today_ist - timedelta(days=1)
cutoff_12_hrs = now_ist - timedelta(hours=12)

# State initialization
if 'outages_list' not in st.session_state: st.session_state.outages_list = [] 

st.markdown("### 🚂 Rake Master Data Entry (IST)")
st.caption("ℹ️ To EDIT a previous rake, enter the same RAKE No. (Edits and new entries restricted to past 12 hours).")

# ==========================================
# 1. BASIC DETAILS (CAPS ENFORCED)
# ==========================================
c1, c2, c3, c4, c5, c6 = st.columns([1, 1.5, 1.5, 1, 1, 1])
with c1: sr_no = st.number_input("Sr.No", min_value=1, step=1)
with c2: rake_no = st.text_input("RAKE No (XX/XXXX)").upper() # CAPS Enforced
with c3: source = st.text_input("Coal Source/MINE").upper()   # CAPS Enforced
with c4: w_qty = st.number_input("Wagon Qty", min_value=1, max_value=99, value=58)
with c5: w_type = st.selectbox("Type", ["N", "R"])
with c6: demurrage = st.number_input("Demurrage(Hrs)", min_value=0.0, step=0.1)
wagon_spec = f"{w_qty}{w_type}"

st.divider()

# ==========================================
# 2. TIMELINE (NO DEFAULTS, 1-MIN RESOLUTION)
# ==========================================
t1, t2, t3, t4 = st.columns(4)
with t1:
    d_rec = st.date_input("Receipt Date", value=None, min_value=yesterday_ist, max_value=today_ist)
    ti_rec = st.time_input("Receipt Time", value=None, step=60)
with t2:
    d_pla = st.date_input("Placement Date", value=None, min_value=yesterday_ist, max_value=today_ist)
    ti_pla = st.time_input("Placement Time", value=None, step=60)
with t3:
    d_end = st.date_input("U/L End Date", value=None, min_value=yesterday_ist, max_value=today_ist)
    ti_end = st.time_input("U/L End Time", value=None, step=60)
with t4:
    d_rel = st.date_input("Release Date", value=None, min_value=yesterday_ist, max_value=today_ist)
    ti_rel = st.time_input("Release Time", value=None, step=60)

st.divider()

# ==========================================
# 3. TIPPLERS & OUTAGES (SIDE-BY-SIDE SQUEEZE)
# ==========================================
col_tip, col_out = st.columns([1.5, 1])

# --- TIPPLERS ---
with col_tip:
    st.markdown("**🏗️ Tipper Details & NTH/MUTH**")
    nm1, nm2, _ = st.columns([1, 1, 2])
    with nm1: nth = st.text_input("NTH Qty").upper()
    with nm2: muth = st.text_input("MUTH Qty").upper()

    w_cols = st.columns(4)
    tippler_data = {}
    
    for i, name in enumerate(["WT-1", "WT-2", "WT-3", "WT-4"]):
        with w_cols[i]:
            t_qty = st.number_input(f"{name} Count", min_value=0, key=f"q_{name}")
            t_start = st.time_input("Start", value=None, key=f"s_{name}", step=60, label_visibility="collapsed")
            t_end = st.time_input("End", value=None, key=f"e_{name}", step=60, label_visibility="collapsed")
            
            if t_qty > 0:
                time_str = f"{t_start.strftime('%H:%M')}-{t_end.strftime('%H:%M')}" if (t_start and t_end) else ""
                tippler_data[name] = f"{t_qty}\n{time_str}".strip()
            else:
                tippler_data[name] = ""

# --- OUTAGES (COLUMN L) ---
with col_out:
    st.markdown("**🛠️ Dept. Outages**")
    with st.form("outage_form", clear_on_submit=True):
        d1, d2 = st.columns(2)
        with d1: dept = st.selectbox("Dept", ["MM", "EMD", "C&I", "OPR", "MGR", "CHEM", "OTHER"])
        with d2: o_reason = st.text_input("Reason")
        
        d3, d4, d5 = st.columns([1, 1, 1])
        with d3: o_start = st.time_input("Start", value=None, step=60)
        with d4: o_end = st.time_input("End", value=None, step=60)
        with d5: 
            st.write("")
            if st.form_submit_button("➕ Add"):
                if o_start:
                    str_s = o_start.strftime('%H:%M')
                    str_e = o_end.strftime('%H:%M') if o_end else "FULL DAY"
                    st.session_state.outages_list.append({"Dept": dept, "Start": str_s, "End": str_e, "Reason": o_reason.upper(), "Log": f"{dept} | {str_s} to {str_e} | {o_reason.upper()}"})

    if st.session_state.outages_list:
        try:
            st.dataframe(pd.DataFrame(st.session_state.outages_list)[["Dept", "Start", "End", "Reason"]], use_container_width=True, hide_index=True)
        except KeyError:
            st.session_state.outages_list.clear()
        if st.button("🗑️ Clear Outages"):
            st.session_state.outages_list.clear()
            st.rerun()

st.divider()

# ==========================================
# 4. VALIDATION & SUBMISSION LOGIC
# ==========================================
def validate_12_hours(d, t, label):
    if not d or not t: 
        st.error(f"❌ Missing date or time for {label}.")
        return False
    dt = IST.localize(datetime.combine(d, t))
    if dt < cutoff_12_hrs:
        st.error(f"❌ {label} ({dt.strftime('%d.%m %H:%M')}) is older than 12 hours! Entry blocked.")
        return False
    if dt > now_ist:
        st.error(f"❌ {label} cannot be in the future!")
        return False
    return True

if st.button("🚀 Submit Data to Master Sheet", type="primary", use_container_width=True):
    # RAKE VALIDATION
    if not re.match(r"^\d+/\d+$", rake_no):
        st.error("❌ RAKE No must be XX/XXXX.")
        st.stop()
        
    # MANDATORY TIPPLER TIME VALIDATION
    for name in ["WT-1", "WT-2", "WT-3", "WT-4"]:
        qty = st.session_state.get(f"q_{name}", 0)
        start = st.session_state.get(f"s_{name}", None)
        end = st.session_state.get(f"e_{name}", None)
        if qty > 0 and (start is None or end is None):
            st.error(f"⚠️ Start and End times are MANDATORY for {name} because Wagon Count is {qty}.")
            st.stop()
            
    # TIMELINE & 12-HOUR VALIDATION
    if not (validate_12_hours(d_rec, ti_rec, "Receipt Time") and validate_12_hours(d_pla, ti_pla, "Placement Time") and 
            validate_12_hours(d_end, ti_end, "Unloading End Time") and validate_12_hours(d_rel, ti_rel, "Release Time")):
        st.stop()

    # CHRONOLOGICAL ORDER VALIDATION
    dt_rec = datetime.combine(d_rec, ti_rec)
    dt_pla = datetime.combine(d_pla, ti_pla)
    dt_end = datetime.combine(d_end, ti_end)
    dt_rel = datetime.combine(d_rel, ti_rel)
    
    if not (dt_rec <= dt_pla <= dt_end <= dt_rel):
        st.error("❌ Timeline error: Dates/Times must be in chronological order (Receipt -> Placement -> End -> Release).")
        st.stop()

    # PAYLOAD ASSEMBLY
    outage_summary = "\n".join([o["Log"] for o in st.session_state.outages_list])

    payload = {
        "sr_no": sr_no, "rake_no": rake_no, "source": source, "wagon_spec": wagon_spec,
        "receipt": f"{d_rec.strftime('%d.%m.%Y')}/{ti_rec.strftime('%H:%M')}",
        "placement": f"{d_pla.strftime('%d.%m.%Y')}/{ti_pla.strftime('%H:%M')}",
        "u_end": f"{d_end.strftime('%d.%m.%Y')}/{ti_end.strftime('%H:%M')}",
        "release": f"{d_rel.strftime('%d.%m.%Y')}/{ti_rel.strftime('%H:%M')}",
        "u_duration": "CALC", "r_duration": "CALC", "demurrage": demurrage, 
        "remarks": outage_summary, 
        "nth": nth, "muth": muth, 
        "wt1": tippler_data["WT-1"], "wt2": tippler_data["WT-2"], 
        "wt3": tippler_data["WT-3"], "wt4": tippler_data["WT-4"],
        "gcv": 0, "vm": 0
    }
    
    with st.spinner("Writing securely..."):
        try:
            res = requests.post(APPS_SCRIPT_URL, json=payload)
            if res.status_code == 200:
                st.success(f"✅ Rake {rake_no} processed successfully!")
                st.session_state.outages_list.clear()
        except Exception as e:
            st.error(f"Connection failed: {e}")

# ==========================================
# 5. RECENT ENTRIES VIEWER (TODAY ONLY)
# ==========================================
st.subheader(f"📊 Today's Rake Entries ({today_ist.strftime('%d.%m.%Y')})")

@st.cache_data(ttl=10) 
def fetch_today_data():
    try:
        df = pd.read_excel(LIVE_EXCEL_URL, engine='openpyxl').dropna(how='all')
        # Filter dataframe to ONLY show rows containing today's date
        today_str = today_ist.strftime('%d.%m.%Y')
        mask = df.astype(str).apply(lambda x: x.str.contains(today_str, na=False)).any(axis=1)
        return df[mask].tail(10)
    except Exception as e:
        return pd.DataFrame()

today_data = fetch_today_data()
if not today_data.empty:
    st.dataframe(today_data, use_container_width=True, hide_index=True)
else:
    st.info("No entries logged for today yet.")
