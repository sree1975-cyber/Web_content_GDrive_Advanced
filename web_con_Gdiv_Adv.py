import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
from utils.data_manager import init_data, save_data
from utils.ui_components import display_header, login_form, add_link_section, browse_section, download_section
from utils.link_operations import save_link, delete_selected_links, fetch_metadata, process_bookmark_file
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Set page configuration (must be the first Streamlit command)
st.set_page_config(
    page_title="Web Content Manager",
    page_icon="🔖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Check Streamlit version (optional warning, does not block execution)
if st.__version__ != "1.31.0":
    logging.warning(f"Streamlit version {st.__version__} detected. The app was tested with 1.31.0, but should work with {st.__version__}.")

# Custom CSS with glossy, professional styling
st.markdown("""
<style>
    body {
        background: linear-gradient(135deg, #e6f0fa, #ffffff);
    }
    .header-admin {
        background: linear-gradient(135deg, #6e8efb, #a777e3);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    .header-guest {
        background: linear-gradient(135deg, #10b981, #34d399);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    .header-public {
        background: linear-gradient(135deg, #f97316, #fb923c);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    .card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease-in-out;
    }
    .card:hover {
        transform: translateY(-2px);
    }
    .dataframe {
        width: 100%;
    }
    .tag {
        display: inline-block;
        background: #e0e7ff;
        color: #4f46e5;
        padding: 0.2rem 0.5rem;
        border-radius: 1rem;
        font-size: 0.8rem;
        margin-right: 0.5rem;
        margin-bottom: 0.3rem;
    }
    .priority-high { color: #dc2626; font-weight: bold; }
    .priority-medium { color: #f59e0b; font-weight: bold; }
    .priority-low { color: #10b981; font-weight: bold; }
    .priority-important { color: #facc15; font-size: 1.2rem; }
    .delete-btn {
        background: linear-gradient(135deg, #ff4b4b, #dc2626) !important;
        color: white !important;
        margin-top: 0.5rem;
        border: none;
        transition: background 0.3s ease;
    }
    .delete-btn:hover {
        background: linear-gradient(135deg, #dc2626, #ff4b4b) !important;
    }
    .mode-indicator-admin {
        background: #e0e7ff;
        color: #4f46e5;
        padding: 0.5rem;
        border-radius: 5px;
        margin-bottom: 1rem;
        font-weight: bold;
        text-align: center;
    }
    .mode-indicator-guest {
        background: #d1fae5;
        color: #065f46;
        padding: 0.5rem;
        border-radius: 5px;
        margin-bottom: 1rem;
        font-weight: bold;
        text-align: center;
    }
    .mode-indicator-public {
        background: #ffedd5;
        color: #7c2d12;
        padding: 0.5rem;
        border-radius: 5px;
        margin-bottom: 1rem;
        font-weight: bold;
        text-align: center;
    }
    .exit-btn {
        background: linear-gradient(135deg, #ff4b4b, #dc2626) !important;
        color: white !important;
        width: 100%;
        margin-top: 1rem;
        border: none;
        transition: background 0.3s ease;
    }
    .exit-btn:hover {
        background: linear-gradient(135deg, #dc2626, #ff4b4b) !important;
    }
    .login-btn {
        background: linear-gradient(135deg, #6e8efb, #a777e3) !important;
        color: white !important;
        width: 100%;
        margin-top: 1rem;
        border: none;
        transition: background 0.3s ease;
    }
    .login-btn:hover {
        background: linear-gradient(135deg, #5a7de3, #9060d6) !important;
    }
    .public-btn {
        background: linear-gradient(135deg, #f97316, #fb923c) !important;
        color: white !important;
        width: 100%;
        margin-top: 1rem;
        border: none;
        transition: background 0.3s ease;
    }
    .public-btn:hover {
        background: linear-gradient(135deg, #ea580c, #f97316) !important;
    }
    .login-container {
        background: linear-gradient(135deg, #ffffff, #f0f7ff);
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        max-width: 500px;
        margin: 2rem auto;
        transition: transform 0.2s ease-in-out;
    }
    .login-container:hover {
        transform: translateY(-2px);
    }
    .login-title {
        text-align: center;
        color: #4f46e5;
        margin-bottom: 1rem;
        font-size: 1.8rem;
    }
    .login-info {
        text-align: center;
        color: #666;
        margin-bottom: 1.5rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        font-weight: bold;
    }
    .scroll-message {
        background: linear-gradient(135deg, #f97316, #fb923c);
        color: white;
        padding: 0.5rem;
        border-radius: 5px;
        margin-bottom: 1rem;
        font-weight: bold;
        text-align: center;
        animation: scroll 20s linear infinite;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    @keyframes scroll {
        0% { transform: translateX(100%); }
        100% { transform: translateX(-100%); }
    }
    .scroll-message:hover {
        animation-play-state: paused;
    }
    .dismiss-btn {
        background: none;
        border: none;
        color: white;
        font-size: 1rem;
        cursor: pointer;
        margin-left: 1rem;
    }
    .duplicate-warning {
        color: #dc2626;
        font-weight: bold;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main function to run the Web Content Manager app"""
    # Check if logged in
    if 'mode' not in st.session_state:
        login_form()
        return
    
    mode = st.session_state['mode']
    username = st.session_state.get('username')
    
    # Scroll message for public users
    if mode == "public" and 'dismiss_scroll_message' not in st.session_state:
        st.session_state['dismiss_scroll_message'] = False
    if mode == "public" and not st.session_state['dismiss_scroll_message']:
        st.markdown("""
        <div class='scroll-message'>
            <span>Please download the Excel file before closing the app after saving all your URLs.</span>
            <button class='dismiss-btn' onclick='this.parentElement.style.display=\"none\"'>✖</button>
        </div>
        """, unsafe_allow_html=True)
    
    # Sidebar with Exit button and navigation
    with st.sidebar:
        st.markdown(f"""
        <div class='mode-indicator-{mode}'>
            {mode.capitalize()} Mode{f" ({username})" if username else ""}
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚪 Exit and Clear Cache", key="exit_button", help="Clear all session data and reset the app"):
            logging.debug(f"Exit button clicked. Session state before clear: {st.session_state}")
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state['password_input_counter'] = 0
            st.session_state['username_input_counter'] = 0
            st.success("✅ Session cleared! App will reset.")
            st.balloons()
            st.rerun()
        
        st.markdown("""
        <div style="padding: 1rem;">
            <h2 style="margin-bottom: 1.5rem;">Navigation</h2>
        </div>
        """, unsafe_allow_html=True)
        
        selected = option_menu(
            menu_title=None,
            options=["Add Link", "Browse Links", "Export Data"],
            icons=['plus-circle', 'book', 'download'],
            default_index=0,
            styles={
                "container": {"padding": "0!important"},
                "icon": {"color": "#6e8efb" if mode == "admin" else "#10b981" if mode == "guest" else "#f97316", "font-size": "1rem"}, 
                "nav-link": {"font-size": "1rem", "text-align": "left", "margin": "0.5rem 0", "padding": "0.5rem 1rem"},
                "nav-link-selected": {"background-color": "#6e8efb" if mode == "admin" else "#10b981" if mode == "guest" else "#f97316", "font-weight": "normal"},
            }
        )
    
    # Initialize data based on mode
    if mode in ["admin", "guest"]:
        if 'df' not in st.session_state or st.session_state.get('username') != username:
            df, excel_file = init_data(mode, username)
            st.session_state['df'] = df
            st.session_state['excel_file'] = excel_file
            st.session_state['username'] = username
        else:
            df = st.session_state['df']
            excel_file = st.session_state['excel_file']
    else:
        df, excel_file = pd.DataFrame(), None
        if 'user_df' not in st.session_state:
            st.session_state['user_df'] = pd.DataFrame(columns=[
                'link_id', 'url', 'title', 'description', 'tags', 
                'created_at', 'updated_at', 'priority', 'number', 'is_duplicate'
            ])
            # Ensure tags is a string, not a list
            st.session_state['user_df']['tags'] = st.session_state['user_df']['tags'].apply(lambda x: '' if pd.isna(x) else str(x))
    
    # Ensure all required columns exist
    required_columns = ['link_id', 'url', 'title', 'description', 'tags', 'created_at', 'updated_at', 'priority', 'number', 'is_duplicate']
    for col in required_columns:
        if col not in df.columns:
            if col == 'tags':
                df[col] = ''
            elif col == 'is_duplicate':
                df[col] = False
            else:
                df[col] = ''
    
    # Display header with mode-specific styling
    display_header(mode, username)
    
    # About section
    with st.expander("ℹ️ About Web Content Manager", expanded=False):
        st.markdown("""
        <div style="padding: 1rem;">
            <h3>Your Personal Web Library</h3>
            <p>Web Content Manager helps you save and organize web links with:</p>
            <ul>
                <li>📌 One-click saving of important web resources</li>
                <li>🏷️ <strong>Smart tagging</strong> - Automatically suggests tags</li>
                <li>🔍 <strong>Powerful search</strong> - Full-text search with tag filtering</li>
                <li>🗑️ <strong>Delete functionality</strong> - Remove unwanted links</li>
                <li>⭐ <strong>Priority marking</strong> - Mark links as Low, Medium, High, or Important</li>
                <li>🔢 <strong>Numbering</strong> - Assign numbers to group related links</li>
                <li>📤 <strong>Bookmark import</strong> - Upload and categorize browser bookmarks</li>
                <li>📊 <strong>Data Table View</strong> - View links in a table</li>
                <li>📥 <strong>Export capability</strong> - Download as Excel with duplicate detection</li>
                <li>💾 <strong>Storage</strong> - Admin/guest data persists in Google Drive; public data is temporary</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Render selected section
    if selected == "Add Link":
        updated_df = add_link_section(df, excel_file, mode)
        if mode == "public":
            st.session_state['user_df'] = updated_df
        else:
            st.session_state['df'] = updated_df
    elif selected == "Browse Links":
        browse_section(df, excel_file, mode)
    elif selected == "Export Data":
        download_section(df, excel_file, mode)

if __name__ == "__main__":
    main()
