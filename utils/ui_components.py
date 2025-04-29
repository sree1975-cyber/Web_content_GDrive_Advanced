import streamlit as st
import pandas as pd
from datetime import datetime
from utils.data_manager import save_data
from utils.link_operations import save_link, delete_selected_links, fetch_metadata, process_bookmark_file
import logging
from io import BytesIO
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
import time
import uuid

# Log Streamlit version for debugging
logging.debug(f"Streamlit version: {st.__version__}")

def apply_css(is_mobile=False):
    """Apply CSS for consistent color scheme, with distinct mobile/desktop layouts"""
    css = """
    <style>
    /* Base styles */
    .header-admin, .header-guest, .header-public {
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .header-admin { background-color: #7a97e8 !important; }
    .header-guest { background-color: #F0FFFF !important; }
    .header-public { background-color: #CCCCFF !important; }
    .login-container {
        background-color: #DA70D6 !important;
        padding: 2rem;
        border-radius: 8px;
        text-align: center;
    }
    .button-tooltip {
        position: relative;
    }
    .button-tooltip:hover::after {
        content: attr(data-tooltip);
        position: absolute;
        background-color: #333;
        color: white;
        padding: 0.5rem;
        border-radius: 4px;
        z-index: 10;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        white-space: nowrap;
    }
    /* Search bar alignment */
    .search-container {
        display: flex;
        gap: 1rem;
        margin-bottom: 1rem;
    }
    /* Public warning box */
    .public-warning {
        background-color: #FFF3CD;
        border: 2px solid #FFC107;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        text-align: center;
        animation: fadeIn 1s ease-in;
    }
    @keyframes fadeIn {
        0% { opacity: 0; }
        100% { opacity: 1; }
    }
    /* Toggle icon styling */
    .layout-toggle {
        font-size: 1.5rem;
        cursor: pointer;
        padding: 0.5rem;
        border-radius: 50%;
        transition: background-color 0.3s;
    }
    .layout-toggle:hover {
        background-color: #e0e0e0;
    }
    .layout-toggle.active {
        background-color: #7a97e8;
        color: white;
    }
    /* Desktop styles */
    .app-container {
        max-width: 90vw;
        margin: 0 auto;
    }
    .stForm, .stDataFrame {
        font-size: 16px;
    }
    .stButton > button {
        margin-bottom: 0.5rem;
    }
    .stDataFrame {
        width: 100%;
    }
    .search-container {
        flex-direction: row;
        gap: 1rem;
    }
    .stTextInput, .stMultiSelect, .stSelectbox {
        width: auto;
    }
    """
    if is_mobile:
        css += """
        /* Mobile styles */
        .app-container {
            max-width: 360px;
            margin: 0 auto;
            padding: 0 0.5rem;
        }
        .stForm, .stDataFrame {
            font-size: 14px;
        }
        .stButton > button {
            width: 100%;
            margin-bottom: 0.5rem;
        }
        .stDataFrame {
            overflow-x: auto;
            width: 100%;
        }
        .search-container {
            flex-direction: column;
            gap: 0.5rem;
        }
        .stTextInput, .stMultiSelect, .stSelectbox {
            width: 100% !important;
        }
        """
    css += """
    /* Debug CSS */
    .debug-css::after {
        content: "CSS Loaded";
        display: none;
    }
    </style>
    <div class="debug-css"></div>
    """
    st.markdown(css, unsafe_allow_html=True)

def display_header(mode):
    """Display the app header with mode-specific styling, logout button, and layout toggle"""
    if 'layout_mode' not in st.session_state:
        st.session_state['layout_mode'] = 'desktop'
    
    apply_css(is_mobile=st.session_state['layout_mode'] == 'mobile')
    
    header_class = f"header-{mode}"
    username = st.session_state.get("username")
    logging.debug(f"Displaying header: mode={mode}, username={username}, layout={st.session_state['layout_mode']}")
    st.markdown(f"""
    <div class="{header_class}">
        <h1 style="margin: 0;">Web Content Manager</h1>
        <p style="margin: 0.5rem 0 0;">Organize and manage your web links efficiently</p>
        <p style="margin: 0.5rem 0 0;">{mode.capitalize()} Mode{f" ({username})" if username else ""}</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🚪 Logout", help="Log out and return to login screen"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("✅ Logged out successfully!")
            st.snow()
            time.sleep(2)
            st.rerun()
    with col2:
        # Icon-based layout toggle
        current_mode = st.session_state['layout_mode']
        icon = "📱" if current_mode == 'desktop' else "📺"
        tooltip = "Switch to Mobile View" if current_mode == 'desktop' else "Switch to Desktop View"
        st.markdown(f"""
        <div class="button-tooltip" data-tooltip="{tooltip}">
            <span class="layout-toggle{' active' if current_mode == ('mobile' if icon == '📱' else 'desktop') else ''}"
                  onclick="streamlitWrite('toggle_layout', '{ 'mobile' if current_mode == 'desktop' else 'desktop' }')">
                {icon}
            </span>
        </div>
        <script>
        function streamlitWrite(key, value) {{
            const event = new CustomEvent('streamlit:setComponentValue', {{detail: {{key: key, value: value}}}});
            window.parent.document.dispatchEvent(event);
        }}
        </script>
        """, unsafe_allow_html=True)
        if st.session_state.get('toggle_layout'):
            st.session_state['layout_mode'] = st.session_state['toggle_layout']
            del st.session_state['toggle_layout']
            logging.debug(f"Layout toggled to: {st.session_state['layout_mode']}")
            st.rerun()

def login_form():
    """Display login form for Admin, Guest, or Public access"""
    apply_css()  # Default to desktop
    st.markdown("""
    <div class="login-container">
        <h2 class="login-title">Welcome to Web Content Manager</h2>
        <p class="login-info">Log in as Admin, Guest, or continue as a Public user.</p>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        logging.debug("Attempting to render About Web Content Manager expander")
        with st.expander("About Web Content Manager", expanded=False):
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
        logging.debug("Expander rendered successfully")
    except Exception as e:
        st.error("❌ Failed to render About expander. Please try again or contact support.")
        logging.error(f"Expander failed: {str(e)}")
    
    if "login_mode" not in st.session_state:
        st.session_state["login_mode"] = "Admin"
    
    mode = st.radio(
        "Select Login Type",
        ["Admin", "Guest", "Public"],
        index=["Admin", "Guest", "Public"].index(st.session_state["login_mode"]),
        key="login_mode_radio"
    )
    
    if mode != st.session_state["login_mode"]:
        st.session_state["login_mode"] = mode
        for key in ["admin_password", "guest_username", "guest_password"]:
            if key in st.session_state:
                del st.session_state[key]
        logging.debug(f"Login mode changed to: {mode}")
        st.rerun()
    
    if mode == "Admin":
        with st.form(key="admin_login_form", clear_on_submit=False):
            password = st.text_input("Admin Password", type="password", key="admin_password")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                if password == "admin@123":
                    st.session_state["mode"] = "admin"
                    st.session_state["username"] = None
                    logging.debug("Admin login successful")
                    st.success("✅ Logged in as Admin!")
                    st.balloons()
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Incorrect Admin password. Please try again.")
    
    elif mode == "Guest":
        with st.form(key="guest_login_form", clear_on_submit=False):
            username = st.text_input("Username", key="guest_username")
            password = st.text_input("Guest Password", type="password", key="guest_password")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                if password == "guest@456" and username:
                    st.session_state["mode"] = "guest"
                    st.session_state["username"] = username
                    logging.debug(f"Guest login: username={username}, session_state_username={st.session_state['username']}")
                    st.success(f"✅ Logged in as Guest ({username})!")
                    st.balloons()
                    time.sleep(0.5)
                    st.rerun()
                elif not username:
                    st.error("❌ Username is required for Guest mode.")
                else:
                    st.error("❌ Incorrect Guest password. Please try again.")
    
    else:
        if st.button("👥 Continue as Public User"):
            st.session_state["mode"] = "public"
            st.session_state["username"] = None
            logging.debug("Public login successful")
            st.success("✅ Continuing as Public User!")
            st.balloons()
            time.sleep(0.5)
            st.rerun()

def add_link_section(df, excel_file, mode):
    """Section for adding new links or uploading bookmark files"""
    apply_css(is_mobile=st.session_state.get('layout_mode', 'desktop') == 'mobile')
    st.markdown("<h3>🌐 Add New Link or Upload Bookmarks</h3>", unsafe_allow_html=True)
    
    required_columns = [
        "link_id", "url", "title", "description", "tags",
        "created_at", "updated_at", "priority", "number", "is_duplicate"
    ]
    if mode == "public" and 'user_df' not in st.session_state:
        st.session_state['user_df'] = pd.DataFrame(columns=required_columns)
    
    working_df = st.session_state['user_df'] if mode == "public" else df
    
    for col in required_columns:
        if col not in working_df.columns:
            if col == "tags":
                working_df[col] = ""
            elif col == "is_duplicate":
                working_df[col] = False
            elif col == "link_id":
                working_df[col] = [str(uuid.uuid4()) for _ in range(len(working_df))]
            else:
                working_df[col] = ""
    
    tab1, tab2 = st.tabs(["Single URL", "Upload Bookmarks"])
    
    with tab1:
        st.markdown("<h4>Add Single URL</h4>", unsafe_allow_html=True)
        
        if 'url_input_counter' not in st.session_state:
            st.session_state['url_input_counter'] = 0
        url_input_key = f"url_input_{st.session_state['url_input_counter']}"
        
        url_value = '' if st.session_state.get('clear_url', False) else st.session_state.get(url_input_key, '')
        
        url_temp = st.text_input(
            "URL*",
            value=url_value,
            placeholder="https://example.com",
            key=url_input_key,
            help="Enter the full URL including https://"
        )
        
        is_url_valid = url_temp.startswith(("http://", "https://")) if url_temp else False
        
        if st.button("Fetch Metadata", disabled=not is_url_valid, key="fetch_metadata"):
            with st.spinner("Fetching metadata..."):
                try:
                    metadata = fetch_metadata(url_temp)
                    st.session_state['auto_title'] = metadata.get("title", "")
                    st.session_state['auto_description'] = metadata.get("description", "")
                    st.session_state['suggested_tags'] = metadata.get("tags", [])
                    logging.debug(f"Fetched metadata for {url_temp}: title={st.session_state['auto_title']}, description={st.session_state['auto_description']}, tags={st.session_state['suggested_tags']}")
                    st.session_state['clear_url'] = False
                    st.session_state['metadata_fetched'] = True
                    st.info("✅ Metadata fetched! Fields updated.")
                    if not st.session_state['suggested_tags']:
                        st.warning("⚠️ No tags found in page metadata. Please select existing tags or add new ones.")
                except Exception as e:
                    st.error(f"❌ Failed to fetch metadata: {str(e)}")
                    logging.error(f"Metadata fetch failed for {url_temp}: {str(e)}")
                    st.session_state['suggested_tags'] = []
                    st.session_state['metadata_fetched'] = True
                st.rerun()
        
        # Debug Tools Expander
        with st.expander("Debug Tools", expanded=False):
            st.markdown("### Debug Information")
            if st.button("Show Session State Keys", help="Display non-sensitive session state keys"):
                protected_keys = ['mode', 'username', 'df', 'user_df', 'public_warning_shown', 'layout_mode']
                safe_keys = [k for k in st.session_state.keys() if k not in protected_keys]
                st.write(f"Session state keys: {safe_keys}")
                logging.debug(f"Displayed session state keys: {safe_keys}")
            
            if st.button("Show Tag Info", help="Display suggested tags and metadata"):
                st.write(f"Suggested tags: {st.session_state.get('suggested_tags', [])}")
                st.write(f"Auto title: {st.session_state.get('auto_title', '')}")
                st.write(f"Auto description: {st.session_state.get('auto_description', '')}")
                logging.debug(f"Tag info: suggested_tags={st.session_state.get('suggested_tags', [])}, title={st.session_state.get('auto_title', '')}")
            
            if st.button("Clear Non-Critical Session State", help="Reset non-critical session state for testing"):
                protected_keys = ['mode', 'username', 'df', 'user_df', 'public_warning_shown', 'layout_mode']
                keys_to_delete = [k for k in st.session_state.keys() if k not in protected_keys]
                for key in keys_to_delete:
                    del st.session_state[key]
                logging.debug(f"Cleared session state keys: {keys_to_delete}")
                st.success("✅ Non-critical session state cleared")
                st.rerun()
        
        with st.form("single_url_form", clear_on_submit=True):
            url = st.text_input(
                "URL (Confirm)*",
                value=st.session_state.get(url_input_key, ''),
                key="url_form_input",
                help="Confirm the URL to save"
            )
            
            title = st.text_input(
                "Title*",
                value=st.session_state.get('auto_title', ''),
                help="Give your link a descriptive title",
                key="title_input"
            )
            
            description = st.text_area(
                "Description",
                value=st.session_state.get('auto_description', ''),
                height=100,
                help="Add notes about why this link is important",
                key="description_input"
            )
            
            all_tags = []
            if 'tags' in working_df.columns:
                all_tags = sorted({str(tag).strip() for tags in working_df['tags']
                                 for tag in (tags.split(',') if isinstance(tags, str) else [str(tags)])
                                 if str(tag).strip()})
            default_tags = ['News', 'Shopping', 'Research', 'Entertainment', 'Cloud', 'Education', 'Other']
            suggested_tags = st.session_state.get('suggested_tags', [])
            all_tags = sorted(list(set(all_tags + default_tags + [str(tag).strip() for tag in suggested_tags if str(tag).strip()])))
            
            logging.debug(f"Rendering multiselect: suggested_tags={suggested_tags}, all_tags={all_tags}")
            
            selected_tags = st.multiselect(
                "Tags",
                options=all_tags,
                default=suggested_tags if suggested_tags else [],
                help="Select existing tags or add new ones below.",
                key=f"existing_tags_input_{st.session_state.get('url_input_counter', 0)}"
            )
            
            new_tag = st.text_input(
                "Add New Tag (optional)",
                placeholder="Type a new tag and press Enter",
                help="Enter a new tag to add to the selected tags",
                key="new_tag_input"
            )
            
            tags = ','.join(selected_tags + ([new_tag.strip()] if new_tag.strip() else []))
            
            priority = st.selectbox(
                "Priority",
                ["Low", "Medium", "High", "Important"],
                index=0,
                key="priority_input"
            )
            
            number = st.number_input(
                "Number (for grouping)",
                min_value=0,
                value=0,
                step=1,
                key="number_input"
            )
            
            submitted = st.form_submit_button("💾 Save Link", help="Save the link to your collection")
            
            if submitted:
                logging.debug(f"Form submitted: URL={url}, Title={title}, Description={description}, Tags={tags}, Priority={priority}, Number={number}, Mode={mode}")
                if not url:
                    st.error("❌ Please enter a URL")
                elif not title:
                    st.error("❌ Please enter a title")
                else:
                    new_df = save_link(working_df, url, title, description, tags, priority, number, mode)
                    if new_df is not None:
                        if mode in ["admin", "guest"] and excel_file:
                            folder_id = st.secrets.get("GOOGLE_DRIVE_FOLDER_ID", "")
                            if save_data(new_df, excel_file, folder_id):
                                st.session_state['df'] = new_df
                                st.success("✅ Link saved successfully!")
                                if new_df.iloc[-1]["is_duplicate"]:
                                    st.warning("⚠️ This URL is a duplicate.")
                                st.balloons()
                                time.sleep(0.5)
                                st.session_state['clear_url'] = True
                                st.session_state['url_input_counter'] += 1
                                for key in ['auto_title', 'auto_description', 'suggested_tags', 'metadata_fetched']:
                                    st.session_state.pop(key, None)
                                st.rerun()
                            else:
                                st.error("❌ Failed to save link to Google Drive")
                        else:
                            st.session_state['user_df'] = new_df
                            st.success("✅ Link saved successfully! Download your links as they are temporary.")
                            if new_df.iloc[-1]["is_duplicate"]:
                                st.warning("⚠️ This URL is a duplicate.")
                            st.balloons()
                            time.sleep(0.5)
                            st.session_state['clear_url'] = True
                            st.session_state['url_input_counter'] += 1
                            for key in ['auto_title', 'auto_description', 'suggested_tags', 'metadata_fetched']:
                                st.session_state.pop(key, None)
                            st.rerun()
                    else:
                        st.error("❌ Failed to process link")

    with tab2:
        st.markdown("<h4>Upload Browser Bookmarks</h4>", unsafe_allow_html=True)
        with st.form(key="upload_bookmarks_form", clear_on_submit=True):
            uploaded_file = st.file_uploader(
                "Upload Bookmarks (Excel, CSV, HTML)",
                type=["xlsx", "csv", "html"],
                key="bookmark_uploader"
            )
            duplicate_action = st.selectbox(
                "Handle Duplicates",
                ["Keep Both", "Skip Duplicates"],
                index=0,
                key="duplicate_action"
            )
            
            submitted = st.form_submit_button("Import Bookmarks", help="Import bookmarks from file")
            
            if submitted:
                if uploaded_file:
                    try:
                        progress_bar = st.progress(0)
                        new_df = process_bookmark_file(working_df, uploaded_file, mode, duplicate_action, progress_bar)
                        if mode in ["admin", "guest"] and excel_file:
                            folder_id = st.secrets.get("GOOGLE_DRIVE_FOLDER_ID", "")
                            if save_data(new_df, excel_file, folder_id):
                                st.session_state['df'] = new_df
                                st.success(f"✅ Bookmarks imported! {len(new_df) - len(working_df)} new links added.")
                                if new_df["is_duplicate"].any():
                                    st.warning("⚠️ Some URLs are duplicates.")
                                st.balloons()
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("❌ Failed to save bookmarks to Google Drive")
                        else:
                            st.session_state['user_df'] = new_df
                            st.success(f"✅ Bookmarks imported! {len(new_df) - len(working_df)} new links added.")
                            if new_df["is_duplicate"].any():
                                st.warning("⚠️ Some URLs are duplicates.")
                            st.balloons()
                            time.sleep(0.5)
                            st.rerun()
                        return new_df
                    except Exception as e:
                        st.error(f"❌ Failed to process bookmark file: {str(e)}")
                        logging.error(f"Bookmark upload failed: {str(e)}")
                    finally:
                        progress_bar.empty()
                else:
                    st.error("❌ Please upload a bookmark file")
    
    return working_df

def browse_section(df, excel_file, mode):
    """Section to browse, search, and delete links"""
    apply_css(is_mobile=st.session_state.get('layout_mode', 'desktop') == 'mobile')
    st.markdown("<h3>📚 Browse Saved Links</h3>", unsafe_allow_html=True)
    
    if mode == "public":
        df = st.session_state.get("user_df", pd.DataFrame(columns=[
            "link_id", "url", "title", "description", "tags", 
            "created_at", "updated_at", "priority", "number", "is_duplicate"
        ]))
    
    required_columns = ["link_id", "url", "title", "description", "tags", "created_at", "updated_at", "priority", "number", "is_duplicate"]
    for col in required_columns:
        if col not in df.columns:
            if col == "tags":
                df[col] = ""
            elif col == "is_duplicate":
                df[col] = False
            elif col == "link_id":
                df[col] = [str(uuid.uuid4()) for _ in range(len(df))]
            else:
                df[col] = ""
    
    # Normalize column types
    df["tags"] = df["tags"].apply(lambda x: str(x) if pd.notnull(x) else "")
    df["is_duplicate"] = df["is_duplicate"].astype(bool)
    
    # Debug DataFrame shape
    st.write(f"Debug: DataFrame shape before filtering: {df.shape}")
    
    # Search and filter inputs in a single row
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        search_query = st.text_input("Search Links", placeholder="Enter keywords or tags...", key="search_query")
    with col2:
        tag_options = sorted(set(','.join(df["tags"].dropna()).split(','))) if not df.empty and "tags" in df.columns else []
        tag_filter = st.multiselect("Filter by Tags", options=tag_options, key="tag_filter")
    with col3:
        priority_filter = st.selectbox("Filter by Priority", ["All", "Low", "Medium", "High", "Important"], key="priority_filter")
    
    # Web search button
    if st.button("🔍 Search Web", help="Search the web with the query and tags"):
        if search_query or tag_filter:
            query = search_query + " " + " ".join(tag_filter) if search_query else " ".join(tag_filter)
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            st.markdown(f"""
            <script>
            window.open("{search_url}", "_blank");
            </script>
            """, unsafe_allow_html=True)
            logging.debug(f"Web search triggered: URL={search_url}")
        else:
            st.warning("⚠️ Please enter a search query or select tags.")
    
    # Filter DataFrame
    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[
            filtered_df["title"].str.contains(search_query, case=False, na=False) |
            filtered_df["description"].str.contains(search_query, case=False, na=False) |
            filtered_df["url"].str.contains(search_query, case=False, na=False) |
            filtered_df["tags"].str.contains(search_query, case=False, na=False)
        ]
    if tag_filter:
        filtered_df = filtered_df[filtered_df["tags"].str.contains('|'.join(tag_filter), case=False, na=False)]
    if priority_filter != "All":
        filtered_df = filtered_df[filtered_df["priority"] == priority_filter]
    
    # Sort by priority and number
    priority_order = {"Important": 0, "High": 1, "Medium": 2, "Low": 3}
    if not filtered_df.empty:
        filtered_df["priority_order"] = filtered_df["priority"].map(priority_order)
        filtered_df = filtered_df.sort_values(by=["priority_order", "number"]).drop(columns=["priority_order"])
    
    if not filtered_df.empty:
        st.markdown("<h4>View All Links</h4>", unsafe_allow_html=True)
        display_df = filtered_df[["url", "title", "description", "tags", "priority", "number", "is_duplicate"]].copy()
        display_df["delete"] = False
        
        # Adjust column widths based on layout mode
        is_mobile = st.session_state.get('layout_mode', 'desktop') == 'mobile'
        column_config = {
            "delete": st.column_config.CheckboxColumn("Delete", default=False, width=50),
            "url": st.column_config.LinkColumn("URL", display_text="Visit", width=100 if is_mobile else 200),
            "title": st.column_config.TextColumn("Title", width=100 if is_mobile else 200),
            "description": st.column_config.TextColumn("Description", width=150 if is_mobile else 300),
            "tags": st.column_config.TextColumn("Tags", width=80 if is_mobile else 150),
            "priority": st.column_config.TextColumn("Priority", width=60 if is_mobile else 100),
            "number": st.column_config.NumberColumn("Number", width=50 if is_mobile else 80),
            "is_duplicate": st.column_config.CheckboxColumn("Is Duplicate", width=80 if is_mobile else 100)
        }
        
        try:
            edited_df = st.data_editor(
                display_df,
                column_config=column_config,
                hide_index=True,
                use_container_width=True,
                disabled=["url", "title", "description", "tags", "priority", "number", "is_duplicate"]
            )
            logging.debug(f"Data editor rendered, delete column exists: {'delete' in edited_df.columns}")
        except Exception as e:
            st.error(f"❌ Failed to display data table: {str(e)}")
            logging.error(f"Data editor failed: {str(e)}")
            return
        
        # Debug button to show link_ids
        if st.button("Show Link IDs (Debug)", help="Display link_ids for selected rows"):
            selected_indices = edited_df[edited_df["delete"] == True].index
            if not selected_indices.empty:
                selected_link_ids = filtered_df.iloc[selected_indices]["link_id"].tolist()
                st.write(f"Selected link_ids: {selected_link_ids}")
            else:
                st.write("No rows selected")
        
        # Show delete button only if at least one checkbox is checked
        if "delete" in edited_df.columns and edited_df["delete"].any():
            logging.debug(f"Delete button visible: {edited_df['delete'].sum()} rows selected")
            if st.button("🗑️ Delete Selected Links", help="Delete selected links"):
                try:
                    selected_indices = edited_df[edited_df["delete"] == True].index
                    if not selected_indices.empty:
                        selected_link_ids = filtered_df.iloc[selected_indices]["link_id"].tolist()
                        logging.debug(f"Selected link_ids: {selected_link_ids}")
                        folder_id = st.secrets.get("GOOGLE_DRIVE_FOLDER_ID", "") if mode in ["admin", "guest"] else ""
                        updated_df = delete_selected_links(df, selected_link_ids, excel_file, mode, folder_id)
                        logging.debug(f"Post-deletion DataFrame shape: {updated_df.shape}")
                        if mode == "public":
                            st.session_state["user_df"] = updated_df
                        else:
                            st.session_state["df"] = updated_df
                        st.success("✅ Selected links deleted successfully!")
                        st.snow()
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("❌ Please select at least one link to delete.")
                except Exception as e:
                    st.error(f"❌ Failed to delete links: {str(e)}")
                    logging.error(f"Delete links failed: {str(e)}")
        else:
            logging.debug("Delete button hidden: no rows selected for deletion")
    
    if filtered_df.empty:
        st.info("No links match the search criteria.")

def delete_selected_links(df, selected_ids, excel_file, mode, folder_id):
    """Delete selected links from the DataFrame"""
    try:
        logging.debug(f"Before deletion: DataFrame shape={df.shape}, selected_ids={selected_ids}")
        updated_df = df[~df["link_id"].isin(selected_ids)].reset_index(drop=True)
        logging.debug(f"After deletion: DataFrame shape={updated_df.shape}")
        if mode in ["admin", "guest"] and excel_file:
            from utils.data_manager import save_data
            if not save_data(updated_df, excel_file, folder_id):
                st.error("❌ Failed to save updated data to Google Drive")
                logging.error("Failed to save updated data to Google Drive")
                return df
        return updated_df
    except Exception as e:
        st.error(f"❌ Error deleting links: {str(e)}")
        logging.error(f"Delete links failed: {str(e)}")
        return df

def download_section(df, excel_file, mode):
    """Section to download links as Excel with hyperlinked URLs"""
    apply_css(is_mobile=st.session_state.get('layout_mode', 'desktop') == 'mobile')
    st.markdown("<h3>Export Data</h3>", unsafe_allow_html=True)
    
    if mode == "public":
        df_to_export = st.session_state.get("user_df", pd.DataFrame())
    else:
        df_to_export = df
    
    if not df_to_export.empty:
        output = pd.DataFrame()
        output["sequence_number"] = range(1, len(df_to_export) + 1)
        output["link_id"] = df_to_export["link_id"]
        output["url"] = df_to_export["url"]
        output["title"] = df_to_export["title"]
        output["description"] = df_to_export["description"]
        output["tags"] = df_to_export["tags"]
        output["priority"] = df_to_export["priority"]
        output["number"] = df_to_export["number"]
        output["created_at"] = df_to_export["created_at"]
        output["updated_at"] = df_to_export["updated_at"]
        output["is_duplicate"] = df_to_export["is_duplicate"]
        
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            output.to_excel(writer, index=False, sheet_name="Links")
            workbook = writer.book
            worksheet = writer.sheets["Links"]
            
            for idx, url in enumerate(output["url"], start=2):
                worksheet[f"C{idx}"].hyperlink = url
                worksheet[f"C{idx}"].style = "Hyperlink"
            
        buffer.seek(0)
        
        st.download_button(
            label="Download Links as Excel",
            data=buffer.getvalue(),
            file_name="links.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Download links as an Excel file with clickable URLs"
        )
    else:
        st.info("No links available to export.")

def analytics_section(df):
    """Admin-only analytics tab"""
    apply_css(is_mobile=st.session_state.get('layout_mode', 'desktop') == 'mobile')
    st.markdown("<h3>Analytics</h3>", unsafe_allow_html=True)
    
    if df.empty:
        st.info("No data available for analytics.")
        return
    
    st.markdown("### Most Frequent URLs")
    url_counts = df["url"].value_counts().head(5)
    st.bar_chart(url_counts)
    
    st.markdown("### Most Common Tags")
    tag_counts = df["tags"].str.split(',', expand=True).stack().value_counts()
    st.bar_chart(tag_counts)
    
    st.markdown("### User Activity Trends")
    df["created_at"] = pd.to_datetime(df["created_at"])
    activity = df.groupby(df["created_at"].dt.date).size()
    st.line_chart(activity)
