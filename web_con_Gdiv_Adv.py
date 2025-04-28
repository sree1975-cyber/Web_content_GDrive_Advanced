import streamlit as st
import pandas as pd
from utils.ui_components import display_header, login_form, add_link_section, browse_section, download_section, analytics_section
from utils.data_manager import load_data, save_data
import logging
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """Main function to run the Web Content Manager app"""
    # Define required columns
    required_columns = [
        "link_id", "url", "title", "description", "tags",
        "created_at", "updated_at", "priority", "number", "is_duplicate"
    ]
    
    # Initialize session state
    if "mode" not in st.session_state:
        st.session_state["mode"] = None
    if "username" not in st.session_state:
        st.session_state["username"] = None
    if "df" not in st.session_state:
        st.session_state["df"] = pd.DataFrame(columns=required_columns)
    if "user_df" not in st.session_state:
        st.session_state["user_df"] = pd.DataFrame(columns=required_columns)
    
    # Display login form if not logged in
    if st.session_state["mode"] is None:
        login_form()
        return
    
    # Get mode and username
    mode = st.session_state["mode"]
    username = st.session_state.get("username", None)
    if mode == "guest" and not username:
        logging.error("Guest mode but username is None")
        st.error("❌ Username missing for Guest mode. Please log in again.")
        st.session_state["mode"] = None
        st.rerun()
    
    logging.debug(f"Main: mode={mode}, username={username}")
    
    # Display header
    display_header(mode, username)
    
    # Initialize DataFrame and Excel file based on mode
    if mode == "public":
        user_df = st.session_state["user_df"]
        excel_file = None
        logging.debug("Public mode: Using user_df from session state")
    else:
        # Determine Excel file based on mode and username
        excel_file = f"links_{username}.xlsx" if mode == "guest" and username else "links.xlsx"
        folder_id = st.secrets["gdrive"].get("folder_id", "") if "gdrive" in st.secrets else ""
        logging.debug(f"Excel file set to: {excel_file}, folder_id={folder_id}")
        
        # Load data from Google Drive or local
        user_df = load_data(excel_file, folder_id)
        if user_df is None or not isinstance(user_df, pd.DataFrame):
            logging.warning(f"Failed to load {excel_file} or invalid DataFrame. Initializing empty DataFrame.")
            user_df = pd.DataFrame(columns=required_columns)
        st.session_state["df"] = user_df
        logging.debug(f"Loaded {excel_file}: {len(user_df)} rows")
    
    # Log user_df state
    logging.debug(f"main: mode={mode}, user_df type={type(user_df)}, columns={user_df.columns.tolist() if isinstance(user_df, pd.DataFrame) else None}")
    
    # Create tabs for different sections
    tabs = ["Add Link", "Browse Links", "Export Data"]
    if mode == "admin":
        tabs.append("Analytics")
    
    tab_objects = st.tabs(tabs)
    
    with tab_objects[0]:
        new_df = add_link_section(user_df, excel_file, mode)
        if new_df is not None and isinstance(new_df, pd.DataFrame):
            if mode == "public":
                st.session_state["user_df"] = new_df
            else:
                st.session_state["df"] = new_df
    
    with tab_objects[1]:
        browse_section(user_df, excel_file, mode)
    
    with tab_objects[2]:
        download_section(user_df, excel_file, mode)
    
    if mode == "admin" and len(tab_objects) > 3:
        with tab_objects[3]:
            analytics_section(user_df)

if __name__ == "__main__":
    main()
