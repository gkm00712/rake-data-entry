import streamlit as st
import requests
from datetime import datetime, timedelta
import pytz 
import re
import pandas as pd
import io
import math

# --- OPTIONAL: KEEPALIVE FOR SESSION ---
# If you installed streamlit-autorefresh, uncomment the next two lines to keep sessions alive forever:
# from streamlit_autorefresh import st_autorefresh
# st_autorefresh(interval=300000, key="session_keepalive") # Pings every 5 mins

# --- CONFIGURATION ---
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx6CM0dhRGBpB0C_TxkohVceQ61MxgFoGasy65As5KIqByHG7tES-gAx0deLdbpugNq/exec"
LIVE_EXCEL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ6PaPvxvRG_cUNa9NKfYEnujEShvxjjm13zo_SChUNm_jrj5eq5jNnj2vTJuiVFuApHyVFDe6OZolN/pub?output=xlsx"
IST = pytz.timezone('Asia/Kolkata')

# --- USERS DATABASE ---
USERS = {
    "operator": {"password": "op123", "role": "Operator"},
    "admin": {"password": "superadmin2026", "role": "Super Admin"}
}

# --- CLEAN UI & DARK MODE SETUP ---
st.set_page_config(page_title="Rake Data Entry", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Ultra-compact but safe main container */
    .block-container { padding-top: 1rem; padding-bottom: 0rem; max-width: 98%; }
    
    /* Shrink gaps between elements safely */
    div[data-testid="stVerticalBlock"] { gap: 0.3rem !important; }
    
    /* Elegant, compact inputs */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stDateInput>div>div>input, .stTimeInput>div>div>input, .stSelectbox>div>div>div {
        height: 1.8rem !important;
        min-height: 1.8rem !important;
        font-size: 0.85rem !important;
        padding-top: 0px !important;
        padding-bottom: 0px !important;
    }
    
    /* Shrink labels slightly to save vertical space */
    label { font-size: 0.8rem !important; font-weight: 600 !important; margin-bottom: -0.2rem !important; }
    
    /* Dark Mode & Light Mode visible disabled inputs (Auto-Calculated) */
    input[disabled] { 
        -webkit-text-fill-color: #0ea5e9 !important; 
        color: #0ea5e9 !important; 
        font-weight: 900 !important; 
        background-color: rgba(14, 165, 233, 0.05) !important; 
        border: 1px solid #0ea5e9 !important;
    }
    
    /* Primary Button Styling */
    button[kind="primary"] {
        font-weight: bold !important;
        height: 2.5rem !important;
        border-radius: 6px !important;
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
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<h2 style='text-align: center; margin-top: 10vh;'>🚂 Rake Control Room</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("Username").strip().lower()
            password = st.text_input("Password", type="password")
            submit_btn = st.form_submit_button("Secure Login", use_container_width=True)
            
            if submit_btn:
                if username in USERS and USERS[username]["password"] == password:
                    st.session_state.logged_in = True
                    st.session_state.role = USERS[username]["role"]
                    st.session_state.username = username
                    st.rerun()
                else: 
                    st.error("❌ Invalid Credentials")
    st.stop() 

# --- TOP BAR (Replaces Sidebar to save space) ---
top1, top2 = st.columns([4, 1])
with top1: 
    st.markdown(f"### 🚂 Rake Data Master ({st.session_state.role})")
with top2: 
    if st.button("🚪 Logout", use_container_width=True):
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

is_super_admin = (st.session_state.role == "Super Admin")
min_date_allowed = None if is_super_admin else yesterday_ist

# ==========================================
# EXCEL DATA FETCHING & HELPER FUNCTIONS
# ==========================================
@st.cache_data(ttl=10)
def get_all_excel_data():
    try:
        r = requests.get(LIVE_EXCEL_URL)
        all_sheets = pd.read_excel(io.BytesIO(r.content), engine='openpyxl', sheet_name=None)
        return pd.concat(all_sheets.values(), ignore_index=True).dropna(how='all')
    except: 
        return pd.DataFrame()

def get_next_rake_details(df):
    if df.empty or 'RAKE No' not in df.columns: 
        return 1, ""
        
    df_clean = df.copy()
    df_clean['RAKE No'] = df_clean['RAKE No'].astype(str).str.strip().str.lstrip("'")
    df_clean = df_clean[~df_clean['RAKE No'].isin(['nan', '', 'None'])]
    
    if df_clean.empty: 
        return 1, ""
        
    if 'Receipt Time & Date' in df_clean.columns:
        def safe_date_parse(dt_str):
            try:
                d_str, t_str = str(dt_str).split('/')
                return datetime.strptime(f"{d_str.strip()} {t_str.strip()}", "%d.%m.%Y %H:%M")
            except: 
                return datetime.min
        df_clean['Parsed_Date'] = df_clean['Receipt Time & Date'].apply(safe_date_parse)
        df_clean = df_clean.sort_values(by='Parsed_Date', ascending=True)

    last_row = df_clean.iloc[-1]
    
    try: 
        next_sr = int(float(last_row.get('Sr. No.', 0))) + 1
    except: 
        next_sr = 1
        
    next_rake = ""
    try:
        parts = str(last_row['RAKE No']).split('/')
        if len(parts) == 2: 
            next_rake = f"{int(parts[0])+1}/{int(parts[1])+1}"
    except: 
        pass
        
    return next_sr, next_rake

def parse_excel_datetime(dt_str):
    try:
        if pd.isna(dt_str) or not str(dt_str).strip(): 
            return None, None
        d_part, t_part = str(dt_str).strip().split('/')
        d_obj = datetime.strptime(d_part.strip(), "%d.%m.%Y").date()
        t_obj = datetime.strptime(t_part.strip(), "%H:%M").time()
        return d_obj, t_obj
    except: 
        return None, None

def parse_excel_tippler(tip_str):
    try:
        if pd.isna(tip_str) or not str(tip_str).strip(): 
            return 0, None, None
        qty_part, time_part = str(tip_str).strip().split('\n')
        qty = int(re.search(r'\d+', qty_part).group())
        s_str, e_str = time_part.split('-')
        s_obj = datetime.strptime(s_str.strip(), "%H:%M").time()
        e_obj = datetime.strptime(e_str.strip(), "%H:%M").time()
        return qty, s_obj, e_obj
    except: 
        return 0, None, None

# ==========================================
# MAIN APPLICATION TABS
# ==========================================
tab1, tab2, tab3 = st.tabs(["📝 Form Dashboard", "📋 View Records", "📥 Reports"])

with tab1:
    entry_mode = st.radio(
        "Mode:", 
        ["➕ New Entry", "✏️ Edit Existing"], 
        horizontal=True, 
        label_visibility="collapsed"
    )
    df_all = get_all_excel_data()
    
    # --- DEFAULT VARIABLES SETUP ---
    default_sr = 1
    default_rake = ""
    default_source = ""
    default_qty = 58
    default_type_idx = 0
    default_nth = ""
    default_muth = ""
    
    d_rec_def = None
    t_rec_def = None
    d_pla_def = None
    t_pla_def = None
    d_end_def = None
    t_end_def = None
    d_rel_def = None
    t_rel_def = None

    tip_defaults = { 
        "WT-1": (0, None, None), 
        "WT-2": (0, None, None), 
        "WT-3": (0, None, None), 
        "WT-4": (0, None, None) 
    }

    # --- MODE LOGIC & HYDRATION ---
    if entry_mode == "➕ New Entry":
        default_sr, default_rake = get_next_rake_details(df_all)
        
    elif entry_mode == "✏️ Edit Existing":
        if df_all.empty or 'RAKE No' not in df_all.columns: 
            st.warning("No data available.")
            st.stop()
            
        existing_rakes = [r for r in df_all['RAKE No'].astype(str).str.strip().str.lstrip("'").tolist() if r.lower() != 'nan']
        display_rakes = existing_rakes if is_super_admin else existing_rakes[-15:]
        
        if not display_rakes: 
            st.warning("No recent rakes found.")
            st.stop()
            
        selected_edit_rake = st.selectbox("Select Rake to Edit:", reversed(display_rakes))
        
        if selected_edit_rake:
            row = df_all[df_all['RAKE No'].astype(str).str.contains(selected_edit_rake, regex=False)].iloc[-1]
            
            try: 
                default_sr = int(row['Sr. No.'])
            except: 
                pass
                
            default_rake = selected_edit_rake
            default_source = str(row['Coal Source/ MINE']) if pd.notna(row['Coal Source/ MINE']) else ""
            default_nth = str(row['NTH']) if pd.notna(row['NTH']) else ""
            default_muth = str(row['MUTH']) if pd.notna(row['MUTH']) else ""
            
            spec_str = str(row['(BOXN / BOBR)'])
            if spec_str and spec_str.lower() != 'nan':
                try: 
                    default_qty = int(''.join(filter(str.isdigit, spec_str)))
                except: 
                    pass
                if 'R' in spec_str.upper(): 
                    default_type_idx = 1
                    
            d_rec_def, t_rec_def = parse_excel_datetime(row['Receipt Time & Date'])
            d_pla_def, t_pla_def = parse_excel_datetime(row['Placement Date & Time'])
            d_end_def, t_end_def = parse_excel_datetime(row['Unloading End Date & Time'])
            d_rel_def, t_rel_def = parse_excel_datetime(row['Rake Release Date & Time'])
            
            for w in ["WT-1", "WT-2", "WT-3", "WT-4"]: 
                tip_defaults[w] = parse_excel_tippler(row.get(w, ''))

    # ==========================================
    # THE 3-COLUMN DASHBOARD UI
    # ==========================================
    col_left, col_mid, col_right = st.columns([1.2, 1.4, 1.6])

    # --- MIDDLE COLUMN: Timeline (Executed First to capture dates for calculations) ---
    with col_mid:
        st.markdown("**2. Operational Timeline**")
        
        # Receipt
        st.caption("📥 Receipt")
        tr1, tr2 = st.columns(2)
        with tr1: d_rec = st.date_input("Date", value=d_rec_def, min_value=min_date_allowed, max_value=today_ist, key="dr")
        with tr2: ti_rec = st.time_input("Time", value=t_rec_def, step=60, key="tr")
        
        # Placement
        st.caption("🏗️ Placement")
        tp1, tp2 = st.columns(2)
        with tp1: d_pla = st.date_input("Date", value=d_pla_def, min_value=min_date_allowed, max_value=today_ist, key="dp")
        with tp2: ti_pla = st.time_input("Time", value=t_pla_def, step=60, key="tp")
        
        # U/L End
        st.caption("🏁 U/L End")
        te1, te2 = st.columns(2)
        with te1: d_end = st.date_input("Date", value=d_end_def, min_value=min_date_allowed, max_value=today_ist, key="de")
        with te2: ti_end = st.time_input("Time", value=t_end_def, step=60, key="te")
        
        # Release
        st.caption("🚀 Release")
        tl1, tl2 = st.columns(2)
        with tl1: d_rel = st.date_input("Date", value=d_rel_def, min_value=min_date_allowed, max_value=today_ist, key="drel")
        with tl2: ti_rel = st.time_input("Time", value=t_rel_def, step=60, key="trel")

    # --- LEFT COLUMN: Identity & Calcs (Executed Second) ---
    with col_left:
        st.markdown("**1. Rake Identity**")
        c1, c2 = st.columns([1, 1.5])
        with c1: 
            sr_no = st.number_input("Sr.No", min_value=1, step=1, value=default_sr)
        with c2: 
            rake_no = st.text_input("RAKE No*", value=default_rake).strip().upper() 
            
        source = st.text_input("Coal Source/MINE*", value=default_source).strip().upper()   
        
        c3, c4 = st.columns(2)
        with c3: 
            w_qty = st.number_input("Wagon Qty*", min_value=1, max_value=99, value=default_qty)
        with c4: 
            w_type = st.selectbox("Type", ["N", "R"], index=default_type_idx)
            
        wagon_spec = f"{w_qty}{w_type}"

        st.markdown("**Auto-Calculated Data**")
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
                u_sec = int((dt_end - dt_pla).total_seconds())
                r_sec = int((dt_rel - dt_rec).total_seconds())
                
                u_duration_str = f"{u_sec//3600:02d}:{(u_sec%3600)//60:02d}:{u_sec%60:02d}"
                r_duration_str = f"{r_sec//3600:02d}:{(r_sec%3600)//60:02d}:{r_sec%60:02d}"
                
                r_hours = r_sec / 3600.0
                free_time = 7.0 if w_type == "N" else 2.0
                if r_hours > free_time: 
                    demurrage_val = math.ceil(r_hours - free_time)

        ca1, ca2 = st.columns(2)
        with ca1: 
            st.text_input("U/L Duration", value=u_duration_str, disabled=True)
        with ca2: 
            st.text_input("Demurrage (Hrs)", value=str(demurrage_val), disabled=True)
            
        st.text_input("Release Duration", value=r_duration_str, disabled=True)

    # --- RIGHT COLUMN: Tipplers, Outages, Submit (Executed Third) ---
    with col_right:
        st.markdown("**3. Tipplers & Submission**")
        nm1, nm2 = st.columns(2)
        with nm1: 
            nth = st.text_input("NTH Qty", value=default_nth).strip().upper()
        with nm2: 
            muth = st.text_input("MUTH Qty", value=default_muth).strip().upper()

        tippler_data = {}
        for name in ["WT-1", "WT-2", "WT-3", "WT-4"]:
            def_qty, def_s, def_e = tip_defaults[name]
            qw1, qw2, qw3 = st.columns([1, 1.2, 1.2])
            with qw1: 
                t_qty = st.number_input(name, min_value=0, value=def_qty, key=f"q_{name}")
            with qw2: 
                t_start = st.time_input("Start", value=def_s, key=f"s_{name}", step=60, label_visibility="collapsed")
            with qw3: 
                t_end = st.time_input("End", value=def_e, key=f"e_{name}", step=60, label_visibility="collapsed")
                
            if t_qty > 0:
                time_str = f"{t_start.strftime('%H:%M')}-{t_end.strftime('%H:%M')}" if (t_start and t_end) else ""
                tippler_data[name] = f"{t_qty}\n{time_str}".strip()
            else: 
                tippler_data[name] = ""

        # Outages Expander
        with st.expander("🛠️ Add Department Outages (Optional)"):
            with st.form("outage_form", clear_on_submit=True):
                o1, o2 = st.columns(2)
                with o1: 
                    dept = st.selectbox("Dept", ["MM", "EMD", "C&I", "OPR", "MGR", "CHEM", "OTHER"])
                with o2: 
                    o_reason = st.text_input("Reason")
                    
                o3, o4 = st.columns(2)
                with o3: 
                    o_start = st.time_input("Start", value=None, step=60)
                with o4: 
                    o_end = st.time_input("End", value=None, step=60)
                    
                if st.form_submit_button("➕ Add Outage", use_container_width=True) and o_start:
                    str_s = o_start.strftime('%H:%M')
                    str_e = o_end.strftime('%H:%M') if o_end else "FULL DAY"
                    st.session_state.outages_list.append({"Dept": dept, "Start": str_s, "End": str_e, "Reason": o_reason.strip().upper(), "Log": f"{dept} | {str_s} to {str_e} | {o_reason.strip().upper()}"})

            if st.session_state.outages_list:
                st.dataframe(pd.DataFrame(st.session_state.outages_list)[["Dept", "Start", "End", "Reason"]], use_container_width=True, hide_index=True, height=100)
                if st.button("🗑️ Clear Outages"): 
                    st.session_state.outages_list.clear()
                    st.rerun()

        st.write("") # Spacer before button
        
        # --- SUBMISSION LOGIC ---
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
                return True 
            if dt < cutoff_12_hrs:
                st.error(f"❌ {label} is > 12 hours old! Blocked.")
                return False
            if dt > now_ist:
                st.error(f"❌ {label} is in the future!")
                return False
            return True

        if st.button("🚀 SUBMIT SECURELY", type="primary", use_container_width=True):
            # 1. Basic Validation
            if not rake_no or not source: 
                st.error("❌ RAKE No and Coal Source are MANDATORY.")
                st.stop()
            if not re.match(r"^\d+/\d+$", rake_no): 
                st.error("❌ RAKE No must be XX/XXXX.")
                st.stop()
            if not dt_rec: 
                st.error("❌ ALL 4 Timeline Dates and Times are MANDATORY.")
                st.stop()

            # 2. Sequence Verification
            if entry_mode == "➕ New Entry" and not df_all.empty and 'RAKE No' in df_all.columns:
                existing_rakes = [r.lstrip("'") for r in df_all['RAKE No'].astype(str).str.strip().str.upper().tolist() if r.lower() != 'nan' and r != '']
                if rake_no not in existing_rakes and len(existing_rakes) > 0:
                    last_rake = existing_rakes[-1]
                    if '/' in last_rake and '/' in rake_no:
                        try:
                            prev_a, prev_b = map(int, last_rake.split('/'))
                            curr_a, curr_b = map(int, rake_no.split('/'))
                            if not is_super_admin:
                                is_valid_sequence = (curr_a == prev_a + 1 or curr_a == 1) and (curr_b == prev_b + 1)
                                if not is_valid_sequence:
                                    st.error(f"❌ Sequence Error: Prev RAKE was **{last_rake}**. Next must be **{prev_a+1}/{prev_b+1}**.")
                                    st.stop()
                        except ValueError: 
                            pass

            # 3. Time Validation
            if not (validate_12_hours(dt_rec, "Receipt") and validate_12_hours(dt_pla, "Placement") and 
                    validate_12_hours(dt_end, "U/L End") and validate_12_hours(dt_rel, "Release")): 
                st.stop()

            if not (dt_rec <= dt_pla <= dt_end <= dt_rel): 
                st.error("❌ Timeline error: Receipt -> Placement -> End -> Release.")
                st.stop()

            # 4. Tippler Boundaries
            for name in ["WT-1", "WT-2", "WT-3", "WT-4"]:
                qty = st.session_state.get(f"q_{name}", 0)
                t_s = st.session_state.get(f"s_{name}", None)
                t_e = st.session_state.get(f"e_{name}", None)
                
                if qty > 0:
                    if t_s is None or t_e is None: 
                        st.error(f"⚠️ Start/End times MANDATORY for {name}.")
                        st.stop()
                    
                    dt_tip_start = resolve_tippler_time(t_s, dt_rec, dt_end)
                    if not dt_tip_start: 
                        st.error(f"❌ {name} Start Time invalid!")
                        st.stop()
                    
                    dt_tip_end = resolve_tippler_time(t_e, dt_tip_start, dt_end)
                    if not dt_tip_end: 
                        st.error(f"❌ {name} End Time invalid!")
                        st.stop()

            # 5. Build Payload & Post
            month_tab_name = d_rec.strftime('%b-%y').upper()
            outage_summary = "\n".join([o["Log"] for o in st.session_state.outages_list])
            
            if entry_mode == "✏️ Edit Existing" and not st.session_state.outages_list:
                row = df_all[df_all['RAKE No'].astype(str).str.contains(rake_no, regex=False)].iloc[-1]
                outage_summary = str(row['REMARKS']) if pd.notna(row['REMARKS']) else ""
            
            payload = {
                "tab_name": month_tab_name, "sr_no": sr_no, "rake_no": rake_no, "source": source, "wagon_spec": wagon_spec,
                "receipt": f"{d_rec.strftime('%d.%m.%Y')}/{ti_rec.strftime('%H:%M')}",
                "placement": f"{d_pla.strftime('%d.%m.%Y')}/{ti_pla.strftime('%H:%M')}",
                "u_end": f"{d_end.strftime('%d.%m.%Y')}/{ti_end.strftime('%H:%M')}",
                "release": f"{d_rel.strftime('%d.%m.%Y')}/{ti_rel.strftime('%H:%M')}",
                "u_duration": u_duration_str, "r_duration": r_duration_str, "demurrage": demurrage_val, 
                "remarks": outage_summary, "nth": nth, "muth": muth, 
                "wt1": tippler_data["WT-1"], "wt2": tippler_data["WT-2"], "wt3": tippler_data["WT-3"], "wt4": tippler_data["WT-4"],
                "gcv": 0, "vm": 0
            }
            
            with st.spinner(f"Writing to {month_tab_name}..."):
                try:
                    res = requests.post(APPS_SCRIPT_URL, json=payload)
                    if res.status_code == 200:
                        st.success(f"✅ Rake {rake_no} processed!")
                        st.session_state.outages_list.clear()
                except Exception as e: 
                    st.error(f"Connection failed: {e}")

# ==========================================
# MULTI-SHEET VIEWERS
# ==========================================
with tab2:
    if not df_all.empty:
        mask = df_all.astype(str).apply(lambda x: x.str.contains(today_ist.strftime('%d.%m.%Y'), na=False)).any(axis=1)
        today_data = df_all[mask].tail(10)
        
        if not today_data.empty: 
            st.dataframe(today_data, use_container_width=True, hide_index=True)
        else: 
            st.info("No entries logged today.")
    else: 
        st.info("No Master Data found.")

with tab3:
    selected_export_date = st.date_input("Select Date to Export", value=today_ist, key="export_date")
    
    if st.button("📥 Download Excel Report", type="primary"):
        with st.spinner(f"Building Report..."):
            if not df_all.empty:
                t_str = selected_export_date.strftime('%d.%m.%Y')
                filtered_df = df_all[df_all.astype(str).apply(lambda x: x.str.contains(t_str, na=False)).any(axis=1)]
                
                if filtered_df.empty: 
                    st.warning(f"No records found for {t_str}.")
                else:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        filtered_df.to_excel(writer, index=False, sheet_name='Master Data')
                        for col in writer.sheets['Master Data'].columns:
                            max_length = max([len(str(c.value)) for c in col] + [0])
                            writer.sheets['Master Data'].column_dimensions[col[0].column_letter].width = min(max_length + 2, 45)
                            
                    st.download_button(
                        label=f"💾 Save {t_str} Report", 
                        data=output.getvalue(), 
                        file_name=f"Rake_{selected_export_date.strftime('%Y%m%d')}.xlsx", 
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
