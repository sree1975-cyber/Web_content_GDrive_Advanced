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
from urllib.parse import urlparse

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
    .header-admin { background-color: #ADD8E6 !important; } /* Light blue for admin */
    .header-guest { background-color: #90EE90 !important; } /* Light parrot green for guest */
    .header-public { background-color: #D8BFD8 !important; } /* Light purple for public */
    .login-container {
        background-color: #FFB6C1 !important; /* Light bluish-pink */
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

def get_domain(url):
    """Extract base domain from URL, normalizing subdomains"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove 'www.' prefix for consistency
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain  # e.g., youtube.com, cnn.com
    except Exception as e:
        logging.error(f"Failed to parse URL {url}: {str(e)}")
        return ""

def display_header(mode, username=None):
    """Display the app header with mode-specific styling and logout button"""
    apply_css()
    header_class = f"header-{mode}"
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
    apply_css()
    st.markdown("""
    <div class="login-container">
        <h2 class="login-title">Welcome to Web Content Manager</h2>
        <p class="login-info">Log in as Admin, Guest, or continue as a Public user.</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form(key="login_form", clear_on_submit=False):
        mode = st.radio("Select Login Type", ["Admin", "Guest", "Public"], index=0)
        
        if mode == "Admin":
            password = st.text_input("Admin Password", type="password", key="admin_password")
        elif mode == "Guest":
            username = st.text_input("Username", key="guest_username")
            password = st.text_input("Guest Password", type="password", key="guest_password")
        else:
            st.info("Click 'Continue as Public User' to access the app without saving to Google Drive.")
        
        submit_button = st.form_submit_button("Login", disabled=(mode == "Public"))
        public_button = st.form_submit_button("👥 Continue as Public User", disabled=(mode != "Public"))
        
        if submit_button:
            if mode == "Admin":
                if password == "admin123":
                    st.session_state["mode"] = "admin"
                    st.success("✅ Logged in as Admin!")
                    st.balloons()
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Incorrect Admin password. Please try again.")
            elif mode == "Guest":
                if password == "guest456" and username:
                    st.session_state["mode"] = "guest"
                    st.session_state["username"] = username
                    st.success(f"✅ Logged in as Guest ({username})!")
                    st.balloons()
                    time.sleep(0.5)
                    st.rerun()
                elif not username:
                    st.error("❌ Username is required for Guest mode.")
                else:
                    st.error("❌ Incorrect Guest password. Please try again.")
        
        if public_button and mode == "Public":
            st.session_state["mode"] = "public"
            st.success("✅ Continuing as Public User!")
            st.balloons()
            time.sleep(0.5)
            st.rerun()

def add_link_section(df, excel_file, mode):
    """Section for adding new links or uploading bookmark files"""
    apply_css()
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
                working_df[col] = [[]] * len(working_df)
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
        
        # Check for related URLs by domain
        prefilled_tags = []
        if url_temp and not working_df.empty and 'url' in working_df.columns:
            domain = get_domain(url_temp)
            if domain:
                # Filter rows with the same domain
                matching_rows = working_df[working_df['url'].apply(get_domain) == domain]
                if not matching_rows.empty:
                    # Sort by updated_at (most recent first) and get tags
                    matching_rows = matching_rows.sort_values(by='updated_at', ascending=False)
                    prefilled_tags = matching_rows.iloc[0]['tags'] if isinstance(matching_rows.iloc[0]['tags'], list) else []
                    if prefilled_tags:
                        st.info(f"✅ Tags pre-filled based on previous domain ({domain}).")
                else:
                    logging.debug(f"No matching rows for domain {domain}")
            else:
                logging.debug(f"Invalid domain for URL {url_temp}")
        
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
                all_tags = sorted({str(tag).strip() for sublist in working_df['tags']
                                 for tag in (sublist if isinstance(sublist, list) else str(sublist).split(',')) 
                                 if str(tag).strip()})
            suggested_tags = st.session_state.get('suggested_tags', []) + \
                           ['News', 'Shopping', 'Research', 'Entertainment', 'Cloud', 'Education', 'Other']
            # Ensure prefilled tags are included in options to avoid ValueError
            all_tags = sorted(list(set(all_tags + [str(tag).strip() for tag in suggested_tags + prefilled_tags if str(tag).strip()])))
            
            selected_tags = st.multiselect(
                "Tags",
                options=all_tags,
                default=prefilled_tags,
                help="Select existing tags or add new ones below.",
                key="existing_tags_input"
            )
            
            new_tag = st.text_input(
                "Add New Tag (optional)",
                placeholder="Type a new tag and press Enter",
                help="Enter a new tag to add to the selected tags",
                key="new_tag_input"
            )
            
            tags = selected_tags + ([new_tag.strip()] if new_tag.strip() else [])
            
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
                            if save_data(new_df, excel_file):
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
                            if save_data(new_df, excel_file):
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
    apply_css()
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
                df[col] = [[]] * len(df)
            elif col == "is_duplicate":
                df[col] = False
            elif col == "link_id":
                df[col] = [str(uuid.uuid4()) for _ in range(len(df))]
            else:
                df[col] = ""
    
    search_query = st.text_input("Search Links", placeholder="Enter keywords or tags...")
    tag_options = sorted(set(','.join([','.join(x) if isinstance(x, list) else str(x) for x in df["tags"].dropna()]).split(','))) if not df.empty and "tags" in df.columns else []
    tag_filter = st.multiselect("Filter by Tags", options=tag_options)
    
    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[
            filtered_df["title"].str.contains(search_query, case=False, na=False) |
            filtered_df["description"].str.contains(search_query, case=False, na=False) |
            filtered_df["url"].str.contains(search_query, case=False, na=False) |
            filtered_df["tags"].apply(lambda x: search_query.lower() in ','.join(x).lower() if isinstance(x, list) else search_query.lower() in str(x).lower())
        ]
    if tag_filter:
        filtered_df = filtered_df[filtered_df["tags"].apply(lambda x: any(tag in (x if isinstance(x, list) else str(x).split(',')) for tag in tag_filter))]
    
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
        
        edited_df = st.data_editor(
            display_df,
            column_config=column_config,
            hide_index=True,
            use_container_width=True,
            disabled=["url", "title", "description", "priority", "number", "is_duplicate"]
        )
        
        if st.button("🗑️ Delete Selected Links", help="Delete selected links"):
            try:
                if "delete" in edited_df.columns:
                    selected_indices = edited_df[edited_df["delete"] == True].index
                    if not selected_indices.empty:
                        selected_link_ids = filtered_df.iloc[selected_indices]["link_id"].tolist()
                        updated_df = delete_selected_links(df, selected_link_ids, excel_file, mode)
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

def download_section(df, excel_file, mode):
    """Section to download links as Excel with hyperlinked URLs"""
    apply_css()
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
        output["tags"] = df_to_export["tags"].apply(lambda x: ','.join(x) if isinstance(x, list) else str(x))
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
    apply_css()
    st.markdown("<h3>Analytics</h3>", unsafe_allow_html=True)
    
    if df.empty:
        st.info("No data available for analytics.")
        return
    
    st.markdown("### Most Frequent URLs")
    url_counts = df["url"].value_counts().head(5)
    st.bar_chart(url_counts)
    
    st.markdown("### Most Common Tags")
    tag_counts = df["tags"].apply(lambda x: ','.join(x) if isinstance(x, list) else str(x)).value_counts()
    st.bar_chart(tag_counts)
    
    st.markdown("### User Activity Trends")
    df["created_at"] = pd.to_datetime(df["created_at"])
    activity = df.groupby(df["created_at"].dt.date).size()
    st.line_chart(activity)
