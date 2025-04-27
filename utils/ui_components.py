import streamlit as st
import pandas as pd
from datetime import datetime
from utils.link_operations import save_link, delete_selected_links, fetch_metadata, process_bookmark_file
import logging

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
    """Section to add new links or upload bookmark files"""
    st.markdown("<h3>Add New Link or Upload Bookmarks</h3>", unsafe_allow_html=True)
    
    with st.form(key="add_link_form"):
        st.markdown("<h4>Manual Link Entry</h4>", unsafe_allow_html=True)
        url = st.text_input("URL", placeholder="https://example.com")
        title = st.text_input("Title (optional)")
        description = st.text_area("Description (optional)")
        tags = st.text_input("Tags (comma-separated, optional)")
        priority = st.selectbox("Priority", ["Low", "Medium", "High", "Important"], index=0)
        
        if url:
            if st.form_submit_button("Fetch Metadata"):
                try:
                    metadata = fetch_metadata(url)
                    if metadata.get('title') and not title:
                        title = metadata['title']
                        st.session_state['fetched_title'] = title
                    if metadata.get('description') and not description:
                        description = metadata['description']
                        st.session_state['fetched_description'] = description
                    if metadata.get('tags') and not tags:
                        tags = ", ".join(metadata['tags'])
                        st.session_state['fetched_tags'] = tags
                    st.success("✅ Metadata fetched!")
                except Exception as e:
                    st.error(f"Failed to fetch metadata: {str(e)}")
        
        st.markdown("<h4>Upload Browser Bookmarks</h4>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Upload Bookmarks (Excel, CSV, HTML)", type=["xlsx", "csv", "html"])
        
        submit_button = st.form_submit_button("Save Link(s)")
        
        if submit_button:
            if url:
                # Save manual link
                tags_list = [tag.strip() for tag in tags.split(",")] if tags else []
                new_df = save_link(df, url, title, description, tags_list, priority, mode)
                if mode in ["admin", "guest"] and excel_file:
                    if save_data(new_df, excel_file):
                        st.success("✅ Link saved successfully!")
                        st.balloons()
                    else:
                        st.error("❌ Failed to save link to Google Drive.")
                else:
                    st.success("✅ Link saved successfully!")
                    st.balloons()
                return new_df
            elif uploaded_file:
                # Process uploaded bookmark file
                try:
                    new_df = process_bookmark_file(df, uploaded_file, mode)
                    if mode in ["admin", "guest"] and excel_file:
                        if save_data(new_df, excel_file):
                            st.success("✅ Bookmarks imported and categorized successfully!")
                            st.balloons()
                        else:
                            st.error("❌ Failed to save bookmarks to Google Drive.")
                    else:
                        st.success("✅ Bookmarks imported and categorized successfully!")
                        st.balloons()
                    return new_df
                except Exception as e:
                    st.error(f"❌ Failed to process bookmark file: {str(e)}")
                    return df
            else:
                st.error("❌ Please provide a URL or upload a bookmark file.")
    
    return df

def browse_section(df, excel_file, mode):
    """Section to browse, search, and delete links"""
    st.markdown("<h3>Browse Links</h3>", unsafe_allow_html=True)
    
    # Search and filter
    search_query = st.text_input("Search Links", placeholder="Enter keywords or tags...")
    tag_filter = st.multiselect("Filter by Tags", options=sorted(set(tag for tags in df['tags'] for tag in tags if tags)))
    
    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[
            filtered_df['title'].str.contains(search_query, case=False, na=False) |
            filtered_df['description'].str.contains(search_query, case=False, na=False) |
            filtered_df['url'].str.contains(search_query, case=False, na=False) |
            filtered_df['tags'].apply(lambda tags: any(search_query.lower() in tag.lower() for tag in tags))
        ]
    if tag_filter:
        filtered_df = filtered_df[filtered_df['tags'].apply(lambda tags: any(tag in tags for tag in tag_filter))]
    
    # Sort by priority
    priority_order = {'Important': 0, 'High': 1, 'Medium': 2, 'Low': 3}
    if not filtered_df.empty:
        filtered_df['priority_order'] = filtered_df['priority'].map(priority_order)
        filtered_df = filtered_df.sort_values(by='priority_order').drop(columns=['priority_order'])
    
    # Display table
    if not filtered_df.empty:
        st.markdown("<h4>Links</h4>", unsafe_allow_html=True)
        for _, row in filtered_df.iterrows():
            with st.expander(f"{row['title'] or row['url']} ({row['priority']})"):
                st.markdown(f"""
                <div class='card'>
                    <p><strong>URL:</strong> <a href='{row['url']}' target='_blank'>{row['url']}</a></p>
                    <p><strong>Title:</strong> {row['title']}</p>
                    <p><strong>Description:</strong> {row['description']}</p>
                    <p><strong>Tags:</strong> {" ".join(f"<span class='tag'>{tag}</span>" for tag in row['tags'])}</p>
                    <p><strong>Priority:</strong> <span class='priority-{row['priority'].lower()}'>{row['priority']}</span></p>
                    <p><strong>Created:</strong> {row['created_at']}</p>
                    <p><strong>Updated:</strong> {row['updated_at']}</p>
                </div>
                """, unsafe_allow_html=True)
    
    # Delete functionality
    if not filtered_df.empty:
        selected_ids = st.multiselect("Select Links to Delete (by ID)", options=filtered_df['id'].tolist())
        if st.button("Delete Selected Links", key="delete_button"):
            if selected_ids:
                updated_df = delete_selected_links(df, selected_ids, excel_file, mode)
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
        output['id'] = df_to_export['id']
        output['url'] = df_to_export['url']
        output['title'] = df_to_export['title']
        output['description'] = df_to_export['description']
        output['tags'] = df_to_export['tags'].apply(lambda x: ", ".join(x))
        output['priority'] = df_to_export['priority']
        output['created_at'] = df_to_export['created_at']
        output['updated_at'] = df_to_export['updated_at']
        
        buffer = pd.ExcelWriter('links.xlsx', engine='openpyxl')
        output.to_excel(buffer, index=False)
        buffer.close()
        
        st.download_button(
            label="Download Links as Excel",
            data=buffer.engine.buffer.getvalue(),
            file_name="links.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No links available to export.")