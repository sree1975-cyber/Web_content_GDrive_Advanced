import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import uuid
from transformers import pipeline  # Added for BERT classifier
import re

def fetch_metadata(url):
    """Fetch metadata for a given URL"""
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = soup.find('title').text if soup.find('title') else ''
        description = ''
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            description = meta_desc['content']
        
        return {
            'title': title,
            'description': description
        }
    except Exception as e:
        logging.error(f"Metadata fetch failed for {url}: {str(e)}")
        return {}

def save_link(df, url, title, description, tags, priority, number, mode):
    """Save a new link to the DataFrame"""
    try:
        new_id = str(uuid.uuid4())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_duplicate = url in df['url'].values if not df.empty else False
        
        # Convert tags list to single string for consistency
        tags_str = tags[0] if tags and isinstance(tags, list) else tags if isinstance(tags, str) else ''
        
        new_row = pd.DataFrame([{
            'link_id': new_id,
            'url': url,
            'title': title or '',
            'description': description or '',
            'tags': tags_str,
            'created_at': now,
            'updated_at': now,
            'priority': priority,
            'number': number,
            'is_duplicate': is_duplicate
        }])
        
        if df.empty:
            return new_row
        return pd.concat([df, new_row], ignore_index=True)
    except Exception as e:
        st.error(f"Error saving link: {str(e)}")
        logging.error(f"Save link failed: {str(e)}")
        return df

def delete_selected_links(df, selected_ids, excel_file, mode):
    """Delete selected links from the DataFrame"""
    try:
        updated_df = df[~df['link_id'].isin(selected_ids)].reset_index(drop=True)
        if mode in ["admin", "guest"] and excel_file:
            from utils.data_manager import save_data
            save_data(updated_df, excel_file)
        return updated_df
    except Exception as e:
        st.error(f"Error deleting links: {str(e)}")
        logging.error(f"Delete links failed: {str(e)}")
        return df

def predict_tag(text, url):
    """Predict a single tag for a URL using BERT classifier or fallback rules"""
    categories = ['News', 'Shopping', 'Research', 'Entertainment', 'Other']
    
    try:
        # Initialize BERT classifier (zero-shot for simplicity)
        classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
        result = classifier(text, candidate_labels=categories, multi_label=False)
        return result['labels'][0]  # Return the top predicted tag
    except Exception as e:
        logging.error(f"BERT tag prediction failed: {str(e)}")
        # Fallback: Rule-based tagging
        text_lower = text.lower()
        url_lower = url.lower()
        
        # Simple keyword-based rules
        if any(keyword in text_lower or keyword in url_lower for keyword in ['news', 'article', 'report', 'cnn', 'bbc']):
            return 'News'
        elif any(keyword in text_lower or keyword in url_lower for keyword in ['shop', 'store', 'buy', 'amazon', 'ebay']):
            return 'Shopping'
        elif any(keyword in text_lower or keyword in url_lower for keyword in ['research', 'study', 'paper', 'academic', 'edu']):
            return 'Research'
        elif any(keyword in text_lower or keyword in url_lower for keyword in ['entertainment', 'movie', 'music', 'youtube', 'netflix']):
            return 'Entertainment'
        else:
            return 'Other'

def process_bookmark_file(df, uploaded_file, mode, duplicate_action, progress_bar):
    """Process uploaded bookmark file (Excel, CSV, HTML) and categorize URLs"""
    try:
        file_type = uploaded_file.name.split('.')[-1].lower()
        links = []
        
        if file_type in ['xlsx', 'csv']:
            if file_type == 'xlsx':
                bookmark_df = pd.read_excel(uploaded_file, engine='openpyxl')
            else:
                bookmark_df = pd.read_csv(uploaded_file)
            
            for idx, row in bookmark_df.iterrows():
                url = row.get('URL') or row.get('url') or ''
                if not url:
                    continue
                title = row.get('Title') or row.get('title') or ''
                description = row.get('Description') or row.get('description') or ''
                number = row.get('Number') or row.get('number') or idx + 1
                links.append({
                    'url': url,
                    'title': title,
                    'description': description,
                    'priority': 'Low',
                    'number': number
                })
        
        elif file_type == 'html':
            soup = BeautifulSoup(uploaded_file, 'html.parser')
            for idx, a_tag in enumerate(soup.find_all('a'), 1):
                url = a_tag.get('href', '')
                if not url:
                    continue
                title = a_tag.text.strip() or ''
                links.append({
                    'url': url,
                    'title': title,
                    'description': '',
                    'priority': 'Low',
                    'number': idx
                })
        
        else:
            raise ValueError("Unsupported file format. Use Excel, CSV, or HTML.")
        
        if not links:
            raise ValueError("No valid URLs found in the uploaded file.")
        
        existing_urls = set(df['url'].values) if not df.empty else set()
        processed_links = []
        total_links = len(links)
        
        for i, link in enumerate(links):
            metadata = fetch_metadata(link['url'])
            if metadata.get('title') and not link['title']:
                link['title'] = metadata['title']
            if metadata.get('description') and not link['description']:
                link['description'] = metadata['description']
            link['is_duplicate'] = link['url'] in existing_urls
            if link['is_duplicate'] and duplicate_action == "Skip Duplicates":
                continue
            # Predict tag using BERT or fallback
            text = f"{link['title']} {link['description']}"
            link['tags'] = predict_tag(text, link['url'])
            processed_links.append(link)
            existing_urls.add(link['url'])
            progress_bar.progress((i + 1) / total_links)
        
        if not processed_links:
            raise ValueError("No new URLs to process after duplicate handling.")
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_rows = pd.DataFrame([
            {
                'link_id': str(uuid.uuid4()),
                'url': link['url'],
                'title': link['title'],
                'description': link['description'],
                'tags': link['tags'],  # Single tag as string
                'created_at': now,
                'updated_at': now,
                'priority': link['priority'],
                'number': link['number'],
                'is_duplicate': link['is_duplicate']
            } for link in processed_links
        ])
        
        if df.empty:
            return new_rows
        return pd.concat([df, new_rows], ignore_index=True)
    
    except Exception as e:
        st.error(f"Error processing bookmark file: {str(e)}")
        logging.error(f"Bookmark processing failed: {str(e)}")
        raise
