import streamlit as st
import pandas as pd
from utils.data_manager import load_data
from utils.ui_components import display_header, login_form, add_link_section, browse_section, download_section, analytics_section
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Set page configuration
st.set_page_config(page_title="Web Content Manager", layout="wide")

# Initialize session state
if "mode" not in st.session_state:
    st.session_state["mode"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None
if "df" not in st.session_state:
    st.session_state["df"] = None
if "user_df" not in st.session_state:
    st.session_state["user_df"] = None

def main():
    # Load secrets
    secrets = st.secrets.get("gdrive", {})
    folder_id = secrets.get("folder_id", "")
    
    # Determine Excel file based on mode and username
    if st.session_state["mode"] == "guest" and st.session_state["username"]:
        excel_file = f"links_{st.session_state['username']}.xlsx"
        logging.debug(f"Guest mode: Using Excel file {excel_file} for user {st.session_state['username']}")
    elif st.session_state["mode"] == "admin":
        excel_file = "links.xlsx"
        logging.debug("Admin mode: Using Excel file links.xlsx")
    else:
        excel_file = None
        logging.debug("Public mode: No Excel file used")
    
    # Load data for admin or guest
    if excel_file and st.session_state["mode"] in ["admin", "guest"]:
        try:
            df = load_data(excel_file, folder_id)
            if df is not None:
                st.session_state["df"] = df
                logging.debug(f"Data loaded successfully for {st.session_state['mode']}: {len(df)} rows")
            else:
                st.session_state["df"] = pd.DataFrame(columns=[
                    "link_id", "url", "title", "description", "tags",
                    "created_at", "updated_at", "priority", "number", "is_duplicate"
                ])
                logging.debug(f"Initialized empty DataFrame for {st.session_state['mode']}")
        except Exception as e:
            st.error(f"❌ Failed to load data: {str(e)}")
            logging.error(f"Failed to load data: {str(e)}")
            st.session_state["df"] = pd.DataFrame(columns=[
                "link_id", "url", "title", "description", "tags",
                "created_at", "updated_at", "priority", "number", "is_duplicate"
            ])
    
    # Display UI based on mode
    if not st.session_state["mode"]:
        login_form()
    else:
        mode = st.session_state["mode"]
        username = st.session_state["username"]
        display_header(mode, username)
        
        if mode in ["admin", "guest"]:
            df = st.session_state.get("df", pd.DataFrame())
            if mode == "admin":
                tab1, tab2, tab3, tab4 = st.tabs(["Add Link", "Browse Links", "Export Data", "Analytics"])
                with tab4:
                    analytics_section(df)
            else:
                tab1, tab2, tab3 = st.tabs(["Add Link", "Browse Links", "Export Data"])
            
            with tab1:
                new_df = add_link_section(df, excel_file, mode)
                if new_df is not None and mode == "guest":
                    st.session_state["df"] = new_df
            with tab2:
                browse_section(df, excel_file, mode)
            with tab3:
                download_section(df, excel_file, mode)
        else:
            tab1, tab2, tab3 = st.tabs(["Add Link", "Browse Links", "Export Data"])
            with tab1:
                user_df = st.session_state.get("user_df", pd.DataFrame())
                new_df = add_link_section(user_df, None, mode)
                if new_df is not None:
                    st.session_state["user_df"] = new_df
            with tab2:
                browse_section(None, None, mode)
            with tab3:
                download_section(None, None, mode)

if __name__ == "__main__":
    main()
