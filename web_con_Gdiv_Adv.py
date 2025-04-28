import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd
from utils.data_manager import init_data, save_data
from utils.ui_components import display_header, login_form, add_link_section, browse_section, download_section
from utils.link_operations import save_link, delete_selected_links, fetch_metadata, process_bookmark_file
import logging

# Set up logging
logging.basicConfigalho
System: You are Grok 3 built by xAI.





### Addressing the Issues and Implementing Changes

#### 1. Login Page Appearance
- **Issue**: The login page has a plain white background and lacks visual appeal.
- **Change**:
  - Apply a glossy background with a subtle gradient (light blue to white).
  - Add a card-like container with shadows and rounded corners for the login form.
  - Use smooth transitions for buttons and form elements (e.g., hover effects).
  - Maintain a clean, professional look without overwhelming the user.
- **Implementation**:
  - Update the CSS in `web_con_Gdiv_Adv.py` to style the login page.
  - Modify `login_form` in `utils/ui_components.py` to use the new styles.

#### 2. Admin and Guest Page Colors
- **Issue**: Admin and guest pages lack a glossy appearance.
- **Change**:
  - Enhance headers with glossy gradients (admin: blue/purple, guest: green/teal).
  - Apply consistent glossy styling to cards, buttons, and navigation elements.
  - Ensure professionalism with subtle shadows and smooth transitions.
- **Implementation**:
  - Update CSS for `.header-admin`, `.header-guest`, `.card`, and `.stButton` in `web_con_Gdiv_Adv.py`.
  - Ensure consistency across all UI components.

#### 3. Public Mode Missing Features
- **Issue**: Public mode lacks web search and "View All Links as Data Table" functionality.
- **Change**:
  - Restore web search (same as admin/guest) with tag filtering and sorting.
  - Add "View All Links as Data Table" in the browse section, styled to match public mode’s orange theme.
  - Ensure public mode DataFrame (`user_df`) supports all features.
- **Implementation**:
  - Update `browse_section` in `utils/ui_components.py` to include data table view for public mode.
  - Ensure `user_df` initialization in `web_con_Gdiv_Adv.py` includes all columns.

#### 4. Separate Web Content Page with Two Tabs
- **Change**:
  - Split the "Add Link" section into two tabs:
    - **Tab 1: Single URL Fetch and Save**:
      - Retain existing URL input, metadata fetch, and save functionality.
      - Add a `priority` column (Low, Medium, High, Important, already implemented).
      - Keep `number` field for grouping (already implemented).
    - **Tab 2: Browser Favorites Upload with ML**:
      - Allow upload of XLSX, CSV, or HTML files.
      - Use ML to predict tags and metadata.
      - Flag duplicate URLs with warnings and options to handle duplicates.
- **Implementation**:
  - Update `add_link_section` in `utils/ui_components.py` to use `st.tabs` for two tabs.
  - Move single URL form to Tab 1.
  - Move file upload and ML processing to Tab 2, enhancing duplicate handling.

#### 5. Tab 1: Single URL Fetch and Save
- **Change**:
  - Retain existing functionality (URL input, fetch metadata, save with title, description, tags).
  - Ensure `priority` (Low, Medium, High, Important) and `number` fields are included (already implemented).
- **Implementation**:
  - Keep the single URL form in `add_link_section` under Tab 1.
  - Verify metadata fetch auto-fills fields and duplicate detection works.

#### 6. Tab 2: Browser Favorites Upload and Machine Learning
- **Change**:
  - Support XLSX, CSV, HTML uploads (already implemented).
  - ML model to:
    - Predict tags based on URL metadata (title, description).
    - Assign metadata (title, description) if missing.
    - Flag duplicates with a warning and provide options (e.g., skip, overwrite, keep both).
  - Add a progress bar for file processing.
  - Provide feedback (e.g., "Processing complete, X duplicates found").
- **Implementation**:
  - Enhance `process_bookmark_file` in `utils/link_operations.py` to include ML tag prediction and duplicate handling options.
  - Add progress bar and feedback in `add_link_section` (Tab 2).
  - Update `save_data` to handle user choices for duplicates.

#### 7. Web Search Functionality
- **Change**:
  - Maintain existing web search with data table view, sorting (by priority, number), and tag filtering.
  - Ensure consistency across admin, guest, and public modes.
- **Implementation**:
  - Update `browse_section` to ensure data table view is available in all modes.
  - Verify sorting and filtering work with `priority` and `number` columns.

#### 8. Link ID in Excel
- **Issue**: `link_id` (UUID) in Excel export is unnecessary.
- **Change**:
  - Remove `link_id` from Excel export.
  - Add a `sequence_number` column (1, 2, 3, ...) to uniquely identify links.
- **Implementation**:
  - Update `download_section` in `utils/ui_components.py` to exclude `link_id` and include `sequence_number`.

#### 9. Additional Suggestions
- **Optimize ML Model**:
  - Use a lightweight ML model (e.g., KMeans with TF-IDF) for tag prediction.
  - Cache vectorizer and model for faster processing of large files.
- **Progress Bar**:
  - Add a progress bar during file upload processing in Tab 2.
- **Feedback**:
  - Show detailed feedback after upload (e.g., number of links processed, duplicates found).
- **Implementation**:
  - Enhance `process_bookmark_file` to include progress updates.
  - Add feedback messages in `add_link_section` (Tab 2).

---

### Updated Code

Below are the complete updated files, incorporating all fixes, restored functionality, and new features. The code builds on the previous versions, ensuring no regressions.

#### 1. `web_con_Gdiv_Adv.py`
Updated with glossy CSS for login page, admin, and guest pages.

<xaiArtifact artifact_id="e0e07425-0652-43b9-ba07-beb31e3efc1b" artifact_version_id="2aab8fa1-2dba-4f4f-858c-ab3802991607" title="web_con_Gdiv_Adv.py" contentType="text/python">
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
