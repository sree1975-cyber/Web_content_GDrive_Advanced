import streamlit as st
import pandas as pd
from datetime import datetime
from utils.data_manager import save_data
from utils.link_operations import save_link, delete_selected_links, fetch_metadata, process_bookmark_file
import logging
from io import BytesIO
import time
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment

# CSS for responsive design and color schemes
st.markdown("""
<style>
/* Base styles */
.header-admin, .header-guest, .header-public {
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
}
.header-admin { background-color: #ADD8E6; } /* Light blue for admin */
.header-guest { background-color: #90EE90; } /* Light parrot green for guest */
.header-public { background-color: #D8BFD8; } /* Light purple for public */
.login-container {
    background-color: #FFB6C1; /* Light bluish-pink */
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
</style>
""", unsafe_allow_html=True)

def display_header(mode, username=None):
    """Display the app header with mode-specific styling and logout button"""
    header_class = f"header-{mode}"
    st.markdown(f"""
    <div class='{header_class}'>
        <h1 style='margin: 0;'>Web Content Manager</h1>
        <p style='margin: 0.5rem 0 0;'>Organize and manage your web links efficiently</p>
        <p style='margin: 0.5rem 0 0;'>{mode.capitalize()} Mode{f' ({username})' if username else ''}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚪 Logout", help="Log out and return to login screen"):
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("✅ Logged out successfully!")
        st.rerun()

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
                    st.session_state["mode"] = "admin"
                    st.success("✅ Logged in as Admin!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Incorrect Admin password. Please try again.")
            elif mode == "Guest":
                if password == "guest456" and username:
                    st.session_state["mode"] = "guest"
                    st.session_state["username"] = username
                    st.success(f"✅ Logged in as Guest ({username})!")
                    st.balloons()
                    st.rerun()
                elif not username:
                    st.error("❌ Username is required for Guest mode.")
                else:
                    st.error("❌ Incorrect Guest password. Please try again.")
        
        if public_button and mode == "Public":
            st.session_state["mode"] = "public"
            st.success("✅ Continuing as Public User!")
            st.balloons()
            st.rerun()

def add_link_section(df, excel_file, mode):
    """Section to add new links or upload bookmark files, split into two tabs"""
    st.markdown("<h3>Add New Link or Upload Bookmarks</h3>", unsafe_allow_html=True)
    
    if "fetched_metadata" not in st.session_state:
        st.session_state["fetched_metadata"] = {}
    
    tab1, tab2 = st.tabs(["Single URL", "Upload Bookmarks"])
    
    recommended_tags = [
        "News", "Shopping", "Research", "Entertainment", "Cloud", "Education", "Other"
    ]
    
    with tab1:
        with st.form(key="single_url_form", clear_on_submit=False):
            st.markdown("<h4>Add Single URL</h4>", unsafe_allow_html=True)
            
            url = st.text_input("URL", placeholder="https://example.com", key="url_input")
            fetch_button = st.form_submit_button(
                "Fetch Metadata",
                help="Fetch title and description from the URL"
            )
            
            title = st.text_input(
                "Title (optional)",
                value=st.session_state["fetched_metadata"].get("title", ""),
                key="title_input"
            )
            description = st.text_area(
                "Description (optional)",
                value=st.session_state["fetched_metadata"].get("description", ""),
                key="description_input"
            )
            tags = st.multiselect(
                "Tags (select or type custom tags)",
                options=recommended_tags,
                default=st.session_state["fetched_metadata"].get("tags", []),
                key="tags_input",
                help="Select or type tags (press Enter to add)"
            )
            custom_tag = st.text_input(
                "Add Custom Tag",
                placeholder="Type a new tag and press Enter",
                key="custom_tag_input"
            )
            if custom_tag and custom_tag not in tags:
                tags.append(custom_tag)
            
            priority = st.selectbox("Priority", ["Low", "Medium", "High", "Important"], index=0)
            number = st.number_input("Number (for grouping)", min_value=0, value=0, step=1)
            
            save_button = st.form_submit_button(
                "💾 Save Link",
                help="Save the link to your collection"
            )
            
            if fetch_button or (url and st.session_state.get("url_submitted")):
                if url:
                    with st.spinner("Fetching metadata..."):
                        metadata = fetch_metadata(url)
                        st.session_state["fetched_metadata"] = {
                            "title": metadata.get("title", ""),
                            "description": metadata.get("description", ""),
                            "tags": []
                        }
                        st.info("✅ Metadata fetched! Fields updated.")
                        st.session_state["url_submitted"] = False
                        st.rerun()
                else:
                    st.error("❌ Please provide a URL.")
            
            if save_button:
                if url:
                    new_df = save_link(df, url, title, description, tags, priority, number, mode)
                    if mode in ["admin", "guest"] and excel_file:
                        if save_data(new_df, excel_file):
                            st.success("✅ Link saved successfully!")
                            if new_df.iloc[-1]["is_duplicate"]:
                                st.warning("⚠️ This URL is a duplicate.")
                            st.balloons()
                            st.session_state["fetched_metadata"] = {}
                        else:
                            st.error("❌ Failed to save link to Google Drive.")
                    else:
                        st.success("✅ Link saved successfully!")
                        if new_df.iloc[-1]["is_duplicate"]:
                            st.warning("⚠️ This URL is a duplicate.")
                        st.balloons()
                        st.session_state["fetched_metadata"] = {}
                    return new_df
                else:
                    st.error("❌ Please provide a URL.")
    
    with tab2:
        with st.form(key="upload_bookmarks_form"):
            st.markdown("<h4>Upload Browser Bookmarks</h4>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader("Upload Bookmarks (Excel, CSV, HTML)", type=["xlsx", "csv", "html"])
            duplicate_action = st.selectbox("Handle Duplicates", ["Keep Both", "Skip Duplicates"], index=0)
            
            if st.form_submit_button("Import Bookmarks", help="Import bookmarks from file"):
                if uploaded_file:
                    try:
                        progress_bar = st.progress(0)
                        new_df = process_bookmark_file(df, uploaded_file, mode, duplicate_action, progress_bar)
                        if mode in ["admin", "guest"] and excel_file:
                            if save_data(new_df, excel_file):
                                st.success(f"✅ Bookmarks imported! {len(new_df) - len(df)} new links added.")
                                if new_df["is_duplicate"].any():
                                    st.warning("⚠️ Some URLs are duplicates.")
                                st.balloons()
                            else:
                                st.error("❌ Failed to save bookmarks to Google Drive.")
                        else:
                            st.success(f"✅ Bookmarks imported! {len(new_df) - len(df)} new links added.")
                            if new_df["is_duplicate"].any():
                                st.warning("⚠️ Some URLs are duplicates.")
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
            else:
                df[col] = ""
    
    search_query = st.text_input("Search Links", placeholder="Enter keywords or tags...")
    tag_options = sorted(set(df["tags"].dropna().astype(str))) if not df.empty and "tags" in df.columns else []
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
        filtered_df = filtered_df[filtered_df["tags"].isin(tag_filter)]
    
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
    
    if filtered_df.empty:
        st.info("No links match the search criteria.")

def download_section(df, excel_file, mode):
    """Section to download links as Excel with hyperlinked URLs"""
    st.markdown("<h3>Export Data</h3>", unsafe_allow_html=True)
    
    if mode == "public":
        df_to_export = st.session_state.get("user_df", pd.DataFrame())
    else:
        df_to_export = df
    
    if not df_to_export.empty:
        output = pd.DataFrame()
        output["sequence_number"] = range(1, len(df_to_export) + 1)
        output["url"] = df_to_export["url"]
        output["title"] = df_to_export["title"]
        output["description"] = df_to_export["description"]
        output["tags"] = df_to_export["tags"].astype(str)
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
            
            # Add hyperlinks to URL column
            for idx, url in enumerate(output["url"], start=2):
                worksheet[f"B{idx}"].hyperlink = url
                worksheet[f"B{idx}"].style = "Hyperlink"
            
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
    st.markdown("<h3>Analytics</h3>", unsafe_allow_html=True)
    
    if df.empty:
        st.info("No data available for analytics.")
        return
    
    # Most frequent URLs
    st.markdown("### Most Frequent URLs")
    url_counts = df["url"].value_counts().head(5)
    st.bar_chart(url_counts)
    
    # Most common tags
    st.markdown("### Most Common Tags")
    tag_counts = df["tags"].value_counts()
    st.bar_chart(tag_counts)
    
    # User activity trends
    st.markdown("### User Activity Trends")
    df["created_at"] = pd.to_datetime(df["created_at"])
    activity = df.groupby(df["created_at"].dt.date).size()
    st.line_chart(activity)
