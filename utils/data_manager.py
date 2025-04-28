import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from oauth2client.service_account import ServiceAccountCredentials
import io
import logging
import os
import json

def get_drive_service():
    """Initialize Google Drive API service"""
    try:
        credentials_data = st.secrets.get("GOOGLE_DRIVE_CREDENTIALS")
        if not credentials_data:
            raise ValueError("GOOGLE_DRIVE_CREDENTIALS not found in secrets")
        
        # Handle string-based secrets (e.g., JSON string)
        if isinstance(credentials_data, str):
            try:
                credentials_data = json.loads(credentials_data)
            except json.JSONDecodeError as e:
                raise ValueError(f"GOOGLE_DRIVE_CREDENTIALS is a string but not valid JSON: {str(e)}")
        
        # Ensure credentials_data is a dictionary
        if not isinstance(credentials_data, dict):
            raise ValueError(f"GOOGLE_DRIVE_CREDENTIALS must be a dictionary, got {type(credentials_data)}")

        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            credentials_data,
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build("drive", "v3", credentials=credentials)
    except Exception as e:
        logging.error(f"Failed to initialize Drive service: {str(e)}")
        return None

def load_data(excel_file):
    """Load data from Google Drive or fallback to session state"""
    try:
        drive_service = get_drive_service()
        if not drive_service:
            logging.warning("Drive service unavailable, checking session state")
            return st.session_state.get("local_df", pd.DataFrame(columns=[
                "link_id", "url", "title", "description", "tags",
                "created_at", "updated_at", "priority", "number", "is_duplicate"
            ]))
        
        folder_id = st.secrets.get("GOOGLE_DRIVE_FOLDER_ID")
        if not folder_id:
            raise ValueError("GOOGLE_DRIVE_FOLDER_ID not found in secrets")
        
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
        return df
    except Exception as e:
        logging.error(f"Failed to load data from Drive: {str(e)}")
        st.error("❌ Failed to load data from Google Drive. Using local storage.")
        return st.session_state.get("local_df", pd.DataFrame(columns=[
            "link_id", "url", "title", "description", "tags",
            "created_at", "updated_at", "priority", "number", "is_duplicate"
        ]))

def save_data(df, excel_file):
    """Save DataFrame to Google Drive and session state"""
    try:
        drive_service = get_drive_service()
        st.session_state["local_df"] = df  # Always save to session state
        
        if not drive_service:
            logging.error("Drive service unavailable, saved to session state only")
            st.warning("⚠️ Saved locally but could not save to Google Drive.")
            return True
        
        folder_id = st.secrets.get("GOOGLE_DRIVE_FOLDER_ID")
        if not folder_id:
            raise ValueError("GOOGLE_DRIVE_FOLDER_ID not found in secrets")
        
        query = f"name='{excel_file}' and '{folder_id}' in parents and trashed=false"
        response = drive_service.files().list(q=query, fields="files(id, name)").execute()
        files = response.get("files", [])
        
        # Save DataFrame to temporary file
        temp_file = "temp_links.xlsx"
        df.to_excel(temp_file, index=False, engine="openpyxl")
        
        file_metadata = {
            "name": excel_file,
            "parents": [folder_id]
        }
        
        media = MediaFileUpload(temp_file, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
        if files:
            # Update existing file
            file_id = files[0]["id"]
            drive_service.files().update(fileId=file_id, media_body=media).execute()
        else:
            # Create new file
            drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        
        os.remove(temp_file)
        return True
    except Exception as e:
        logging.error(f"Failed to save data to Drive: {str(e)}")
        st.error("❌ Failed to save data to Google Drive. Saved locally.")
        return True
