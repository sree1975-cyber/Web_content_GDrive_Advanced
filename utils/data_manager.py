import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from oauth2client.service_account import ServiceAccountCredentials
import io
import logging
import os
import json
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment

def get_drive_service():
    """Initialize Google Drive API service"""
    try:
        credentials_data = st.secrets.get("GOOGLE_DRIVE_CREDENTIALS")
        logging.debug(f"Secrets keys available: {list(st.secrets.keys())}")
        if not credentials_data:
            logging.error("GOOGLE_DRIVE_CREDENTIALS not found in secrets")
            st.error("❌ GOOGLE_DRIVE_CREDENTIALS not found. Check Streamlit Cloud secrets.")
            return None
        
        # Handle string-based secrets (e.g., JSON string)
        if isinstance(credentials_data, str):
            try:
                credentials_data = json.loads(credentials_data)
            except json.JSONDecodeError as e:
                logging.error(f"GOOGLE_DRIVE_CREDENTIALS is a string but not valid JSON: {str(e)}")
                st.error(f"❌ Invalid GOOGLE_DRIVE_CREDENTIALS format: {str(e)}")
                return None
        
        # Ensure credentials_data is a dictionary
        if not isinstance(credentials_data, dict):
            logging.error(f"GOOGLE_DRIVE_CREDENTIALS must be a dictionary, got {type(credentials_data)}")
            st.error(f"❌ GOOGLE_DRIVE_CREDENTIALS must be a dictionary, got {type(credentials_data)}")
            return None
        
        # Validate required keys
        required_keys = ["type", "project_id", "private_key", "client_email", "client_id"]
        missing_keys = [key for key in required_keys if key not in credentials_data]
        if missing_keys:
            logging.error(f"Missing keys in GOOGLE_DRIVE_CREDENTIALS: {missing_keys}")
            st.error(f"❌ Missing keys in GOOGLE_DRIVE_CREDENTIALS: {missing_keys}")
            return None
        
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            credentials_data,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        logging.debug("Google Drive service initialized successfully")
        return build("drive", "v3", credentials=credentials)
    except Exception as e:
        logging.error(f"Failed to initialize Drive service: {str(e)}")
        st.error(f"❌ Failed to initialize Google Drive: {str(e)}")
        return None

def load_data(excel_file, folder_id):
    """Load data from Google Drive or fallback to session state"""
    try:
        drive_service = get_drive_service()
        if not drive_service:
            logging.warning(f"Drive service unavailable for {excel_file}, checking session state")
            return st.session_state.get("local_df", pd.DataFrame(columns=[
                "link_id", "url", "title", "description", "tags",
                "created_at", "updated_at", "priority", "number", "is_duplicate"
            ]))
        
        if not folder_id:
            logging.error("GOOGLE_DRIVE_FOLDER_ID not found in secrets")
            st.error("❌ GOOGLE_DRIVE_FOLDER_ID not found. Check Streamlit Cloud secrets.")
            return st.session_state.get("local_df", pd.DataFrame(columns=[
                "link_id", "url", "title", "description", "tags",
                "created_at", "updated_at", "priority", "number", "is_duplicate"
            ]))
        
        query = f"name='{excel_file}' and '{folder_id}' in parents and trashed=false"
        response = drive_service.files().list(q=query, fields="files(id, name)").execute()
        files = response.get("files", [])
        
        if not files:
            logging.info(f"No file named {excel_file} found in Drive folder")
            return st.session_state.get("local_df", pd.DataFrame(columns=[
                "link_id", "url", "title", "description", "tags",
                "created_at", "updated_at", "priority", "number", "is_duplicate"
            ]))
        
        file_id = files[0]["id"]
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        fh.seek(0)
        df = pd.read_excel(fh, engine="openpyxl")
        st.session_state["local_df"] = df  # Cache in session state
        logging.debug(f"Loaded {excel_file} from Google Drive: {len(df)} rows")
        return df
    except Exception as e:
        logging.error(f"Failed to load data from Drive for {excel_file}: {str(e)}")
        st.error(f"❌ Failed to load {excel_file} from Google Drive. Using local storage.")
        return st.session_state.get("local_df", pd.DataFrame(columns=[
            "link_id", "url", "title", "description", "tags",
            "created_at", "updated_at", "priority", "number", "is_duplicate"
        ]))

def save_data(df, excel_file, folder_id):
    """Save DataFrame to Google Drive and session state with link_id and hyperlinked URLs"""
    try:
        drive_service = get_drive_service()
        st.session_state["local_df"] = df  # Always save to session state
        
        # Ensure all required columns are present
        required_columns = [
            "link_id", "url", "title", "description", "tags",
            "created_at", "updated_at", "priority", "number", "is_duplicate"
        ]
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
        
        # Create output DataFrame with desired column order
        output_df = df[required_columns].copy()
        
        if not drive_service:
            logging.error(f"Drive service unavailable for {excel_file}, saved to session state only")
            st.warning(f"⚠️ Saved locally but could not save {excel_file} to Google Drive.")
            return True
        
        if not folder_id:
            logging.error("GOOGLE_DRIVE_FOLDER_ID not found in secrets")
            st.error(f"❌ GOOGLE_DRIVE_FOLDER_ID not found for {excel_file}. Check Streamlit Cloud secrets.")
            return True
        
        query = f"name='{excel_file}' and '{folder_id}' in parents and trashed=false"
        response = drive_service.files().list(q=query, fields="files(id, name)").execute()
        files = response.get("files", [])
        
        # Save DataFrame to temporary file with hyperlinks
        temp_file = f"temp_{excel_file}"
        with pd.ExcelWriter(temp_file, engine="openpyxl") as writer:
            output_df.to_excel(writer, index=False, sheet_name="Links")
            workbook = writer.book
            worksheet = writer.sheets["Links"]
            
            # Add hyperlinks to URL column (column B, since link_id is column A)
            for idx, url in enumerate(output_df["url"], start=2):
                worksheet[f"B{idx}"].hyperlink = url
                worksheet[f"B{idx}"].style = "Hyperlink"
        
        file_metadata = {
            "name": excel_file,
            "parents": [folder_id]
        }
        
        media = MediaFileUpload(temp_file, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        if files:
            # Update existing file
            file_id = files[0]["id"]
            drive_service.files().update(fileId=file_id, media_body=media).execute()
            logging.debug(f"Updated {excel_file} in Google Drive, file_id={file_id}")
        else:
            # Create new file
            file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
            logging.debug(f"Created new {excel_file} in Google Drive, file_id={file.get('id')}")
        
        os.remove(temp_file)
        logging.debug(f"Successfully saved {excel_file} to Google Drive")
        return True
    except Exception as e:
        logging.error(f"Failed to save data to Drive for {excel_file}: {str(e)}")
        st.error(f"❌ Failed to save {excel_file} to Google Drive. Saved locally.")
        return True
