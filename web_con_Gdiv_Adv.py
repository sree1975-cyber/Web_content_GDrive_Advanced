import streamlit as st
import pandas as pd
from utils.ui_components import display_header, login_form, add_link_section, browse_section, download_section, analytics_section
from utils.data_manager import load_data
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Set page config for wide layout
st.set_page_config(page_title="Web Content Manager", layout="wide")

def main():
    # Initialize session state
    if "mode" not in st.session_state:
        st.session_state["mode"] = None
    if "df" not in st.session_state:
        st.session_state["df"] = pd.DataFrame()
    if "public_warning_shown" not in st.session_state:
        st.session_state["public_warning_shown"] = False

    # Load data (for Admin/Guest)
    excel_file = None
    if st.session_state["mode"] in ["admin", "guest"]:
        folder_id = st.secrets.get("GOOGLE_DRIVE_FOLDER_ID", "")
        username = st.session_state.get("username", "")
        excel_file = f"links_{username}.xlsx" if st.session_state["mode"] == "guest" else "links.xlsx"
        try:
            st.session_state["df"] = load_data(excel_file, folder_id)
            logging.debug(f"Loaded data for {st.session_state['mode']}: {len(st.session_state['df'])} rows")
        except Exception as e:
            st.error(f"❌ Failed to load data: {str(e)}")
            logging.error(f"Data load failed: {str(e)}")

    # Render app
    if st.session_state["mode"] is None:
        login_form()
    else:
        display_header(st.session_state["mode"])
        
        # Show public user warning after login (once per session)
        if st.session_state["mode"] == "public" and not st.session_state["public_warning_shown"]:
            st.markdown("""
            <div class="public-warning">
                <h4>📢 Save Your Links!</h4>
                <p>As a Public user, your links are temporary and will be lost when you close the app. Please visit the <strong>Export Data</strong> tab to download your links as an Excel file! 🚀</p>
            </div>
            """, unsafe_allow_html=True)
            logging.debug("Displayed public user warning on main page")
            st.session_state["public_warning_shown"] = True

        # Render tabs
        tabs = ["Add Link", "Browse Links", "Export Data", "Help"]
        if st.session_state["mode"] == "admin":
            tabs.insert(-1, "Analytics")
        
        tab_objects = st.tabs(tabs)
        tab_dict = {tab: tab_obj for tab, tab_obj in zip(tabs, tab_objects)}
        
        with tab_dict["Add Link"]:
            new_df = add_link_section(st.session_state["df"], excel_file, st.session_state["mode"])
            if new_df is not None:
                if st.session_state["mode"] == "public":
                    st.session_state["user_df"] = new_df
                else:
                    st.session_state["df"] = new_df
        
        with tab_dict["Browse Links"]:
            browse_section(st.session_state["df"], excel_file, st.session_state["mode"])
        
        with tab_dict["Export Data"]:
            download_section(st.session_state["df"], excel_file, st.session_state["mode"])
        
        if st.session_state["mode"] == "admin" and "Analytics" in tab_dict:
            with tab_dict["Analytics"]:
                analytics_section(st.session_state["df"])
        
        with tab_dict["Help"]:
            st.markdown("<h3>User Guide</h3>", unsafe_allow_html=True)
            try:
                with open("docs/USER_GUIDE.md", "r") as f:
                    user_guide = f.read()
                st.markdown(user_guide)
            except FileNotFoundError:
                st.error("❌ User Guide not found. Please contact support.")
                logging.error("Failed to load USER_GUIDE.md")

if __name__ == "__main__":
    main()
