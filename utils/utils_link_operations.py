import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import uuid
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np

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
        
        keywords = []
        if title:
            keywords.extend(title.lower().split())
        if description:
            keywords.extend(description.lower().split())
        tags = list(set([kw for kw in keywords if len(kw) > 3 and kw.isalpha()][:5]))
        
        return {
            'title': title,
            'description': description,
            'tags': tags
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
        
        new_row = pd.DataFrame([{
            'link_id': new_id,
            'url': url,
            'title': title or '',
            'description': description or '',
            'tags': tags,
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
                tags = row.get('Tags') or row.get('tags') or ''
                tags_list = [tag.strip() for tag in tags.split(',')] if isinstance(tags, str) else []
                number = row.get('Number') or row.get('number') or idx + 1
                links.append({
                    'url': url,
                    'title': title,
                    'description': description,
                    'tags': tags_list,
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
                tags = a_tag.get('tags', '').split(',') or []
                links.append({
                    'url': url,
                    'title': title,
                    'description': '',
                    'tags': tags,
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
            link['tags'].extend(metadata.get('tags', []))
            link['tags'] = list(set(link['tags']))
            link['is_duplicate'] = link['url'] in existing_urls
            if link['is_duplicate'] and duplicate_action == "Skip Duplicates":
                continue
            processed_links.append(link)
            existing_urls.add(link['url'])
            progress_bar.progress((i + 1) / total_links)
        
        if not processed_links:
            raise ValueError("No new URLs to process after duplicate handling.")
        
        texts = [f"{link['title']} {link['description']} {' '.join(link['tags'])}" for link in processed_links]
        vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        X = vectorizer.fit_transform(texts)
        kmeans = KMeans(n_clusters=min(5, len(processed_links)), random_state=42)
        labels = kmeans.fit_predict(X)
        
        categories = ['News', 'Shopping', 'Research', 'Entertainment', 'Other']
        for i, link in enumerate(processed_links):
            cluster = labels[i]
            link['tags'].append(categories[cluster % len(categories)])
            link['tags'] = list(set(link['tags']))
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_rows = pd.DataFrame([
            {
                'link_id': str(uuid.uuid4()),
                'url': link['url'],
                'title': link['title'],
                'description': link['description'],
                'tags': link['tags'],
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