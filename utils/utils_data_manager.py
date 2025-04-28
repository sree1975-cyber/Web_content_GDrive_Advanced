import pandas as pd
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.http import MediaIoBaseDownload
from io import BytesIO
import streamlit as st
import json

def init_data(mode, username=None):
    """
    Initialize or load Excel file from Google Drive based on mode.
    
    Args:
        mode (str): 'admin', 'guest', or 'public'
        username (str, optional): Username for guest mode
    
    Returns:
        tuple: (DataFrame, excel_file_name or None)
    """
    columns = [
        'link_id', 'url', 'title', 'description', 'tags', 
        'created_at', 'updated_at', 'priority', 'number', 'is_duplicate'
    ]
    
    if mode == "admin":
        excel_file = 'web_links.xlsx'
    elif mode == "guest":
        if not username:
            raise ValueError("Username required for guest mode")
        excel_file = f'guest_{username}.xlsx'
    else:
        return pd.DataFrame(columns=columns), None  # Public mode uses session state
    
    try:
        service = get_drive_service()
        file_id = find_file_in_drive(service, excel_file)
        
        if file_id:
            df = download_file_from_drive(service, file_id)
            if 'tags' in df.columns:
                df['tags'] = df['tags'].apply(lambda x: x.split(',') if isinstance(x, str) else [] if pd.isna(x) else x)
            if 'id' in df.columns:
                df = df.rename(columns={'id': 'link_id'})
            for col in columns:
                if col not in df.columns:
                    if col == 'is_duplicate':
                        df[col] = False
                    elif col == 'tags':
                        df[col] = [[] for _ in range(len(df))]
                    else:
                        df[col] = ''
            for col in ['title', 'url', 'description', 'priority', 'number']:
                if col in df.columns:
                    df[col] = df[col].astype(str).replace('nan', '')
            logging.info(f"Loaded {excel_file} from Google Drive")
        else:
            df = pd.DataFrame(columns=columns)
            logging.info(f"Created new {excel_file}")
        return df, excel_file
    except Exception as e:
        st.error(f"Failed to initialize {excel_file}: {str(e)}")
        logging.error(f"Data initialization failed: {str(e)}")
        return pd.DataFrame(columns=columns), excel_file

def save_data(df, excel_file):
    """
    Save DataFrame to Google Drive.
    
    Args:
        df (DataFrame): DataFrame to save
        excel_file (str): Name of the Excel file
    
    Returns:
        bool: True if save successful, False otherwise
    """
    try:
        logging.debug(f"Saving DataFrame to {excel_file}: {df.to_dict()}")
        df_to_save = df.copy()
        if 'tags' in df_to_save.columns:
            df_to_save['tags'] = df_to_save['tags'].apply(lambda x: ','.join(map(str, x)) if isinstance(x, list) else '')
        
        output = BytesIO()
        df_to_save.to_excel(output, index=False, engine='openpyxl')
        output.seek(0)
        
        service = get_drive_service()
        file_id = find_file_in_drive(service, excel_file)
        
        folder_id = st.secrets["GOOGLE_DRIVE_FOLDER_ID"]
        
        if file_id:
            media = MediaIoBaseUpload(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
            logging.info(f"Updated {excel_file} in Google Drive")
        else:
            file_metadata = {
                'name': excel_file,
                'parents': [folder_id],
                'mimeType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
            media = MediaIoBaseUpload(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            service.files().create(
                body=file_metadata,
                media_body=media
            ).execute()
            logging.info(f"Created {excel_file} in Google Drive")
        
        return True
    except Exception as e:
        st.error(f"Error saving data to Google Drive: {str(e)}")
        logging.error(f"Data save failed: {str(e)}")
        return False

def get_drive_service():
    """
    Create Google Drive API service using service account credentials.
    
    Returns:
        Google Drive API service object
    """
    try:
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(st.secrets["GOOGLE_DRIVE_CREDENTIALS"]),
            scopes=['https://www.googleapis.com/auth/drive']
        )
        return build('drive', 'v3', credentials=credentials)
    except Exception as e:
        st.error(f"Failed to initialize Google Drive service: {str(e)}")
        logging.error(f"Drive service initialization failed: {str(e)}")
        raise

def find_file_in_drive(service, file_name):
    """
    Find file in Google Drive by name.
    
    Args:
        service: Google Drive API service
        file_name (str): Name of the file to find
    
    Returns:
        str: File ID if found, None otherwise
    """
    try:
        folder_id = st.secrets["GOOGLE_DRIVE_FOLDER_ID"]
        query = f"name='{file_name}' and '{folder_id}' in parents and trashed=false"
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id)'
        ).execute()
        files = results.get('files', [])
        return files[0]['id'] if files else None
    except Exception as e:
        st.error(f"Error finding file in Google Drive: {str(e)}")
        logging.error(f"Find file failed: {str(e)}")
        return None

def download_file_from_drive(service, file_id):
    """
    Download file from Google Drive and load as DataFrame.
    
    Args:
        service: Google Drive API service
        file_id (str): ID of the file to download
    
    Returns:
        DataFrame: Loaded DataFrame
    """
    try:
        request = service.files().get_media(fileId=file_id)
        output = BytesIO()
        downloader = MediaIoBaseDownload(output, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        output.seek(0)
        return pd.read_excel(output, engine='openpyxl')
    except Exception as e:
        st.error(f"Error downloading file from Google Drive: {str(e)}")
        logging.error(f"Download file failed: {str(e)}")
        raise