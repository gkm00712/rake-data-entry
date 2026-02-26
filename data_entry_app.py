import streamlit as st
import requests
from datetime import datetime

# Paste the URL you copied from Google Apps Script here:
GOOGLE_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbw486LKteo0S9emoeMhDcQEuQSrekZ-pYXtyZedmas7CIfnscwml-U0_1ogVRc_Zubr/exec"

st.title("📝 Free Google Sheets Data Entry")

with st.form("entry_form", clear_on_submit=True):
    rake_no = st.text_input("RAKE No (e.g. 1/1481)")
    source = st.selectbox("Coal Source", ["SLSP/CCL", "NUGP/CCL", "BNDG/NTPC"])
    demurrage = st.number_input("Demurrage (Hrs)", min_value=0.0)
    remarks = st.text_area("REMARKS")
    
    if st.form_submit_button("Submit Rake Record"):
        # Package the data into a simple dictionary
        new_data = {
            "rake_no": rake_no,
            "source": source,
            "receipt_time": datetime.now().strftime("%d.%m.%Y/%H:%M"),
            "demurrage": demurrage,
            "remarks": remarks
        }
        
        # Send the data to your Google Sheet
        response = requests.post(GOOGLE_WEB_APP_URL, json=new_data)
        
        if response.status_code == 200:
            st.success(f"✅ Successfully saved Rake {rake_no} to Google Sheets!")
        else:
            st.error("Failed to save data.")
