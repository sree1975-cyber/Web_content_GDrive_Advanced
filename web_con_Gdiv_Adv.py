import streamlit as st

# Streamlit page configuration must be the first command
st.set_page_config(page_title="Web Content Manager", layout="wide")

import pandas as pd
from utils.data_manager import load_data
from utils.ui_components import display_header, login_form, add_link_section, browse_section, download_section, analytics_section
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Initialize session state
if "mode" not in st.session_state:
    st.session_state["mode"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None
if "df" not in st.session_state:
    st.session_state["df"] = pd.DataFrame()
if "user_df" not in st.session_state:
    st.session_state["user_df"] = pd.DataFrame()
if "activity_log" not in st.session_state:
    st.session_state["activity_log"] = []

def main():
    """Main application logic"""
    mode = st.session_state.get("mode")
    username = st.session_state.get("username")
    logging.debug(f"Main: mode={mode}, username={username}")
    
    if not mode:
        login_form()
        return
    
    display_header(mode)
    
    # Set Excel file based on mode and username
    if mode == "admin":
        excel_file = "links.xlsx"
    elif mode == "guest":
        excel_file = f"links_{username}.xlsx" if username else "links.xlsx"
    else:
        excel_file = None
    logging.debug(f"Selected excel_file: {excel_file}, mode={mode}, username={username}")
    
    # Load data
    if mode in ["admin", "guest"]:
        try:
            folder_id = st.secrets.get("GOOGLE_DRIVE_FOLDER_ID", "")
            st.session_state["df"] = load_data(excel_file, folder_id)
            logging.debug(f"Loaded data for {excel_file}: {len(st.session_state['df'])} rows")
        except Exception as e:
            st.error(f"Failed to load data: {str(e)}")
            logging.error(f"Data load failed for {excel_file}: {str(e)}")
    
    # Create tabs
    tabs = ["Add Link", "Browse Links", "Export Data"]
    if mode == "admin":
        tabs.append("Analytics")
    
    tab_objects = st.tabs(tabs)
    
    with tab_objects[0]:
        new_df = add_link_section(st.session_state.get("df" if mode != "public" else "user_df"), excel_file, mode)
        if new_df is not None:
            if mode == "public":
                st.session_state["user_df"] = new_df
            else:
                st.session_state["df"] = new_df
            st.session_state["activity_log"].append({
                "action": "add_link",
                "timestamp": datetime.now(),
                "mode": mode,
                "username": username
            })
    
    with tab_objects[1]:
        browse_section(st.session_state.get("df" if mode != "public" else "user_df"), excel_file, mode)
    
    with tab_objects[2]:
        download_section(st.session_state.get("df" if mode != "public" else "user_df"), excel_file, mode)
    
    if mode == "admin" and len(tabs) > 3:
        with tab_objects[3]:
            analytics_section(st.session_state.get("df"))

    with st.expander("ℹ️ About Web Content Manager", expanded=False):
        st.markdown("""
        <div style="padding: 1rem;">
            <h3>Your Personal Web Library</h3>
            <p>Web Content Manager helps you save and organize web links with:</p>
            <ul>
                <li>📌 One-click saving of important web resources</li>
                <li>🏷️ <strong>Smart tagging</strong> - Automatically suggests tags from page metadata</li>
                <li>🔍 <strong>Powerful search</strong> - Full-text search across all fields with tag filtering</li>
                <li>🗑️ <strong>Delete functionality</strong> - Remove unwanted links</li>
                <li>📊 <strong>Data Table View</strong> - See all links in a sortable, filterable table</li>
                <li>📥 <strong>Export capability</strong> - Download your collection in Excel or CSV format</li>
                <li>💾 <strong>Persistent storage</strong> - Your data is saved automatically and persists between sessions</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
