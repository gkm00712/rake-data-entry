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

# --- PROFESSIONAL UI & SQUEEZE CSS ---
st.set_page_config(page_title="Rake Data Entry System", layout="wide")
st.markdown("""
    <style>
    /* 1. Squeeze Main Container to prevent scrolling */
    .block-container { padding-top: 0.5rem; padding-bottom: 0rem; max-width: 98%; }
    
    /* 2. Global Professional Font */
    * { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important; }
    
    /* 3. Remove Gaps Between Elements */
    div[data-testid="stVerticalBlock"] { gap: 0rem !important; }
    div[data-testid="stHorizontalBlock"] { gap: 0.5rem !important; }
    
    /* 4. Elegant Heading Colors (Navy Blue) */
    h3 { color: #003366 !important; font-weight: 700 !important; margin-top: -0.5rem !important; padding-bottom: 0rem !important; }
    p, label { font-size: 0.85rem !important; color: #333333 !important; font-weight: 600 !important; margin-bottom: 0.1rem !important; }
    
    /* 5. Compact Input Fields */
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stDateInput>div>div>input, .stTimeInput>div>div>input, .stSelectbox>div>div>div {
        height: 1.8rem !important;
        min-height: 1.8rem !important;
        font-size: 0.85rem !important;
        border-color: #A0AAB2 !important;
    }
    
    /* 6. Highlight Auto-Calculated/Disabled Fields */
    input[disabled] { color: #003366 !important; font-weight: bold !important; background-color: #E8EEF5 !important; border: 1px solid #003366 !important; }
    
    /* 7. Squeeze Dividers */
    hr { margin-top: 0.4rem !important; margin-bottom: 0.4rem !important; border-color: #D1D5DB !important; }
    
    /* 8. Professional Primary Button */
    button[kind="primary"] {
        background-color: #003366 !important;
        color: white !important;
        border-radius: 4px !important;
        padding: 0.2rem 1rem !important;
        font-weight: 700 !important;
        border: none !important;
        transition: 0.3s;
    }
    button[kind="primary"]:hover { background-color: #002244 !important; }
    
    /* 9. Compact Form Box */
    [data-testid="stForm"] { border: 1px solid #E5E7EB !important; padding: 0.5rem !important; background-color: #F9FAFB !important; }
    </style>
""", unsafe_allow_html=True)

# --- TIME LOGIC ---
now_ist = datetime.now(IST)
today_ist = now_ist.date()
yesterday_ist = today_ist - timedelta(days=1)
cutoff_12_hrs = now_ist - timedelta(hours=12)

if 'outages_list' not in st.session_state: st.session_state.outages_list = [] 

st.markdown("### 🚂 Rake Data Entry System")

tab1, tab2, tab3 = st.tabs(["📝 Data Entry", "📋 View Recent", "📥 Export Reports"])

with tab1:
    # ==========================================
    # 1. BASIC DETAILS (Squeezed 6 Columns)
    # ==========================================
    c1, c2, c3, c4, c5 = st.columns([0.8, 1.5, 1.5, 0.8, 0.8])
    with c1: sr_no = st.number_input("Sr.No", min_value=1, step=1)
    with c2: rake_no = st.text_input("RAKE No (XX/XXXX) *").strip().upper() 
    with c3: source = st.text_input("Coal Source/MINE *").strip().upper()   
    with c4: w_qty = st.number_input("Wagon Qty *", min_value=1, max_value=99, value=58)
    with c5: w_type = st.selectbox("Type", ["N", "R"])
    wagon_spec = f"{w_qty}{w_type}"

    st.divider()

    # ==========================================
    # 2. TIMELINE & AUTO-CALCULATIONS (Squeezed Grid)
    # ==========================================
    col_time, col_calc = st.columns([2.5, 1.5])
    
    with col_time:
        t1, t2, t3, t4 = st.columns(4)
        with t1:
            d_rec = st.date_input("Receipt Date*", value=None, min_value=yesterday_ist, max_value=today_ist)
            ti_rec = st.time_input("Receipt Time*", value=None, step=60)
        with t2:
            d_pla = st.date_input("Placement Date*", value=None, min_value=yesterday_ist, max_value=today_ist)
            ti_pla = st.time_input("Placement Time*", value=None, step=60)
        with t3:
            d_end = st.date_input("U/L End Date*", value=None, min_value=yesterday_ist, max_value=today_ist)
            ti_end = st.time_input("U/L End Time*", value=None, step=60)
        with t4:
            d_rel = st.date_input("Release Date*", value=None, min_value=yesterday_ist, max_value=today_ist)
            ti_rel = st.time_input("Release Time*", value=None, step=60)

    # --- AUTO-CALCULATION ENGINE ---
    u_duration_str, r_duration_str, demurrage_val = "00:00:00", "00:00:00", 0
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
            if r_hours > free_time: demurrage_val = math.ceil(r_hours - free_time)

    with col_calc:
        st.write(" ") # Alignment buffer
        cd1, cd2, cd3 = st.columns(3)
        with cd1: st.text_input("U/L Dur.", value=u_duration_str, disabled=True)
        with cd2: st.text_input("Rel. Dur.", value=r_duration_str, disabled=True)
        with cd3: st.text_input("Dem. (Hrs)", value=str(demurrage_val), disabled=True)

    st.divider()

    # ==========================================
    # 3. TIPPLERS & OUTAGES (Side-by-side)
    # ==========================================
    col_tip, col_out = st.columns([1.5, 1])

    with col_tip:
        nm1, nm2, _ = st.columns([1, 1, 2])
        with nm1: nth = st.text_input("NTH Qty").strip().upper()
        with nm2: muth = st.text_input("MUTH Qty").strip().upper()

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
                else: tippler_data[name] = ""

    with col_out:
        with st.form("outage_form", clear_on_submit=True):
            d1, d2 = st.columns([1, 1.5])
            with d1: dept = st.selectbox("Dept", ["MM", "EMD", "C&I", "OPR", "MGR", "CHEM", "OTHER"])
            with d2: o_reason = st.text_input("Reason")
            
            d3, d4, d5 = st.columns([1, 1, 0.8])
            with d3: o_start = st.time_input("Start", value=None, step=60, label_visibility="collapsed")
            with d4: o_end = st.time_input("End", value=None, step=60, label_visibility="collapsed")
            with d5: 
                if st.form_submit_button("➕ Add"):
                    if o_start:
                        str_s = o_start.strftime('%H:%M')
                        str_e = o_end.strftime('%H:%M') if o_end else "FULL DAY"
                        st.session_state.outages_list.append({"Dept": dept, "Start": str_s, "End": str_e, "Reason": o_reason.strip().upper(), "Log": f"{dept} | {str_s} to {str_e} | {o_reason.strip().upper()}"})

        if st.session_state.outages_list:
            try:
                st.dataframe(pd.DataFrame(st.session_state.outages_list)[["Dept", "Start", "End", "Reason"]], use_container_width=True, hide_index=True, height=100)
            except KeyError: st.session_state.outages_list.clear()

    st.divider()

    # ==========================================
    # 4. VALIDATION & SUBMISSION
    # ==========================================
    def validate_12_hours(dt, label):
        if dt < cutoff_12_hrs: st.error(f"❌ {label} is older than 12 hours! Blocked."); return False
        if dt > now_ist: st.error(f"❌ {label} cannot be in the future!"); return False
        return True

    if st.button("🚀 Securely Submit Rake Data", type="primary", use_container_width=True):
        if not rake_no or not source: st.error("❌ RAKE No and Coal Source are MANDATORY."); st.stop()
        if not re.match(r"^\d+/\d+$", rake_no): st.error("❌ RAKE No must be XX/XXXX."); st.stop()
        if not (d_rec and ti_rec and d_pla and ti_pla and d_end and ti_end and d_rel and ti_rel):
            st.error("❌ ALL 4 Timeline Dates and Times are MANDATORY."); st.stop()

        if not (validate_12_hours(dt_rec, "Receipt Time") and validate_12_hours(dt_pla, "Placement Time") and 
                validate_12_hours(dt_end, "Unloading End Time") and validate_12_hours(dt_rel, "Release Time")): st.stop()

        if not (dt_rec <= dt_pla <= dt_end <= dt_rel): st.error("❌ Timeline error: Must be Receipt -> Placement -> End -> Release."); st.stop()

        for name in ["WT-1", "WT-2", "WT-3", "WT-4"]:
            qty, t_s, t_e = st.session_state.get(f"q_{name}", 0), st.session_state.get(f"s_{name}", None), st.session_state.get(f"e_{name}", None)
            if qty > 0:
                if t_s is None or t_e is None: st.error(f"⚠️ Start/End times MANDATORY for {name}."); st.stop()
                dt_tip_start = IST.localize(datetime.combine(d_pla, t_s))
                if dt_tip_start < dt_pla: dt_tip_start += timedelta(days=1)
                dt_tip_end = IST.localize(datetime.combine(d_pla, t_e))
                if dt_tip_end < dt_tip_start: dt_tip_end += timedelta(days=1)

                if dt_tip_start < dt_pla: st.error(f"❌ {name} Start Time cannot be before Placement!"); st.stop()
                if dt_tip_end > dt_rel: st.error(f"❌ {name} End Time cannot be after Release!"); st.stop()

        outage_summary = "\n".join([o["Log"] for o in st.session_state.outages_list])
        payload = {
            "sr_no": sr_no, "rake_no": rake_no, "source": source, "wagon_spec": wagon_spec,
            "receipt": f"{d_rec.strftime('%d.%m.%Y')}/{ti_rec.strftime('%H:%M')}",
            "placement": f"{d_pla.strftime('%d.%m.%Y')}/{ti_pla.strftime('%H:%M')}",
            "u_end": f"{d_end.strftime('%d.%m.%Y')}/{ti_end.strftime('%H:%M')}",
            "release": f"{d_rel.strftime('%d.%m.%Y')}/{ti_rel.strftime('%H:%M')}",
            "u_duration": u_duration_str, "r_duration": r_duration_str, "demurrage": demurrage_val, 
            "remarks": outage_summary, "nth": nth, "muth": muth, 
            "wt1": tippler_data["WT-1"], "wt2": tippler_data["WT-2"], 
            "wt3": tippler_data["WT-3"], "wt4": tippler_data["WT-4"],
            "gcv": 0, "vm": 0
        }
        
        with st.spinner("Writing securely..."):
            try:
                res = requests.post(APPS_SCRIPT_URL, json=payload)
                if res.status_code == 200: st.success(f"✅ Rake {rake_no} processed successfully!"); st.session_state.outages_list.clear()
            except Exception as e: st.error(f"Connection failed: {e}")

# ==========================================
# 5. RECENT VIEWER & DOWNLOADER TABS
# ==========================================
with tab2:
    @st.cache_data(ttl=10) 
    def fetch_today_data():
        try:
            r = requests.get(LIVE_EXCEL_URL)
            df = pd.read_excel(io.BytesIO(r.content), engine='openpyxl').dropna(how='all')
            mask = df.astype(str).apply(lambda x: x.str.contains(today_ist.strftime('%d.%m.%Y'), na=False)).any(axis=1)
            return df[mask].tail(10)
        except: return pd.DataFrame()
    td_data = fetch_today_data()
    if not td_data.empty: st.dataframe(td_data, use_container_width=True, hide_index=True)
    else: st.info("No entries logged for today yet.")

with tab3:
    col_d1, col_d2 = st.columns([1, 3])
    with col_d1: selected_export_date = st.date_input("Select Target Date", value=today_ist)
    with col_d2:
        st.write(" ")
        if st.button("🔍 Generate Excel Report", type="primary"):
            with st.spinner("Building Report..."):
                try:
                    r = requests.get(LIVE_EXCEL_URL)
                    df = pd.read_excel(io.BytesIO(r.content), engine='openpyxl').dropna(how='all')
                    t_str = selected_export_date.strftime('%d.%m.%Y')
                    filtered_df = df[df.astype(str).apply(lambda x: x.str.contains(t_str, na=False)).any(axis=1)]
                    if filtered_df.empty: st.warning(f"No records found for {t_str}.")
                    else:
                        out = io.BytesIO()
                        with pd.ExcelWriter(out, engine='openpyxl') as w:
                            filtered_df.to_excel(w, index=False, sheet_name='Master Data')
                            for col in w.sheets['Master Data'].columns:
                                max_len = max([len(str(c.value)) for c in col] + [0])
                                w.sheets['Master Data'].column_dimensions[col[0].column_letter].width = min(max_len + 2, 45)
                        st.download_button(f"💾 Download {t_str} Report", data=out.getvalue(), file_name=f"Rake_{selected_export_date.strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                except Exception as e: st.error(f"Failed: {e}")
