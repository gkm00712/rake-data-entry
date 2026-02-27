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

# --- SQUEEZE UI ---
st.set_page_config(page_title="Rake Master Entry", layout="wide")
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 0rem; max-width: 98%; }
    div[data-testid="stVerticalBlock"] { gap: 0.2rem; }
    input[disabled] { color: #1f77b4 !important; font-weight: bold; background-color: #f0f2f6; }
    </style>
""", unsafe_allow_html=True)

# --- TIME LOGIC ---
now_ist = datetime.now(IST)
today_ist = now_ist.date()
yesterday_ist = today_ist - timedelta(days=1)
cutoff_12_hrs = now_ist - timedelta(hours=12)

if 'outages_list' not in st.session_state: 
    st.session_state.outages_list = [] 

st.markdown("### 🚂 Rake Master Data Entry (IST)")

tab1, tab2, tab3 = st.tabs(["📝 New Entry Form", "📋 View Yesterday & Today", "📥 Download Reports"])

with tab1:
    st.caption("ℹ️ To EDIT a previous rake, enter the exact RAKE No. (Edits and new entries restricted to past 12 hours).")
    
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
    # 2. TIMELINE (MANDATORY, NO DEFAULTS)
    # ==========================================
    t1, t2, t3, t4 = st.columns(4)
    with t1:
        d_rec = st.date_input("Receipt Date *", value=None, min_value=yesterday_ist, max_value=today_ist)
        ti_rec = st.time_input("Receipt Time *", value=None, step=60)
    with t2:
        d_pla = st.date_input("Placement Date *", value=None, min_value=yesterday_ist, max_value=today_ist)
        ti_pla = st.time_input("Placement Time *", value=None, step=60)
    with t3:
        d_end = st.date_input("U/L End Date *", value=None, min_value=yesterday_ist, max_value=today_ist)
        ti_end = st.time_input("U/L End Time *", value=None, step=60)
    with t4:
        d_rel = st.date_input("Release Date *", value=None, min_value=yesterday_ist, max_value=today_ist)
        ti_rel = st.time_input("Release Time *", value=None, step=60)

    # ==========================================
    # 2.5 AUTO-CALCULATE DURATIONS & DEMURRAGE
    # ==========================================
    u_duration_str = "00:00:00"
    r_duration_str = "00:00:00"
    demurrage_val = 0

    # Only calculate if all timeline fields are filled
    if d_rec and ti_rec and d_pla and ti_pla and d_end and ti_end and d_rel and ti_rel:
        dt_rec = IST.localize(datetime.combine(d_rec, ti_rec))
        dt_pla = IST.localize(datetime.combine(d_pla, ti_pla))
        dt_end = IST.localize(datetime.combine(d_end, ti_end))
        dt_rel = IST.localize(datetime.combine(d_rel, ti_rel))

        # Ensure timeline is chronological before calculating
        if dt_rec <= dt_pla <= dt_end <= dt_rel:
            u_td = dt_end - dt_pla
            r_td = dt_rel - dt_rec
            
            # Format Durations to HH:MM:SS
            u_sec = int(u_td.total_seconds())
            r_sec = int(r_td.total_seconds())
            u_duration_str = f"{u_sec//3600:02d}:{(u_sec%3600)//60:02d}:{u_sec%60:02d}"
            r_duration_str = f"{r_sec//3600:02d}:{(r_sec%3600)//60:02d}:{r_sec%60:02d}"

            # Demurrage Calculation Logic
            r_hours = r_sec / 3600.0
            free_time = 7.0 if w_type == "N" else 2.0
            
            if r_hours > free_time:
                # math.ceil rounds up to the next higher numeral (e.g., 0.25 excess hours -> 1 hour demurrage)
                demurrage_val = math.ceil(r_hours - free_time)

    # Display Calculated Values (Disabled/Read-Only boxes)
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
                t_qty = st.number_input(f"{name} Count", min_value=0, key=f"q_{name}")
                t_start = st.time_input("Start", value=None, key=f"s_{name}", step=60, label_visibility="collapsed")
                t_end = st.time_input("End", value=None, key=f"e_{name}", step=60, label_visibility="collapsed")
                
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
            
            d3, d4, d5 = st.columns([1, 1, 1])
            with d3: o_start = st.time_input("Start", value=None, step=60)
            with d4: o_end = st.time_input("End", value=None, step=60)
            with d5: 
                st.write("")
                if st.form_submit_button("➕ Add"):
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
    def validate_12_hours(dt, label):
        if dt < cutoff_12_hrs:
            st.error(f"❌ {label} ({dt.strftime('%d.%m %H:%M')}) is older than 12 hours! Entry blocked.")
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
        if d_rec is None or ti_rec is None or d_pla is None or ti_pla is None or d_end is None or ti_end is None or d_rel is None or ti_rel is None:
            st.error("❌ ALL 4 Timeline Dates and Times are MANDATORY.")
            st.stop()

        dt_rec = IST.localize(datetime.combine(d_rec, ti_rec))
        dt_pla = IST.localize(datetime.combine(d_pla, ti_pla))
        dt_end = IST.localize(datetime.combine(d_end, ti_end))
        dt_rel = IST.localize(datetime.combine(d_rel, ti_rel))

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
                
                dt_tip_start = IST.localize(datetime.combine(d_pla, t_s))
                if dt_tip_start < dt_pla: dt_tip_start += timedelta(days=1)
                dt_tip_end = IST.localize(datetime.combine(d_pla, t_e))
                if dt_tip_end < dt_tip_start: dt_tip_end += timedelta(days=1)

                if dt_tip_start < dt_pla:
                    st.error(f"❌ {name} Start Time ({t_s.strftime('%H:%M')}) cannot be before Placement Time!")
                    st.stop()
                if dt_tip_end > dt_rel:
                    st.error(f"❌ {name} End Time ({t_e.strftime('%H:%M')}) cannot be after Rake Release Time!")
                    st.stop()

        outage_summary = "\n".join([o["Log"] for o in st.session_state.outages_list])
        
        # Uses the Auto-Calculated Durations
        payload = {
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
        
        with st.spinner("Writing securely..."):
            try:
                res = requests.post(APPS_SCRIPT_URL, json=payload)
                if res.status_code == 200:
                    st.success(f"✅ Rake {rake_no} processed successfully!")
                    st.session_state.outages_list.clear()
            except Exception as e:
                st.error(f"Connection failed: {e}")

# ==========================================
# 5. RECENT ENTRIES VIEWER
# ==========================================
with tab2:
    st.subheader(f"📊 Today's Rake Entries ({today_ist.strftime('%d.%m.%Y')})")
    @st.cache_data(ttl=10) 
    def fetch_today_data():
        try:
            r = requests.get(LIVE_EXCEL_URL)
            df = pd.read_excel(io.BytesIO(r.content), engine='openpyxl').dropna(how='all')
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

# ==========================================
# 6. DOWNLOAD DATE-SPECIFIC EXCEL TAB
# ==========================================
with tab3:
    st.subheader("📥 Export Master Data by Date")
    st.markdown("Select a date below to instantly download that day's records in a formatted Excel file.")
    
    selected_export_date = st.date_input("Select Date", value=today_ist, key="export_date")
    
    if st.button("🔍 Search & Generate Excel File", type="primary"):
        with st.spinner(f"Fetching records for {selected_export_date.strftime('%d.%m.%Y')}..."):
            try:
                r = requests.get(LIVE_EXCEL_URL)
                df = pd.read_excel(io.BytesIO(r.content), engine='openpyxl').dropna(how='all')
                target_str = selected_export_date.strftime('%d.%m.%Y')
                mask = df.astype(str).apply(lambda x: x.str.contains(target_str, na=False)).any(axis=1)
                filtered_df = df[mask]
                
                if filtered_df.empty:
                    st.warning(f"No records found for {target_str}. Please try another date.")
                else:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        filtered_df.to_excel(writer, index=False, sheet_name='Master Data')
                        worksheet = writer.sheets['Master Data']
                        for col in worksheet.columns:
                            max_length = 0
                            column = col[0].column_letter
                            for cell in col:
                                try:
                                    if len(str(cell.value)) > max_length:
                                        max_length = len(str(cell.value))
                                except: pass
                            worksheet.column_dimensions[column].width = min((max_length + 2), 45)

                    excel_data = output.getvalue()
                    
                    st.success(f"✅ Found {len(filtered_df)} records for {target_str}!")
                    st.download_button(
                        label=f"💾 Download {target_str} Excel Report",
                        data=excel_data,
                        file_name=f"Rake_Report_{selected_export_date.strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"Failed to generate report: {e}")
