import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz 
import re
import pandas as pd
import io
import math

# --- CONFIGURATION ---
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyWmANSD06mgC05nEi4SZkdN4pxZp4V_c3TTWK0OsqM0mnWVAq7lqDJsnSSBaegt07r/exec"
LIVE_EXCEL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ6PaPvxvRG_cUNa9NKfYEnujEShvxjjm13zo_SChUNm_jrj5eq5jNnj2vTJuiVFuApHyVFDe6OZolN/pub?output=xlsx"
IST = pytz.timezone('Asia/Kolkata')

# --- USERS DATABASE ---
USERS = {
    "operator": {"password": "op123", "role": "Operator"},
    "admin": {"password": "superadmin2026", "role": "Super Admin"}
}

# --- CLEAN UI & DARK MODE SETUP ---
st.set_page_config(page_title="Rake Master Entry", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; max-width: 98%; }
    /* Dark Mode & Light Mode visible disabled inputs */
    input[disabled] { 
        -webkit-text-fill-color: #0ea5e9 !important; /* Bright cyan pops in dark & light mode */
        color: #0ea5e9 !important; 
        font-weight: 900 !important; 
        background-color: transparent !important; 
        border: 1px solid #0ea5e9 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if 'logged_in' not in st.session_state: 
    st.session_state.logged_in = False
if 'role' not in st.session_state: 
    st.session_state.role = None
if 'username' not in st.session_state: 
    st.session_state.username = None
if 'outages_list' not in st.session_state: 
    st.session_state.outages_list = [] 

# ==========================================
# 0. LOGIN SCREEN
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔒 Rake Data Entry System</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("**Please sign in to continue**")
            username = st.text_input("Username").strip().lower()
            password = st.text_input("Password", type="password")
            submit_btn = st.form_submit_button("Login", use_container_width=True)
            
            if submit_btn:
                if username in USERS and USERS[username]["password"] == password:
                    st.session_state.logged_in = True
                    st.session_state.role = USERS[username]["role"]
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("❌ Invalid Username or Password")
    st.stop() # Stops the rest of the code from running until logged in

# --- SIDEBAR LOGOUT ---
st.sidebar.markdown(f"👤 **User:** {st.session_state.username}")
st.sidebar.markdown(f"🛡️ **Role:** {st.session_state.role}")
if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None
    st.session_state.outages_list = []
    st.rerun()

# --- TIME LOGIC ---
now_ist = datetime.now(IST)
today_ist = now_ist.date()
yesterday_ist = today_ist - timedelta(days=1)
cutoff_12_hrs = now_ist - timedelta(hours=12)

# --- ROLE-BASED DATE LIMITS ---
is_super_admin = (st.session_state.role == "Super Admin")
min_date_allowed = None if is_super_admin else yesterday_ist

st.markdown(f"### 🚂 Rake Master Data Entry (IST)")

tab1, tab2, tab3 = st.tabs(["📝 New Entry Form", "📋 View Records", "📥 Download Reports"])

with tab1:
    if is_super_admin:
        st.success("🛡️ **Super Admin Mode Active:** 12-hour restriction disabled. You can enter or edit data for any past date.")
    else:
        st.info("ℹ️ To EDIT a previous rake, enter the exact RAKE No. (Edits and new entries restricted to past 12 hours).")
    
    # ==========================================
    # 1. BASIC DETAILS
    # ==========================================
    c1, c2, c3, c4, c5 = st.columns([1, 1.5, 1.5, 1, 1])
    with c1: sr_no = st.number_input("Sr.No", min_value=1, step=1)
    with c2: rake_no = st.text_input("RAKE No (XX/XXXX) *").strip().upper() 
    with c3: source = st.text_input("Coal Source/MINE *").strip().upper()   
    with c4: w_qty = st.number_input("Wagon Qty *", min_value=1, max_value=99, value=58)
    with c5: w_type = st.selectbox("Type", ["N", "R"])
    wagon_spec = f"{w_qty}{w_type}"

    st.divider()

    # ==========================================
    # 2. TIMELINE (MANDATORY, ROLE-BASED MIN DATE)
    # ==========================================
    t1, t2, t3, t4 = st.columns(4)
    with t1:
        d_rec = st.date_input("Receipt Date *", value=None, min_value=min_date_allowed, max_value=today_ist)
        ti_rec = st.time_input("Receipt Time *", value=None, step=60)
    with t2:
        d_pla = st.date_input("Placement Date *", value=None, min_value=min_date_allowed, max_value=today_ist)
        ti_pla = st.time_input("Placement Time *", value=None, step=60)
    with t3:
        d_end = st.date_input("U/L End Date *", value=None, min_value=min_date_allowed, max_value=today_ist)
        ti_end = st.time_input("U/L End Time *", value=None, step=60)
    with t4:
        d_rel = st.date_input("Release Date *", value=None, min_value=min_date_allowed, max_value=today_ist)
        ti_rel = st.time_input("Release Time *", value=None, step=60)

    # ==========================================
    # 2.5 AUTO-CALCULATE DURATIONS & DEMURRAGE
    # ==========================================
    u_duration_str = "00:00:00"
    r_duration_str = "00:00:00"
    demurrage_val = 0
    dt_rec = None
    dt_pla = None
    dt_end = None
    dt_rel = None

    if d_rec and ti_rec and d_pla and ti_pla and d_end and ti_end and d_rel and ti_rel:
        dt_rec = IST.localize(datetime.combine(d_rec, ti_rec))
        dt_pla = IST.localize(datetime.combine(d_pla, ti_pla))
        dt_end = IST.localize(datetime.combine(d_end, ti_end))
        dt_rel = IST.localize(datetime.combine(d_rel, ti_rel))

        if dt_rec <= dt_pla <= dt_end <= dt_rel:
            u_td = dt_end - dt_pla
            r_td = dt_rel - dt_rec
            
            u_sec = int(u_td.total_seconds())
            r_sec = int(r_td.total_seconds())
            u_duration_str = f"{u_sec//3600:02d}:{(u_sec%3600)//60:02d}:{u_sec%60:02d}"
            r_duration_str = f"{r_sec//3600:02d}:{(r_sec%3600)//60:02d}:{r_sec%60:02d}"

            r_hours = r_sec / 3600.0
            free_time = 7.0 if w_type == "N" else 2.0
            if r_hours > free_time:
                demurrage_val = math.ceil(r_hours - free_time)

    st.markdown("**⏱️ Auto-Calculated Durations & Demurrage**")
    cd1, cd2, cd3 = st.columns(3)
    with cd1: st.text_input("Unloading Duration", value=u_duration_str, disabled=True)
    with cd2: st.text_input("Release Duration", value=r_duration_str, disabled=True)
    with cd3: st.text_input("Demurrage (Hrs) - Auto Calculated", value=str(demurrage_val), disabled=True)

    st.divider()

    # ==========================================
    # 3. TIPPLERS & OUTAGES
    # ==========================================
    col_tip, col_out = st.columns([1.5, 1])

    with col_tip:
        st.markdown("**🏗️ Tipper Details & NTH/MUTH**")
        nm1, nm2, _ = st.columns([1, 1, 2])
        with nm1: nth = st.text_input("NTH Qty (Optional)").strip().upper()
        with nm2: muth = st.text_input("MUTH Qty (Optional)").strip().upper()

        w_cols = st.columns(4)
        tippler_data = {}
        
        for i, name in enumerate(["WT-1", "WT-2", "WT-3", "WT-4"]):
            with w_cols[i]:
                st.markdown(f"**{name}**")
                t_qty = st.number_input(f"Wagons", min_value=0, key=f"q_{name}")
                t_start = st.time_input("Start Time", value=None, key=f"s_{name}", step=60)
                t_end = st.time_input("End Time", value=None, key=f"e_{name}", step=60)
                
                if t_qty > 0:
                    time_str = f"{t_start.strftime('%H:%M')}-{t_end.strftime('%H:%M')}" if (t_start and t_end) else ""
                    tippler_data[name] = f"{t_qty}\n{time_str}".strip()
                else:
                    tippler_data[name] = ""

    with col_out:
        st.markdown("**🛠️ Dept. Outages (Optional)**")
        with st.form("outage_form", clear_on_submit=True):
            d1, d2 = st.columns(2)
            with d1: dept = st.selectbox("Dept", ["MM", "EMD", "C&I", "OPR", "MGR", "CHEM", "OTHER"])
            with d2: o_reason = st.text_input("Reason")
            
            d3, d4 = st.columns(2)
            with d3: o_start = st.time_input("Start", value=None, step=60)
            with d4: o_end = st.time_input("End", value=None, step=60)
            
            if st.form_submit_button("➕ Add Outage", use_container_width=True):
                if o_start:
                    str_s = o_start.strftime('%H:%M')
                    str_e = o_end.strftime('%H:%M') if o_end else "FULL DAY"
                    st.session_state.outages_list.append({"Dept": dept, "Start": str_s, "End": str_e, "Reason": o_reason.strip().upper(), "Log": f"{dept} | {str_s} to {str_e} | {o_reason.strip().upper()}"})

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
    
    # Helper function to figure out the date for a given HH:MM time
    def resolve_tippler_time(t_time, dt_min, dt_max):
        curr = dt_min.date()
        while curr <= dt_max.date():
            candidate = IST.localize(datetime.combine(curr, t_time))
            if dt_min <= candidate <= dt_max:
                return candidate
            curr += timedelta(days=1)
        return None

    def validate_12_hours(dt, label):
        if is_super_admin:
            return True # Super Admin bypasses this check completely
            
        if dt < cutoff_12_hrs:
            st.error(f"❌ {label} ({dt.strftime('%d.%m %H:%M')}) is older than 12 hours! Entry blocked. Contact Super Admin to edit.")
            return False
        if dt > now_ist:
            st.error(f"❌ {label} cannot be in the future!")
            return False
        return True

    if st.button("🚀 Submit Data to Master Sheet", type="primary", use_container_width=True):
        if not rake_no or not source:
            st.error("❌ RAKE No and Coal Source are MANDATORY.")
            st.stop()
        if not re.match(r"^\d+/\d+$", rake_no):
            st.error("❌ RAKE No must be XX/XXXX.")
            st.stop()
        if not dt_rec:
            st.error("❌ ALL 4 Timeline Dates and Times are MANDATORY.")
            st.stop()

        # Run 12-hour rule (Auto-bypassed if Super Admin)
        if not (validate_12_hours(dt_rec, "Receipt Time") and validate_12_hours(dt_pla, "Placement Time") and 
                validate_12_hours(dt_end, "Unloading End Time") and validate_12_hours(dt_rel, "Release Time")):
            st.stop()

        if not (dt_rec <= dt_pla <= dt_end <= dt_rel):
            st.error("❌ Timeline error: Must be strictly Receipt -> Placement -> End -> Release.")
            st.stop()

        for name in ["WT-1", "WT-2", "WT-3", "WT-4"]:
            qty = st.session_state.get(f"q_{name}", 0)
            t_s = st.session_state.get(f"s_{name}", None)
            t_e = st.session_state.get(f"e_{name}", None)
            
            if qty > 0:
                if t_s is None or t_e is None:
                    st.error(f"⚠️ Start and End times are MANDATORY for {name} because Wagon Count is {qty}.")
                    st.stop()
                
                # Verify Tippler Start Time is >= Receipt Time and <= U/L End Time
                dt_tip_start = resolve_tippler_time(t_s, dt_rec, dt_end)
                if not dt_tip_start:
                    st.error(f"❌ {name} Start Time ({t_s.strftime('%H:%M')}) cannot be before Receipt Time or after U/L End Time!")
                    st.stop()
                
                # Verify Tippler End Time is >= Tippler Start Time and <= U/L End Time
                dt_tip_end = resolve_tippler_time(t_e, dt_tip_start, dt_end)
                if not dt_tip_end:
                    st.error(f"❌ {name} End Time ({t_e.strftime('%H:%M')}) cannot be before its Start Time or after U/L End Time!")
                    st.stop()

        # Generate month tab name e.g. "FEB-26"
        month_tab_name = d_rec.strftime('%b-%y').upper()

        outage_summary = "\n".join([o["Log"] for o in st.session_state.outages_list])
        
        payload = {
            "tab_name": month_tab_name,
            "sr_no": sr_no, "rake_no": rake_no, "source": source, "wagon_spec": wagon_spec,
            "receipt": f"{d_rec.strftime('%d.%m.%Y')}/{ti_rec.strftime('%H:%M')}",
            "placement": f"{d_pla.strftime('%d.%m.%Y')}/{ti_pla.strftime('%H:%M')}",
            "u_end": f"{d_end.strftime('%d.%m.%Y')}/{ti_end.strftime('%H:%M')}",
            "release": f"{d_rel.strftime('%d.%m.%Y')}/{ti_rel.strftime('%H:%M')}",
            "u_duration": u_duration_str, "r_duration": r_duration_str, "demurrage": demurrage_val, 
            "remarks": outage_summary, 
            "nth": nth, "muth": muth, 
            "wt1": tippler_data["WT-1"], "wt2": tippler_data["WT-2"], 
            "wt3": tippler_data["WT-3"], "wt4": tippler_data["WT-4"],
            "gcv": 0, "vm": 0
        }
        
        with st.spinner(f"Writing securely to {month_tab_name} tab in Google Sheets..."):
            try:
                res = requests.post(APPS_SCRIPT_URL, json=payload)
                if res.status_code == 200:
                    st.success(f"✅ Rake {rake_no} processed successfully to {month_tab_name}!")
                    st.session_state.outages_list.clear()
            except Exception as e:
                st.error(f"Connection failed: {e}")

# ==========================================
# 5 & 6. MULTI-SHEET READING LOGIC
# ==========================================
def get_all_excel_data():
    try:
        r = requests.get(LIVE_EXCEL_URL)
        all_sheets = pd.read_excel(io.BytesIO(r.content), engine='openpyxl', sheet_name=None)
        return pd.concat(all_sheets.values(), ignore_index=True).dropna(how='all')
    except:
        return pd.DataFrame()

with tab2:
    st.subheader(f"📊 Today's Rake Entries ({today_ist.strftime('%d.%m.%Y')})")
    
    df_all = get_all_excel_data()
    if not df_all.empty:
        mask = df_all.astype(str).apply(lambda x: x.str.contains(today_ist.strftime('%d.%m.%Y'), na=False)).any(axis=1)
        today_data = df_all[mask].tail(10)
        
        if not today_data.empty:
            st.dataframe(today_data, use_container_width=True, hide_index=True)
        else:
            st.info("No entries logged for today yet.")
    else:
        st.info("No Master Data found.")

with tab3:
    st.subheader("📥 Export Master Data by Date")
    st.markdown("Select a date below to instantly download that day's records in a formatted Excel file.")
    
    selected_export_date = st.date_input("Select Date", value=today_ist, key="export_date")
    
    if st.button("🔍 Search & Generate Excel File", type="primary"):
        with st.spinner(f"Fetching records..."):
            df_export = get_all_excel_data()
            if not df_export.empty:
                t_str = selected_export_date.strftime('%d.%m.%Y')
                mask = df_export.astype(str).apply(lambda x: x.str.contains(t_str, na=False)).any(axis=1)
                filtered_df = df_export[mask]
                
                if filtered_df.empty:
                    st.warning(f"No records found for {t_str}. Please try another date.")
                else:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        filtered_df.to_excel(writer, index=False, sheet_name='Master Data')
                        for col in writer.sheets['Master Data'].columns:
                            max_len = max([len(str(c.value)) for c in col] + [0])
                            writer.sheets['Master Data'].column_dimensions[col[0].column_letter].width = min(max_len + 2, 45)
                            
                    st.success(f"✅ Found {len(filtered_df)} records for {t_str}!")
                    st.download_button(
                        label=f"💾 Download {t_str} Excel Report", 
                        data=output.getvalue(), 
                        file_name=f"Rake_{selected_export_date.strftime('%Y%m%d')}.xlsx", 
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                        use_container_width=True
                    )
            else:
                st.error("Failed to connect to Google Sheets.")
