import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import logging
import os

def get_drive_service():
    """Initialize Google Drive API service"""
    try:
        if "gdrive" not in st.secrets:
            logging.error("No 'gdrive' section found in secrets.toml")
            st.error("❌ Google Drive configuration is missing. Add [gdrive] section to secrets.toml in Streamlit Cloud settings with service account credentials and folder_id.")
            return None
        
        creds_dict = st.secrets["gdrive"]
        logging.debug(f"Loaded gdrive secrets: keys={list(creds_dict.keys())}")
        
        required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id", "auth_uri", "token_uri", "auth_provider_x509_cert_url", "client_x509_cert_url", "folder_id"]
        missing_keys = [key for key in required_keys if key not in creds_dict]
        if missing_keys:
            logging.error(f"Missing keys in gdrive secrets: {missing_keys}")
            st.error(f"❌ Incomplete Google Drive configuration. Missing keys: {missing_keys}. Update secrets.toml in Streamlit Cloud settings.")
            return None
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            creds_dict, 
            scopes=[
                'https://www.googleapis.com/auth/drive',
                'https://spreadsheets.google.com/feeds'
            ]
        )
        drive_service = build('drive', 'v3', credentials=creds)
        logging.debug("Google Drive service initialized successfully")
        return drive_service
    except Exception as e:
        logging.error(f"Failed to initialize Google Drive service: {str(e)}")
        st.error(f"❌ Failed to initialize Google Drive: {str(e)}. Check service account credentials in secrets.toml.")
        return None

def get_file_id(drive_service, file_name, folder_id):
    """Get the file ID of an Excel file in Google Drive"""
    if not drive_service:
        logging.error("No drive service available")
        return None
    try:
        query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        if files:
            file_id = files[0]['id']
            logging.debug(f"Found file {file_name} with ID {file_id}")
            return file_id
        logging.debug(f"No file found with name {file_name}")
        return None
    except Exception as e:
        logging.error(f"Failed to get file ID for {file_name}: {str(e)}")
        return None

def load_data(file_name, folder_id):
    """Load data from an Excel file in Google Drive"""
    drive_service = get_drive_service()
    if not drive_service:
        logging.error(f"Cannot load data for {file_name}: No drive service")
        return None
    
    file_id = get_file_id(drive_service, file_name, folder_id)
    if not file_id:
        logging.debug(f"No existing file {file_name}, returning empty DataFrame")
        return None
    
    try:
        request = drive_service.files().get_media(fileId=file_id)
        file_path = f"/tmp/{file_name}"
        with open(file_path, 'wb') as f:
            f.write(request.execute())
        
        df = pd.read_excel(file_path)
        
        if 'tags' in df.columns:
            df['tags'] = df['tags'].apply(lambda x: x.split(',') if isinstance(x, str) else x)
        
        os.remove(file_path)
        logging.debug(f"Loaded data from {file_name}: {len(df)} rows")
        return df
    except Exception as e:
        logging.error(f"Failed to load data from {file_name}: {str(e)}")
        return None

def save_data(df, file_name):
    """Save DataFrame to an Excel file in Google Drive"""
    drive_service = get_drive_service()
    if not drive_service:
        logging.error(f"Cannot save data to {file_name}: No drive service")
        return False
    
    try:
        temp_file = f"/tmp/{file_name}"
        output_df = df.copy()
        if 'tags' in output_df.columns:
            output_df['tags'] = output_df['tags'].apply(lambda x: ','.join(x) if isinstance(x, list) else x)
        output_df.to_excel(temp_file, index=False)
        
        folder_id = st.secrets["gdrive"].get("folder_id", "")
        if not folder_id:
            logging.error("Missing folder_id in gdrive secrets")
            st.error("❌ Missing folder_id in Google Drive configuration. Update secrets.toml.")
            return False
        
        file_id = get_file_id(drive_service, file_name, folder_id)
        
        media = MediaFileUpload(temp_file, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        if file_id:
            drive_service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
            logging.debug(f"Updated file {file_name} with ID {file_id}")
        else:
            file_metadata = {
                'name': file_name,
                'parents': [folder_id],
                'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
            file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            file_id = file.get('id')
            logging.debug(f"Created new file {file_name} with ID {file_id}")
        
        os.remove(temp_file)
        logging.debug(f"Successfully saved {file_name} to Google Drive")
        return True
    except Exception as e:
        logging.error(f"Failed to save data to {file_name}: {str(e)}")
        return False
