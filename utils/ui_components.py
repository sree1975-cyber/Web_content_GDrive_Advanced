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

def apply_css():
    """Apply CSS for consistent color scheme across the app"""
    css = """
    <style>
    /* Base styles */
    .header-admin, .header-guest, .header-public {
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .header-admin { background-color: #7a97e8 !important; } /* Light blue for admin */
    .header-guest { background-color: #F0FFFF !important; } /* Light parrot green for guest */
    .header-public { background-color: #CCCCFF !important; } /* Light purple for public */
    .login-container {
        background-color: #DA70D6 !important; /* Orchid */
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

    /* Responsive design */
    @media (max-width: 768px) {
        .stForm, .stDataFrame {
            font-size: 14px;
        }
        .stButton > button {
            width: 100%;
            margin-bottom: 0.5rem;
        }
        .stDataFrame {
            overflow-x: auto;
        }
    }

    /* Debug CSS application */
    .debug-css::after {
        content: "CSS Loaded";
        display: none;
    }
    </style>
    <div class="debug-css"></div>
    """
    st.markdown(css, unsafe_allow_html=True)

def display_header(mode):
    """Display the app header with mode-specific styling and logout button"""
    apply_css()  # Ensure CSS is applied
    header_class = f"header-{mode}"
    username = st.session_state.get("username")
    logging.debug(f"Displaying header: mode={mode}, username={username}")
    st.markdown(f"""
    <div class="{header_class}">
        <h1 style="margin: 0;">Web Content Manager</h1>
        <p style="margin: 0.5rem 0 0;">Organize and manage your web links efficiently</p>
        <p style="margin: 0.5rem 0 0;">{mode.capitalize()} Mode{f" ({username})" if username else ""}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚪 Logout", help="Log out and return to login screen"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("✅ Logged out successfully!")
        st.snow()
        time.sleep(2)
        st.rerun()

def login_form():
    """Display login form for Admin, Guest, or Public access"""
    apply_css()  # Ensure CSS is applied
    st.markdown("""
    <div class="login-container">
        <h2 class="login-title">Welcome to Web Content Manager</h2>
        <p class="login-info">Log in as Admin, Guest, or continue as a Public user.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize login mode in session state
    if "login_mode" not in st.session_state:
        st.session_state["login_mode"] = "Admin"
    
    # Radio button outside form for dynamic updates
    mode = st.radio(
        "Select Login Type",
        ["Admin", "Guest", "Public"],
        index=["Admin", "Guest", "Public"].index(st.session_state["login_mode"]),
        key="login_mode_radio"
    )
    
    # Update session state when mode changes
    if mode != st.session_state["login_mode"]:
        st.session_state["login_mode"] = mode
        # Clear previous form inputs to avoid stale data
        for key in ["admin_password", "guest_username", "guest_password"]:
            if key in st.session_state:
                del st.session_state[key]
        logging.debug(f"Login mode changed to: {mode}")
        st.rerun()
    
    # Render appropriate form or button based on mode
    if mode == "Admin":
        with st.form(key="admin_login_form", clear_on_submit=False):
            password = st.text_input("Admin Password", type="password", key="admin_password")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                if password == "admin123":
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
                if password == "guest456" and username:
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
    
    else:  # Public mode
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
    apply_css()  # Ensure CSS is applied
    st.markdown("<h3>🌐 Add New Link or Upload Bookmarks</h3>", unsafe_allow_html=True)
    
    # Initialize user DataFrame for public mode with all required columns
    required_columns = [
        "link_id", "url", "title", "description", "tags",
        "created_at", "updated_at", "priority", "number", "is_duplicate"
    ]
    if mode == "public" and 'user_df' not in st.session_state:
        st.session_state['user_df'] = pd.DataFrame(columns=required_columns)
    
    # Determine the DataFrame to use
    working_df = st.session_state['user_df'] if mode == "public" else df
    
    # Ensure all required columns exist
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
        
        # Dynamic key for url_input to force reset
        if 'url_input_counter' not in st.session_state:
            st.session_state['url_input_counter'] = 0
        url_input_key = f"url_input_{st.session_state['url_input_counter']}"
        
        # Clear URL field if signaled
        url_value = '' if st.session_state.get('clear_url', False) else st.session_state.get(url_input_key, '')
        
        # Fetch Metadata button
        url_temp = st.text_input(
            "URL*",
            value=url_value,
            placeholder="https://example.com",
            key=url_input_key,
            help="Enter the full URL including https://"
        )
        
        is_url_valid = url_temp.startswith(("http://", "https://")) if url_temp else False
        
        if st.button("Fetch Metadata", disabled=not is_url_valid, key="fetch_metadata"):
            with st.spinner("Fetching..."):
                metadata = fetch_metadata(url_temp)
                st.session_state['auto_title'] = metadata.get("title", "")
                st.session_state['auto_description'] = metadata.get("description", "")
                st.session_state['suggested_tags'] = metadata.get("tags", [])
                st.session_state['clear_url'] = False
                st.info("✅ Metadata fetched! Fields updated.")
        
        # Form for saving link
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
            
            # Get all unique tags from DataFrame with fallback
            all_tags = []
            if 'tags' in working_df.columns:
                all_tags = sorted({str(tag).strip() for tags in working_df['tags']
                                 for tag in (tags.split(',') if isinstance(tags, str) else [str(tags)])
                                 if str(tag).strip()})
            suggested_tags = st.session_state.get('suggested_tags', []) + \
                           ['News', 'Shopping', 'Research', 'Entertainment', 'Cloud', 'Education', 'Other']
            all_tags = sorted(list(set(all_tags + [str(tag).strip() for tag in suggested_tags if str(tag).strip()])))
            
            selected_tags = st.multiselect(
                "Tags",
                options=all_tags,
                default=[],
                help="Select existing tags or add new ones below.",
                key="existing_tags_input"
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
            
            # Ensure submit button is present
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
                                for key in ['auto_title', 'auto_description', 'suggested_tags']:
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
                            for key in ['auto_title', 'auto_description', 'suggested_tags']:
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
    apply_css()  # Ensure CSS is applied
    st.markdown("<h3>Browse Links</h3>", unsafe_allow_html=True)
    
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
    
    search_query = st.text_input("Search Links", placeholder="Enter keywords or tags...")
    tag_options = sorted(set(','.join(df["tags"].dropna()).split(','))) if not df.empty and "tags" in df.columns else []
    tag_filter = st.multiselect("Filter by Tags", options=tag_options)
    
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
    
    priority_order = {"Important": 0, "High": 1, "Medium": 2, "Low": 3}
    if not filtered_df.empty:
        filtered_df["priority_order"] = filtered_df["priority"].map(priority_order)
        filtered_df = filtered_df.sort_values(by=["priority_order", "number"]).drop(columns=["priority_order"])
    
    if not filtered_df.empty:
        st.markdown("<h4>View All Links</h4>", unsafe_allow_html=True)
        display_df = filtered_df[["url", "title", "description", "tags", "priority", "number", "is_duplicate"]].copy()
        display_df["delete"] = False
        
        column_config = {
            "delete": st.column_config.CheckboxColumn("Delete", default=False),
            "url": st.column_config.LinkColumn("URL", display_text="Visit"),
            "title": st.column_config.TextColumn("Title"),
            "description": st.column_config.TextColumn("Description"),
            "tags": st.column_config.TextColumn("Tags"),
            "priority": st.column_config.TextColumn("Priority"),
            "number": st.column_config.NumberColumn("Number"),
            "is_duplicate": st.column_config.CheckboxColumn("Is Duplicate")
        }
        
        try:
            edited_df = st.data_editor(
                display_df,
                column_config=column_config,
                hide_index=True,
                use_container_width=True,
                disabled=["url", "title", "description", "tags", "priority", "number", "is_duplicate"]
            )
        except Exception as e:
            st.error(f"❌ Failed to display data table: {str(e)}")
            logging.error(f"Data editor failed: {str(e)}")
            return
        
        if st.button("🗑️ Delete Selected Links", help="Delete selected links"):
            try:
                if "delete" in edited_df.columns:
                    selected_indices = edited_df[edited_df["delete"] == True].index
                    if not selected_indices.empty:
                        selected_link_ids = filtered_df.iloc[selected_indices]["link_id"].tolist()
                        folder_id = st.secrets.get("GOOGLE_DRIVE_FOLDER_ID", "") if mode in ["admin", "guest"] else ""
                        updated_df = delete_selected_links(df, selected_link_ids, excel_file, mode, folder_id)
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
                else:
                    st.error("❌ Deletion column not found.")
            except Exception as e:
                st.error(f"❌ Failed to delete links: {str(e)}")
                logging.error(f"Delete links failed: {str(e)}")
    
    if filtered_df.empty:
        st.info("No links match the search criteria.")

def delete_selected_links(df, selected_ids, excel_file, mode, folder_id):
    """Delete selected links from the DataFrame"""
    try:
        updated_df = df[~df["link_id"].isin(selected_ids)].reset_index(drop=True)
        if mode in ["admin", "guest"] and excel_file:
            from utils.data_manager import save_data
            save_data(updated_df, excel_file, folder_id)
        return updated_df
    except Exception as e:
        st.error(f"Error deleting links: {str(e)}")
        logging.error(f"Delete links failed: {str(e)}")
        return df

def download_section(df, excel_file, mode):
    """Section to download links as Excel with hyperlinked URLs"""
    apply_css()  # Ensure CSS is applied
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
    apply_css()  # Ensure CSS is applied
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
