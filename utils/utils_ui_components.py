import streamlit as st
import pandas as pd
from datetime import datetime
from utils.data_manager import save_data
from utils.link_operations import save_link, delete_selected_links, fetch_metadata, process_bookmark_file
import logging
from io import BytesIO

def display_header(mode, username=None):
    """Display the app header with mode-specific styling"""
    header_class = f"header-{mode}"
    st.markdown(f"""
    <div class='{header_class}'>
        <h1 style='margin: 0;'>Web Content Manager</h1>
        <p style='margin: 0.5rem 0 0;'>Organize and manage your web links efficiently</p>
        <p style='margin: 0.5rem 0 0;'>{mode.capitalize()} Mode{f' ({username})' if username else ''}</p>
    </div>
    """, unsafe_allow_html=True)

def login_form():
    """Display login form for Admin, Guest, or Public access"""
    st.markdown("""
    <div class='login-container'>
        <h2 class='login-title'>Welcome to Web Content Manager</h2>
        <p class='login-info'>Log in as Admin, Guest, or continue as a Public user.</p>
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
        public_button = st.form_submit_button("Continue as Public User", disabled=(mode != "Public"))
        
        if submit_button:
            if mode == "Admin":
                if password == "admin123":
                    st.session_state['mode'] = "admin"
                    st.success("✅ Logged in as Admin!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Incorrect Admin password. Please try again.")
            elif mode == "Guest":
                if password == "guest456" and username:
                    st.session_state['mode'] = "guest"
                    st.session_state['username'] = username
                    st.success(f"✅ Logged in as Guest ({username})!")
                    st.balloons()
                    st.rerun()
                elif not username:
                    st.error("❌ Username is required for Guest mode.")
                else:
                    st.error("❌ Incorrect Guest password. Please try again.")
        
        if public_button and mode == "Public":
            st.session_state['mode'] = "public"
            st.success("✅ Continuing as Public User!")
            st.balloons()
            st.rerun()

def add_link_section(df, excel_file, mode):
    """Section to add new links or upload bookmark files, split into two tabs"""
    st.markdown("<h3>Add New Link or Upload Bookmarks</h3>", unsafe_allow_html=True)
    
    # Initialize form state
    if 'fetched_metadata' not in st.session_state:
        st.session_state['fetched_metadata'] = {}
    
    # Create two tabs
    tab1, tab2 = st.tabs(["Single URL", "Upload Bookmarks"])
    
    # Tab 1: Single URL Fetch and Save
    with tab1:
        with st.form(key="single_url_form"):
            st.markdown("<h4>Add Single URL</h4>", unsafe_allow_html=True)
            
            url = st.text_input("URL", placeholder="https://example.com", key="url_input")
            
            title = st.text_input(
                "Title (optional)",
                value=st.session_state['fetched_metadata'].get('title', ''),
                key="title_input"
            )
            description = st.text_area(
                "Description (optional)",
                value=st.session_state['fetched_metadata'].get('description', ''),
                key="description_input"
            )
            tags = st.text_input(
                "Tags (comma-separated, optional)",
                value=st.session_state['fetched_metadata'].get('tags', ''),
                key="tags_input"
            )
            priority = st.selectbox("Priority", ["Low", "Medium", "High", "Important"], index=0)
            number = st.number_input("Number (for grouping related links)", min_value=0, value=0, step=1)
            
            col1, col2 = st.columns([1, 1])
            with col1:
                fetch_button = st.form_submit_button("Fetch Metadata")
            with col2:
                save_button = st.form_submit_button("Save Link")
            
            if fetch_button and url:
                try:
                    metadata = fetch_metadata(url)
                    st.session_state['fetched_metadata'] = {
                        'title': metadata.get('title', ''),
                        'description': metadata.get('description', ''),
                        'tags': ", ".join(metadata.get('tags', []))
                    }
                    st.success("✅ Metadata fetched! Fields updated.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to fetch metadata: {str(e)}")
            
            if save_button:
                if url:
                    tags_list = [tag.strip() for tag in tags.split(",")] if tags else []
                    new_df = save_link(df, url, title, description, tags_list, priority, number, mode)
                    if mode in ["admin", "guest"] and excel_file:
                        if save_data(new_df, excel_file):
                            st.success("✅ Link saved successfully!")
                            if new_df.iloc[-1]['is_duplicate']:
                                st.warning("⚠️ This URL is a duplicate. Review in the exported Excel file.")
                            st.balloons()
                            st.session_state['fetched_metadata'] = {}
                        else:
                            st.error("❌ Failed to save link to Google Drive.")
                    else:
                        st.success("✅ Link saved successfully!")
                        if new_df.iloc[-1]['is_duplicate']:
                            st.warning("⚠️ This URL is a duplicate. Review in the exported Excel file.")
                        st.balloons()
                        st.session_state['fetched_metadata'] = {}
                    return new_df
                else:
                    st.error("❌ Please provide a URL.")
    
    # Tab 2: Upload Browser Bookmarks
    with tab2:
        with st.form(key="upload_bookmarks_form"):
            st.markdown("<h4>Upload Browser Bookmarks</h4>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader("Upload Bookmarks (Excel, CSV, HTML)", type=["xlsx", "csv", "html"])
            duplicate_action = st.selectbox("Handle Duplicates", ["Keep Both", "Skip Duplicates"], index=0)
            
            if st.form_submit_button("Import Bookmarks"):
                if uploaded_file:
                    try:
                        progress_bar = st.progress(0)
                        new_df = process_bookmark_file(df, uploaded_file, mode, duplicate_action, progress_bar)
                        if mode in ["admin", "guest"] and excel_file:
                            if save_data(new_df, excel_file):
                                st.success(f"✅ Bookmarks imported successfully! {len(new_df) - len(df)} new links added.")
                                if new_df['is_duplicate'].any():
                                    st.warning("⚠️ Some URLs are duplicates. Review in the exported Excel file.")
                                st.balloons()
                            else:
                                st.error("❌ Failed to save bookmarks to Google Drive.")
                        else:
                            st.success(f"✅ Bookmarks imported successfully! {len(new_df) - len(df)} new links added.")
                            if new_df['is_duplicate'].any():
                                st.warning("⚠️ Some URLs are duplicates. Review in the exported Excel file.")
                            st.balloons()
                        return new_df
                    except Exception as e:
                        st.error(f"❌ Failed to process bookmark file: {str(e)}")
                    finally:
                        progress_bar.empty()
                else:
                    st.error("❌ Please upload a bookmark file.")
    
    return df

def browse_section(df, excel_file, mode):
    """Section to browse, search, and delete links"""
    st.markdown("<h3>Browse Links</h3>", unsafe_allow_html=True)
    
    # Search and filter
    search_query = st.text_input("Search Links", placeholder="Enter keywords or tags...")
    
    # Handle tag filtering safely
    tag_options = []
    if not df.empty and 'tags' in df.columns:
        tag_options = sorted(set(tag for tags in df['tags'] if isinstance(tags, list) for tag in tags))
    tag_filter = st.multiselect("Filter by Tags", options=tag_options)
    
    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[
            filtered_df['title'].str.contains(search_query, case=False, na=False) |
            filtered_df['description'].str.contains(search_query, case=False, na=False) |
            filtered_df['url'].str.contains(search_query, case=False, na=False) |
            filtered_df['tags'].apply(lambda tags: any(search_query.lower() in tag.lower() for tag in tags) if isinstance(tags, list) else False)
        ]
    if tag_filter:
        filtered_df = filtered_df[filtered_df['tags'].apply(lambda tags: any(tag in tags for tag in tag_filter) if isinstance(tags, list) else False)]
    
    # Sort by priority and number
    priority_order = {'Important': 0, 'High': 1, 'Medium': 2, 'Low': 3}
    if not filtered_df.empty:
        filtered_df['priority_order'] = filtered_df['priority'].map(priority_order)
        filtered_df = filtered_df.sort_values(by=['priority_order', 'number']).drop(columns=['priority_order'])
    
    # View All Links as Data Table
    if not filtered_df.empty:
        st.markdown("<h4>View All Links as Data Table</h4>", unsafe_allow_html=True)
        display_df = filtered_df[['url', 'title', 'description', 'tags', 'priority', 'number', 'is_duplicate']]
        display_df['tags'] = display_df['tags'].apply(lambda x: ", ".join(x) if isinstance(x, list) else '')
        st.dataframe(display_df, use_container_width=True)
    
    # Display links as cards
    if not filtered_df.empty:
        st.markdown("<h4>Links</h4>", unsafe_allow_html=True)
        for _, row in filtered_df.iterrows():
            with st.expander(f"{row['title'] or row['url']} ({row['priority']}, Number: {row['number']})"):
                st.markdown(f"""
                <div class='card'>
                    <p><strong>URL:</strong> <a href='{row['url']}' target='_blank'>{row['url']}</a></p>
                    <p><strong>Title:</strong> {row['title']}</p>
                    <p><strong>Description:</strong> {row['description']}</p>
                    <p><strong>Tags:</strong> {" ".join(f"<span class='tag'>{tag}</span>" for tag in row['tags'] if isinstance(row['tags'], list))}</p>
                    <p><strong>Priority:</strong> <span class='priority-{row['priority'].lower()}'>{row['priority']}</span></p>
                    <p><strong>Number:</strong> {row['number']}</p>
                    <p><strong>Created:</strong> {row['created_at']}</p>
                    <p><strong>Updated:</strong> {row['updated_at']}</p>
                    {"<p class='duplicate-warning'>⚠️ Duplicate URL</p>" if row['is_duplicate'] else ""}
                </div>
                """, unsafe_allow_html=True)
    
    # Delete functionality
    if not filtered_df.empty:
        selected_numbers = st.multiselect("Select Links to Delete (by Number)", options=filtered_df['number'].tolist())
        if st.button("Delete Selected Links", key="delete_button"):
            if selected_numbers:
                selected_link_ids = filtered_df[filtered_df['number'].isin(selected_numbers)]['link_id'].tolist()
                updated_df = delete_selected_links(df, selected_link_ids, excel_file, mode)
                if mode == "public":
                    st.session_state['user_df'] = updated_df
                else:
                    st.session_state['df'] = updated_df
                st.success("✅ Selected links deleted successfully!")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Please select at least one link to delete.")
    
    if filtered_df.empty:
        st.info("No links match the search criteria.")

def download_section(df, excel_file, mode):
    """Section to download links as Excel"""
    st.markdown("<h3>Export Data</h3>", unsafe_allow_html=True)
    
    if mode == "public":
        df_to_export = st.session_state.get('user_df', pd.DataFrame())
    else:
        df_to_export = df
    
    if not df_to_export.empty:
        output = pd.DataFrame()
        output['sequence_number'] = range(1, len(df_to_export) + 1)
        output['url'] = df_to_export['url']
        output['title'] = df_to_export['title']
        output['description'] = df_to_export['description']
        output['tags'] = df_to_export['tags'].apply(lambda x: ", ".join(x) if isinstance(x, list) else '')
        output['priority'] = df_to_export['priority']
        output['number'] = df_to_export['number']
        output['created_at'] = df_to_export['created_at']
        output['updated_at'] = df_to_export['updated_at']
        output['is_duplicate'] = df_to_export['is_duplicate']
        
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            output.to_excel(writer, index=False)
        buffer.seek(0)
        
        st.download_button(
            label="Download Links as Excel",
            data=buffer.getvalue(),
            file_name="links.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No links available to export.")