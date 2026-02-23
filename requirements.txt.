import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. INITIALIZE SQLITE DATABASE ---
# This creates a file called 'railway_database.db' in the same folder if it doesn't exist
def init_db():
    conn = sqlite3.connect('railway_database.db')
    cursor = conn.cursor()
    # Create the table with all necessary columns from your Rake Reports
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rake_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rake_no TEXT,
            coal_source TEXT,
            wagon_type TEXT,
            receipt_time TEXT,
            demurrage_hrs REAL,
            wt1_unloaded INTEGER,
            wt2_unloaded INTEGER,
            wt3_unloaded INTEGER,
            wt4_unloaded INTEGER,
            remarks TEXT,
            operator_id TEXT,
            entry_timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- 2. AUTHENTICATION SYSTEM ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def login():
    st.markdown("### 🔒 Operator Login")
    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        # For production, use secure hashed passwords!
        if user == "admin" and pwd == "password123":
            st.session_state['logged_in'] = True
            st.session_state['user'] = user
            st.rerun()
        else:
            st.error("Invalid credentials")

# --- 3. MAIN APPLICATION UI ---
st.set_page_config(page_title="Rake Data Entry", layout="wide")
st.title("📝 Independent Rake Data Entry")

if not st.session_state['logged_in']:
    login()
else:
    st.sidebar.success(f"Logged in as: {st.session_state['user']}")
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.rerun()
    
    # --- FORM FOR DATA ENTRY ---
    with st.form("entry_form", clear_on_submit=True):
        st.subheader("Rake Details")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            rake_no = st.text_input("RAKE No (e.g. 1/1481)")
            wagon_type = st.selectbox("Wagon Type", ["58N", "59N", "58R", "59R", "BOXN", "BOBR"])
        
        with col2:
            source = st.selectbox("Coal Source", ["SLSP/CCL", "NUGP/CCL", "BNDG/NTPC", "CHRI/CCL", "BCSR/CCL"])
            receipt = st.datetime_input("Receipt Time", datetime.now())
            
        with col3:
            demurrage = st.number_input("Demurrage (Hrs)", min_value=0.0, step=0.5)
        
        st.subheader("Wagon Tipper Unloading Counts")
        wt1, wt2, wt3, wt4 = st.columns(4)
        with wt1: wt1_val = st.number_input("WT-1", min_value=0)
        with wt2: wt2_val = st.number_input("WT-2", min_value=0)
        with wt3: wt3_val = st.number_input("WT-3", min_value=0)
        with wt4: wt4_val = st.number_input("WT-4", min_value=0)
        
        remarks = st.text_area("REMARKS (Delays, Breakdowns, etc.)")
        
        # --- SUBMIT BUTTON & DATABASE SAVE ---
        if st.form_submit_button("Submit Rake Record"):
            if rake_no == "":
                st.error("Please enter a Rake Number before submitting.")
            else:
                # Open connection, insert data, and close connection
                conn = sqlite3.connect('railway_database.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO rake_records 
                    (rake_no, coal_source, wagon_type, receipt_time, demurrage_hrs, 
                    wt1_unloaded, wt2_unloaded, wt3_unloaded, wt4_unloaded, remarks, operator_id, entry_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (rake_no, source, wagon_type, str(receipt), demurrage, 
                      wt1_val, wt2_val, wt3_val, wt4_val, remarks, st.session_state['user'], str(datetime.now())))
                conn.commit()
                conn.close()
                
                st.success(f"✅ Successfully saved Rake {rake_no} to the central database!")

    # --- VIEW RECENT ENTRIES ---
    st.divider()
    st.subheader("Recent Database Entries")
    # Fetch data directly from SQLite to show the operator their recent inputs
    conn = sqlite3.connect('railway_database.db')
    df = pd.read_sql_query("SELECT * FROM rake_records ORDER BY id DESC LIMIT 5", conn)
    conn.close()
    st.dataframe(df, use_container_width=True)
